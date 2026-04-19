"""Extended evaluation metrics for RepoCompass.

Adds retrieval quality, inference latency profiling, and ROUGE-like
overlap scoring for groundedness -- metrics specifically needed for
the capstone assignment grading criteria.
"""
import time
import numpy as np
from dataclasses import dataclass, field
from rag.indexing.vector_store import VectorIndex
from rag.embeddings.embedder import EmbeddingService
from app.schemas import ChunkRecord, EvidenceRef


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""
    mean_reciprocal_rank: float
    mean_similarity_at_k: dict
    queries_evaluated: int
    per_query_details: list = field(default_factory=list)


def evaluate_retrieval(
    index: VectorIndex,
    embedder: EmbeddingService,
    query_relevance: list[dict],
    k_values: list[int] = None,
) -> RetrievalMetrics:
    if k_values is None:
        k_values = [1, 3, 5]
    mrr_scores = []
    sim_at_k = {k: [] for k in k_values}
    details = []
    for qr in query_relevance:
        query = qr["query"]
        relevant_patterns = qr["relevant_file_patterns"]
        query_vec = embedder.embed_query(query)
        results = index.search(query_vec, top_k=max(k_values))
        rr = 0.0
        for rank, (chunk, score) in enumerate(results, 1):
            if any(pat in chunk.repo_relative_path for pat in relevant_patterns):
                rr = 1.0 / rank
                break
        mrr_scores.append(rr)
        for k in k_values:
            top_k_results = results[:k]
            if top_k_results:
                mean_sim = np.mean([s for _, s in top_k_results])
                sim_at_k[k].append(float(mean_sim))
        details.append({"query": query, "reciprocal_rank": rr,
                        "top_result": results[0][0].repo_relative_path if results else None,
                        "top_score": float(results[0][1]) if results else None,
                        "relevant_patterns": relevant_patterns})
    mean_mrr = float(np.mean(mrr_scores)) if mrr_scores else 0.0
    mean_sims = {k: float(np.mean(v)) if v else 0.0 for k, v in sim_at_k.items()}
    return RetrievalMetrics(mean_reciprocal_rank=round(mean_mrr, 4),
                            mean_similarity_at_k=mean_sims,
                            queries_evaluated=len(query_relevance),
                            per_query_details=details)


@dataclass
class LatencyProfile:
    ingestion_ms: float = 0.0
    filtering_ms: float = 0.0
    chunking_ms: float = 0.0
    embedding_ms: float = 0.0
    indexing_ms: float = 0.0
    extraction_ms: float = 0.0
    retrieval_ms: float = 0.0
    total_ms: float = 0.0
    embedding_dim: int = 0
    num_chunks: int = 0
    throughput_chunks_per_sec: float = 0.0


def profile_pipeline_latency(repo_root, filtered_files, chunks, embedder, num_retrieval_queries: int = 5) -> LatencyProfile:
    from backend.services.ingestion import enumerate_files
    from rag.chunking.filtering import filter_files
    from rag.chunking.chunker import chunk_repo
    from rag.indexing.vector_store import VectorIndex
    from extractors.api.fastapi_extractor import extract_api_map
    profile = LatencyProfile()
    t = time.perf_counter()
    all_files = enumerate_files(repo_root)
    profile.ingestion_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    _ = filter_files(all_files)
    profile.filtering_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    _ = chunk_repo(repo_root, filtered_files)
    profile.chunking_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    embeddings = embedder.embed_chunks(chunks, show_progress=False)
    profile.embedding_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    index = VectorIndex(dimension=embeddings.shape[1])
    index.add(chunks, embeddings)
    profile.indexing_ms = (time.perf_counter() - t) * 1000
    code_files = [fp for fp, ct in filtered_files if ct == "code"]
    t = time.perf_counter()
    _ = extract_api_map(repo_root, code_files)
    profile.extraction_ms = (time.perf_counter() - t) * 1000
    queries = ["API endpoint", "main function", "configuration", "database", "health check"]
    t = time.perf_counter()
    for q in queries[:num_retrieval_queries]:
        qv = embedder.embed_query(q)
        index.search(qv, top_k=5)
    profile.retrieval_ms = ((time.perf_counter() - t) * 1000) / num_retrieval_queries
    profile.num_chunks = len(chunks)
    profile.embedding_dim = embeddings.shape[1]
    profile.total_ms = (profile.ingestion_ms + profile.filtering_ms + profile.chunking_ms +
                        profile.embedding_ms + profile.indexing_ms + profile.extraction_ms)
    profile.throughput_chunks_per_sec = round(len(chunks) / (profile.embedding_ms / 1000), 2) if profile.embedding_ms > 0 else 0
    return profile


def ngram_overlap(generated: str, source: str, n: int = 2) -> float:
    def get_ngrams(text, n):
        words = text.lower().split()
        return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))
    gen_ngrams = get_ngrams(generated, n)
    src_ngrams = get_ngrams(source, n)
    if not gen_ngrams:
        return 0.0
    return len(gen_ngrams & src_ngrams) / len(gen_ngrams)


def evaluate_groundedness_overlap(claims: list[str], evidence_texts: list[str], n: int = 2) -> dict:
    results = []
    for claim in claims:
        best_overlap = 0.0
        for ev_text in evidence_texts:
            best_overlap = max(best_overlap, ngram_overlap(claim, ev_text, n))
        results.append({"claim": claim[:80], "best_overlap": round(best_overlap, 4)})
    avg = sum(r["best_overlap"] for r in results) / len(results) if results else 0.0
    return {"average_overlap": round(avg, 4), "num_claims": len(results), "per_claim": results}
