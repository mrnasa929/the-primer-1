"""the-primer — a YAML-driven tutoring engine built on the capillary-actions-sdk.

This package is a *reference implementation* that consumes the
``capillary-actions-sdk`` contracts (ports, models, events) and extends its
learner-interaction domain with pedagogy-specific concepts (Bloom taxonomy,
assessment modalities, mastery gating). It does not, and must not, modify the
SDK — the dependency is one-way: ``the_primer`` -> ``capillary_actions_sdk``.
"""

from the_primer.enums import AssessmentModality, BloomLevel, GateDecision
from the_primer.loader import (
    load_bloom_policy,
    load_kg,
    load_modality_policy,
    load_yaml,
)
from the_primer.models import (
    AssessmentResult,
    ConceptMasteryRecord,
    KnowledgeConcept,
    KnowledgeGraph,
    LearnerProgress,
    MasteryGateDecision,
    RubricScore,
)
from the_primer.session_runner import SessionRunner
from the_primer.tutor import MasteryGate, TutoringAgent

__all__ = [
    "AssessmentModality",
    "BloomLevel",
    "GateDecision",
    "AssessmentResult",
    "ConceptMasteryRecord",
    "KnowledgeConcept",
    "KnowledgeGraph",
    "LearnerProgress",
    "MasteryGateDecision",
    "RubricScore",
    "load_bloom_policy",
    "load_kg",
    "load_modality_policy",
    "load_yaml",
    "SessionRunner",
    "MasteryGate",
    "TutoringAgent",
]
