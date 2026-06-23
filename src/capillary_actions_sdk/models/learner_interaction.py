"""Learner Interaction models — Knowledge Graph, Learner Progress, and Teaching Context."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from capillary_actions_sdk.models.enums import AssessmentModality, BloomLevel, GateDecision
from capillary_actions_sdk.utils import _utcnow


class KnowledgeConcept(BaseModel):
    """A node in the Knowledge Graph representing a teachable concept."""

    id: str  # slug identifier
    name: str
    description: str
    prerequisites: list[str] = Field(default_factory=list)  # IDs of prerequisite concepts
    difficulty: int = 1  # 1-5 scale
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    bloom_level: BloomLevel = BloomLevel.understand
    assessment_modality: AssessmentModality = AssessmentModality.explanation
    passing_threshold: float = 0.75
    mastery_criteria: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    decay_halflife_days: int = 14
    max_attempts: int = 3
    estimated_minutes: int = 20


class KnowledgeGraph(BaseModel):
    """A structured representation of a course or curriculum."""

    id: UUID
    name: str
    description: str
    source: str  # e.g., 'MIT OCW', 'NGSS', 'XRP'
    concepts: list[KnowledgeConcept]
    metadata: dict[str, Any] = Field(default_factory=dict)

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
    score: float = 0.0                               # current competency estimate
    attempts: int = 0
    last_assessed: datetime | None = None
    decay_factor: float = 1.0                        # 1.0 = no decay yet
    last_bloom_level_reached: BloomLevel | None = None
    passed: bool = False

    def effective_score(self) -> float:
        """Score adjusted for forgetting-curve decay."""
        return self.score * self.decay_factor

class LearnerProgress(BaseModel):
    """Tracks a learner's progress through a Knowledge Graph."""

    learner_id: UUID
    knowledge_graph_id: UUID
    mastery: dict[str, float] = Field(default_factory=dict)  # concept_id -> mastery score (0-1)
    current_concept: str | None = None
    completed_concepts: list[str] = Field(default_factory=list)
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    concept_records: dict[str, ConceptMasteryRecord] = Field(default_factory=dict)
    streak_days: int = 0
    preferred_modality: AssessmentModality | None = None
    calibration_confidence: float = 0.5              # how much we trust our own estimates

    def mastered_ids(self, threshold: float | None = None) -> set[str]:
        """IDs of concepts whose effective score meets or exceeds their threshold."""
        return {
            cid for cid, rec in self.concept_records.items()
            if rec.passed
        }

    def record_for(self, concept_id: str) -> ConceptMasteryRecord:
        if concept_id not in self.concept_records:
            self.concept_records[concept_id] = ConceptMasteryRecord(concept_id=concept_id)
        return self.concept_records[concept_id]


class TeachingContext(BaseModel):
    """Assembled context for a teaching interaction — combines KG + Student Model."""

    learner_progress: LearnerProgress
    target_concept: KnowledgeConcept
    student_working_memory: dict[str, Any] = Field(default_factory=dict)
    recommended_approach: str | None = None  # e.g., 'visual', 'worked_example', 'socratic'

# ---------------------------------------------------------------------------
# AssessmentResult  (new model — output of a single assessment cycle)
# ---------------------------------------------------------------------------


class RubricScore(BaseModel):
    criterion: str
    score: float                                     # 0.0–1.0
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
    score: float                                     # weighted average of rubric_scores
    passed: bool
    agent_rationale: str | None = None              # why the agent decided pass/fail


# ---------------------------------------------------------------------------
# MasteryGateDecision  (new model — the AI progression gate)
# ---------------------------------------------------------------------------


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

    rationale: str                                   # always required — agent must explain
