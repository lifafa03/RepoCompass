"""Tests for vector index operations."""
import tempfile
from pathlib import Path
import numpy as np
import pytest

from app.schemas import ChunkRecord
from rag.indexing.vector_store import VectorIndex


def _make_chunk(i: int) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=f"chunk_{i}", file_path=f"test_{i}.py", language="python",
        symbol=f"func_{i}", line_start=i*10+1, line_end=i*10+10,
        content=f"def func_{i}(): pass", content_type="code",
        repo_relative_path=f"test_{i}.py",
    )


class TestVectorIndex:
    def test_add_and_search(self):
        dim = 8
        index = VectorIndex(dimension=dim)
        chunks = [_make_chunk(i) for i in range(5)]
        embeddings = np.random.randn(5, dim).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        index.add(chunks, embeddings)
        assert index.size == 5
        query = embeddings[0]
        results = index.search(query, top_k=3)
        assert len(results) == 3
        assert results[0][0].chunk_id == "chunk_0"
        assert results[0][1] > 0.9
    def test_save_and_load(self):
        dim = 8
        index = VectorIndex(dimension=dim)
        chunks = [_make_chunk(i) for i in range(3)]
        embeddings = np.random.randn(3, dim).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        index.add(chunks, embeddings)
        tmp = Path(tempfile.mkdtemp())
        index.save(tmp)
        loaded = VectorIndex.load(tmp)
        assert loaded.size == 3
        assert loaded.chunks[0].chunk_id == "chunk_0"
    def test_empty_search(self):
        index = VectorIndex(dimension=8)
        query = np.random.randn(8).astype(np.float32)
        assert index.search(query) == []
