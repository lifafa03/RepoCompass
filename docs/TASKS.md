# Tasks

This file defines the concrete work plan for RepoCompass. It is intended to keep implementation focused and prevent drift.

## Status Labels

- `TODO` = not started
- `IN PROGRESS` = actively being built
- `BLOCKED` = waiting on a decision or dependency
- `DONE` = implemented and validated

## Phase 0 — Repository Audit

### Task 0.1 — Inspect current codebase
**Status:** TODO

**Goal:**
Understand the current repository before making structural changes.

**Output:**
- module inventory
- current entrypoints
- dependency map
- missing components list

**Acceptance criteria:**
- major directories identified
- current implementation boundaries documented
- unknowns explicitly called out

---

### Task 0.2 — Confirm v1 framework target
**Status:** TODO

**Goal:**
Choose the single framework to support for API extraction in v1.

**Output:**
- chosen framework documented in config or docs
- framework-specific extraction approach defined

**Acceptance criteria:**
- v1 extractor scope is explicit
- extractor design leaves room for future extension

## Phase 1 — Ingestion and Parsing

### Task 1.1 — Implement repository ingestion
**Status:** TODO

**Goal:**
Allow the system to ingest a repository from a ZIP upload or local path.

**Output:**
- ingestion service
- extraction logic
- basic input validation

**Acceptance criteria:**
- repository contents can be enumerated
- extraction errors are surfaced clearly
- unsupported inputs fail safely

---

### Task 1.2 — File filtering
**Status:** TODO

**Goal:**
Keep only relevant files for indexing.

**Output:**
- configurable allowlist / denylist rules
- filtering logs or counters

**Acceptance criteria:**
- source, config, and docs files can be retained
- generated / binary / oversized files can be skipped

---

### Task 1.3 — Code-aware chunking
**Status:** TODO

**Goal:**
Split files into retrievable chunks without destroying useful local structure.

**Output:**
- chunking module
- chunk metadata structure

**Acceptance criteria:**
- chunks include file path and source location
- chunk sizes are bounded
- chunking strategy is deterministic enough to test

## Phase 2 — Embeddings and Indexing

### Task 2.1 — Metadata schema
**Status:** TODO

**Goal:**
Define the canonical structure for indexed chunks.

**Output:**
- schema for chunk id, file path, language, symbol, line range, and content

**Acceptance criteria:**
- schema is documented
- retrieval pipeline can consume it consistently

---

### Task 2.2 — Embeddings pipeline
**Status:** TODO

**Goal:**
Generate embeddings for repository chunks.

**Output:**
- embeddings service
- batching logic
- caching hooks if needed

**Acceptance criteria:**
- embeddings can be produced for chunked content
- failures are logged clearly

---

### Task 2.3 — Vector index
**Status:** TODO

**Goal:**
Store and retrieve repository evidence using FAISS or Chroma.

**Output:**
- index builder
- retriever interface

**Acceptance criteria:**
- chunks can be indexed
- retrieval returns content plus metadata

## Phase 3 — API Extraction

### Task 3.1 — Implement v1 framework extractor
**Status:** TODO

**Goal:**
Extract API endpoint information for one chosen framework.

**Output:**
- framework-specific extractor
- structured endpoint records

**Acceptance criteria:**
- method, route, handler location, and evidence are captured when present
- uncertain records expose confidence or uncertainty

---

### Task 3.2 — Structured API map output
**Status:** TODO

**Goal:**
Produce machine-readable API inventory output.

**Output:**
- JSON export that matches `docs/OUTPUT_FORMATS.md`

**Acceptance criteria:**
- output is schema-consistent
- evidence references are included

## Phase 4 — Grounded Generation

### Task 4.1 — Architecture explainer generation
**Status:** TODO

**Goal:**
Generate a readable system explanation from retrieved evidence.

**Output:**
- architecture generation pipeline

**Acceptance criteria:**
- major claims cite retrieved evidence
- unsupported claims are rejected or marked uncertain

---

### Task 4.2 — Call-flow summary generation
**Status:** TODO

**Goal:**
Generate a high-level call-flow summary for major request paths.

**Output:**
- call-flow generation pipeline

**Acceptance criteria:**
- flows are evidence-backed
- unclear paths are labeled as partial or uncertain

## Phase 5 — Review Layer

### Task 5.1 — Reviewer logic
**Status:** TODO

**Goal:**
Challenge unsupported statements before final output.

**Output:**
- review step or reviewer agent logic

**Acceptance criteria:**
- weak claims can be flagged or removed
- output can include `insufficient evidence`

---

### Task 5.2 — Risk note generation
**Status:** TODO

**Goal:**
Generate risk indicators tied to source evidence.

**Output:**
- risk note generator

**Acceptance criteria:**
- notes are framed as indicators, not definitive vulnerabilities
- each note includes evidence and confidence

## Phase 6 — UI

### Task 6.1 — Streamlit application shell
**Status:** TODO

**Goal:**
Create a usable interface for the capstone demo.

**Output:**
- tabs for System Map, API Map, Call-Flow Summary, Risk Notes, Ask-Repo Q&A

**Acceptance criteria:**
- main tabs render
- each tab can display generated output or clear empty-state messaging

---

### Task 6.2 — Ask-Repo Q&A
**Status:** TODO

**Goal:**
Allow user questions against indexed repository evidence.

**Output:**
- retrieval-based question answering path

**Acceptance criteria:**
- answers include evidence
- unsupported answers are refused or marked insufficient

## Phase 7 — Evaluation

### Task 7.1 — API map evaluation
**Status:** TODO

**Goal:**
Evaluate extracted endpoints against known ground truth when available.

**Output:**
- precision / recall / F1 calculation support

**Acceptance criteria:**
- metric calculation runs on at least one evaluation set

---

### Task 7.2 — Groundedness metrics
**Status:** TODO

**Goal:**
Measure citation coverage and unsupported claim rate.

**Output:**
- evaluation script or report

**Acceptance criteria:**
- at least one run can quantify groundedness outputs

---

### Task 7.3 — Runtime and resource tracking
**Status:** TODO

**Goal:**
Track latency and resource usage for the capstone demo.

**Output:**
- timing logs
- simple resource reporting

**Acceptance criteria:**
- indexing and generation steps can report time

## Stretch Tasks

These are optional and should only begin after the core workflow works end to end.

- add support for a second framework
- improve chunking with parser-aware logic such as Tree-sitter
- add Docker packaging
- add caching for repeated repo analysis
- add exportable report generation

## Priority Rule

Do not start stretch tasks until the following are working together:
- ingestion
- chunking
- indexing
- API extraction
- grounded generation
- reviewer logic
- UI
