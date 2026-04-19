# Output Formats

This file defines the expected output formats for RepoCompass. These schemas are intentionally conservative so the system does not overclaim.

## General Rules

- Every repo-specific output must be evidence-backed.
- Evidence should identify where the support came from.
- If evidence is partial, include an uncertainty note.
- If evidence is missing, return `insufficient evidence` instead of guessing.

## 1. Architecture Explainer

### Purpose
Provide a readable explanation of the repository’s high-level structure, major components, and likely interactions.

### Output Shape

```json
{
  "summary": "string",
  "components": [
    {
      "name": "string",
      "role": "string",
      "evidence": [
        {
          "file_path": "string",
          "line_start": 0,
          "line_end": 0,
          "snippet_id": "string"
        }
      ],
      "confidence": "high | medium | low",
      "uncertainty_note": "string or null"
    }
  ],
  "system_observations": [
    {
      "claim": "string",
      "evidence": [
        {
          "file_path": "string",
          "line_start": 0,
          "line_end": 0,
          "snippet_id": "string"
        }
      ],
      "confidence": "high | medium | low",
      "uncertainty_note": "string or null"
    }
  ]
}
```

### Notes
- `summary` should be concise and evidence-grounded.
- `components` should only list identifiable parts supported by the repo.
- `system_observations` should separate clear observations from weaker interpretations.

## 2. API Map

### Purpose
Provide a structured inventory of discovered API endpoints for the supported framework.

### Output Shape

```json
{
  "framework": "string",
  "endpoints": [
    {
      "method": "GET | POST | PUT | PATCH | DELETE | OTHER",
      "route": "string",
      "handler_name": "string or null",
      "handler_location": {
        "file_path": "string",
        "line_start": 0,
        "line_end": 0
      },
      "evidence": [
        {
          "file_path": "string",
          "line_start": 0,
          "line_end": 0,
          "snippet_id": "string"
        }
      ],
      "confidence": "high | medium | low",
      "uncertainty_note": "string or null"
    }
  ]
}
```

### Notes
- Do not output endpoints that are not supported by evidence.
- If route or handler resolution is partial, keep the record and mark uncertainty.

## 3. Call-Flow Summary

### Purpose
Describe high-level request or execution flow for major repository paths.

### Output Shape

```json
{
  "flows": [
    {
      "name": "string",
      "entrypoint": "string",
      "steps": [
        {
          "step_number": 1,
          "description": "string",
          "evidence": [
            {
              "file_path": "string",
              "line_start": 0,
              "line_end": 0,
              "snippet_id": "string"
            }
          ],
          "confidence": "high | medium | low",
          "uncertainty_note": "string or null"
        }
      ],
      "overall_confidence": "high | medium | low",
      "uncertainty_note": "string or null"
    }
  ]
}
```

### Notes
- A flow is allowed to be partial.
- Missing transitions should not be guessed.

## 4. Risk Notes

### Purpose
Flag uncertain, potentially unsafe, or review-worthy implementation areas.

### Output Shape

```json
{
  "risk_notes": [
    {
      "title": "string",
      "category": "security | correctness | maintainability | ambiguity | configuration",
      "description": "string",
      "why_it_matters": "string",
      "evidence": [
        {
          "file_path": "string",
          "line_start": 0,
          "line_end": 0,
          "snippet_id": "string"
        }
      ],
      "confidence": "high | medium | low",
      "requires_human_review": true,
      "uncertainty_note": "string or null"
    }
  ]
}
```

### Notes
- These are risk indicators, not definitive vulnerability findings.
- Avoid absolute security language unless directly supported.

## 5. Ask-Repo Q&A

### Purpose
Answer user questions about the repository using retrieved evidence.

### Output Shape

```json
{
  "question": "string",
  "answer": "string",
  "evidence": [
    {
      "file_path": "string",
      "line_start": 0,
      "line_end": 0,
      "snippet_id": "string"
    }
  ],
  "confidence": "high | medium | low",
  "insufficient_evidence": false,
  "uncertainty_note": "string or null"
}
```

### Failure Case Shape

```json
{
  "question": "string",
  "answer": "insufficient evidence",
  "evidence": [],
  "confidence": "low",
  "insufficient_evidence": true,
  "uncertainty_note": "The repository evidence retrieved was not sufficient to answer the question reliably."
}
```

## 6. Internal Chunk Record

### Purpose
Define the minimum structure for indexed repository chunks.

### Output Shape

```json
{
  "chunk_id": "string",
  "file_path": "string",
  "language": "string or null",
  "symbol": "string or null",
  "line_start": 0,
  "line_end": 0,
  "content": "string",
  "content_type": "code | config | docs",
  "repo_relative_path": "string"
}
```

## Evidence Reference Rules

Each evidence item should point to a real location from the indexed repository. At minimum, store:
- file path
- line start
- line end
- snippet or chunk id

If exact line ranges are not available at some stage, the system should still preserve file path and chunk id, then upgrade to line-aware references when possible.
