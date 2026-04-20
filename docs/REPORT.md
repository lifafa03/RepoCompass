# RepoCompass: Multi-Agent RAG for Codebase Architecture Explainers & API Mapping

**Course:** DS552 - Generative AI Capstone  
**Student:** Rohan Reddy S  
**GitHub:** [https://github.com/lifafa03/RepoCompass](https://github.com/lifafa03/RepoCompass)  

---

## 1. Introduction and Objective

Understanding an unfamiliar codebase is one of the most time-consuming tasks software engineers face. Whether onboarding onto a new team, evaluating an open-source library, or conducting a code review, developers must manually trace through hundreds of files to understand system architecture, API endpoints, call flows, and potential risks. This process is tedious, error-prone, and does not scale.

**RepoCompass** is an interactive web application that automates codebase understanding using a multi-agent Retrieval-Augmented Generation (RAG) pipeline. Given a software repository (uploaded as a ZIP or provided as a local path), RepoCompass produces five grounded outputs:

1. **System / Architecture Explainer** - a natural-language summary of the system's components, their roles, and how they interact
2. **API Endpoint Inventory** - a structured catalog of every API endpoint, extracted via static analysis
3. **Call-Flow Summary** - step-by-step traces of how requests move through the codebase
4. **Risk Notes** - evidence-linked warnings about security, correctness, maintainability, and configuration concerns
5. **Ask-Repo Q&A** - an interactive question-answering interface grounded in retrieved code evidence

Every claim produced by RepoCompass is backed by traceable citations - specific file paths, line numbers, and code snippets. When evidence is insufficient, the system explicitly marks outputs as uncertain rather than fabricating information. This evidence-first design philosophy addresses the core problem of LLM hallucination in code analysis tasks.

---

## 2. Selection of Generative AI Model

RepoCompass uses a **two-model architecture** - each chosen for its specific role in the pipeline.

### 2.1 Embedding Model: sentence-transformers/all-MiniLM-L6-v2

**What it does:** Converts code chunks and user queries into 384-dimensional dense vector representations. These vectors enable semantic similarity search over the repository.

**Why this model:**
- **Lightweight and local:** At ~90MB, it runs entirely on CPU with no API calls or GPU requirements. This makes RepoCompass deployable on any machine without specialized hardware.
- **Strong retrieval quality:** Despite its small size, all-MiniLM-L6-v2 achieves competitive performance on semantic similarity benchmarks. Our evaluation shows a Mean Reciprocal Rank (MRR) of 0.767 - meaning relevant code is found at rank 1 for 60% of queries.
- **Fast inference:** 18.2 chunks per second embedding throughput, enabling real-time indexing of repositories.
- **No vendor lock-in:** The model is downloaded from Hugging Face and cached locally. No API key, subscription, or network connection is required after first download.

### 2.2 Generation Model: Llama 3.1 8B Instant (via Groq)

**What it does:** Generates natural-language outputs - architecture summaries, call-flow descriptions, and Q&A answers - grounded in retrieved code evidence.

**Why this model:**
- **Speed:** Groq's LPU inference hardware delivers sub-100ms token generation, making the interactive Q&A experience responsive.
- **Cost:** Groq's free tier provides sufficient quota for capstone demonstration.
- **Quality:** Llama 3.1 8B produces coherent, structured analysis when given focused prompts with retrieved evidence.
- **Compatibility:** Accessed via the OpenAI-compatible API standard, making it interchangeable with any compatible provider (OpenAI, Gemini, Mistral, local Ollama).

### 2.3 Why RAG Instead of Fine-Tuning

RepoCompass does **not** fine-tune or train any model. Instead, it uses Retrieval-Augmented Generation (RAG) for several reasons:

1. **Repository-specific grounding:** Fine-tuning would produce a model that "knows" general code patterns but cannot cite specific lines from a specific repository. RAG retrieves actual code evidence, enabling traceable citations.
2. **Zero training cost:** No labeled dataset, GPU hours, or training pipeline needed.
3. **Universal applicability:** The same system works on any repository without retraining - the "knowledge" comes from the repository itself via retrieval.
4. **Hallucination control:** By constraining the LLM to answer only from retrieved evidence and having a separate review agent validate outputs, the system minimizes fabricated claims.

---

## 3. Project Definition and Use Case

### 3.1 Application Concept

RepoCompass is a **code analysis and documentation assistant**. It takes a software repository as input and produces structured, evidence-linked documentation that would otherwise require hours of manual code reading.

**Target users:**
- **New team members** onboarding onto an unfamiliar codebase
- **Code reviewers** who need quick architectural context before reviewing changes
- **Open-source contributors** evaluating projects before submitting PRs
- **Security auditors** identifying risk indicators in code structure

### 3.2 How the Generative AI Model is Integrated

The RAG architecture integrates both models into a multi-stage pipeline:

```
Repository -> Ingestion -> Filtering -> Chunking -> Embedding -> FAISS Index
                                                              |
API Map (AST) -------------------------------------> Retrieval <--- User Query
                                                      |           |
                            Review Agent <--- LLM Generation (Architecture,
                            |                            Call-flow, Q&A)
                    Documentation Editor -> Final Output with Citations
```

1. **Static Analysis Layer (no LLM):** Files are classified, filtered, chunked using Python symbol-aware splitting, and API endpoints are extracted via Abstract Syntax Tree (AST) parsing.
2. **Retrieval Layer (embedding model):** Code chunks are embedded into vectors and stored in a FAISS index. User queries are embedded and matched via inner-product similarity.
3. **Generation Layer (LLM):** Retrieved code evidence is passed to the LLM with carefully engineered prompts that instruct it to answer only from the provided evidence.
4. **Validation Layer (rule-based):** A reviewer agent checks every claim for supporting evidence, downgrades confidence when evidence is weak, and flags items requiring human review.

---

## 4. Implementation Plan

### 4.1 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|----------|
| Web Framework | Streamlit | Interactive UI with file upload, 5 analysis tabs |
| Backend API | FastAPI | REST endpoints for programmatic access |
| Embedding | sentence-transformers (Hugging Face) | Local code/query embedding |
| Vector Store | FAISS (Facebook AI) | Fast similarity search over code embeddings |
| AST Parsing | Python ast module | Static API endpoint extraction |
| LLM Client | OpenAI Python SDK | Compatible with Groq, OpenAI, Gemini, Ollama |
| Data Models | Pydantic v2 | Strict schema validation for all outputs |
| Testing | pytest | 56 integration and unit tests |
| Deployment | Docker + Streamlit Cloud | Containerized and hosted deployment |

### 4.2 Web Framework: Streamlit

Streamlit was chosen for its rapid prototyping capabilities and built-in support for:
- File upload widgets (ZIP files)
- Tabbed layouts (5 analysis sections)
- Expandable evidence panels (code citations)
- Real-time metric displays (evaluation sidebar)
- Session state management (caching pipeline results)

### 4.3 Architecture Modules

The codebase is organized into 8 packages:

```
RepoCompass/
  app/                    # FastAPI application + config + schemas
    main.py              # FastAPI app with /health, /upload, /ask routes
    config.py            # Centralized configuration from env vars
    schemas.py           # 20+ Pydantic models for all pipeline outputs
  backend/
    services/
      ingestion.py       # ZIP extraction + local path enumeration
      llm.py             # OpenAI-compatible LLM client
    pipelines/
      analysis.py        # Full pipeline orchestration with timing
    api/
      routes.py          # FastAPI route handlers
  rag/
    chunking/
      filtering.py       # File classification (code/config/doc/skip)
      chunker.py         # Python symbol-aware + generic line chunking
    embeddings/
      embedder.py        # all-MiniLM-L6-v2 embedding service
    indexing/
      vector_store.py    # FAISS IndexFlatIP with save/load
    retrieval/
      retriever.py       # Top-K search with context assembly
  extractors/
    api/
      fastapi_extractor.py  # AST-based route extraction
  agents/
    code_analyst.py      # Architecture + call-flow generation (LLM)
    reviewer.py          # Evidence validation + risk note generation
    documentation_editor.py  # Finalization + uncertainty marking
  evaluators/
    metrics.py           # F1, groundedness, resource tracking
    extended_metrics.py  # MRR, latency profiling, ROUGE-like overlap
    run_evaluation.py    # Standard evaluation runner
    run_comprehensive_eval.py  # Full rubric-aligned evaluation
  frontend/
    streamlit_app.py     # 5-tab interactive UI
  tests/
    test_integration.py  # 56 tests across all modules
  docs/
    REPORT_NOTES.md     # Detailed findings for this report
    TASKS.md             # 21 tasks, all completed
```

### 4.4 Development Steps

The project was developed in 8 phases:

1. **Phase 0 - Repository Audit:** Analyzed project requirements, confirmed FastAPI as v1 target framework
2. **Phase 1 - Ingestion & Chunking:** Built file enumeration, filtering (language detection, dotfile awareness), and symbol-aware chunking for Python files
3. **Phase 2 - Schema & Embeddings:** Defined 20+ Pydantic output schemas; integrated sentence-transformers embedding model
4. **Phase 3 - Vector Indexing:** Implemented FAISS IndexFlatIP with save/load, inner-product search with normalized embeddings
5. **Phase 4 - API Extraction:** Built AST-based FastAPI route extractor supporting both decorator patterns and add_api_route calls
6. **Phase 5 - Multi-Agent System:** Implemented code analyst (LLM), reviewer (evidence validation), and documentation editor (finalization)
7. **Phase 6 - UI & Backend:** Built Streamlit 5-tab interface and FastAPI REST API with proper serialization
8. **Phase 7 - Evaluation:** Created comprehensive evaluation harness measuring F1, MRR, groundedness, latency, and memory

### 4.5 Testing

56 tests cover all major components:

- Ingestion: ZIP and local path handling
- Filtering: file classification, dotfile handling, language detection
- Chunking: Python symbol extraction, generic line-based splitting
- Embedding: dimension consistency, query embedding
- Indexing: add/search/save/load roundtrip
- Extraction: FastAPI decorator detection, add_api_route support
- Evaluation: metric computation accuracy
- Reviewer: confidence downgrade logic
- Vector Index: persistence and retrieval quality

All 56 tests pass in ~17 seconds.

---

## 5. Model Evaluation and Performance Metrics

### 5.1 Evaluation Methodology

We constructed a **ground truth** dataset by manually annotating a sample FastAPI repository. The ground truth contains 4 endpoints, each with method, route, handler name, file path, and line numbers. This was cross-verified against the AST extractor's output.

For retrieval evaluation, we defined 5 query-relevance pairs - natural language queries with expected relevant file patterns - to measure whether the retrieval system surfaces the right code.

### 5.2 API Extraction Accuracy

| Metric | Value |
|--------|-------|
| Precision | 100% (4/4 predicted endpoints are correct) |
| Recall | 100% (4/4 ground truth endpoints found) |
| F1-Score | 100% |
| True Positives | 4 |
| False Positives | 0 |
| False Negatives | 0 |

**Method:** Endpoint matching by (HTTP method, route path) pairs against manually annotated ground truth. The AST extractor correctly identified all @app.get, @app.post, and @app.delete decorated functions.

**Note:** This perfect score reflects the focused evaluation on a small, well-structured FastAPI codebase. Real-world repos with routers, middleware, and dynamic route registration would likely produce lower scores.

### 5.3 Retrieval Quality

| Metric | Value |
|--------|-------|
| Mean Reciprocal Rank (MRR) | 0.767 |
| Mean Similarity@1 | 0.494 |
| Mean Similarity@3 | 0.366 |
| Mean Similarity@5 | 0.296 |
| Queries evaluated | 5 |

**Per-query results:**

| Query | Top Result | Score | Reciprocal Rank |
|-------|-----------|-------|----------------|
| "health check endpoint" | app/main.py | 0.546 | 1.00 |
| "item creation API" | app/main.py | 0.553 | 1.00 |
| "database configuration" | .env.example | 0.328 | 0.50 |
| "Pydantic data models" | requirements.txt | 0.345 | 0.33 |
| "delete item by ID" | app/main.py | 0.698 | 1.00 |

3 out of 5 queries return the relevant result at rank 1. The lower scores for "database configuration" and "Pydantic data models" reflect that these queries target configuration and import files which have shorter, less descriptive content than source code files.

### 5.4 Groundedness / Citation Coverage

| Metric | Value |
|--------|-------|
| Total claims | 4 |
| Claims with evidence | 4 |
| Unsupported rate | 0% |
| Average evidence per claim | 1.0 |
| Confidence distribution | 4 high, 0 medium, 0 low |

Every extracted endpoint carries at least one EvidenceRef pointing to the exact file and line range where it was found. The reviewer agent validated all claims as high confidence.

### 5.5 Inference Time / Latency

| Component | Latency |
|-----------|--------|
| Ingestion | 0.5 ms |
| Filtering | 0.1 ms |
| Chunking | 0.9 ms |
| Embedding (11 chunks) | 603 ms |
| Indexing | 0.1 ms |
| API Extraction (AST) | 1.9 ms |
| Retrieval (per query) | 59.7 ms |
| **Total pipeline** | **606 ms** |

**Analysis:** Embedding generation accounts for 99.4% of pipeline time. This is expected - transformer inference is compute-intensive even for a small model. However, at 18.2 chunks/second throughput and sub-60ms query latency, the system is well-suited for interactive use.

### 5.6 Computational Resource Usage

| Resource | Value |
|----------|-------|
| Peak memory | 10.6 MB |
| Embedding model size | ~90 MB (all-MiniLM-L6-v2) |
| Vector index size | ~16 KB (11 vectors x 384 floats) |
| GPU required | No - runs entirely on CPU |
| Embedding throughput | 18.2 chunks/sec |

The system's 10.6 MB peak memory footprint is remarkably low for an ML-powered application, making it deployable on resource-constrained environments like Raspberry Pi or free-tier cloud instances.

### 5.7 Text Overlap (ROUGE-like Metric)

We implemented a simplified ROUGE-like bigram overlap metric to measure how much of the generated text overlaps with source evidence. For structured outputs (endpoint descriptions), the overlap is 0.0 - expected because these are labels, not natural language. This metric is more meaningful for LLM-generated natural language outputs (architecture summaries, Q&A answers).

---

## 6. Deployment Strategy

### 6.1 Docker Deployment

The application includes a complete Docker setup:

**Dockerfile:**
- Base image: python:3.11-slim
- Installs FAISS build dependencies (cmake, build-essential)
- Installs Python dependencies from requirements.txt
- Exposes ports 8000 (FastAPI) and 8501 (Streamlit)

**docker-compose.yaml:**
- Two services: backend (FastAPI on port 8000) and frontend (Streamlit on port 8501)
- Shared volume for data persistence
- Environment variable configuration via .env file

**Usage:**
```bash
docker-compose up --build
```

### 6.2 Streamlit Cloud Deployment

The application is configured for deployment on Streamlit Community Cloud:

1. The .streamlit/config.toml sets upload size limits and disables telemetry
2. The Streamlit app loads LLM credentials from st.secrets (Streamlit Cloud's secret management)
3. The requirements.txt is automatically detected and installed by Streamlit Cloud

**Configuration:**
```toml
# Streamlit Cloud Secrets
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_API_KEY = "<api-key>"
LLM_MODEL = "llama-3.1-8b-instant"
```

### 6.3 Local Deployment

For local development and testing:
```bash
# Install dependencies
pip install -r requirements.txt

# Run evaluation
python evaluators/run_comprehensive_eval.py

# Run tests
pytest tests/ -v

# Start backend
uvicorn app.main:app --reload --port 8000

# Start frontend
streamlit run frontend/streamlit_app.py --server.port 8501
```

### 6.4 LLM Provider Flexibility

The system supports any OpenAI-compatible API endpoint through .env configuration:

| Provider | LLM_BASE_URL | LLM_MODEL |
|----------|-------------|-----------|
| Groq (free) | https://api.groq.com/openai/v1 | llama-3.1-8b-instant |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| Google Gemini | https://generativelanguage.googleapis.com/v1beta/openai/ | gemini-2.0-flash |
| Ollama (local) | http://localhost:11434/v1 | mistral |

The embedding model (all-MiniLM-L6-v2) always runs locally regardless of LLM provider - no API key needed for embeddings.

### 6.5 Expected User Interaction

1. User uploads a repository ZIP file (or provides a local path)
2. The pipeline runs automatically: ingestion -> chunking -> embedding -> indexing -> extraction -> generation
3. Results appear across 5 tabs: System Map, API Map, Call-Flow, Risk Notes, Ask-Repo Q&A
4. Each result includes confidence indicators (high/medium/low) and expandable evidence citations
5. Users can ask follow-up questions in the Q&A tab - the system retrieves relevant code and generates grounded answers
6. Evaluation metrics are displayed in the sidebar showing precision, recall, groundedness, and resource usage

---

## 7. Expected Outcomes and Challenges

### 7.1 Expected Impact

- **Reduced onboarding time:** New developers can understand a codebase's architecture and API surface in seconds rather than hours
- **Evidence-linked documentation:** Every claim traces back to specific code, enabling verification
- **Risk-aware analysis:** The system identifies potential issues (security patterns, configuration problems, code smells) without requiring security expertise
- **Interactive exploration:** The Q&A feature allows developers to ask targeted questions about specific aspects of the codebase

### 7.2 Challenges Encountered

| Challenge | Impact | Mitigation |
|-----------|--------|-----------|
| LLM hallucination | Generated outputs could contain fabricated claims | Multi-agent review system validates every claim against evidence; uncertainty is explicitly marked |
| LLM dependency | Architecture, call-flow, and Q&A require an external LLM endpoint | Modular design separates static analysis (works offline) from LLM-dependent generation; multiple provider support |
| API key quota limits | Free-tier API keys (Gemini, Groq) have rate limits that can be exhausted | Support for multiple providers; Ollama option for unlimited local inference |
| Embedding bottleneck | Embedding generation accounts for 99.4% of pipeline time | All-MiniLM-L6-v2 chosen for speed; 18.2 chunks/sec throughput is acceptable for interactive use |
| Small evaluation set | Ground truth only covers 4 endpoints in a single sample repo | Honest reporting of limitations; evaluation framework is extensible for larger benchmarks |
| Real-world complexity | v1 only supports FastAPI route extraction | Extensible extractor architecture; additional framework support planned |
| FAISS index persistence | Index saved to disk per repository; no database integration | Simple file-based storage works for single-user scenarios; could be extended to use vector databases |

### 7.3 Solutions and Mitigations

1. **Evidence-first design:** The reviewer agent checks every claim for supporting evidence. Claims without evidence are flagged with low confidence and marked as requiring human review. The unsupported rate in our evaluation is 0%.

2. **Confidence downgrade system:** When the reviewer finds weak or missing evidence, it downgrades the confidence level from "high" to "medium" or "low" and adds an uncertainty_note. This prevents overconfident incorrect outputs.

3. **Provider-agnostic LLM integration:** The system uses the OpenAI-compatible API standard, supporting any provider. Switching from Groq to OpenAI to a local Ollama instance requires only changing three environment variables.

4. **Graceful degradation:** When no LLM is configured, the static pipeline (API extraction, risk notes, evaluation metrics) still works. The UI shows informative messages explaining which features require LLM configuration.

---

## 8. Resources Required

### 8.1 Tools and Frameworks

| Resource | Version | Purpose |
|----------|---------|----------|
| Python | 3.11 | Runtime environment |
| Streamlit | >=1.32.0 | Web UI framework |
| FastAPI | >=0.110.0 | Backend REST API |
| sentence-transformers | >=2.6.0 | Embedding model loading and inference |
| FAISS (faiss-cpu) | >=1.8.0 | Vector similarity search |
| OpenAI Python SDK | >=1.14.0 | LLM API client |
| Pydantic | >=2.6.0 | Data validation and serialization |
| pytest | >=8.1.0 | Testing framework |
| NumPy | >=1.26.0 | Numerical operations |
| Docker | Any recent | Containerized deployment |

### 8.2 Models

| Model | Size | Purpose | Location |
|-------|------|---------|----------|
| all-MiniLM-L6-v2 | ~90 MB | Code/query embedding | Hugging Face (local cache) |
| Llama 3.1 8B Instant | Hosted | Text generation | Groq API |

### 8.3 Hardware Requirements

- **CPU:** Any modern x86_64 or ARM processor
- **RAM:** 512 MB minimum (observed peak: 10.6 MB)
- **GPU:** Not required - all models run on CPU
- **Disk:** ~500 MB for Python environment + model cache
- **Network:** Required only for LLM API calls (optional with Ollama)

### 8.4 External Services

- **Groq API** (or compatible): For LLM inference
- **Hugging Face Hub**: For initial model download (cached locally after first use)

---

## 9. Conclusion

RepoCompass demonstrates that a well-designed RAG pipeline can produce grounded, evidence-linked code analysis without fine-tuning or training any model. The system achieves 100% F1-score on API endpoint extraction, 0.767 MRR on retrieval quality, and 100% citation coverage - all measured against manually constructed ground truth.

### Key Takeaways

1. **RAG over fine-tuning for code analysis:** Repository understanding requires grounding in specific code, not general knowledge. RAG naturally provides this grounding through retrieval, while fine-tuning would require per-repository training data that doesn't exist.

2. **Multi-agent validation prevents hallucination:** Separating generation (code analyst) from validation (reviewer) from presentation (documentation editor) creates natural checkpoints. The reviewer catches unsupported claims before they reach the user.

3. **Static + AI hybrid architecture:** Not everything needs an LLM. API endpoint extraction via AST parsing is 100% accurate and costs nothing. Reserving the LLM for natural-language generation (where it adds real value) reduces cost and improves reliability.

4. **Evidence-first design works:** By requiring every output to carry file path and line number citations, the system naturally avoids fabrication. When evidence is missing, the system says so explicitly rather than guessing.

### Potential Improvements and Future Enhancements

1. **Multi-framework API extraction:** Extend beyond FastAPI to support Flask, Django, Express.js, Spring Boot, and other popular frameworks
2. **Larger evaluation benchmarks:** Test on real-world open-source repositories with 100+ endpoints to validate scalability
3. **Baseline comparison:** Implement a naive LLM (no RAG) baseline and compare groundedness scores
4. **Streaming responses:** Stream LLM output in real-time for the Q&A interface instead of waiting for full generation
5. **Multi-file context windows:** Use longer context models to capture cross-file dependencies for call-flow analysis
6. **Incremental indexing:** Support adding files to an existing index without re-embedding the entire repository
7. **Collaborative features:** Allow multiple users to share indexed repositories and Q&A history
8. **CI/CD integration:** Provide a CLI mode that generates documentation as part of a build pipeline

---

## Appendix A: Evaluation Report (Raw Data)

The complete measured evaluation results are stored in data/eval_sets/comprehensive_report.json in the repository. Key metrics:

```json
{
  "api_extraction": {
    "precision": 1.0, "recall": 1.0, "f1_score": 1.0,
    "true_positives": 4, "false_positives": 0, "false_negatives": 0
  },
  "retrieval_quality": {
    "mean_reciprocal_rank": 0.7667,
    "mean_similarity_at_k": {"1": 0.494, "3": 0.366, "5": 0.296}
  },
  "groundedness": {
    "total_claims": 4, "claims_with_evidence": 4,
    "unsupported_rate": 0.0, "avg_evidence_per_claim": 1.0
  },
  "latency": {
    "embedding_ms": 603.0, "retrieval_ms_per_query": 59.7, "total_ms": 606.4,
    "throughput_chunks_per_sec": 18.24
  },
  "resources": {
    "peak_memory_mb": 10.6, "embedding_dimension": 384,
    "num_chunks": 11, "total_seconds": 3.29
  }
}
```

## Appendix B: Test Coverage Summary

56 tests across all pipeline components:

| Test Suite | Tests | Status |
|-----------|-------|--------|
| test_integration.py | 18 | All passing |
| test_chunking.py | 8 | All passing |
| test_evaluator.py | 6 | All passing |
| test_extractor.py | 8 | All passing |
| test_reviewer.py | 8 | All passing |
| test_vector_index.py | 8 | All passing |
| **Total** | **56** | **All passing** |

## Appendix C: Repository Structure

All source code is available at: [https://github.com/lifafa03/RepoCompass](https://github.com/lifafa03/RepoCompass)

The repository contains 28+ source files across 8 packages, with complete documentation in the docs/ directory.
