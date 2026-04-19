"""Full RepoCompass pipeline: ingestion → indexing → extraction → generation → review."""
import time
from pathlib import Path
from dataclasses import dataclass, field

from backend.services.ingestion import ingest_local, ingest_zip, enumerate_files
from rag.chunking.filtering import filter_files
from rag.chunking.chunker import chunk_repo
from rag.embeddings.embedder import EmbeddingService
from rag.indexing.vector_store import VectorIndex
from rag.retrieval.retriever import Retriever
from extractors.api.fastapi_extractor import extract_api_map
from agents.code_analyst import generate_architecture, generate_callflow
from agents.reviewer import review_architecture, review_api_map, generate_risk_notes
from agents.documentation_editor import finalize_architecture, finalize_risk_notes

from app.schemas import (
    ArchitectureExplainer, APIMap, CallFlowSummary, RiskNotes, AskRepoAnswer,
)
from backend.services.llm import generate


@dataclass
class PipelineResult:
    """Complete output from the RepoCompass pipeline."""
    repo_id: str
    architecture: ArchitectureExplainer = field(default_factory=lambda: ArchitectureExplainer(summary=""))
    api_map: APIMap = field(default_factory=lambda: APIMap(framework="fastapi"))
    callflow: CallFlowSummary = field(default_factory=CallFlowSummary)
    risk_notes: RiskNotes = field(default_factory=RiskNotes)
    stats: dict = field(default_factory=dict)
    evaluation: dict | None = None
    chunks_count: int = 0


class RepoCompassPipeline:
    def __init__(self):
        self.embedder = EmbeddingService()
        self._timings: dict[str, float] = {}

    def _time(self, label: str):
        self._timings[label] = time.time()

    def run(self, source: Path, repo_id: str | None = None) -> PipelineResult:
        result = PipelineResult(repo_id=repo_id or "unknown")
        self._time("ingest_start")
        if source.is_file() and source.suffix == ".zip":
            repo_root = ingest_zip(source, repo_id)
        else:
            repo_root = ingest_local(source, repo_id)
        self._time("ingest_end")

        self._time("filter_start")
        all_files = enumerate_files(repo_root)
        filtered = filter_files(all_files)
        self._time("filter_end")

        self._time("chunk_start")
        chunks = chunk_repo(repo_root, filtered)
        self._time("chunk_end")

        if not chunks:
            result.stats = self._compute_stats()
            return result

        self._time("embed_start")
        embeddings = self.embedder.embed_chunks(chunks)
        self._time("embed_end")

        self._time("index_start")
        index = VectorIndex(dimension=embeddings.shape[1])
        index.add(chunks, embeddings)
        self._time("index_end")

        from app import config
        index_dir = config.VECTOR_STORE_DIR / result.repo_id
        index.save(index_dir)

        retriever = Retriever(index, self.embedder)

        self._time("extract_start")
        source_files = [fp for fp, ct in filtered if ct == "code"]
        api_map = extract_api_map(repo_root, source_files)
        api_map = review_api_map(api_map)
        result.api_map = api_map
        self._time("extract_end")

        self._time("gen_start")
        try:
            result.architecture = generate_architecture(retriever)
            result.architecture = review_architecture(result.architecture)
            result.architecture = finalize_architecture(result.architecture)
        except Exception as e:
            result.architecture = ArchitectureExplainer(summary=f"Generation failed: {e}")
        try:
            result.callflow = generate_callflow(retriever)
        except Exception:
            result.callflow = CallFlowSummary()
        self._time("gen_end")

        self._time("risk_start")
        result.risk_notes = generate_risk_notes(result.architecture, result.api_map, result.callflow)
        result.risk_notes = finalize_risk_notes(result.risk_notes)
        self._time("risk_end")

        result.chunks_count = len(chunks)
        result.stats = self._compute_stats()

        from evaluators.metrics import run_full_evaluation
        evaluation = run_full_evaluation(result.architecture, result.api_map, result.callflow, result.risk_notes, result.stats, chunks_count=len(chunks))
        result.evaluation = evaluation.to_dict()

        return result

    def ask_repo(self, repo_id: str, question: str) -> AskRepoAnswer:
        from app import config
        from agents.documentation_editor import format_answer
        index_dir = config.VECTOR_STORE_DIR / repo_id
        if not index_dir.exists():
            return AskRepoAnswer(question=question, answer="insufficient evidence", evidence=[], confidence="low", insufficient_evidence=True, uncertainty_note="Repository not indexed.")
        index = VectorIndex.load(index_dir)
        retriever = Retriever(index, self.embedder)
        context = retriever.retrieve_context(question, top_k=8)
        refs = retriever.retrieve_as_evidence(question, top_k=8)
        prompt = f"""Answer the following question about a repository using ONLY the evidence provided.

QUESTION: {question}

EVIDENCE:
{context}

If you cannot answer from the evidence, respond with exactly: insufficient evidence
Otherwise, provide a concise answer and reference specific files/lines."""
        try:
            response = generate(prompt)
            if "insufficient evidence" in response.lower():
                return AskRepoAnswer(question=question, answer="insufficient evidence", evidence=[], confidence="low", insufficient_evidence=True, uncertainty_note="Evidence was not sufficient to answer reliably.")
            return AskRepoAnswer(question=question, answer=response.strip(), evidence=refs[:5], confidence="medium", insufficient_evidence=False)
        except Exception as e:
            return AskRepoAnswer(question=question, answer=f"Error: {e}", evidence=[], confidence="low", insufficient_evidence=True, uncertainty_note=str(e))

    def _compute_stats(self) -> dict:
        timings = {}
        prev = None
        for label, t in sorted(self._timings.items()):
            if prev is not None and label.endswith("_end"):
                key = label.replace("_end", "")
                start_label = key + "_start"
                if start_label in self._timings:
                    timings[f"{key}_seconds"] = round(t - self._timings[start_label], 2)
            prev = label
        return timings
