"""Retrieval service: query the vector index for evidence."""
from rag.indexing.vector_store import VectorIndex
from rag.embeddings.embedder import EmbeddingService
from app.schemas import ChunkRecord, EvidenceRef


class Retriever:
    def __init__(self, index: VectorIndex, embedder: EmbeddingService):
        self.index = index
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 10) -> list[tuple[ChunkRecord, float]]:
        query_emb = self.embedder.embed_query(query)
        return self.index.search(query_emb, top_k)

    def retrieve_as_evidence(self, query: str, top_k: int = 10) -> list[EvidenceRef]:
        results = self.retrieve(query, top_k)
        refs = []
        for chunk, score in results:
            refs.append(EvidenceRef(
                file_path=chunk.repo_relative_path,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                snippet_id=chunk.chunk_id,
            ))
        return refs

    def retrieve_context(self, query: str, top_k: int = 10) -> str:
        results = self.retrieve(query, top_k)
        if not results:
            return "No relevant evidence found."
        parts = []
        for i, (chunk, score) in enumerate(results):
            parts.append(
                f"[{i+1}] {chunk.repo_relative_path}:{chunk.line_start}-{chunk.line_end} "
                f"(score={score:.3f})\n{chunk.content}"
            )
        return "\n\n---\n\n".join(parts)
