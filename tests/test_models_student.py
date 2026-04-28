from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from primer_sdk.models.student_model import (
    Cohort,
    CohortSnapshot,
    IngestResult,
    MembershipEvent,
    MemoryEntry,
    PreferenceSignal,
    WorkingMemoryAssembly,
)


class TestPreferenceSignal:
    def test_creation_with_valid_data(self):
        signal = PreferenceSignal(
            id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            signal_type="click",
            payload={"item_id": "abc123", "duration": 42},
            source="web-app",
        )
        assert isinstance(signal.id, UUID)
        assert isinstance(signal.user_id, UUID)
        assert isinstance(signal.org_id, UUID)
        assert signal.signal_type == "click"
        assert signal.payload == {"item_id": "abc123", "duration": 42}
        assert signal.source == "web-app"
        assert isinstance(signal.timestamp, datetime)

    def test_timestamp_defaults_to_utcnow(self):
        before = datetime.now(timezone.utc)
        signal = PreferenceSignal(
            id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            signal_type="view",
            payload={},
            source="mobile",
        )
        after = datetime.now(timezone.utc)
        assert before <= signal.timestamp <= after

    def test_arbitrary_payload(self):
        payload = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "score": 0.95,
            "flag": True,
        }
        signal = PreferenceSignal(
            id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            signal_type="rating",
            payload=payload,
            source="recommendation-engine",
        )
        assert signal.payload == payload

    def test_explicit_timestamp(self):
        ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        signal = PreferenceSignal(
            id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            signal_type="purchase",
            payload={"amount": 99.99},
            timestamp=ts,
            source="checkout",
        )
        assert signal.timestamp == ts


class TestMembershipEvent:
    def test_join_event(self):
        event = MembershipEvent(
            user_id=uuid4(),
            cohort_id=uuid4(),
            action="join",
            timestamp=datetime.now(timezone.utc),
        )
        assert event.action == "join"
        assert isinstance(event.user_id, UUID)
        assert isinstance(event.cohort_id, UUID)

    def test_leave_event(self):
        event = MembershipEvent(
            user_id=uuid4(),
            cohort_id=uuid4(),
            action="leave",
            timestamp=datetime.now(timezone.utc),
        )
        assert event.action == "leave"

    def test_timestamp_stored(self):
        ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        event = MembershipEvent(
            user_id=uuid4(),
            cohort_id=uuid4(),
            action="join",
            timestamp=ts,
        )
        assert event.timestamp == ts


class TestCohortSnapshot:
    def test_creation_with_valid_data(self):
        snapshot = CohortSnapshot(
            timestamp=datetime.now(timezone.utc),
            member_count=42,
            aggregate_state={"avg_score": 0.75, "top_topic": "python"},
            drift_score=0.12,
        )
        assert snapshot.member_count == 42
        assert snapshot.drift_score == 0.12
        assert snapshot.aggregate_state == {"avg_score": 0.75, "top_topic": "python"}

    def test_zero_drift_score(self):
        snapshot = CohortSnapshot(
            timestamp=datetime.now(timezone.utc),
            member_count=0,
            aggregate_state={},
            drift_score=0.0,
        )
        assert snapshot.drift_score == 0.0
        assert snapshot.member_count == 0

    def test_arbitrary_aggregate_state(self):
        state = {"topics": ["ml", "data"], "progress": {"ml": 0.8, "data": 0.5}}
        snapshot = CohortSnapshot(
            timestamp=datetime.now(timezone.utc),
            member_count=10,
            aggregate_state=state,
            drift_score=0.33,
        )
        assert snapshot.aggregate_state == state


class TestCohort:
    def _make_cohort(self, **overrides):
        defaults = dict(
            id=uuid4(),
            org_id=uuid4(),
            name="Beginner Python Learners",
            description="Students starting Python",
            strategy_type="similarity",
            member_ids=set(),
            membership_history=[],
            aggregate_state={},
            state_version=1,
            last_evolved=datetime.now(timezone.utc),
            snapshots=[],
        )
        defaults.update(overrides)
        return Cohort(**defaults)

    def test_creation_with_valid_data(self):
        cohort = self._make_cohort()
        assert isinstance(cohort.id, UUID)
        assert cohort.name == "Beginner Python Learners"
        assert cohort.strategy_type == "similarity"
        assert cohort.state_version == 1
        assert isinstance(cohort.member_ids, set)

    def test_member_ids_as_set_of_uuids(self):
        uid1, uid2, uid3 = uuid4(), uuid4(), uuid4()
        cohort = self._make_cohort(member_ids={uid1, uid2, uid3})
        assert len(cohort.member_ids) == 3
        assert uid1 in cohort.member_ids

    def test_membership_history_with_events(self):
        cohort_id = uuid4()
        user_id = uuid4()
        join_event = MembershipEvent(
            user_id=user_id,
            cohort_id=cohort_id,
            action="join",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        leave_event = MembershipEvent(
            user_id=user_id,
            cohort_id=cohort_id,
            action="leave",
            timestamp=datetime(2025, 3, 1, tzinfo=timezone.utc),
        )
        cohort = self._make_cohort(
            id=cohort_id,
            membership_history=[join_event, leave_event],
        )
        assert len(cohort.membership_history) == 2
        assert cohort.membership_history[0].action == "join"
        assert cohort.membership_history[1].action == "leave"

    def test_snapshots_within_cohort(self):
        snap1 = CohortSnapshot(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            member_count=5,
            aggregate_state={"avg_score": 0.5},
            drift_score=0.05,
        )
        snap2 = CohortSnapshot(
            timestamp=datetime(2025, 2, 1, tzinfo=timezone.utc),
            member_count=12,
            aggregate_state={"avg_score": 0.65},
            drift_score=0.15,
        )
        cohort = self._make_cohort(snapshots=[snap1, snap2])
        assert len(cohort.snapshots) == 2
        assert cohort.snapshots[0].member_count == 5
        assert cohort.snapshots[1].drift_score == 0.15

    def test_empty_collections_default(self):
        cohort = self._make_cohort()
        assert cohort.member_ids == set()
        assert cohort.membership_history == []
        assert cohort.snapshots == []
        assert cohort.aggregate_state == {}

    def test_mutable_defaults_are_independent(self):
        cohort_a = self._make_cohort()
        cohort_b = self._make_cohort()
        cohort_a.member_ids.add(uuid4())
        assert len(cohort_b.member_ids) == 0


class TestIngestResult:
    def test_creation_with_valid_data(self):
        result = IngestResult(
            processed=100,
            skipped=5,
            failed=2,
            errors=["Record 42: missing field", "Record 87: invalid UUID"],
        )
        assert result.processed == 100
        assert result.skipped == 5
        assert result.failed == 2
        assert len(result.errors) == 2

    def test_no_errors(self):
        result = IngestResult(
            processed=50,
            skipped=0,
            failed=0,
            errors=[],
        )
        assert result.errors == []
        assert result.failed == 0

    def test_all_failed(self):
        errors = [f"Record {i}: bad data" for i in range(10)]
        result = IngestResult(
            processed=0,
            skipped=0,
            failed=10,
            errors=errors,
        )
        assert result.processed == 0
        assert len(result.errors) == 10

    def test_errors_default_empty(self):
        result = IngestResult(processed=1, skipped=0, failed=0)
        assert result.errors == []


class TestMemoryEntry:
    def test_creation_with_required_fields(self):
        entry = MemoryEntry(
            id=uuid4(),
            tier="working",
            dimension="history",
            content={"topic": "algebra", "score": 0.85},
        )
        assert isinstance(entry.id, UUID)
        assert entry.tier == "working"
        assert entry.dimension == "history"
        assert entry.content == {"topic": "algebra", "score": 0.85}

    def test_default_values(self):
        before = datetime.now(timezone.utc)
        entry = MemoryEntry(
            id=uuid4(),
            tier="long_term",
            dimension="affinities",
            content={"preference": "visual"},
        )
        after = datetime.now(timezone.utc)
        assert entry.relevance_score == 1.0
        assert before <= entry.created_at <= after
        assert entry.expires_at is None
        assert entry.metadata == {}

    def test_explicit_optional_fields(self):
        expires = datetime(2026, 12, 31, tzinfo=timezone.utc)
        entry = MemoryEntry(
            id=uuid4(),
            tier="short_term",
            dimension="regula",
            content={"strategy": "spaced-repetition"},
            relevance_score=0.72,
            expires_at=expires,
            metadata={"source": "quiz-engine"},
        )
        assert entry.relevance_score == 0.72
        assert entry.expires_at == expires
        assert entry.metadata == {"source": "quiz-engine"}

    def test_mutable_metadata_independent(self):
        entry_a = MemoryEntry(
            id=uuid4(), tier="working", dimension="history", content={}
        )
        entry_b = MemoryEntry(
            id=uuid4(), tier="working", dimension="history", content={}
        )
        entry_a.metadata["key"] = "value"
        assert entry_b.metadata == {}


class TestWorkingMemoryAssembly:
    def _make_entry(self, **overrides):
        defaults = dict(
            id=uuid4(),
            tier="working",
            dimension="history",
            content={"fact": "example"},
        )
        defaults.update(overrides)
        return MemoryEntry(**defaults)

    def test_creation_with_required_fields(self):
        entry = self._make_entry()
        assembly = WorkingMemoryAssembly(
            learner_id=uuid4(),
            entries=[entry],
        )
        assert isinstance(assembly.learner_id, UUID)
        assert len(assembly.entries) == 1
        assert assembly.entries[0].tier == "working"

    def test_default_values(self):
        before = datetime.now(timezone.utc)
        assembly = WorkingMemoryAssembly(
            learner_id=uuid4(),
            entries=[],
        )
        after = datetime.now(timezone.utc)
        assert before <= assembly.assembled_at <= after
        assert assembly.context_summary is None

    def test_explicit_optional_fields(self):
        ts = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        assembly = WorkingMemoryAssembly(
            learner_id=uuid4(),
            entries=[],
            assembled_at=ts,
            context_summary="Learner prefers visual content and struggles with algebra.",
        )
        assert assembly.assembled_at == ts
        expected_summary = "Learner prefers visual content and struggles with algebra."
        assert assembly.context_summary == expected_summary

    def test_multiple_entries(self):
        entries = [
            self._make_entry(dimension="history"),
            self._make_entry(dimension="affinities"),
            self._make_entry(dimension="aspirations"),
        ]
        assembly = WorkingMemoryAssembly(
            learner_id=uuid4(),
            entries=entries,
        )
        assert len(assembly.entries) == 3
        dims = [e.dimension for e in assembly.entries]
        assert dims == ["history", "affinities", "aspirations"]

    def test_mutable_entries_independent(self):
        assembly_a = WorkingMemoryAssembly(learner_id=uuid4(), entries=[])
        assembly_b = WorkingMemoryAssembly(learner_id=uuid4(), entries=[])
        assembly_a.entries.append(self._make_entry())
        assert len(assembly_b.entries) == 0
