"""Standalone evaluation runner for RepoCompass.

Usage:
    python evaluators/run_evaluation.py [--repo PATH] [--ground-truth PATH]

Runs the full pipeline (without LLM generation — static extraction only)
and produces a measurable evaluation report.

Ground truth construction:
    Ground truth is constructed by manually annotating the known API endpoints
    in a target repository. For the sample repo, this means listing every
    FastAPI route decorator with its method, path, handler name, file, and line.

    Construction steps:
    1. Read every Python file in the repo
    2. For each @app.get/post/put/delete decorator, record method + route
    3. Record the handler function name and line number
    4. Cross-check by running the extractor and comparing
    5. Store as JSON in data/eval_sets/

    This is manual for v1. Future: automate from test suites or OpenAPI specs.
"""
import argparse
import json
import sys
import time
import tracemalloc
import tempfile
import zipfile
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import (
    ArchitectureExplainer, APIMap, APIEndpoint, CallFlowSummary, RiskNotes,
    EvidenceRef,
)
from backend.services.ingestion import ingest_local, ingest_zip, enumerate_files
from rag.chunking.filtering import filter_files
from rag.chunking.chunker import chunk_repo
from rag.embeddings.embedder import EmbeddingService
from rag.indexing.vector_store import VectorIndex
from rag.retrieval.retriever import Retriever
from extractors.api.fastapi_extractor import extract_api_map
from agents.reviewer import review_api_map, generate_risk_notes
from agents.documentation_editor import finalize_risk_notes
from evaluators.metrics import (
    evaluate_api_map, evaluate_groundedness, measure_pipeline_stats,
    run_full_evaluation,
)


# ── Sample repo (embedded for reproducibility) ──

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
    "README.md": "# Sample API\n\nA sample FastAPI application for testing RepoCompass.\n\n## Endpoints\n\n- GET /health\n- GET /items/{id}\n- POST /items\n- DELETE /items/{id}\n",
    ".env.example": "DATABASE_URL=sqlite:///./test.db\nDEBUG=false\n",
    "docker-compose.yaml": "version: '3.8'\nservices:\n  api:\n    build: .\n    ports:\n      - '8000:8000'\n",
}


def create_sample_repo(dest: Path):
    for rel, content in SAMPLE_REPO_FILES.items():
        fp = dest / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
    (dest / "__pycache__").mkdir()
    (dest / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"\x00" * 100)


def get_ground_truth() -> APIMap:
    """Manually annotated ground truth for the sample repo."""
    return APIMap(framework="fastapi", endpoints=[
        APIEndpoint(method="GET", route="/health", handler_name="health_check",
                    evidence=[EvidenceRef(file_path="app/main.py", line_start=7, line_end=9, snippet_id="gt_1")]),
        APIEndpoint(method="GET", route="/items/{item_id}", handler_name="get_item",
                    evidence=[EvidenceRef(file_path="app/main.py", line_start=12, line_end=15, snippet_id="gt_2")]),
        APIEndpoint(method="POST", route="/items", handler_name="create_item",
                    evidence=[EvidenceRef(file_path="app/main.py", line_start=17, line_end=20, snippet_id="gt_3")]),
        APIEndpoint(method="DELETE", route="/items/{item_id}", handler_name="delete_item",
                    evidence=[EvidenceRef(file_path="app/main.py", line_start=22, line_end=25, snippet_id="gt_4")]),
    ])


def run_evaluation(repo_path: Path | None = None, ground_truth_path: Path | None = None, output_path: Path | None = None):
    """Run the full evaluation and return results."""
    print("=" * 60)
    print("RepoCompass Evaluation Runner")
    print("=" * 60)

    tracemalloc.start()
    t_start = time.time()

    # ── Phase 1: Setup repo ──
    if repo_path is None:
        repo_path = Path(tempfile.mkdtemp()) / "eval_repo"
        repo_path.mkdir()
        create_sample_repo(repo_path)
        print(f"\n📦 Using built-in sample repo: {repo_path}")
    else:
        print(f"\n📦 Using provided repo: {repo_path}")

    # ── Phase 2: Ingestion ──
    print("\n── Phase 1: Ingestion ──")
    t_ingest = time.time()
    all_files = enumerate_files(repo_path)
    t_ingest_end = time.time()
    print(f"  Files enumerated: {len(all_files)} ({t_ingest_end - t_ingest:.3f}s)")

    # ── Phase 3: Filtering ──
    print("\n── Phase 2: Filtering ──")
    t_filter = time.time()
    filtered = filter_files(all_files)
    t_filter_end = time.time()
    code_count = sum(1 for _, ct in filtered if ct == "code")
    config_count = sum(1 for _, ct in filtered if ct == "config")
    docs_count = sum(1 for _, ct in filtered if ct == "docs")
    print(f"  Retained: {len(filtered)} files (code={code_count}, config={config_count}, docs={docs_count}) ({t_filter_end - t_filter:.3f}s)")

    # ── Phase 4: Chunking ──
    print("\n── Phase 3: Chunking ──")
    t_chunk = time.time()
    chunks = chunk_repo(repo_root=repo_path, filtered_files=filtered)
    t_chunk_end = time.time()
    py_chunks = [c for c in chunks if c.language == "python"]
    symbols = [c for c in py_chunks if c.symbol]
    print(f"  Chunks: {len(chunks)} total ({len(py_chunks)} Python, {len(symbols)} with symbols) ({t_chunk_end - t_chunk:.3f}s)")

    # ── Phase 5: Embeddings + Index ──
    print("\n── Phase 4: Embeddings + Indexing ──")
    t_embed = time.time()
    embedder = EmbeddingService()
    embeddings = embedder.embed_chunks(chunks, show_progress=False)
    t_embed_end = time.time()

    t_index = time.time()
    index = VectorIndex(dimension=embeddings.shape[1])
    index.add(chunks, embeddings)
    t_index_end = time.time()
    print(f"  Embedding dim: {embeddings.shape[1]}, vectors: {embeddings.shape[0]} ({t_embed_end - t_embed:.3f}s)")
    print(f"  Index built: {index.size} entries ({t_index_end - t_index:.3f}s)")

    # ── Phase 6: API Extraction (static, no LLM) ──
    print("\n── Phase 5: API Extraction ──")
    t_extract = time.time()
    code_files = [fp for fp, ct in filtered if ct == "code"]
    api_map = extract_api_map(repo_path, code_files)
    api_map = review_api_map(api_map)
    t_extract_end = time.time()
    print(f"  Endpoints extracted: {len(api_map.endpoints)} ({t_extract_end - t_extract:.3f}s)")
    for ep in api_map.endpoints:
        print(f"    {ep.confidence:6s} {ep.method:6s} {ep.route:25s} handler={ep.handler_name}")

    # ── Phase 7: Groundedness (on extraction results) ──
    print("\n── Phase 6: Groundedness Assessment ──")
    arch = ArchitectureExplainer(summary="Static extraction — no LLM generation")
    callflow = CallFlowSummary()
    risk_notes = generate_risk_notes(arch, api_map, callflow)
    risk_notes = finalize_risk_notes(risk_notes)
    groundedness = evaluate_groundedness(arch, api_map, callflow, risk_notes)
    print(f"  Total claims: {groundedness.total_claims}")
    print(f"  With evidence: {groundedness.claims_with_evidence}")
    print(f"  Without evidence: {groundedness.claims_without_evidence}")
    print(f"  Unsupported rate: {groundedness.unsupported_rate:.1%}")
    print(f"  Avg evidence/claim: {groundedness.avg_evidence_per_claim:.2f}")
    print(f"  Confidence: {groundedness.confidence_distribution}")

    # ── Phase 8: API Map Accuracy ──
    print("\n── Phase 7: API Map Accuracy ──")
    ground_truth = get_ground_truth()
    if ground_truth_path:
        with open(ground_truth_path) as f:
            gt_data = json.load(f)
        ground_truth = APIMap(framework=gt_data["framework"], endpoints=[
            APIEndpoint(method=e["method"], route=e["route"], handler_name=e.get("handler"),
                       evidence=[EvidenceRef(file_path=e.get("file", ""), line_start=e.get("line", 0), line_end=e.get("line", 0), snippet_id=f"gt_{i}")])
            for i, e in enumerate(gt_data["endpoints"])
        ])
    api_metrics = evaluate_api_map(api_map, ground_truth)
    print(f"  Ground truth endpoints: {len(ground_truth.endpoints)}")
    print(f"  True positives: {api_metrics.true_positives}")
    print(f"  False positives: {api_metrics.false_positives}")
    print(f"  False negatives: {api_metrics.false_negatives}")
    print(f"  Precision: {api_metrics.precision:.1%}")
    print(f"  Recall:    {api_metrics.recall:.1%}")
    print(f"  F1:        {api_metrics.f1:.1%}")
    if api_metrics.false_positives > 0:
        pred_keys = {f"{ep.method} {ep.route}" for ep in api_map.endpoints}
        gt_keys = {f"{ep.method} {ep.route}" for ep in ground_truth.endpoints}
        print(f"  FP details: {pred_keys - gt_keys}")
    if api_metrics.false_negatives > 0:
        pred_keys = {f"{ep.method} {ep.route}" for ep in api_map.endpoints}
        gt_keys = {f"{ep.method} {ep.route}" for ep in ground_truth.endpoints}
        print(f"  FN details: {gt_keys - pred_keys}")

    # ── Phase 9: Runtime ──
    t_total = time.time() - t_start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\n── Phase 8: Runtime & Resources ──")
    print(f"  Total time: {t_total:.2f}s")
    print(f"  Ingestion + enum: {t_ingest_end - t_ingest:.3f}s")
    print(f"  Filtering: {t_filter_end - t_filter:.3f}s")
    print(f"  Chunking: {t_chunk_end - t_chunk:.3f}s")
    print(f"  Embedding: {t_embed_end - t_embed:.3f}s")
    print(f"  Indexing: {t_index_end - t_index:.3f}s")
    print(f"  Extraction: {t_extract_end - t_extract:.3f}s")
    print(f"  Memory peak: {peak / 1024 / 1024:.1f} MB")

    # ── Save report ──
    stats = {
        "ingest_seconds": round(t_ingest_end - t_ingest, 3),
        "filter_seconds": round(t_filter_end - t_filter, 3),
        "chunk_seconds": round(t_chunk_end - t_chunk, 3),
        "embed_seconds": round(t_embed_end - t_embed, 3),
        "index_seconds": round(t_index_end - t_index, 3),
        "extract_seconds": round(t_extract_end - t_extract, 3),
    }

    report = run_full_evaluation(arch, api_map, callflow, risk_notes, stats, ground_truth, len(chunks))
    report_dict = report.to_dict()
    report_dict["runtime"] = {
        "total_seconds": round(t_total, 2),
        "memory_peak_mb": round(peak / 1024 / 1024, 1),
        "chunks_indexed": len(chunks),
    }
    report_dict["disclaimer"] = (
        "Architecture explainer and call-flow generation were NOT evaluated in this run "
        "because they require an LLM endpoint. Only static extraction (API map, filtering, "
        "chunking, indexing) was measured. Groundedness scores reflect extraction-only outputs."
    )
    report_dict["ground_truth_construction"] = (
        "Ground truth was constructed by manually reading the sample FastAPI repo source code "
        "and recording every @app.<method> decorator with its HTTP method, route path, handler "
        "function name, source file, and line number. This is verified against the AST extractor "
        "output. For v1, this is manual annotation. Future versions could auto-generate from "
        "OpenAPI specs or test suites."
    )

    if output_path is None:
        output_path = Path("data/eval_sets/last_run_report.json")
    report.save(output_path)
    print(f"\n📄 Report saved to: {output_path}")

    # ── Summary ──
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"API Extraction:  P={api_metrics.precision:.1%}  R={api_metrics.recall:.1%}  F1={api_metrics.f1:.1%}")
    print(f"Groundedness:    {groundedness.claims_with_evidence}/{groundedness.total_claims} claims evidences ({1 - groundedness.unsupported_rate:.0%} coverage)")
    print(f"Runtime:         {t_total:.2f}s total, {len(chunks)} chunks indexed")
    print(f"Memory:          {peak / 1024 / 1024:.1f} MB peak")
    print(f"Limitations:     LLM-dependent outputs (architecture, call-flow) not evaluated")
    print("=" * 60)

    return report_dict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RepoCompass evaluation")
    parser.add_argument("--repo", type=Path, help="Path to repository to evaluate")
    parser.add_argument("--ground-truth", type=Path, help="Path to ground truth JSON")
    parser.add_argument("--output", type=Path, default=Path("data/eval_sets/last_run_report.json"), help="Output report path")
    args = parser.parse_args()
    run_evaluation(args.repo, args.ground_truth, args.output)
