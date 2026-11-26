from neo4j import GraphDatabase


class Graph:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self):
        self.driver.close()

    def run(self, cypher: str, params: dict | None = None):
        with self.driver.session(database=self.database) as session:
            return list(session.run(cypher, params or {}))

    def exec_many(self, statements: list[tuple[str, dict]]):
        def tx_work(tx):
            for cypher, params in statements:
                tx.run(cypher, params).consume()

        with self.driver.session(database=self.database) as session:
            session.execute_write(tx_work)

    def verify(self) -> bool:
        self.run("RETURN 1")
        return True

    def vector_search(self, index: str, query_vector: list[float], k: int) -> list[dict]:
        cypher = (
            f"CALL db.index.vector.queryNodes($index, $k, $vector) "
            "YIELD node, score "
            "RETURN node.id AS id, node.source AS source, node.title AS title, "
            "node.text AS text, node.url AS url, node.ts AS ts, labels(node) AS labels, "
            "score ORDER BY score DESC"
        )
        records = self.run(cypher, {"index": index, "k": k, "vector": query_vector})
        return [dict(r) for r in records]
