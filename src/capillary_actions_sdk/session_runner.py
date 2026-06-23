from typing import Any

from capillary_actions_sdk.models.enums import GateDecision


class SessionRunner:
    """
    Orchestrates a full tutoring session:
        teach → probe → score → gate → update progress
    """

    def __init__(self, kg, agent, gate):
        self.kg = kg
        self.agent = agent
        self.gate = gate

    def run(self, concept_id: str, student_response: str) -> Any:
        concept = self.kg.get(concept_id)
        if not concept:
            raise ValueError(f"Concept '{concept_id}' not found")

        print ("\n" + "=" * 60)
        print(f"CONCEPT: {concept.name}")
        print(f"BLOOM: {concept.bloom_level.value}")
        print(f"MODALITY: {concept.assessment_modality.value}")
        print("=" * 60)

        print("\n── TEACHING ─────────────────────────────────────────\n")
        teaching = self.agent.teach()
        print(teaching)

        print("\n── PROBE ─────────────────────────────────────────────\n")
        probe = self.agent.probe(teaching)
        print(probe)

        print("\n── STUDENT RESPONSE ──────────────────────────────────\n")
        print(student_response)

        print("\n── SCORING ───────────────────────────────────────────\n")
        result = self.agent.score(teaching, probe, student_response)

        for r in result.rubric_scores:
            bar = "█" * int(r.score * 10) + "░" * (10 - int(r.score * 10))
            print(f"[{bar}] {r.score:.2f}  {r.criterion}")
            if r.rationale:
                print(f"   → {r.rationale}")

        print(f"\nScore: {result.score:.2f}")
        print(f"Bloom: {result.bloom_level_demonstrated.value}")
        print(f"Passed: {result.passed}")

        print("\n── GATE DECISION ─────────────────────────────────────\n")
        decision = self.gate.decide(result)

        print(f"Decision: {decision.decision.value}")
        print(f"Rationale: {decision.rationale}")

        if decision.decision == GateDecision.pass_:
            print(f"Next concept: {decision.next_concept_id}")

        elif decision.decision == GateDecision.retry:
            print(f"Retry in: {decision.retry_delay_days} days")

        elif decision.decision == GateDecision.escalate:
            print(f"Escalate to modality: {decision.retry_modality}")

        return {
            "teaching": teaching,
            "probe": probe,
            "result": result,
            "decision": decision,
        }
