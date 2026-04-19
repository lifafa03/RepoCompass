"""Pydantic schemas for RepoCompass inputs and outputs."""
from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    snippet_id: str = ""


class ChunkRecord(BaseModel):
    chunk_id: str
    file_path: str
    language: Optional[str] = None
    symbol: Optional[str] = None
    line_start: int
    line_end: int
    content: str
    content_type: Literal["code", "config", "docs"]
    repo_relative_path: str


class Component(BaseModel):
    name: str
    role: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    uncertainty_note: Optional[str] = None


class SystemObservation(BaseModel):
    claim: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    uncertainty_note: Optional[str] = None


class ArchitectureExplainer(BaseModel):
    summary: str
    components: list[Component] = Field(default_factory=list)
    system_observations: list[SystemObservation] = Field(default_factory=list)


class HandlerLocation(BaseModel):
    file_path: str
    line_start: int
    line_end: int


class APIEndpoint(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OTHER"]
    route: str
    handler_name: Optional[str] = None
    handler_location: Optional[HandlerLocation] = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    uncertainty_note: Optional[str] = None


class APIMap(BaseModel):
    framework: str
    endpoints: list[APIEndpoint] = Field(default_factory=list)


class FlowStep(BaseModel):
    step_number: int
    description: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    uncertainty_note: Optional[str] = None


class CallFlow(BaseModel):
    name: str
    entrypoint: str
    steps: list[FlowStep] = Field(default_factory=list)
    overall_confidence: Literal["high", "medium", "low"] = "medium"
    uncertainty_note: Optional[str] = None


class CallFlowSummary(BaseModel):
    flows: list[CallFlow] = Field(default_factory=list)


class RiskNote(BaseModel):
    title: str
    category: Literal["security", "correctness", "maintainability", "ambiguity", "configuration"]
    description: str
    why_it_matters: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    requires_human_review: bool = True
    uncertainty_note: Optional[str] = None


class RiskNotes(BaseModel):
    risk_notes: list[RiskNote] = Field(default_factory=list)


class AskRepoAnswer(BaseModel):
    question: str
    answer: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    insufficient_evidence: bool = False
    uncertainty_note: Optional[str] = None
