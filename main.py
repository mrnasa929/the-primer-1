import json
import math
import os
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from capillary_actions_sdk.models.enums import AssessmentModality, BloomLevel, GateDecision
from capillary_actions_sdk.models.learner_interaction import AssessmentResult, KnowledgeConcept, KnowledgeGraph, LearnerProgress, MasteryGateDecision, RubricScore
from capillary_actions_sdk.utils import _utcnow
from example import ABSTRACT_ALGEBRA_KG

load_dotenv()

# ---------------------------------------------------------------------------
# Client — swap model string here if you want a different one
# ---------------------------------------------------------------------------

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

MODEL = "openai/gpt-4o"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chat(system: str, messages: list[dict]) -> str:
    """Send a chat request and return the assistant's reply as a string."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, *messages],
        temperature=0.3,        # low temperature — we want consistent scoring
    )
    return response.choices[0].message.content.strip()

def _chat_json(system: str, messages: list[dict]) -> dict:
    """Same as _chat but parses the response as JSON.
    The system prompt must instruct the model to return only JSON.
    """
    raw = _chat(system, messages)
    # Strip accidental markdown fences the model sometimes adds
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(clean)

# ---------------------------------------------------------------------------
# Bloom-level instructions — what the model should do at each level
# ---------------------------------------------------------------------------
 
BLOOM_TEACHING_INSTRUCTIONS: dict[BloomLevel, str] = {
    BloomLevel.remember: (
        "Introduce the concept clearly and concisely. Define key terms. "
        "Keep the explanation short — the student only needs to recall the definition."
    ),
    BloomLevel.understand: (
        "Explain the concept in depth. Use an analogy. Walk through why it works, "
        "not just what it is. The student should be able to re-explain it in their own words."
    ),
    BloomLevel.apply: (
        "Explain the concept by showing how to use it on a concrete example. "
        "Demonstrate the procedure step by step. The student will need to apply it independently."
    ),
    BloomLevel.analyze: (
        "Explain the concept and its internal structure. Show how the parts relate. "
        "Highlight what breaks or what changes under different conditions. "
        "The student will need to decompose and reason about novel cases."
    ),
    BloomLevel.evaluate: (
        "Explain the concept and the criteria for judging it. "
        "Show how to compare alternatives and justify a choice. "
        "The student will need to make and defend a reasoned judgment."
    ),
    BloomLevel.create: (
        "Explain the concept and how it can be composed with other ideas to produce something new. "
        "The student will need to design or construct something original."
    ),
}
 
BLOOM_PROBE_INSTRUCTIONS: dict[BloomLevel, str] = {
    BloomLevel.remember: (
        "Ask the student to recall and state the definition or key facts. "
        "Example: 'Define X in your own words.'"
    ),
    BloomLevel.understand: (
        "Ask the student to explain the concept in their own words and give an example. "
        "Example: 'Explain X and describe a situation where it applies.'"
    ),
    BloomLevel.apply: (
        "Give the student a specific, novel problem to solve using the concept. "
        "Example: 'Here is [concrete case]. Apply X to solve it, showing your work.'"
    ),
    BloomLevel.analyze: (
        "Give the student a case and ask them to break it down, identify components, "
        "or explain why something holds or fails. "
        "Example: 'Given [structure], determine whether X applies and explain each step.'"
    ),
    BloomLevel.evaluate: (
        "Present two alternatives and ask the student to compare and justify a choice. "
        "Example: 'Compare A and B. Which is preferable under condition C, and why?'"
    ),
    BloomLevel.create: (
        "Ask the student to design or construct something using the concept. "
        "Example: 'Construct an example of X that satisfies these constraints.'"
    ),
}
 
MODALITY_CONTEXT: dict[AssessmentModality, str] = {
    AssessmentModality.recall:      "This is a recall question — a short factual answer is expected.",
    AssessmentModality.explanation: "This is an explanation question — the student should explain in their own words.",
    AssessmentModality.application: "This is an application problem — the student should show their working.",
    AssessmentModality.project:     "This is a project task — the student should produce a structured artefact.",
}

# ---------------------------------------------------------------------------
# TutoringAgent
# ---------------------------------------------------------------------------

class TutoringAgent:
    """Orchestrates a single concept session: teach → probe → score."""
 
    def __init__(self, concept: KnowledgeConcept) -> None:
        self.concept = concept
        self.session_id = uuid4()
 
    # ------------------------------------------------------------------
    # Step 1 — Teach
    # ------------------------------------------------------------------
 
    def teach(self) -> str:
        """Generate a teaching explanation targeted at the concept's Bloom level."""
        c = self.concept
        bloom_instruction = BLOOM_TEACHING_INSTRUCTIONS[c.bloom_level]
 
        system = f"""You are an expert tutor in {c.tags[0] if c.tags else 'mathematics'}.
Your job is to teach a student about '{c.name}'.
 
Teaching instruction for Bloom level '{c.bloom_level.value}':
{bloom_instruction}
 
Known misconceptions to address proactively:
{chr(10).join(f'- {m}' for m in c.misconceptions)}
 
Keep your explanation focused and clear. Do not assess the student yet — just teach.
End with a single sentence that signals you are ready to check their understanding."""
 
        messages = [
            {
                "role": "user",
                "content": f"Please teach me about: {c.name}",
            }
        ]
 
        return _chat(system, messages)
 
    # ------------------------------------------------------------------
    # Step 2 — Probe
    # ------------------------------------------------------------------
 
    def probe(self, teaching: str) -> str:
        """Generate an assessment question matched to the concept's Bloom level and modality."""
        c = self.concept
        bloom_instruction  = BLOOM_PROBE_INSTRUCTIONS[c.bloom_level]
        modality_context   = MODALITY_CONTEXT[c.assessment_modality]
 
        system = f"""You are an expert tutor assessing a student on '{c.name}'.
You have just finished teaching. Now generate exactly ONE assessment question.
 
Bloom level target: '{c.bloom_level.value}'
{bloom_instruction}
 
Assessment modality: '{c.assessment_modality.value}'
{modality_context}
 
The question must be designed so that a correct answer would demonstrate ALL of these criteria:
{chr(10).join(f'- {crit}' for crit in c.mastery_criteria)}
 
Output only the question — no preamble, no explanation."""
 
        messages = [
            {"role": "assistant", "content": teaching},
            {"role": "user",      "content": "I think I understand. Can you test me?"},
        ]
 
        return _chat(system, messages)
 
    # ------------------------------------------------------------------
    # Step 3 — Score
    # ------------------------------------------------------------------
 
    def score(
        self,
        teaching: str,
        probe: str,
        student_response: str,
    ) -> AssessmentResult:
        """Score the student's response against mastery criteria.
 
        Returns a fully populated AssessmentResult including:
          - rubric_scores per criterion
          - bloom_level_demonstrated (may be lower than target)
          - overall score and passed flag
          - agent_rationale
        """
        c = self.concept
 
        system = f"""You are an expert assessor for '{c.name}'.
Evaluate the student's response against EACH mastery criterion below.
 
Concept Bloom target: {c.bloom_level.value}
Passing threshold: {c.passing_threshold}
 
Mastery criteria:
{chr(10).join(f'{i+1}. {crit}' for i, crit in enumerate(c.mastery_criteria))}
 
Bloom levels (for demonstrated level assessment):
remember < understand < apply < analyze < evaluate < create
 
You MUST respond with ONLY valid JSON — no markdown, no prose outside the JSON.
Schema:
{{
  "rubric_scores": [
    {{
      "criterion": "<exact criterion text>",
      "score": <float 0.0-1.0>,
      "rationale": "<one sentence explaining the score>"
    }}
  ],
  "bloom_level_demonstrated": "<one of: remember|understand|apply|analyze|evaluate|create>",
  "overall_rationale": "<two sentences: what the student showed and what is missing>"
}}
 
Be strict. A student who recites a memorised definition has demonstrated 'remember', not 'understand'.
A student who applies a procedure correctly to a novel case has demonstrated 'apply'."""
 
        messages = [
            {"role": "assistant", "content": teaching},
            {"role": "user",      "content": probe},
            {"role": "assistant", "content": "Please go ahead with your response."},
            {"role": "user",      "content": student_response},
        ]
 
        raw = _chat_json(system, messages)
 
        # Parse rubric scores
        rubric_scores = [
            RubricScore(
                criterion=r["criterion"],
                score=float(r["score"]),
                rationale=r.get("rationale"),
            )
            for r in raw["rubric_scores"]
        ]
 
        # Weighted average (equal weights for PoC — can be weighted later)
        overall_score = (
            sum(r.score for r in rubric_scores) / len(rubric_scores)
            if rubric_scores else 0.0
        )
 
        bloom_demonstrated = BloomLevel(raw["bloom_level_demonstrated"])
        passed = overall_score >= c.passing_threshold
 
        return AssessmentResult(
            id=uuid4(),
            engagement_id=self.session_id,
            learner_id=uuid4(),          # in a real system, pass the learner UUID in
            concept_id=c.id,
            target_bloom_level=c.bloom_level,
            target_modality=c.assessment_modality,
            bloom_level_demonstrated=bloom_demonstrated,
            rubric_scores=rubric_scores,
            score=overall_score,
            passed=passed,
            agent_rationale=raw.get("overall_rationale"),
        )
 
 
# ---------------------------------------------------------------------------
# MasteryGate
# ---------------------------------------------------------------------------
 
class MasteryGate:
    """Decides pass / retry / escalate from an AssessmentResult."""
 
    def __init__(self, kg: "KnowledgeGraph", progress: LearnerProgress) -> None:
        self.kg       = kg
        self.progress = progress
 
    def decide(self, result: AssessmentResult) -> MasteryGateDecision:
        concept = self.kg.get(result.concept_id)
        if not concept:
            raise ValueError(f"Concept '{result.concept_id}' not found in KG")
 
        record = self.progress.record_for(result.concept_id)
 
        # Update the mastery record
        record.attempts     += 1
        record.score         = result.score
        record.last_assessed = _utcnow()
        record.last_bloom_level_reached = result.bloom_level_demonstrated
 
        # Also keep the flat SDK-compat dict in sync
        self.progress.mastery[result.concept_id] = result.score
 
        # ── PASS ──────────────────────────────────────────────────────────
        if result.passed:
            record.passed = True
            self.progress.completed_concepts.append(result.concept_id)
 
            # Find the first newly unlocked concept
            mastered   = self.progress.mastered_ids()
            unlocked   = self.kg.unlocked_by(mastered)
            next_id    = unlocked[0].id if unlocked else None
 
            return MasteryGateDecision(
                assessment_result_id=result.id,
                concept_id=result.concept_id,
                decision=GateDecision.pass_,
                next_concept_id=next_id,
                rationale=(
                    f"Score {result.score:.2f} ≥ threshold {concept.passing_threshold:.2f}. "
                    f"Demonstrated Bloom level: {result.bloom_level_demonstrated.value}. "
                    f"Concept mastered."
                ),
            )
 
        # ── ESCALATE ──────────────────────────────────────────────────────
        if record.attempts >= concept.max_attempts:
            # Switch to a different modality
            new_modality = (
                AssessmentModality.application
                if concept.assessment_modality != AssessmentModality.application
                else AssessmentModality.explanation
            )
            return MasteryGateDecision(
                assessment_result_id=result.id,
                concept_id=result.concept_id,
                decision=GateDecision.escalate,
                retry_modality=new_modality,
                escalation_reason=(
                    f"Failed {record.attempts} consecutive attempts. "
                    f"Switching modality from '{concept.assessment_modality.value}' "
                    f"to '{new_modality.value}'."
                ),
                rationale=(
                    f"Score {result.score:.2f} < threshold {concept.passing_threshold:.2f} "
                    f"after {record.attempts} attempts. Escalating."
                ),
            )
 
        # ── RETRY ─────────────────────────────────────────────────────────
        # Delay scales inversely with score — lower score → more forgetting → sooner retry
        delay = max(1, math.ceil(concept.decay_halflife_days * (1 - result.score)))
 
        # Detect Bloom gap — student demonstrated a lower level than targeted
        bloom_gap = (
            concept.bloom_level.depth() - result.bloom_level_demonstrated.depth()
        )
        bloom_note = (
            f" Bloom gap: targeted '{concept.bloom_level.value}' but demonstrated "
            f"'{result.bloom_level_demonstrated.value}' — {bloom_gap} level(s) below target."
            if bloom_gap > 0 else ""
        )
 
        return MasteryGateDecision(
            assessment_result_id=result.id,
            concept_id=result.concept_id,
            decision=GateDecision.retry,
            retry_delay_days=delay,
            rationale=(
                f"Score {result.score:.2f} < threshold {concept.passing_threshold:.2f}. "
                f"Attempt {record.attempts}/{concept.max_attempts}. "
                f"Retry in {delay} day(s).{bloom_note}"
            ),
        )

# ---------------------------------------------------------------------------
# Session runner — ties everything together
# ---------------------------------------------------------------------------
 
def run_session(concept_id: str, student_response: str) -> None:
    """Run a complete teaching → probe → score → gate session.
 
    Args:
        concept_id:       The KG concept slug to teach (e.g. 'group').
        student_response: Simulate the student's answer to the probe question.
                          In a real system this comes from user input.
    """
    concept = ABSTRACT_ALGEBRA_KG.get(concept_id)
    if not concept:
        raise ValueError(f"Concept '{concept_id}' not found in KG")
 
    # Fresh learner progress for this demo
    from uuid import uuid4
    progress = LearnerProgress(
        learner_id=uuid4(),
        knowledge_graph_id=ABSTRACT_ALGEBRA_KG.id,
    )
 
    agent = TutoringAgent(concept)
    gate  = MasteryGate(ABSTRACT_ALGEBRA_KG, progress)
 
    # ── Step 1: Teach ────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"  CONCEPT  : {concept.name}")
    print(f"  BLOOM    : {concept.bloom_level.value}")
    print(f"  MODALITY : {concept.assessment_modality.value}")
    print(f"  THRESHOLD: {concept.passing_threshold}")
    print("═" * 60)
 
    print("\n── TEACHING ──────────────────────────────────────────────\n")
    teaching = agent.teach()
    print(teaching)
 
    # ── Step 2: Probe ────────────────────────────────────────────────────
    print("\n── PROBE QUESTION ────────────────────────────────────────\n")
    probe = agent.probe(teaching)
    print(probe)
 
    # ── Student response (simulated here, real input in production) ──────
    print("\n── STUDENT RESPONSE ──────────────────────────────────────\n")
    print(student_response)
 
    # ── Step 3: Score ────────────────────────────────────────────────────
    print("\n── SCORING ───────────────────────────────────────────────\n")
    result = agent.score(teaching, probe, student_response)
 
    for rs in result.rubric_scores:
        bar = "█" * int(rs.score * 10) + "░" * (10 - int(rs.score * 10))
        print(f"  [{bar}] {rs.score:.2f}  {rs.criterion}")
        if rs.rationale:
            print(f"           → {rs.rationale}")
 
    print(f"\n  Overall score     : {result.score:.2f}")
    print(f"  Bloom demonstrated: {result.bloom_level_demonstrated.value}")
    print(f"  Passed            : {result.passed}")
    print(f"\n  Rationale: {result.agent_rationale}")
 
    # ── Step 4: Gate ─────────────────────────────────────────────────────
    print("\n── GATE DECISION ─────────────────────────────────────────\n")
    decision = gate.decide(result)
 
    print(f"  Decision  : {decision.decision.value.upper()}")
    print(f"  Rationale : {decision.rationale}")
 
    if decision.decision == GateDecision.pass_:
        print(f"  Next concept unlocked: {decision.next_concept_id or 'none (end of KG)'}")
 
    elif decision.decision == GateDecision.retry:
        print(f"  Retry in  : {decision.retry_delay_days} day(s)")
 
    elif decision.decision == GateDecision.escalate:
        print(f"  New modality : {decision.retry_modality.value if decision.retry_modality else '—'}")
        print(f"  Reason       : {decision.escalation_reason}")
 
    # ── Summary ──────────────────────────────────────────────────────────
    print("\n── MASTERY RECORD ────────────────────────────────────────\n")
    record = progress.record_for(concept_id)
    print(f"  concept_id             : {record.concept_id}")
    print(f"  score                  : {record.score:.2f}")
    print(f"  attempts               : {record.attempts}")
    print(f"  passed                 : {record.passed}")
    print(f"  last_bloom_reached     : {record.last_bloom_level_reached.value if record.last_bloom_level_reached else '—'}")
 
    print("\n── UNLOCKED AFTER THIS SESSION ───────────────────────────\n")
    unlocked = ABSTRACT_ALGEBRA_KG.unlocked_by(progress.mastered_ids())
    if unlocked:
        for c in unlocked:
            print(f"  ✓ {c.name}  ({c.bloom_level.value})")
    else:
        print("  — none yet (prerequisites not all met)")
 
    print("\n" + "═" * 60 + "\n")
 
 
# ---------------------------------------------------------------------------
# Entry point — two demo sessions showing pass and retry
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
 
    # ── Demo 1: strong student response — should PASS ────────────────────
    run_session(
        concept_id="set-theory",
        student_response=(
            "A set is an unordered collection of distinct elements. "
            "The union A ∪ B contains everything in either A or B. "
            "The intersection A ∩ B contains only what is in both. "
            "A ⊆ B means every element of A is also in B, while A ⊂ B adds that A ≠ B. "
            "The Cartesian product A × B is the set of all ordered pairs (a, b) "
            "where a ∈ A and b ∈ B."
        ),
    )
 
    # ── Demo 2: weak student response — should RETRY ─────────────────────
    run_session(
        concept_id="group",
        student_response=(
            "A group is a set with some operation. "
            "I think it needs an identity and inverses."
        ),
    )