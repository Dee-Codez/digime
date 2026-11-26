from digime.graph.entity import extract_emails, extract_topics
from digime.models import Memory

ME_MERGE = "MERGE (me:Me {id: 'me'})"

TYPE_LABELS = {
    "youtube": "Video",
    "gmail": "Email",
    "browser": "Browser",
}


def _topics(m: Memory):
    return extract_topics(m.title)


def _memory_node(m: Memory, embedding: list[float]) -> tuple[str, dict]:
    label = TYPE_LABELS.get(m.source, "Activity")
    cypher = (
        f"MERGE (n:{label}:Memory {{id: $id}}) "
        "SET n.source = $source, n.title = $title, n.text = $text, "
        "n.url = $url, n.ts = $ts, n.embedding = $embedding"
    )
    params = {
        "id": m.id(),
        "source": m.source,
        "title": m.title,
        "text": m.text,
        "url": m.url,
        "ts": m.ts,
        "embedding": embedding,
    }
    return cypher, params


def _node_ref(m: Memory) -> tuple[str, dict]:
    label = TYPE_LABELS.get(m.source, "Activity")
    return f"(n:{label} {{id: $id}})", {"id": m.id()}


def _about_topics(m: Memory) -> list[tuple[str, dict]]:
    ref, params = _node_ref(m)
    stmts = []
    for topic in _topics(m):
        stmts.append((
            f"MERGE (t:Topic {{name: $name}}) MERGE {ref} MERGE (n)-[:ABOUT]->(t)",
            {"name": topic, **params},
        ))
    return stmts


def _video_relationships(m: Memory) -> list[tuple[str, dict]]:
    ref, params = _node_ref(m)
    stmts = [(
        f"MERGE (me:Me {{id: 'me'}}) MERGE {ref} MERGE (me)-[:WATCHED {{ts: $ts}}]->(n)",
        {"ts": m.ts, **params},
    )]
    channel = (m.metadata.get("channel") or "").strip()
    if channel:
        stmts.append((
            f"MERGE (c:Channel {{name: $name}}) MERGE {ref} MERGE (n)-[:BY]->(c)",
            {"name": channel, **params},
        ))
    return stmts


def _activity_relationships(m: Memory) -> list[tuple[str, dict]]:
    ref, params = _node_ref(m)
    return [(
        f"MERGE (me:Me {{id: 'me'}}) MERGE {ref} MERGE (me)-[:SEARCHED {{ts: $ts}}]->(n)",
        {"ts": m.ts, **params},
    )]


def _email_relationships(m: Memory, me_email: str) -> list[tuple[str, dict]]:
    ref, params = _node_ref(m)
    stmts = []
    sender_emails = extract_emails(m.metadata.get("from", ""))
    recipient_emails = extract_emails(m.metadata.get("to", ""))
    me_email_l = me_email.lower() if me_email else None

    for email in sender_emails:
        if me_email_l and email == me_email_l:
            stmts.append((
                f"MERGE (me:Me {{id: 'me'}}) MERGE {ref} MERGE (me)-[:SENT {{ts: $ts}}]->(n)",
                {"ts": m.ts, **params},
            ))
        else:
            stmts.append((
                f"MERGE (p:Person {{email: $email}}) MERGE {ref} MERGE (p)-[:SENT {{ts: $ts}}]->(n)",
                {"email": email, "ts": m.ts, **params},
            ))

    for email in recipient_emails:
        if me_email_l and email == me_email_l:
            stmts.append((
                f"MERGE (me:Me {{id: 'me'}}) MERGE {ref} MERGE (me)-[:RECEIVED {{ts: $ts}}]->(n)",
                {"ts": m.ts, **params},
            ))
        else:
            stmts.append((
                f"MERGE (p:Person {{email: $email}}) MERGE {ref} MERGE (p)-[:RECEIVED {{ts: $ts}}]->(n)",
                {"email": email, "ts": m.ts, **params},
            ))

    people = [e for e in sender_emails | recipient_emails if not (me_email_l and e == me_email_l)]
    for a in people:
        for b in people:
            if a != b:
                stmts.append((
                    "MERGE (pa:Person {email: $a}) MERGE (pb:Person {email: $b}) "
                    "MERGE (pa)-[:CORRESPONDS_WITH]->(pb)",
                    {"a": a, "b": b},
                ))
    return stmts


def build_statements(memories: list[Memory], embedder, me_email: str = "") -> list[tuple[str, dict]]:
    statements = [(ME_MERGE, {})]
    if not memories:
        return statements

    embeddings = embedder.embed([m.text for m in memories])
    for m, emb in zip(memories, embeddings):
        statements.append(_memory_node(m, emb))
        if m.source == "youtube":
            statements.extend(_video_relationships(m))
        elif m.source == "gmail":
            statements.extend(_email_relationships(m, me_email))
        else:
            statements.extend(_activity_relationships(m))
        statements.extend(_about_topics(m))

    return statements
