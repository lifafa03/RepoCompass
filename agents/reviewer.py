"""Security/Correctness Reviewer agent: challenges unsupported claims."""
from app.schemas import (
    ArchitectureExplainer, CallFlowSummary, RiskNotes, RiskNote,
    APIMap, EvidenceRef
)


def review_architecture(architecture: ArchitectureExplainer) -> ArchitectureExplainer:
    for comp in architecture.components:
        if not comp.evidence:
            comp.confidence = "low"
            comp.uncertainty_note = (comp.uncertainty_note or "") + " No direct evidence linked. "
    for obs in architecture.system_observations:
        if not obs.evidence:
            obs.confidence = "low"
            obs.uncertainty_note = (obs.uncertainty_note or "") + " No direct evidence linked. "
    return architecture


def review_api_map(api_map: APIMap) -> APIMap:
    for ep in api_map.endpoints:
        if not ep.evidence:
            ep.confidence = "low"
            ep.uncertainty_note = "No direct evidence for this endpoint."
        if ep.handler_name is None:
            ep.uncertainty_note = (ep.uncertainty_note or "") + " Handler name could not be resolved. "
            ep.confidence = min_confidence(ep.confidence, "medium")
    return api_map


def generate_risk_notes(architecture: ArchitectureExplainer, api_map: APIMap,
                        callflow: CallFlowSummary) -> RiskNotes:
    notes = []
    for comp in architecture.components:
        if comp.confidence == "low" or (comp.uncertainty_note and "insufficient" in (comp.uncertainty_note or "").lower()):
            notes.append(RiskNote(
                title=f"Uncertain component: {comp.name}",
                category="ambiguity",
                description=f"Component '{comp.name}' has low-confidence identification.",
                why_it_matters="May indicate incomplete repository coverage or ambiguous module boundaries.",
                evidence=comp.evidence,
                confidence="low",
                requires_human_review=True,
                uncertainty_note=comp.uncertainty_note,
            ))
    for ep in api_map.endpoints:
        if ep.handler_location is None and ep.confidence != "high":
            notes.append(RiskNote(
                title=f"Endpoint with unresolved handler: {ep.method} {ep.route}",
                category="ambiguity",
                description=f"The handler for {ep.method} {ep.route} could not be located.",
                why_it_matters="May indicate dynamic routing, middleware-based dispatch, or incomplete extraction.",
                evidence=ep.evidence,
                confidence="medium",
                requires_human_review=False,
                uncertainty_note=ep.uncertainty_note,
            ))
    for flow in callflow.flows:
        if flow.overall_confidence == "low":
            notes.append(RiskNote(
                title=f"Partial call flow: {flow.name}",
                category="correctness",
                description=f"Call flow '{flow.name}' has low overall confidence.",
                why_it_matters="The documented flow may be incomplete or incorrect.",
                evidence=[],
                confidence="low",
                requires_human_review=True,
                uncertainty_note=flow.uncertainty_note,
            ))
    return RiskNotes(risk_notes=notes)


def min_confidence(a: str, b: str) -> str:
    order = {"high": 0, "medium": 1, "low": 2}
    return a if order.get(a, 2) >= order.get(b, 2) else b
