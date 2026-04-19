"""Code Analyst agent: drafts initial outputs from retrieved evidence."""
import json
from rag.retrieval.retriever import Retriever
from backend.services.llm import generate
from app.schemas import ArchitectureExplainer, CallFlowSummary


ARCHITECTURE_PROMPT = """You are a Code Analyst. Analyze the following repository evidence and produce a system/architecture explainer.

RULES:
- Only make claims supported by the evidence below.
- If you are unsure, say so explicitly.
- Do NOT invent modules, services, or dependencies.
- Identify the major components, their roles, and relationships.

EVIDENCE:
{evidence}

Produce a JSON object with this structure:
{{
  "summary": "Concise architecture summary",
  "components": [
    {{
      "name": "Component name",
      "role": "What it does",
      "evidence": [{{"file_path": "...", "line_start": 0, "line_end": 0, "snippet_id": "..."}}],
      "confidence": "high|medium|low",
      "uncertainty_note": null or "why uncertain"
    }}
  ],
  "system_observations": [
    {{
      "claim": "Observation",
      "evidence": [{{"file_path": "...", "line_start": 0, "line_end": 0, "snippet_id": "..."}}],
      "confidence": "high|medium|low",
      "uncertainty_note": null or "why uncertain"
    }}
  ]
}}

Return ONLY valid JSON."""


CALLFLOW_PROMPT = """You are a Code Analyst. Analyze the following repository evidence and produce a high-level call-flow summary.

RULES:
- Only describe flows supported by evidence.
- If a flow is partial, mark it as partial.
- Do NOT guess transitions between components.

EVIDENCE:
{evidence}

Produce a JSON object:
{{
  "flows": [
    {{
      "name": "Flow name",
      "entrypoint": "Where it starts",
      "steps": [
        {{
          "step_number": 1,
          "description": "What happens",
          "evidence": [{{"file_path": "...", "line_start": 0, "line_end": 0, "snippet_id": "..."}}],
          "confidence": "high|medium|low",
          "uncertainty_note": null
        }}
      ],
      "overall_confidence": "high|medium|low",
      "uncertainty_note": null
    }}
  ]
}}

Return ONLY valid JSON."""


def generate_architecture(retriever: Retriever) -> ArchitectureExplainer:
    queries = [
        "main application entry point setup",
        "module structure and imports",
        "class definitions and responsibilities",
        "configuration and dependencies",
        "API routes and handlers",
    ]
    all_context = []
    for q in queries:
        ctx = retriever.retrieve_context(q, top_k=8)
        all_context.append(ctx)
    combined = "\n\n===\n\n".join(all_context)
    prompt = ARCHITECTURE_PROMPT.format(evidence=combined[:12000])
    try:
        response = generate(prompt)
        data = json.loads(response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
        return ArchitectureExplainer.model_validate(data)
    except Exception as e:
        return ArchitectureExplainer(summary=f"Failed to generate architecture explainer: {e}")


def generate_callflow(retriever: Retriever) -> CallFlowSummary:
    queries = [
        "request handling flow from entry to response",
        "data processing pipeline steps",
        "middleware and service layer interactions",
    ]
    all_context = []
    for q in queries:
        ctx = retriever.retrieve_context(q, top_k=8)
        all_context.append(ctx)
    combined = "\n\n===\n\n".join(all_context)
    prompt = CALLFLOW_PROMPT.format(evidence=combined[:12000])
    try:
        response = generate(prompt)
        data = json.loads(response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
        return CallFlowSummary.model_validate(data)
    except Exception as e:
        return CallFlowSummary(flows=[])
