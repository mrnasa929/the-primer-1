"""the-primer domain models — pedagogy extensions built ON the capillary-actions-sdk.

The base contracts (``KnowledgeConcept``, ``KnowledgeGraph``, ``LearnerProgress``)
come from ``capillary_actions_sdk``. the-primer *subclasses* them to add the
competency-measurement fields and behaviour this tutoring engine needs, and adds
its own assessment/mastery models on top. The SDK never imports from here.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from capillary_actions_sdk.models.learner_interaction import (
    KnowledgeConcept as SDKKnowledgeConcept,
)
from capillary_actions_sdk.models.learner_interaction import (
    KnowledgeGraph as SDKKnowledgeGraph,
)
from capillary_actions_sdk.models.learner_interaction import (
    LearnerProgress as SDKLearnerProgress,
)
from pydantic import BaseModel, Field

from the_primer.enums import AssessmentModality, BloomLevel, GateDecision
from the_primer.utils import _utcnow


class KnowledgeConcept(SDKKnowledgeConcept):
    """SDK concept extended with pedagogy + mastery metadata."""

    bloom_level: BloomLevel = BloomLevel.understand
    assessment_modality: AssessmentModality = AssessmentModality.explanation
    passing_threshold: float = 0.75
    mastery_criteria: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    decay_halflife_days: int = 14
    max_attempts: int = 3
    estimated_minutes: int = 20


class KnowledgeGraph(SDKKnowledgeGraph):
    """SDK knowledge graph narrowed to the-primer concepts, with traversal helpers."""

    concepts: list[KnowledgeConcept]

    def get(self, concept_id: str) -> KnowledgeConcept | None:
        return next((c for c in self.concepts if c.id == concept_id), None)

    def prerequisites_of(self, concept_id: str) -> list[KnowledgeConcept]:
        concept = self.get(concept_id)
        if not concept:
            return []
        return [c for c in self.concepts if c.id in concept.prerequisites]

    def unlocked_by(self, mastered_ids: set[str]) -> list[KnowledgeConcept]:
        """Return concepts whose prerequisites are all mastered."""
        result = []
        for concept in self.concepts:
            if concept.id in mastered_ids:
                continue
            if all(p in mastered_ids for p in concept.prerequisites):
                result.append(concept)
        return result


class ConceptMasteryRecord(BaseModel):
    """Per-concept mastery state for a single learner."""

    concept_id: str
    score: float = 0.0  # current competency estimate
    attempts: int = 0
    last_assessed: datetime | None = None
    decay_factor: float = 1.0  # 1.0 = no decay yet
    last_bloom_level_reached: BloomLevel | None = None
    passed: bool = False

    def effective_score(self) -> float:
        """Score adjusted for forgetting-curve decay."""
        return self.score * self.decay_factor


class LearnerProgress(SDKLearnerProgress):
    """SDK learner progress extended with per-concept mastery records."""

    concept_records: dict[str, ConceptMasteryRecord] = Field(default_factory=dict)
    streak_days: int = 0
    preferred_modality: AssessmentModality | None = None
    calibration_confidence: float = 0.5  # how much we trust our own estimates

    def mastered_ids(self, threshold: float | None = None) -> set[str]:
        """IDs of concepts whose effective score meets or exceeds their threshold."""
        return {cid for cid, rec in self.concept_records.items() if rec.passed}

    def record_for(self, concept_id: str) -> ConceptMasteryRecord:
        if concept_id not in self.concept_records:
            self.concept_records[concept_id] = ConceptMasteryRecord(concept_id=concept_id)
        return self.concept_records[concept_id]


class RubricScore(BaseModel):
    criterion: str
    score: float  # 0.0–1.0
    rationale: str | None = None


class AssessmentResult(BaseModel):
    """What the agent observed after one assessment engagement."""

    id: UUID
    engagement_id: UUID
    learner_id: UUID
    concept_id: str
    attempted_at: datetime = Field(default_factory=_utcnow)

    # what was targeted
    target_bloom_level: BloomLevel
    target_modality: AssessmentModality

    # what was observed
    bloom_level_demonstrated: BloomLevel
    rubric_scores: list[RubricScore] = Field(default_factory=list)
    score: float  # weighted average of rubric_scores
    passed: bool
    agent_rationale: str | None = None  # why the agent decided pass/fail


class MasteryGateDecision(BaseModel):
    """The agent's decision after evaluating an AssessmentResult."""

    assessment_result_id: UUID
    concept_id: str
    decision: GateDecision
    decided_at: datetime = Field(default_factory=_utcnow)

    # populated on pass
    next_concept_id: str | None = None

    # populated on retry
    retry_delay_days: int | None = None
    retry_modality: AssessmentModality | None = None  # may escalate to different modality

    # populated on escalate
    escalation_reason: str | None = None

    rationale: str  # always required — agent must explain
