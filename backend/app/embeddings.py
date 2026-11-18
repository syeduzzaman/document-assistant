import hashlib
import math
import re
from collections import Counter

DIMENSIONS = 384
STOPWORDS = set("""
a an the is are was were be been being to of in on at for from by with and or as
it its this that these those i you we they he she what which who how when where
do does did can could would should have has had my your our their about please
tell me much many document documents according say says
""".split())


def tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"\b\w+\b", text.casefold()) if token not in STOPWORDS]


class DemoEmbedder:
    """Deterministic lexical baseline; these are not semantic model embeddings."""

    space = "lexical-hash-v1:384"

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = []
        for text in texts:
            vector = [0.0] * DIMENSIONS
            for token, count in Counter(tokens(text)).items():
                index = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big") % DIMENSIONS
                vector[index] += 1 + math.log(count)
            norm = math.sqrt(sum(value * value for value in vector))
            result.append([value / norm for value in vector] if norm else vector)
        return result


class OpenAIEmbedder:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model
        self.space = f"openai:{model}:{DIMENSIONS}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), 32):
            response = self.client.embeddings.create(
                model=self.model, input=texts[start:start + 32], dimensions=DIMENSIONS,
            )
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
        if len(vectors) != len(texts) or any(len(vector) != DIMENSIONS for vector in vectors):
            raise ValueError("The embedding provider returned an unexpected vector shape.")
        return vectors


def vector_literal(vector: list[float]) -> str:
    if len(vector) != DIMENSIONS or not all(math.isfinite(value) for value in vector):
        raise ValueError("Invalid embedding vector.")
    return "[" + ",".join(str(value) for value in vector) + "]"
