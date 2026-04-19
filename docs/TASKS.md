# Tasks

This file defines the concrete work plan for RepoCompass. It is intended to keep implementation focused and prevent drift.

## Status Labels

- `TODO` = not started
- `IN PROGRESS` = actively being built
- `BLOCKED` = waiting on a decision or dependency
- `DONE` = implemented and validated

## Phase 0 — Repository Audit

### Task 0.1 — Inspect current codebase
**Status:** DONE

**Output:**
- Module inventory: 8 packages, 28+ source files
- Entrypoints: `app/main.py` (FastAPI), `frontend/streamlit_app.py` (Streamlit)
- Dependency map: fastapi → routes → pipeline → (ingestion, chunking, embeddings, indexing, extraction, agents)
- All major directories identified and populated

---

### Task 0.2 — Confirm v1 framework target
**Status:** DONE

**Output:**
- v1 framework: FastAPI (documented in `app/config.py:V1_FRAMEWORK`)
- AST-based extraction via `extractors/api/fastapi_extractor.py`
- Extractor design is class-based, extensible for future frameworks

## Phase 1 — Ingestion and Parsing

### Task 0.1 — Implement repository ingestion
**Status:** DONE

**Output:**
- `backend/services/ingestion.py`: ZIP extraction + local path copy + auto-unwrap
- Enumerate files respecting skip directories
- 5 integration tests covering ZIP, local, unwrap, skip dirs, error handling

---

### Task 1.2 — File filtering
**Status:** DONE

**Output:**
- `rag/chunking/filtering.py`: classify_file (code/config/docs), filter_files, detect_language
- Dotfile-aware classification (.env.*, .gitignore, Dockerfile)
- Configurable allow/deny via `app/config.py`
- 6 unit tests + 3 integration tests

---

### Task 1.3 — Code-aware chunking
**Status:** DONE

**Output:**
- `rag/chunking/chunker.py`: Python symbol-aware + generic line-based with overlap
- Chunks include chunk_id, file_path, language, symbol, line_start, line_end, content
- Deterministic chunk IDs (tested)
- 4 unit tests + 3 integration tests

## Phase 2 — Embeddings and Indexing

### Task 2.1 — Metadata schema
**Status:** DONE

**Output:**
- `app/schemas.py`: All Pydantic models matching OUTPUT_FORMATS.md
- EvidenceRef, ChunkRecord, Component, ArchitectureExplainer, APIEndpoint, APIMap, CallFlow, CallFlowSummary, RiskNote, RiskNotes, AskRepoAnswer

---

### Task 2.2 — Embeddings pipeline
**Status:** DONE

**Output:**
- `rag/embeddings/embedder.py`: SentenceTransformer (all-MiniLM-L6-v2, 384-dim)
- Batch embedding with normalize_embeddings for cosine similarity
- 2 integration tests for embed + query

---

### Task 2.3 — Vector index
**Status:** DONE

**Output:**
- `rag/indexing/vector_store.py`: FAISS IndexFlatIP with save/load (index.faiss + chunks.jsonl)
- `rag/retrieval/retriever.py`: retrieve, retrieve_as_evidence, retrieve_context
- 3 unit tests + 4 integration tests (including save/load roundtrip)

## Phase 3 — API Extraction

### Task 3.1 — Implement v1 framework extractor
**Status:** DONE

**Output:**
- `extractors/api/fastapi_extractor.py`: AST-based extraction of @decorator routes + add_api_route
- Captures method, route, handler_name, handler_location, evidence refs
- Confidence scoring via evidence presence
- 7 unit tests + 2 integration tests (P/R/F1 = 1.0 on sample repo)

---

### Task 3.2 — Structured API map output
**Status:** DONE

**Output:**
- APIMap schema with framework + endpoints list
- JSON export via model_dump(), validated against OUTPUT_FORMATS.md

## Phase 4 — Grounded Generation

### Task 4.1 — Architecture explainer generation
**Status:** DONE (requires LLM endpoint)

**Output:**
- `agents/code_analyst.py`: generate_architecture() with multi-query retrieval
- Evidence-grounded prompt with explicit "only from evidence" instruction
- JSON parsing with fallback to error message
- Review + finalize pipeline stages

---

### Task 4.2 — Call-flow summary generation
**Status:** DONE (requires LLM endpoint)

**Output:**
- `agents/code_analyst.py`: generate_callflow() with multi-query retrieval
- Partial flows allowed, missing transitions not guessed
- Fallback to empty CallFlowSummary on failure

## Phase 5 — Review Layer

### Task 5.1 — Reviewer logic
**Status:** DONE

**Output:**
- `agents/reviewer.py`: review_architecture (downgrades no-evidence), review_api_map (flags uncertain)
- Confidence downgrade for claims without evidence
- 5 unit tests

---

### Task 5.2 — Risk note generation
**Status:** DONE

**Output:**
- `agents/reviewer.py`: generate_risk_notes() — checks low-confidence components, unresolved handlers, partial flows
- `agents/documentation_editor.py`: finalize_risk_notes() — rewrites "vulnerability" → "potential risk indicator"
- Risk categories: security, correctness, maintainability, ambiguity, configuration
- Notes include evidence, confidence, requires_human_review flag

## Phase 6 — UI

### Task 6.1 — Streamlit application shell
**Status:** DONE

**Output:**
- `frontend/streamlit_app.py`: 5 tabs (System Map, API Map, Call-Flow, Risk Notes, Ask-Repo Q&A)
- Sidebar with ZIP upload + local path input
- Pipeline stats and evaluation metrics in sidebar
- Error handling, empty-state messaging

---

### Task 6.2 — Ask-Repo Q&A
**Status:** DONE (requires LLM endpoint)

**Output:**
- Pipeline.ask_repo() loads saved index, retrieves evidence, generates grounded answer
- Returns AskRepoAnswer with evidence refs, confidence, insufficient_evidence flag
- UI shows evidence expander, confidence badge

## Phase 7 — Evaluation

### Task 7.1 — API map evaluation
**Status:** DONE

**Output:**
- `evaluators/metrics.py`: evaluate_api_map() with P/R/F1 calculation
- Ground truth: `data/eval_sets/sample_fastapi_ground_truth.json`
- Measured: P=100%, R=100%, F1=100% on sample FastAPI repo (4 endpoints)
- 10 unit tests for metrics

---

### Task 7.2 — Groundedness metrics
**Status:** DONE

**Output:**
- `evaluators/metrics.py`: evaluate_groundedness() — citation coverage, unsupported rate, confidence distribution
- Measured: 4/4 claims evidenced, 0% unsupported rate, all high confidence
- Covers: components, system observations, endpoints, flow steps, risk notes

---

### Task 7.3 — Runtime and resource tracking
**Status:** DONE

**Output:**
- `evaluators/run_evaluation.py`: tracemalloc memory tracking + per-phase wall-clock timing
- `PipelineResult.stats`: timing for all 8 phases
- Measured: 3.14s total (embedding: 3.13s, extraction: 4ms, rest: <5ms), 10.6 MB peak

## Deployment

### Docker packaging
**Status:** DONE

**Output:**
- `Dockerfile`: Python 3.11-slim, FAISS build deps, pip install
- `docker-compose.yaml`: backend (port 8000) + frontend (port 8501)
- Data volume mount for persistence

## Stretch Tasks

### Exportable report generation
**Status:** DONE

**Output:**
- `PipelineResult.to_dict()` serializes full output as JSON
- FastAPI routes return complete analysis as structured JSON
- Evaluation report saved to `data/eval_sets/last_run_report.json`

### Remaining stretch (not started)
- Second framework extraction (Flask, Express)
- Tree-sitter chunking for better multi-language support
- Caching layer for repeated analyses
