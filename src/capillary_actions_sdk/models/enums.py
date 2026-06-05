"""Additional Enums for Competency Measurement."""

from __future__ import annotations

from enum import Enum


class BloomLevel(str, Enum):
    """Bloom's revised taxonomy — ordered from lowest to highest cognitive depth."""
    remember    = "remember"
    understand  = "understand"
    apply       = "apply"
    analyze     = "analyze"
    evaluate    = "evaluate"
    create      = "create"

    def depth(self) -> int:
        return list(BloomLevel).index(self) + 1

class AssessmentModality(str, Enum):
    """How the agent assesses the student for this concept."""
    recall       = "recall"        # multiple choice / short answer
    explanation  = "explanation"   # student explains in own words
    application  = "application"   # student solves a novel problem
    project      = "project"       # student produces something

class GateDecision(str, Enum):
    pass_     = "pass"      # mastered — unlock next concepts
    retry     = "retry"     # not yet — schedule re-attempt
    escalate  = "escalate"  # max_attempts exhausted — change modality
