"""Tests for the-primer's pedagogy extensions over the SDK models.

These confirm the one-way extension relationship: the-primer models are SDK
models plus pedagogy fields/behaviour, and remain valid SDK instances.
"""

from __future__ import annotations

from uuid import UUID

from capillary_actions_sdk.models.learner_interaction import (
    KnowledgeConcept as SDKKnowledgeConcept,
)
from capillary_actions_sdk.models.learner_interaction import (
    KnowledgeGraph as SDKKnowledgeGraph,
)

from the_primer.enums import AssessmentModality, BloomLevel
from the_primer.models import KnowledgeConcept, KnowledgeGraph


def _concept(cid: str, prereqs: list[str]) -> KnowledgeConcept:
    return KnowledgeConcept(
        id=cid,
        name=cid.title(),
        description=f"{cid} concept",
        prerequisites=prereqs,
        bloom_level=BloomLevel.understand,
        assessment_modality=AssessmentModality.explanation,
    )


def test_primer_concept_is_an_sdk_concept() -> None:
    """the-primer KnowledgeConcept must remain a valid SDK KnowledgeConcept."""
    c = _concept("group", [])
    assert isinstance(c, SDKKnowledgeConcept)
    # Pedagogy defaults supplied by the-primer (not present on the SDK base).
    assert c.bloom_level is BloomLevel.understand
    assert c.passing_threshold == 0.75
    assert c.max_attempts == 3


def test_bloom_depth_is_ordered() -> None:
    assert BloomLevel.remember.depth() < BloomLevel.create.depth()


def test_knowledge_graph_unlocked_by_respects_prerequisites() -> None:
    kg = KnowledgeGraph(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Algebra",
        description="test",
        source="test",
        concepts=[
            _concept("set-theory", []),
            _concept("group", ["set-theory"]),
            _concept("subgroup", ["group"]),
        ],
    )
    assert isinstance(kg, SDKKnowledgeGraph)

    # Nothing mastered -> only prerequisite-free concepts unlock.
    unlocked = {c.id for c in kg.unlocked_by(set())}
    assert unlocked == {"set-theory"}

    # Master set-theory -> group unlocks; subgroup still gated.
    unlocked = {c.id for c in kg.unlocked_by({"set-theory"})}
    assert unlocked == {"group"}

    assert kg.get("missing") is None
    assert [c.id for c in kg.prerequisites_of("group")] == ["set-theory"]
