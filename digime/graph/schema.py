CONSTRAINTS = [
    "CREATE CONSTRAINT person_email IF NOT EXISTS FOR (p:Person) REQUIRE p.email IS UNIQUE",
    "CREATE CONSTRAINT channel_name IF NOT EXISTS FOR (c:Channel) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT me_node IF NOT EXISTS FOR (m:Me) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX email_ts IF NOT EXISTS FOR (e:Email) ON (e.ts)",
    "CREATE INDEX activity_ts IF NOT EXISTS FOR (a:Activity) ON (a.ts)",
    "CREATE INDEX video_ts IF NOT EXISTS FOR (v:Video) ON (v.ts)",
]


def _vector_index(dim: int) -> str:
    return (
        "CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS "
        "FOR (m:Memory) ON (m.embedding) "
        "OPTIONS {indexConfig: {`vector.dimensions`: %d, `vector.similarity_function`: 'cosine'}}" % dim
    )


def create_schema(graph, embed_dim: int = 384):
    graph.exec_many([(c, {}) for c in CONSTRAINTS])
    graph.exec_many([(i, {}) for i in INDEXES])
    graph.exec_many([(_vector_index(embed_dim), {})])
