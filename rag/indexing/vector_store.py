"""FAISS vector index for repository chunks."""
import json
import numpy as np
import faiss
from pathlib import Path

from app import config
from app.schemas import ChunkRecord


class VectorIndex:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: list[ChunkRecord] = []

    def add(self, chunks: list[ChunkRecord], embeddings: np.ndarray):
        assert len(chunks) == embeddings.shape[0]
        assert embeddings.shape[1] == self.dimension
        self.chunks.extend(chunks)
        self.index.add(embeddings.astype(np.float32))

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> list[tuple[ChunkRecord, float]]:
        if self.index.ntotal == 0:
            return []
        query = query_embedding.reshape(1, -1).astype(np.float32)
        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            results.append((self.chunks[idx], float(score)))
        return results

    def save(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / "index.faiss"))
        with open(directory / "chunks.jsonl", "w") as f:
            for chunk in self.chunks:
                f.write(chunk.model_dump_json() + "\n")

    @classmethod
    def load(cls, directory: Path) -> "VectorIndex":
        index = faiss.read_index(str(directory / "index.faiss"))
        vi = cls(dimension=index.d)
        vi.index = index
        with open(directory / "chunks.jsonl", "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    vi.chunks.append(ChunkRecord.model_validate_json(line))
        return vi

    @property
    def size(self) -> int:
        return self.index.ntotal
