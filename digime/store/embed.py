from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


class Embedder:
    def __init__(self):
        self._ef = DefaultEmbeddingFunction()
        self.dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [list(map(float, v)) for v in self._ef(texts)]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
