# Project Brief

## Project Name

RepoCompass: Multi-Agent RAG Web App for Codebase Architecture Explainers and API Mapping

## Problem

Developers often spend too much time understanding unfamiliar repositories, locating API implementations, identifying component boundaries, and tracing data or request flows. Documentation is often incomplete or stale, and critical context is scattered across code, configs, and markdown files. fileciteturn0file0L8-L16

## Objective

Build a web application that ingests a software repository and produces grounded, developer-oriented outputs:

1. system / architecture explainer
2. API endpoint inventory
3. high-level call-flow summary
4. evidence-linked risk notes for uncertain or potentially unsafe areas
5. Ask-Repo Q&A grounded in repository evidence

The proposal states that these outputs should be generated using retrieved repository evidence rather than unsupported model memory. fileciteturn0file0L8-L16 fileciteturn0file0L33-L43

## Product Concept

RepoCompass is a developer productivity tool that converts repositories into auditable architecture and API documentation. It is intended to support onboarding, API discovery, and change impact reasoning. fileciteturn0file0L28-L36

## Primary Use Cases

### Developer onboarding and system comprehension
Generate a readable architecture explainer and module map.

### API discovery and verification
Produce a structured API map listing routes, methods, handler locations, and major assumptions.

### Change impact reasoning
Provide a grounded call-flow summary for major request paths and dependencies. fileciteturn0file0L28-L36

## Method

The system should use a Retrieval-Augmented Generation workflow:
- ingest repository code, configs, and docs
- chunk and index relevant content
- retrieve evidence for each output
- generate outputs only from retrieved evidence
- use a multi-agent review process before finalizing results

The proposal defines three roles:
- Code Analyst
- Security/Correctness Reviewer
- Documentation Editor fileciteturn0file0L33-L43

## Proposed Stack

The proposal lists the following stack:
- Hugging Face Transformers + PyTorch for LLM inference
- embeddings + FAISS/Chroma for RAG indexing
- file-type filtering + code-aware chunking for parsing
- FastAPI for backend
- Streamlit for web UI
- Docker as optional packaging / deployment support fileciteturn0file0L44-L55

## Version 1 Scope

Version 1 should include:
- repo upload or local repo ingestion
- relevant file extraction and filtering
- code-aware chunking
- embeddings + vector index with metadata
- API extraction for one framework only
- grounded generation for architecture, API inventory, and call-flow summary
- review step that rejects unsupported claims
- UI tabs for the main outputs
- basic evaluation support

## Explicit Constraints

- No unsupported repository-specific claims
- No invented endpoints, modules, or flows
- One supported framework first
- Security output should be framed as risk indicators, not definitive vulnerability claims
- Optimize for a practical capstone demo, not a full enterprise platform

## Suggested Supported Framework for v1

Choose one and commit early:
- FastAPI, or
- Express

Pick the framework that best matches the repositories you will use for demos and evaluation.

## Inputs

Expected system inputs:
- repository ZIP or local repository path
- source files
- configuration files
- markdown / docs
- optional evaluation repo with known API ground truth

## Outputs

Required system outputs:
- architecture explainer
- API map
- call-flow summary
- risk notes
- Ask-Repo Q&A answers

Output schemas are defined in `docs/OUTPUT_FORMATS.md`.

## Success Criteria

A successful capstone build should allow a user to ingest a repository and generate the required artifacts with grounded evidence. The proposal’s evaluation criteria emphasize runtime, resource usage, API map quality, citation coverage, unsupported claim rate, and scalability trends within the project’s scope. fileciteturn0file0L72-L90

## Known Challenges

The proposal already identifies major risks:
- hallucination risk
- framework diversity
- large repository performance
- unsafe interpretation of security output

It also proposes mitigation through citation requirements, scoping, filtering, caching, and framing outputs as indicators rather than certainty. fileciteturn0file0L92-L107
