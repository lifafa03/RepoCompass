"""Documentation Editor agent: produces final structured outputs with evidence references."""
from app.schemas import (
    ArchitectureExplainer, CallFlowSummary, RiskNotes,
    AskRepoAnswer, EvidenceRef
)


def finalize_architecture(draft: ArchitectureExplainer) -> ArchitectureExplainer:
    for comp in draft.components:
        if comp.uncertainty_note and "insufficient" in comp.uncertainty_note.lower():
            comp.confidence = "low"
    for obs in draft.system_observations:
        if not obs.evidence:
            obs.uncertainty_note = obs.uncertainty_note or "No evidence available; marked as insufficient."
            obs.confidence = "low"
    return draft


def finalize_risk_notes(notes: RiskNotes) -> RiskNotes:
    for note in notes.risk_notes:
        if note.category == "security":
            note.description = note.description.replace("vulnerability", "potential risk indicator")
            note.description = note.description.replace("exploit", "potential concern")
    return notes


def format_answer(question: str, answer_text: str, evidence: list[EvidenceRef],
                  confidence: str) -> AskRepoAnswer:
    if not evidence or confidence == "low":
        return AskRepoAnswer(
            question=question, answer="insufficient evidence",
            evidence=[], confidence="low", insufficient_evidence=True,
            uncertainty_note="The repository evidence retrieved was not sufficient to answer the question reliably.",
        )
    return AskRepoAnswer(
        question=question, answer=answer_text,
        evidence=evidence, confidence=confidence,
        insufficient_evidence=False, uncertainty_note=None,
    )
