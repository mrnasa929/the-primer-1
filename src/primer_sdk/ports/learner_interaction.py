"""Learner Interaction ports — Knowledge Graph, Learner Progress, and Teaching."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from primer_sdk.models.learner_interaction import (
    KnowledgeConcept,
    KnowledgeGraph,
    LearnerProgress,
    TeachingContext,
)

# ---------------------------------------------------------------------------
# Outbound ports
# ---------------------------------------------------------------------------


class KnowledgeGraphPort(ABC):
    """Outbound port for querying and managing Knowledge Graphs.

    Participants implement this ABC to provide knowledge graph storage
    and retrieval capabilities to the platform.
    """

    @abstractmethod
    async def get_graph(self, graph_id: UUID) -> KnowledgeGraph:
        """Retrieve a Knowledge Graph by ID.

        Args:
            graph_id: UUID of the graph to retrieve.

        Returns:
            The :class:`~primer_sdk.models.learner_interaction.KnowledgeGraph`.
        """
        ...

    @abstractmethod
    async def get_concept(self, concept_id: str) -> KnowledgeConcept:
        """Retrieve a single concept by its slug identifier.

        Args:
            concept_id: Slug identifier of the concept.

        Returns:
            The :class:`~primer_sdk.models.learner_interaction.KnowledgeConcept`.
        """
        ...

    @abstractmethod
    async def get_prerequisites(self, concept_id: str) -> list[KnowledgeConcept]:
        """Return all prerequisite concepts for a given concept.

        Args:
            concept_id: Slug identifier of the concept.

        Returns:
            List of prerequisite
            :class:`~primer_sdk.models.learner_interaction.KnowledgeConcept` instances.
        """
        ...

    @abstractmethod
    async def search_concepts(
        self, query: str, graph_id: UUID | None = None
    ) -> list[KnowledgeConcept]:
        """Search for concepts matching a text query.

        Args:
            query: Free-text search string.
            graph_id: Optional graph to restrict the search to.

        Returns:
            List of matching
            :class:`~primer_sdk.models.learner_interaction.KnowledgeConcept` instances.
        """
        ...


class LearnerProgressPort(ABC):
    """Outbound port for tracking learner progress through Knowledge Graphs.

    Participants implement this ABC to persist and query learner mastery state.
    """

    @abstractmethod
    async def get_progress(self, learner_id: UUID, graph_id: UUID) -> LearnerProgress:
        """Retrieve a learner's progress within a Knowledge Graph.

        Args:
            learner_id: UUID of the learner.
            graph_id: UUID of the Knowledge Graph.

        Returns:
            :class:`~primer_sdk.models.learner_interaction.LearnerProgress` for this
            learner/graph pair.
        """
        ...

    @abstractmethod
    async def update_mastery(self, learner_id: UUID, concept_id: str, score: float) -> None:
        """Update the mastery score for a learner on a specific concept.

        Args:
            learner_id: UUID of the learner.
            concept_id: Slug identifier of the concept.
            score: New mastery score (0.0 to 1.0).
        """
        ...

    @abstractmethod
    async def get_next_concept(
        self, learner_id: UUID, graph_id: UUID
    ) -> KnowledgeConcept | None:
        """Determine the next concept a learner should study.

        Args:
            learner_id: UUID of the learner.
            graph_id: UUID of the Knowledge Graph.

        Returns:
            The next recommended
            :class:`~primer_sdk.models.learner_interaction.KnowledgeConcept`,
            or ``None`` if all concepts are mastered.
        """
        ...


class TeachingPort(ABC):
    """Outbound port for assembling teaching context and recording outcomes.

    Participants implement this ABC to provide teaching session management
    that combines Knowledge Graph data with Student Model context.
    """

    @abstractmethod
    async def build_context(self, learner_id: UUID, concept_id: str) -> TeachingContext:
        """Assemble the teaching context for a learner and concept.

        Combines the learner's progress, the target concept details, and
        relevant student model data into a single context object.

        Args:
            learner_id: UUID of the learner.
            concept_id: Slug identifier of the concept to teach.

        Returns:
            :class:`~primer_sdk.models.learner_interaction.TeachingContext` ready
            for use in a teaching interaction.
        """
        ...

    @abstractmethod
    async def record_outcome(
        self, learner_id: UUID, concept_id: str, outcome: dict[str, Any]
    ) -> None:
        """Record the outcome of a teaching interaction.

        Args:
            learner_id: UUID of the learner.
            concept_id: Slug identifier of the concept that was taught.
            outcome: Outcome data (e.g. assessment results, engagement metrics).
        """
        ...
