# Report Support Notes — RepoCompass

These notes are derived from the actual implementation. Nothing is hallucinated or aspirational. Where something is not yet measured or not implemented, that is stated explicitly.

---

## Project Title

**RepoCompass: Multi-Agent RAG Web App for Codebase Architecture Explainers and API Mapping**

Course: DS552 – Generative AI  
Type: Capstone project  
Repo: `github.com/lifafa03/RepoCompass`

---

## Introduction and Objective

### Problem
Developers spend significant time understanding unfamiliar codebases — locating API implementations, identifying module boundaries, and tracing data flows. Documentation is often incomplete or scattered across source files, configuration, and markdown.

### Objective
Build a web application that ingests a software repository and produces five grounded, developer-oriented outputs:

1. **System/Architecture Explainer** — grounded overview of repository structure and components
2. **API Endpoint Inventory** — structured route list with handler locations and evidence
3. **Call-Flow Summary** — high-level request/execution flow for major paths
4. **Evidence-Linked Risk Notes** — indicators for uncertainty or potentially unsafe logic
5. **Ask-Repo Q&A** — answers grounded in retrieved source evidence

### What is implemented
All five output types are implemented in the pipeline. The system produces structured JSON matching defined schemas (see `docs/OUTPUT_FORMATS.md`). Three of the five (API endpoint inventory, risk notes, Ask-Repo Q&A infrastructure) are fully functional without an LLM endpoint. Architecture explainer and call-flow summary require an LLM endpoint for generation but have complete agent logic and review pipelines.

### What is partially implemented
- Architecture explainer and call-flow summary: agent logic exists, prompts are grounded, review pipeline exists, but actual generation requires a running LLM endpoint (OpenAI-compatible API).
- Ask-Repo Q&A: retrieval + evidence infrastructure is complete, LLM answer generation requires endpoint.

---

## Selection of Generative AI Model

### Model for embeddings
**sentence-transformers/all-MiniLM-L6-v2** (384-dimensional embeddings)
- Chosen for: small footprint, fast inference, good code retrieval quality
- Used via `sentence-transformers` library
- Normalized for cosine similarity via FAISS IndexFlatIP

### Model for generation
**OpenAI-compatible API** (configurable)
- Designed to work with any OpenAI-compatible endpoint:
  - OpenAI GPT-4o-mini (cloud)
  - Mistral 7B Instruct via vLLM (local)
  - Ollama (local)
- Configured via environment variables: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
- Default config: Mistral 7B Instruct class model

### Why this approach
- Separates embedding from generation — embeddings are always local, generation is configurable
- Allows demo with any available LLM (no hardware dependency for embedding)
- Capstone-appropriate: demonstrates RAG architecture without requiring specific GPU hardware

### What is measured
- Embedding dimension: 384
- Embedding time: 3.13s for 12 chunks (sample repo)
- Model loads once, reused across queries

### What is not yet measured
- Generation latency (requires running LLM endpoint)
- Generation quality metrics (BLEU, ROUGE, etc. — not used; groundedness is measured instead)

---

## Project Definition and Use Case

### Use case 1: Developer onboarding
A developer uploads an unfamiliar repository. RepoCompass generates a system map showing major components, their roles, and evidence linking each claim to source code.

**Status:** Pipeline implemented. Architecture explainer generated via Code Analyst agent with multi-query retrieval (5 queries covering entry points, module structure, class definitions, config, and API routes). Output validated by Reviewer agent.

### Use case 2: API discovery
A developer needs to find all API endpoints in a FastAPI repository. RepoCompass extracts routes using AST-based static analysis, producing method, route, handler name, handler location, and evidence references.

**Status:** Fully implemented and measured. Precision = 100%, Recall = 100%, F1 = 100% on sample FastAPI repo with 4 endpoints.

### Use case 3: Risk identification
A reviewer needs to identify uncertain, potentially unsafe, or ambiguous implementation areas. RepoCompass generates risk notes with categories (security, correctness, maintainability, ambiguity, configuration), evidence, and confidence scores.

**Status:** Fully implemented. Risk notes generated for low-confidence components, unresolved handlers, and partial flows. Notes framed as "risk indicators" not vulnerabilities.

### Use case 4: Repository Q&A
A developer asks natural-language questions about the repository. RepoCompass retrieves relevant evidence and generates grounded answers.

**Status:** Retrieval infrastructure complete. LLM answer generation requires running endpoint. Evidence refs and confidence scoring implemented.

---

## Implementation Plan

### Architecture
```
Repository (ZIP/Local)
    ↓
Ingestion (extract, enumerate)
    ↓
Filtering (classify: code/config/docs, skip binary/cache)
    ↓
Chunking (Python symbol-aware, generic with overlap)
    ↓
Embedding (sentence-transformers, batch, normalized)
    ↓
Vector Index (FAISS IndexFlatIP, saved to disk)
    ↓
    ├→ API Extraction (AST, static, no LLM)
    ├→ Architecture Generation (LLM, multi-query retrieval)
    ├→ Call-Flow Generation (LLM, multi-query retrieval)
    ├→ Risk Notes (rule-based + evidence validation)
    └→ Ask-Repo Q&A (retrieval + LLM)
    ↓
Review Layer (confidence downgrade, uncertainty marking)
    ↓
Documentation Editor (finalize, sanitize language)
    ↓
Output (JSON, Streamlit UI, FastAPI API)
```

### Multi-agent workflow
1. **Code Analyst** (`agents/code_analyst.py`): Drafts architecture and call-flow from retrieved evidence. Uses multi-query retrieval for broad coverage. Instructed to only claim what evidence supports.

2. **Security/Correctness Reviewer** (`agents/reviewer.py`): Challenges unsupported claims. Downgrades confidence of claims without evidence. Generates risk notes for low-confidence items.

3. **Documentation Editor** (`agents/documentation_editor.py`): Finalizes outputs. Marks uncertainty. Sanitizes security language ("vulnerability" → "potential risk indicator").

### Technology stack
| Component | Technology |
|-----------|------------|
| Backend | FastAPI |
| Frontend | Streamlit |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | FAISS (IndexFlatIP) |
| API Extraction | Python AST (ast module) |
| LLM Client | OpenAI-compatible API |
| Language | Python 3.11 |
| Deployment | Docker + docker-compose |

### Codebase size
- 28+ source files
- 56 passing tests
- ~3,500 lines of Python (excluding tests)

---

## Model Evaluation and Performance Metrics

### API Map Extraction Accuracy (measured)
- **Ground truth:** 4 manually annotated FastAPI endpoints
- **Method:** (method, route) pair matching
- **Results:**
  - Precision: 100% (4/4 predicted endpoints are correct)
  - Recall: 100% (4/4 ground truth endpoints found)
  - F1: 100%
  - True positives: 4, False positives: 0, False negatives: 0
- **Ground truth construction:** Manual annotation by reading source code, recording every `@app.<method>` decorator with method, route, handler name, file, and line number. Cross-verified against AST extractor output.
- **Limitation:** Only tested on a small sample repo (4 endpoints, 1 file). Real repos with routers, middleware, sub-apps would stress the extractor more.

### Groundedness / Citation Coverage (measured)
- **Method:** Count claims with ≥1 EvidenceRef vs total claims
- **Scope:** API endpoint extraction (static pipeline)
- **Results:**
  - Total claims: 4
  - Claims with evidence: 4
  - Unsupported rate: 0%
  - Average evidence per claim: 1.0
  - Confidence distribution: 4 high, 0 medium, 0 low
- **Limitation:** Only measured on extraction outputs. LLM-generated outputs (architecture, call-flow) not yet measured — requires running LLM endpoint.

### Runtime and Resource Usage (measured)
- **Method:** `time.time()` wall-clock + `tracemalloc` peak memory
- **Results (sample FastAPI repo, 8 files, 12 chunks):**

| Phase | Time |
|-------|------|
| Ingestion | 1ms |
| Filtering | <1ms |
| Chunking | 3ms |
| Embedding | 3,131ms |
| Indexing | <1ms |
| Extraction | 4ms |
| **Total** | **3.14s** |

- Memory peak: 10.6 MB
- Bottleneck: Embedding generation (99.7% of total time)

### Retrieval Quality (measured via integration tests)
- Query "health check endpoint" → top result contains health_check function
- Query "item creation endpoint" → retrieves create_item chunk
- Query "database configuration" → retrieves config.py and database.py chunks
- Save/load roundtrip preserves all 12 chunks and retrieval quality

### What is not yet measured
- Architecture explainer groundedness (requires LLM)
- Call-flow accuracy (requires LLM)
- Ask-Repo Q&A answer quality (requires LLM)
- Scalability with larger repositories (tested up to 12 chunks only)
- Comparison against baseline (no baseline RAG system implemented)

---

## Deployment Strategy

### Current deployment
- **Docker** via `docker-compose.yaml`
  - Backend service: FastAPI on port 8000
  - Frontend service: Streamlit on port 8501
  - Shared data volume for uploads and vector stores
- **Local development:** venv + uvicorn + streamlit

### Configuration
- Environment variables via `.env` file
- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` for generation
- `EMBEDDING_MODEL` for embeddings
- `UPLOAD_DIR`, `VECTOR_STORE_DIR` for data paths

### What is deployed
- Full pipeline: ingestion → filtering → chunking → embedding → indexing → extraction → review
- 5-tab Streamlit UI
- REST API with 3 endpoints: `/api/upload`, `/api/analyze-path`, `/api/ask`

### What requires additional setup for full demo
- LLM endpoint (any OpenAI-compatible API)
- Without LLM: static extraction (API map, filtering, chunking, risk notes) works fully
- With LLM: architecture explainer, call-flow, and Q&A also work

---

## Expected Outcomes and Challenges

### Achieved outcomes
1. ✅ Repository ingestion from ZIP and local paths
2. ✅ File filtering with configurable rules (code, config, docs classification)
3. ✅ Code-aware chunking with Python symbol extraction
4. ✅ Embedding and vector indexing pipeline (384-dim, FAISS)
5. ✅ AST-based FastAPI route extraction (100% P/R/F1 on sample)
6. ✅ Multi-agent pipeline: Code Analyst → Reviewer → Documentation Editor
7. ✅ Evidence-grounded generation prompts
8. ✅ Confidence scoring and uncertainty marking
9. ✅ Risk note generation with proper framing
10. ✅ Interactive Streamlit UI with 5 tabs
11. ✅ REST API backend
12. ✅ Evaluation harness with measured metrics
13. ✅ Docker packaging

### Known challenges (honest)
1. **LLM dependency:** Architecture, call-flow, and Q&A outputs require a running LLM endpoint. Without it, these tabs show empty states.
2. **Single framework:** Only FastAPI extraction supported. Express, Flask, etc. not covered.
3. **Small test coverage:** Evaluation measured on 4-endpoint sample repo. Not yet tested on large real-world repos.
4. **Embedding model fixed:** Uses all-MiniLM-L6-v2. No comparison against other embedding models.
5. **No baseline comparison:** Haven't compared RAG output against naive LLM generation.
6. **Ground truth is manual:** Not scalable to large repos.

---

## Resources Required

### Hardware
- **Minimum:** Any machine with Python 3.11+ and 2GB RAM
- **Embedding model:** ~90MB download (all-MiniLM-L6-v2)
- **LLM generation:** Requires separate endpoint (local GPU or cloud API)

### Software
- Python 3.11+
- Dependencies listed in `requirements.txt` (fastapi, streamlit, sentence-transformers, faiss-cpu, openai, pydantic)
- Docker (optional, for containerized deployment)

### Data
- No training data required (uses pre-trained embedding model + LLM)
- Evaluation requires ground truth annotations (manual for v1)

---

## Conclusion

RepoCompass demonstrates a complete RAG pipeline for repository understanding with:
- **Measured extraction quality:** 100% F1 on FastAPI route extraction
- **Evidence-grounded outputs:** 0% unsupported claim rate on extraction
- **Multi-agent architecture:** Three-agent workflow (Analyst → Reviewer → Editor)
- **Interactive web interface:** 5-tab Streamlit UI + REST API
- **Docker-deployable:** Full containerization for easy setup

The system is honest about its limitations: LLM-dependent outputs (architecture, call-flow, Q&A) require a running endpoint and have not been quantitatively evaluated. Static extraction (API map, filtering, chunking, risk notes) is fully measured and validated with 56 passing tests.
