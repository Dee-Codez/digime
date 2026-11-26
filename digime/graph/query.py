from digime.graph.graph import Graph

NAMED_QUERIES = {
    "contacts": (
        "MATCH (p:Person)-[r:SENT|RECEIVED]->(e:Email) "
        "RETURN p.email AS who, count(e) AS emails ORDER BY emails DESC LIMIT 10"
    ),
    "channels": (
        "MATCH (c:Channel)<-[:BY]-(v:Video) "
        "RETURN c.name AS channel, count(v) AS videos ORDER BY videos DESC LIMIT 10"
    ),
    "topics": (
        "MATCH (t:Topic) "
        "OPTIONAL MATCH (t)<-[:ABOUT]-() "
        "RETURN t.name AS topic, count(*) AS links ORDER BY links DESC LIMIT 20"
    ),
    "stats": (
        "MATCH (n) UNWIND labels(n) AS label "
        "RETURN label, count(*) AS count ORDER BY count DESC"
    ),
    "paths": (
        "MATCH p = shortestPath((me:Me {id:'me'})-[*..4]-(t:Topic {name: $name})) "
        "RETURN [x IN nodes(p) | coalesce(x.name, x.title, x.subject, x.email, x.id)] AS path"
    ),
}


def run_named(query: str, params: dict, graph: Graph) -> list[dict]:
    cypher = NAMED_QUERIES[query]
    records = graph.run(cypher, params)
    return [dict(r) for r in records]


def run_raw(cypher: str, graph: Graph) -> list[dict]:
    records = graph.run(cypher)
    return [dict(r) for r in records]
