"""Embeddings pipeline using sentence-transformers."""
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from app import config
from app.schemas import ChunkRecord


class EmbeddingService:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def embed_chunks(self, chunks: list[ChunkRecord], batch_size: int = 64, show_progress: bool = True) -> np.ndarray:
        """Generate embeddings for a list of chunks."""
        texts = [c.content for c in chunks]
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )
        return np.array(embeddings)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string."""
        vec = self.model.encode([query], normalize_embeddings=True)
        return np.array(vec[0])
