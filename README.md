# RepoCompass

RepoCompass is a capstone project focused on turning an unfamiliar software repository into grounded, developer-facing documentation. The system is intended to ingest a repository, retrieve relevant code and configuration evidence, and generate the following artifacts:

- a system / architecture explainer
- an API endpoint inventory
- a high-level call-flow summary
- evidence-linked risk notes for ambiguous or potentially unsafe areas
- Ask-Repo Q&A answers grounded in repository evidence

This README includes both:
1. the repo-facing build and execution context, and
2. the core project context from the capstone proposal,
so that a human developer or coding agent can understand the purpose, scope, deliverables, and guardrails without needing to read the report first.

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

The target outputs are:
- system / architecture explanation
- API endpoint inventory
- high-level call-flow summary
- evidence-linked risk notes

### Why this project exists
The project is designed to solve a practical developer productivity problem: reducing the time and effort required to understand an unfamiliar codebase while keeping outputs auditable and grounded in source evidence.

---

## Project Summary

RepoCompass follows a Retrieval-Augmented Generation workflow. Repository code, configuration, and documentation are indexed first. The model is then expected to generate outputs only from retrieved repository evidence instead of relying on unsupported memory-based generation.

The project also follows a multi-agent workflow:
- a **Code Analyst** drafts the outputs
- a **Security / Correctness Reviewer** challenges unsupported claims
- a **Documentation Editor** produces the final structured output

This project is not meant to be a generic code summarizer. It is meant to be an evidence-first repository intelligence tool.

---

## Main Deliverables

The intended deliverables for version 1 are:

1. **System / Architecture Explainer**
   - a grounded overview of the repository structure
   - major modules, responsibilities, and component relationships

2. **API Endpoint Inventory**
   - structured list of routes/endpoints for one supported framework
   - route, method, handler location, and supporting evidence

3. **Call-Flow Summary**
   - high-level request / execution flow for major paths
   - dependency and interaction summary where supported by evidence

4. **Risk Notes**
   - evidence-linked notes for uncertainty, weak coverage, ambiguous ownership, or potentially unsafe logic
   - phrased as indicators for review, not definitive security findings

5. **Ask-Repo Q&A**
   - answers to repository questions grounded in retrieved source evidence

---

## Core Principles

### 1. Evidence first
- No repository-specific claim without supporting repository evidence.
- If evidence is partial, the output must say so.
- If evidence is missing, the output must explicitly state: `insufficient evidence`.

### 2. No hallucinated architecture
- Do not invent modules, services, APIs, dependencies, or flows.
- Do not assume intent where code does not support it.

### 3. Single-framework scope for v1
- API extraction should support only one ecosystem/framework first.
- The extractor should be modular enough for future extension.

### 4. Risk indicators, not final vulnerability claims
- Security and correctness notes should be framed as review signals.
- RepoCompass should not present speculative findings as proven vulnerabilities.

### 5. Practical capstone execution
- Prioritize a reliable demo over broad unsupported scope.
- Prefer measurable, testable outputs over ambitious but weakly validated features.

---

## Proposed Technical Stack

The proposal defines the following implementation direction:

- **LLM inference:** Hugging Face Transformers + PyTorch
- **RAG indexing:** embeddings + FAISS or Chroma
- **Repository parsing:** file-type filtering + code-aware chunking
- **Backend:** FastAPI
- **Web UI:** Streamlit
- **Packaging / deployment:** optional Docker, local or Colab-runnable demo

The selected model direction in the proposal is a **Mistral 7B Instruct-class model**, primarily used for synthesis from retrieved evidence rather than free-form generation.

---

## Version 1 Scope

Version 1 should focus on these capabilities:

### Repository ingestion
- accept repository input as ZIP or local source
- extract repository contents
- filter to relevant source, config, and markdown files
- exclude generated, irrelevant, or oversized files where appropriate

### Chunking and indexing
- perform code-aware chunking
- retain metadata such as file path, symbol name, and source range where available
- generate embeddings
- build a searchable vector index

### API extraction
- support one framework only for the initial release
- extract route definitions and handler mappings
- output structured JSON

### Grounded generation
- generate system map / architecture explanation from retrieved evidence
- generate API map from extracted and retrieved evidence
- generate call-flow summary from retrieved repository evidence

### Multi-agent review
- draft output
- challenge unsupported claims
- finalize outputs with explicit uncertainty markers where needed

### Web UI
- support the following tabs or views:
  - System Map
  - API Map
  - Call-Flow Summary
  - Risk Notes
  - Ask-Repo Q&A

### Evaluation harness
- evaluate API extraction quality where ground truth exists
- measure groundedness and unsupported-claim rate
- record runtime and resource usage where practical

---

## Out of Scope for Version 1

To keep the project realistic and prevent drift, the following are not required in the first implementation unless added later deliberately:

- full support for many frameworks at once
- full multi-language static analysis across all ecosystems
- production-grade vulnerability scanning
- production multi-tenant deployment
- large-scale cloud indexing for very large repositories
- autonomous code changes to the uploaded repository

---

## Recommended Build Order

The practical build sequence for this repo is:

1. repository ingestion
2. file filtering
3. code-aware chunking
4. metadata schema
5. embeddings and vector index
6. single-framework API extractor
7. grounded generation pipeline
8. reviewer / challenge step
9. Streamlit UI
10. evaluation harness

This build order keeps the project testable early and aligned with the original proposal.

---

## Suggested Repository Structure

```text
RepoCompass/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py
│   ├── config.py
│   └── schemas.py
├── backend/
│   ├── api/
│   ├── services/
│   └── pipelines/
├── frontend/
│   └── streamlit_app.py
├── rag/
│   ├── chunking/
│   ├── embeddings/
│   ├── indexing/
│   └── retrieval/
├── extractors/
│   └── api/
├── agents/
│   ├── code_analyst.py
│   ├── reviewer.py
│   └── documentation_editor.py
├── evaluators/
│   └── metrics.py
├── tests/
├── data/
│   ├── sample_repos/
│   └── eval_sets/
└── docs/
    ├── PROJECT_BRIEF.md
    ├── AGENT37_INSTRUCTIONS.md
    ├── TASKS.md
    └── OUTPUT_FORMATS.md
```

This is a recommended implementation structure for organizing the project. It is not a claim that all of these files or folders already exist.

---

## Local Setup

### 1. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run backend

```bash
uvicorn app.main:app --reload
```

### 4. Run UI

```bash
streamlit run frontend/streamlit_app.py
```

Adjust entrypoints if the final repo structure differs.

---

## Engineering Rules

- keep all repo-specific outputs evidence-grounded
- separate observed facts from interpretation
- reject unsupported claims
- log uncertainty explicitly
- prefer modular and testable components
- centralize configuration
- use structured schemas for machine-readable outputs
- do not silently ignore parser, retrieval, or extraction failures
- write small validation tests for chunking, extraction, and retrieval logic

---

## Expected Success Criteria

A successful project demo should be able to:

- ingest a repository
- build an index over relevant source material
- extract API information for one supported framework
- generate a grounded architecture explainer
- generate a grounded call-flow summary
- produce evidence-linked risk notes
- answer Ask-Repo questions using retrieved evidence
- show measurable evaluation metrics for at least part of the pipeline

---

## Documentation Included in This Repo

This repo should include the following support documents:

- `docs/PROJECT_BRIEF.md` — concise project scope and project-level direction
- `docs/AGENT37_INSTRUCTIONS.md` — strict operating instructions for Agent 37
- `docs/TASKS.md` — execution roadmap and implementation checklist
- `docs/OUTPUT_FORMATS.md` — required output schemas and formatting rules

These files are intended to reduce ambiguity for both human collaborators and coding agents.

---

## Guidance for Coding Agents

If you are an engineering agent or coding assistant working in this repo:

- read `README.md` first for full project context
- read the files inside `docs/` before making changes
- do not invent missing features and present them as complete
- identify what exists, what is missing, and what should be built next
- optimize for a reliable capstone demo with grounded outputs
- surface uncertainty early instead of masking it

