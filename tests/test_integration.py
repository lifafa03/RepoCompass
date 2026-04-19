"""End-to-end integration tests for the RepoCompass foundation pipeline.

Tests the full path: ingestion → filtering → chunking → embedding → indexing → retrieval
without requiring an LLM endpoint.
"""
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pytest

from backend.services.ingestion import ingest_zip, ingest_local, enumerate_files
from rag.chunking.filtering import filter_files, classify_file, detect_language
from rag.chunking.chunker import chunk_repo, chunk_file
from rag.embeddings.embedder import EmbeddingService
from rag.indexing.vector_store import VectorIndex
from rag.retrieval.retriever import Retriever
from app.schemas import ChunkRecord


SAMPLE_REPO_FILES = {
    "app/main.py": '''"""Sample FastAPI app."""
from fastapi import FastAPI
from typing import Optional

app = FastAPI(title="Sample API")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/items/{item_id}")
async def get_item(item_id: int, q: Optional[str] = None):
    """Retrieve an item by ID."""
    return {"item_id": item_id, "q": q}

@app.post("/items")
async def create_item(name: str, price: float):
    """Create a new item."""
    return {"name": name, "price": price}

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an item."""
    return {"deleted": True, "item_id": item_id}
''',
    "app/models.py": '''"""Data models."""
from pydantic import BaseModel
from typing import Optional


class Item(BaseModel):
    name: str
    price: float
    description: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
''',
    "app/config.py": '''"""Configuration."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
''',
    "app/database.py": '''"""Database setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',
    "requirements.txt": "fastapi>=0.110.0\nuvicorn>=0.29.0\npydantic>=2.6.0\nsqlalchemy>=2.0.0\n",
    "README.md": "# Sample API\\n\\nA sample FastAPI application for testing RepoCompass.\\n\\n## Endpoints\\n\\n- GET /health\\n- GET /items/{id}\\n- POST /items\\n- DELETE /items/{id}\\n",
    ".env.example": "DATABASE_URL=sqlite:///./test.db\nDEBUG=false\n",
    "docker-compose.yaml": "version: '3.8'\\nservices:\\n  api:\\n    build: .\\n    ports:\\n      - '8000:8000'\\n",
}


@pytest.fixture
def sample_repo(tmp_path):
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    for rel_path, content in SAMPLE_REPO_FILES.items():
        fp = repo_dir / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
    (repo_dir / "__pycache__").mkdir()
    (repo_dir / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"\x00" * 100)
    (repo_dir / "static").mkdir()
    (repo_dir / "static" / "logo.png").write_bytes(b"\x89PNG" + b"\x00" * 200)
    return repo_dir


@pytest.fixture
def sample_zip(tmp_path, sample_repo):
    zip_path = tmp_path / "sample_repo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fp in sample_repo.rglob("*"):
            if fp.is_file():
                zf.write(fp, fp.relative_to(sample_repo))
    return zip_path


@pytest.fixture
def unwrapped_zip(tmp_path):
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "main.py").write_text("def hello(): pass\n")
    zip_path = tmp_path / "wrapped.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fp in inner.rglob("*"):
            if fp.is_file():
                zf.write(fp, Path("myproject") / fp.relative_to(inner))
    return zip_path


class TestIngestionIntegration:
    def test_ingest_zip_extracts_all_files(self, sample_zip, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_zip(sample_zip, "test_repo_1")
        assert repo_root.exists()
        assert (repo_root / "app" / "main.py").exists()

    def test_ingest_zip_unwraps_single_dir(self, unwrapped_zip, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_zip(unwrapped_zip, "test_unwrap")
        assert (repo_root / "main.py").exists()
        assert not (repo_root / "myproject").exists()

    def test_ingest_local_copies_directory(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_local")
        assert (repo_root / "app" / "main.py").exists()

    def test_ingest_local_nonexistent_raises(self, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        with pytest.raises(FileNotFoundError):
            ingest_local(tmp_path / "nonexistent")

    def test_enumerate_files_skips_cache_dirs(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_enum")
        files = enumerate_files(repo_root)
        paths = [str(f.relative_to(repo_root)) for f in files]
        assert not any("__pycache__" in p for p in paths)
        assert any("main.py" in p for p in paths)


class TestFilteringIntegration:
    def test_filter_retains_source_files(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_filter")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        paths = [str(fp.relative_to(repo_root)) for fp, ct in filtered]
        assert any("main.py" in p for p in paths)
        assert any("README.md" in p for p in paths)

    def test_filter_skips_binaries(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_filter_bin")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        paths = [str(fp.relative_to(repo_root)) for fp, ct in filtered]
        assert not any(".png" in p for p in paths)

    def test_filter_classifies_correctly(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_classify")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        by_path = {str(fp.relative_to(repo_root)): ct for fp, ct in filtered}
        assert by_path.get("app/main.py") == "code"
        assert by_path.get("README.md") == "docs"
        assert by_path.get("docker-compose.yaml") == "config"
        assert by_path.get(".env.example") == "config"


class TestChunkingIntegration:
    def test_chunk_repo_produces_chunks(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_chunk")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        chunks = chunk_repo(repo_root, filtered)
        assert len(chunks) > 0
        for c in chunks:
            assert c.chunk_id
            assert c.file_path
            assert c.line_start > 0
            assert c.line_end >= c.line_start
            assert c.content
            assert c.content_type in ("code", "config", "docs")
            assert c.repo_relative_path

    def test_python_chunks_have_symbols(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_symbols")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        chunks = chunk_repo(repo_root, filtered)
        py_chunks = [c for c in chunks if c.language == "python"]
        symbols = [c.symbol for c in py_chunks if c.symbol]
        assert len(symbols) > 0
        symbol_names = " ".join(symbols)
        assert "health_check" in symbol_names or "def health_check" in symbol_names

    def test_chunk_determinism(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_determinism")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        chunks1 = chunk_repo(repo_root, filtered)
        chunks2 = chunk_repo(repo_root, filtered)
        assert [c.chunk_id for c in chunks1] == [c.chunk_id for c in chunks2]


class TestEmbeddingIndexPipeline:
    def test_embed_and_index(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_embed")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        chunks = chunk_repo(repo_root, filtered)
        assert len(chunks) > 5
        embedder = EmbeddingService()
        embeddings = embedder.embed_chunks(chunks, show_progress=False)
        assert embeddings.shape[0] == len(chunks)
        assert embeddings.shape[1] == embedder.dimension
        index = VectorIndex(dimension=embeddings.shape[1])
        index.add(chunks, embeddings)
        assert index.size == len(chunks)
        query_vec = embedder.embed_query("health check endpoint")
        results = index.search(query_vec, top_k=5)
        assert len(results) == 5
        top_chunk = results[0][0]
        assert "health" in top_chunk.content.lower() or "health_check" in top_chunk.content

    def test_save_load_roundtrip(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_roundtrip")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        chunks = chunk_repo(repo_root, filtered)
        embedder = EmbeddingService()
        embeddings = embedder.embed_chunks(chunks, show_progress=False)
        index = VectorIndex(dimension=embeddings.shape[1])
        index.add(chunks, embeddings)
        save_dir = tmp_path / "saved_index"
        index.save(save_dir)
        assert (save_dir / "index.faiss").exists()
        loaded = VectorIndex.load(save_dir)
        assert loaded.size == index.size
        query_vec = embedder.embed_query("API endpoints")
        results = loaded.search(query_vec, top_k=3)
        assert len(results) == 3


class TestRetrievalIntegration:
    def test_retriever_returns_evidence(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_retrieval")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        chunks = chunk_repo(repo_root, filtered)
        embedder = EmbeddingService()
        embeddings = embedder.embed_chunks(chunks, show_progress=False)
        index = VectorIndex(dimension=embedder.dimension)
        index.add(chunks, embeddings)
        retriever = Retriever(index, embedder)
        refs = retriever.retrieve_as_evidence("item creation endpoint", top_k=3)
        assert len(refs) == 3
        for ref in refs:
            assert ref.file_path
            assert ref.line_start > 0
            assert ref.snippet_id

    def test_retriever_context_format(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_context")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        chunks = chunk_repo(repo_root, filtered)
        embedder = EmbeddingService()
        embeddings = embedder.embed_chunks(chunks, show_progress=False)
        index = VectorIndex(dimension=embedder.dimension)
        index.add(chunks, embeddings)
        retriever = Retriever(index, embedder)
        context = retriever.retrieve_context("database configuration", top_k=3)
        assert len(context) > 100
        assert "score=" in context
        assert "---" in context


class TestExtractorIntegration:
    def test_extracts_all_endpoints_from_repo(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_extract")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        code_files = [fp for fp, ct in filtered if ct == "code"]
        from extractors.api.fastapi_extractor import extract_api_map
        api_map = extract_api_map(repo_root, code_files)
        assert len(api_map.endpoints) == 4
        methods = {ep.method for ep in api_map.endpoints}
        assert "GET" in methods and "POST" in methods and "DELETE" in methods
        routes = {ep.route for ep in api_map.endpoints}
        assert "/health" in routes and "/items" in routes

    def test_extractor_evidence_links(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_ev")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        code_files = [fp for fp, ct in filtered if ct == "code"]
        from extractors.api.fastapi_extractor import extract_api_map
        api_map = extract_api_map(repo_root, code_files)
        for ep in api_map.endpoints:
            assert len(ep.evidence) > 0
            ev = ep.evidence[0]
            assert ev.file_path
            assert ev.line_start > 0
            assert (repo_root / ev.file_path).exists()


class TestEvaluationIntegration:
    def test_evaluation_on_real_extraction(self, sample_repo, tmp_path):
        from app import config
        config.UPLOAD_DIR = tmp_path / "uploads"
        repo_root = ingest_local(sample_repo, "test_eval")
        files = enumerate_files(repo_root)
        filtered = filter_files(files)
        code_files = [fp for fp, ct in filtered if ct == "code"]
        from extractors.api.fastapi_extractor import extract_api_map
        from evaluators.metrics import evaluate_api_map
        from app.schemas import APIEndpoint
        predicted = extract_api_map(repo_root, code_files)
        ground_truth = type('obj', (object,), {'framework': 'fastapi', 'endpoints': [
            APIEndpoint(method="GET", route="/health"),
            APIEndpoint(method="GET", route="/items/{item_id}"),
            APIEndpoint(method="POST", route="/items"),
            APIEndpoint(method="DELETE", route="/items/{item_id}"),
        ]})()
        metrics = evaluate_api_map(predicted, ground_truth)
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0
        assert metrics.true_positives == 4
