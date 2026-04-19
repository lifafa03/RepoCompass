# RepoCompass

RepoCompass is a capstone project focused on turning an unfamiliar software repository into grounded, developer-facing documentation. The system is intended to ingest a repository, retrieve relevant code and configuration evidence, and generate the following artifacts:

- a system / architecture explainer
- an API endpoint inventory
- a high-level call-flow summary
- evidence-linked risk notes for ambiguous or potentially unsafe areas
- Ask-Repo Q&A answers grounded in repository evidence

---

## Quick Start

### 1. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure LLM (required for generation, optional for static extraction)

```bash
cp .env.example .env
# Edit .env with your LLM endpoint. Options:
#   - OpenAI:   LLM_BASE_URL=https://api.openai.com/v1  LLM_API_KEY=sk-...  LLM_MODEL=gpt-4o-mini
#   - Local:    LLM_BASE_URL=http://localhost:11434/v1   LLM_API_KEY=not-needed  LLM_MODEL=mistral
#   - vLLM:     LLM_BASE_URL=http://localhost:8000/v1    LLM_API_KEY=not-needed  LLM_MODEL=mistral-7b-instruct
```

### 4. Run the backend API

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Run the Streamlit UI

```bash
streamlit run frontend/streamlit_app.py --server.port 8501
```

### 6. Run the evaluation harness

```bash
python evaluators/run_evaluation.py
```

### 7. Run the test suite

```bash
pytest tests/ -v
```

### Docker

```bash
docker-compose up --build
```

Backend: http://localhost:8000 | Frontend: http://localhost:8501

### What works without an LLM

The following pipeline stages are fully static and work without any LLM configured:
- Repository ingestion (ZIP + local path)
- File filtering and classification
- Code-aware chunking (Python symbol-aware)
- Embedding + FAISS vector index
- FastAPI route extraction (AST-based)
- Evidence validation and confidence scoring
- Evaluation metrics (P/R/F1, groundedness)

The following require an LLM endpoint:
- Architecture explainer generation
- Call-flow summary generation
- Ask-Repo Q&A

---

## Proposal Context

### Academic context
- **Course:** DS552 – Generative AI
- **Project type:** Capstone project proposal and implementation
- **Project title:** RepoCompass: Multi-Agent RAG Web App for Codebase Architecture Explainers and API Mapping

### Problem statement
Modern development teams spend significant time understanding unfamiliar repositories, locating where APIs are implemented, identifying component boundaries, and tracing data flow across services and modules. In many repositories, documentation is incomplete, outdated, or scattered across source files, configuration, and markdown documents.

### Project objective
The objective of RepoCompass is to build a web application that ingests a software repository and produces grounded, developer-oriented outputs that improve repository understanding and onboarding speed.

---

## Project Summary

RepoCompass follows a Retrieval-Augmented Generation workflow. Repository code, configuration, and documentation are indexed first. The model is then expected to generate outputs only from retrieved repository evidence instead of relying on unsupported memory-based generation.

The project also follows a multi-agent workflow:
- a **Code Analyst** drafts the outputs
- a **Security / Correctness Reviewer** challenges unsupported claims
- a **Documentation Editor** produces the final structured output

---

## Main Deliverables

1. **System / Architecture Explainer** — grounded overview of repository structure
2. **API Endpoint Inventory** — structured route list with handler locations and evidence
3. **Call-Flow Summary** — high-level request/execution flow
4. **Risk Notes** — evidence-linked indicators for uncertainty or unsafe logic
5. **Ask-Repo Q&A** — answers grounded in retrieved source evidence

---

## Core Principles

1. **Evidence first** — no repo-specific claim without evidence
2. **No hallucinated architecture** — don't invent modules or flows
3. **Single-framework scope for v1** — FastAPI only, extensible later
4. **Risk indicators, not vulnerability claims** — frame as review signals
5. **Practical capstone execution** — reliable demo over broad unsupported scope

---

## Technical Stack

- **LLM inference:** OpenAI-compatible API (local or remote)
- **RAG indexing:** sentence-transformers + FAISS
- **Repository parsing:** file-type filtering + code-aware chunking
- **Backend:** FastAPI
- **Web UI:** Streamlit
- **Deployment:** Docker

---

## Repository Structure

```text
RepoCompass/
├── app/                    # FastAPI app, config, Pydantic schemas
├── backend/
│   ├── api/routes.py       # REST endpoints: /upload, /analyze-path, /ask
│   ├── services/           # Ingestion, LLM client
│   └── pipelines/          # Full analysis pipeline
├── frontend/
│   └── streamlit_app.py    # 5-tab UI
├── rag/
│   ├── chunking/           # File filtering + code-aware chunking
│   ├── embeddings/         # sentence-transformers embedding
│   ├── indexing/           # FAISS vector store
│   └── retrieval/          # Evidence retrieval
├── extractors/api/         # AST-based FastAPI route extractor
├── agents/                 # Code Analyst, Reviewer, Doc Editor
├── evaluators/             # P/R/F1, groundedness, runtime metrics
├── tests/                  # 56 passing tests
├── data/                   # uploads, vector stores, eval sets
└── docs/                   # PROJECT_BRIEF, TASKS, OUTPUT_FORMATS, AGENT37_INSTRUCTIONS
```

---

## Engineering Rules

- keep all repo-specific outputs evidence-grounded
- separate observed facts from interpretation
- reject unsupported claims
- log uncertainty explicitly
- prefer modular and testable components
- centralize configuration
- use structured schemas for machine-readable outputs

---

## Success Criteria

A successful demo should:
- ingest a repository (ZIP or local path)
- build an index over relevant source material
- extract API information for FastAPI
- generate a grounded architecture explainer (with LLM)
- generate a grounded call-flow summary (with LLM)
- produce evidence-linked risk notes
- answer Ask-Repo questions using retrieved evidence (with LLM)
- show measurable evaluation metrics
