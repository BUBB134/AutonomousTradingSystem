"""Tests for auditable strategy lifecycle transitions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from autonomous_trading.audit import ActorKind, AuditActor, AuditEvent
from autonomous_trading.registry import (
    LEGAL_STRATEGY_LIFECYCLE_TRANSITIONS,
    STRATEGY_LIFECYCLE_AUDIT_EVENT_TYPE,
    STRATEGY_LIFECYCLE_AUDIT_SCHEMA_NAME,
    STRATEGY_LIFECYCLE_SCHEMA_VERSION,
    STRATEGY_LIFECYCLE_STATES,
    ApprovalRecord,
    EvidenceReference,
    RiskEnvelope,
    StrategyLifecycle,
    StrategyLifecycleIntegrityError,
    StrategyLifecycleState,
    StrategyLifecycleTransition,
    StrategyLifecycleValidationError,
    is_legal_strategy_lifecycle_transition,
)

STRATEGY_ID = "strategy-alpha"
DECIDED_AT = datetime(2026, 6, 25, 12, 0, 0, 123456, tzinfo=UTC)


class _TransitionControls(TypedDict, total=False):
    evidence: tuple[EvidenceReference, ...]
    approval_record: ApprovalRecord | None
    risk_envelope: RiskEnvelope | None


def _uuid(value: int) -> UUID:
    return UUID(f"11111111-1111-4111-8111-{value:012d}")


def _evidence(kind: str = "promotion_evidence", value: int = 1) -> EvidenceReference:
    return EvidenceReference(
        kind=kind,
        uri=f"urn:autonomous-trading:evidence:{kind}:{value}",
        sha256=f"{value:064x}",
        schema_name=f"{kind}.schema",
        schema_version=1,
    )


def _approval(value: int = 100) -> ApprovalRecord:
    return ApprovalRecord(
        approved_by="owner",
        approved_at=DECIDED_AT + timedelta(minutes=value),
        approval_reference=_evidence("owner_approval", value),
    )


def _risk_envelope() -> RiskEnvelope:
    return RiskEnvelope(
        allowed_symbols=("AAA", "BBB"),
        max_gross_exposure_fraction=Decimal("0.25"),
        max_single_position_fraction=Decimal("0.10"),
        expires_at=DECIDED_AT + timedelta(days=30),
    )


def _transition(
    *,
    from_state: StrategyLifecycleState = StrategyLifecycleState.PROPOSED,
    to_state: StrategyLifecycleState = StrategyLifecycleState.RESEARCH,
    sequence: int = 1,
    evidence: tuple[EvidenceReference, ...] = (),
    approval_record: ApprovalRecord | None = None,
    risk_envelope: RiskEnvelope | None = None,
    strategy_id: str = STRATEGY_ID,
    transition_id: UUID | None = None,
    actor: str = "codex",
) -> StrategyLifecycleTransition:
    return StrategyLifecycleTransition(
        schema_version=STRATEGY_LIFECYCLE_SCHEMA_VERSION,
        transition_id=transition_id or _uuid(1),
        strategy_id=strategy_id,
        sequence=sequence,
        from_state=from_state,
        to_state=to_state,
        decided_at=DECIDED_AT + timedelta(minutes=sequence),
        actor=actor,
        evidence=evidence,
        approval_record=approval_record,
        risk_envelope=risk_envelope,
        reason="ticket BUB-9",
    )


def _transition_controls(
    from_state: StrategyLifecycleState,
    to_state: StrategyLifecycleState,
) -> _TransitionControls:
    controls: _TransitionControls = {}
    if (from_state, to_state) in {
        (StrategyLifecycleState.RESEARCH, StrategyLifecycleState.BACKTESTED),
        (StrategyLifecycleState.BACKTESTED, StrategyLifecycleState.VALIDATED),
        (StrategyLifecycleState.VALIDATED, StrategyLifecycleState.PAPER),
        (StrategyLifecycleState.PAPER, StrategyLifecycleState.LIVE_CANDIDATE),
        (StrategyLifecycleState.LIVE_CANDIDATE, StrategyLifecycleState.LIMITED_LIVE),
    }:
        controls["evidence"] = (_evidence(value=200 + len(from_state.value)),)
    if to_state is StrategyLifecycleState.LIMITED_LIVE:
        controls["approval_record"] = _approval()
        controls["risk_envelope"] = _risk_envelope()
    return controls


def _advance_to(state: StrategyLifecycleState) -> StrategyLifecycle:
    lifecycle = StrategyLifecycle.initialize(STRATEGY_ID)
    path = [
        StrategyLifecycleState.RESEARCH,
        StrategyLifecycleState.BACKTESTED,
        StrategyLifecycleState.VALIDATED,
        StrategyLifecycleState.PAPER,
        StrategyLifecycleState.LIVE_CANDIDATE,
        StrategyLifecycleState.LIMITED_LIVE,
    ]
    for index, next_state in enumerate(path, start=1):
        if lifecycle.current_state is state:
            break
        controls = _transition_controls(lifecycle.current_state, next_state)
        lifecycle = lifecycle.transition_to(
            transition_id=_uuid(index),
            to_state=next_state,
            decided_at=DECIDED_AT + timedelta(minutes=index),
            actor="codex",
            reason="advance for test",
            **controls,
        )
    if state is StrategyLifecycleState.PROPOSED:
        return StrategyLifecycle.initialize(STRATEGY_ID)
    if lifecycle.current_state is not state:
        raise AssertionError(f"helper cannot advance to {state}")
    return lifecycle


def test_lifecycle_states_are_unique_and_complete() -> None:
    """Every lifecycle state is represented exactly once in the public contract."""
    assert tuple(state.value for state in STRATEGY_LIFECYCLE_STATES) == (
        "PROPOSED",
        "RESEARCH",
        "BACKTESTED",
        "VALIDATED",
        "PAPER",
        "LIVE_CANDIDATE",
        "LIMITED_LIVE",
        "RETIRED",
    )
    assert len(set(STRATEGY_LIFECYCLE_STATES)) == len(STRATEGY_LIFECYCLE_STATES)
    assert set(LEGAL_STRATEGY_LIFECYCLE_TRANSITIONS) == {
        (StrategyLifecycleState.PROPOSED, StrategyLifecycleState.RESEARCH),
        (StrategyLifecycleState.PROPOSED, StrategyLifecycleState.RETIRED),
        (StrategyLifecycleState.RESEARCH, StrategyLifecycleState.BACKTESTED),
        (StrategyLifecycleState.RESEARCH, StrategyLifecycleState.RETIRED),
        (StrategyLifecycleState.BACKTESTED, StrategyLifecycleState.VALIDATED),
        (StrategyLifecycleState.BACKTESTED, StrategyLifecycleState.RETIRED),
        (StrategyLifecycleState.VALIDATED, StrategyLifecycleState.PAPER),
        (StrategyLifecycleState.VALIDATED, StrategyLifecycleState.RETIRED),
        (StrategyLifecycleState.PAPER, StrategyLifecycleState.LIVE_CANDIDATE),
        (StrategyLifecycleState.PAPER, StrategyLifecycleState.RETIRED),
        (StrategyLifecycleState.LIVE_CANDIDATE, StrategyLifecycleState.LIMITED_LIVE),
        (StrategyLifecycleState.LIVE_CANDIDATE, StrategyLifecycleState.RETIRED),
        (StrategyLifecycleState.LIMITED_LIVE, StrategyLifecycleState.RETIRED),
    }


def test_expected_path_advances_append_only_with_evidence() -> None:
    """Legal promotions append deterministic records and leave prior lifecycles unchanged."""
    proposed = StrategyLifecycle.initialize(STRATEGY_ID)

    researched = proposed.transition_to(
        transition_id=_uuid(1),
        to_state=StrategyLifecycleState.RESEARCH,
        decided_at=DECIDED_AT,
        actor="codex",
    )
    backtested = researched.transition_to(
        transition_id=_uuid(2),
        to_state=StrategyLifecycleState.BACKTESTED,
        decided_at=DECIDED_AT + timedelta(minutes=1),
        actor="codex",
        evidence=(_evidence("backtest_result", 2),),
    )
    validated = backtested.transition_to(
        transition_id=_uuid(3),
        to_state=StrategyLifecycleState.VALIDATED,
        decided_at=DECIDED_AT + timedelta(minutes=2),
        actor="validator",
        evidence=(_evidence("validation_report", 3),),
    )
    paper = validated.transition_to(
        transition_id=_uuid(4),
        to_state=StrategyLifecycleState.PAPER,
        decided_at=DECIDED_AT + timedelta(minutes=3),
        actor="operator",
        evidence=(_evidence("promotion_gate", 4),),
    )
    live_candidate = paper.transition_to(
        transition_id=_uuid(5),
        to_state=StrategyLifecycleState.LIVE_CANDIDATE,
        decided_at=DECIDED_AT + timedelta(minutes=4),
        actor="operator",
        evidence=(_evidence("paper_qualification", 5),),
    )
    limited_live = live_candidate.transition_to(
        transition_id=_uuid(6),
        to_state=StrategyLifecycleState.LIMITED_LIVE,
        decided_at=DECIDED_AT + timedelta(minutes=5),
        actor="owner",
        evidence=(_evidence("limited_live_packet", 6),),
        approval_record=_approval(),
        risk_envelope=_risk_envelope(),
    )

    assert proposed.current_state is StrategyLifecycleState.PROPOSED
    assert proposed.history() == ()
    assert limited_live.current_state is StrategyLifecycleState.LIMITED_LIVE
    assert [transition.sequence for transition in limited_live.history()] == [1, 2, 3, 4, 5, 6]
    assert [transition.to_state for transition in limited_live.history()] == [
        StrategyLifecycleState.RESEARCH,
        StrategyLifecycleState.BACKTESTED,
        StrategyLifecycleState.VALIDATED,
        StrategyLifecycleState.PAPER,
        StrategyLifecycleState.LIVE_CANDIDATE,
        StrategyLifecycleState.LIMITED_LIVE,
    ]
    assert all(len(transition.content_sha256) == 64 for transition in limited_live.history())


@pytest.mark.parametrize("from_state", STRATEGY_LIFECYCLE_STATES[:-1])
def test_retirement_is_permitted_from_every_non_retired_state(
    from_state: StrategyLifecycleState,
) -> None:
    """Retirement is append-only and does not require a live-capital path."""
    lifecycle = _advance_to(from_state)

    retired = lifecycle.transition_to(
        transition_id=_uuid(900 + len(lifecycle.history())),
        to_state=StrategyLifecycleState.RETIRED,
        decided_at=DECIDED_AT + timedelta(days=1),
        actor="operator",
        reason="retired by policy",
    )

    assert retired.current_state is StrategyLifecycleState.RETIRED
    assert lifecycle.current_state is from_state


def test_invalid_state_jump_fails_without_mutating_history() -> None:
    """A direct research-to-paper jump is rejected and the lifecycle remains unchanged."""
    lifecycle = StrategyLifecycle.initialize(STRATEGY_ID).transition_to(
        transition_id=_uuid(1),
        to_state=StrategyLifecycleState.RESEARCH,
        decided_at=DECIDED_AT,
        actor="codex",
    )

    with pytest.raises(StrategyLifecycleValidationError, match="not permitted"):
        lifecycle.transition_to(
            transition_id=_uuid(2),
            to_state=StrategyLifecycleState.PAPER,
            decided_at=DECIDED_AT + timedelta(minutes=1),
            actor="codex",
            evidence=(_evidence(),),
        )

    assert lifecycle.current_state is StrategyLifecycleState.RESEARCH
    assert len(lifecycle.history()) == 1


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (StrategyLifecycleState.RESEARCH, StrategyLifecycleState.BACKTESTED),
        (StrategyLifecycleState.BACKTESTED, StrategyLifecycleState.VALIDATED),
        (StrategyLifecycleState.VALIDATED, StrategyLifecycleState.PAPER),
        (StrategyLifecycleState.PAPER, StrategyLifecycleState.LIVE_CANDIDATE),
        (StrategyLifecycleState.LIVE_CANDIDATE, StrategyLifecycleState.LIMITED_LIVE),
    ],
)
def test_promotions_require_machine_readable_evidence(
    from_state: StrategyLifecycleState,
    to_state: StrategyLifecycleState,
) -> None:
    """Promotion transitions fail closed when evidence references are absent."""
    controls = _transition_controls(from_state, to_state)
    controls["evidence"] = ()

    with pytest.raises(StrategyLifecycleValidationError, match="evidence references"):
        _transition(from_state=from_state, to_state=to_state, **controls)


def test_research_cannot_transition_directly_to_paper_or_live_states() -> None:
    """Research cannot skip validation, paper approval, or live-candidate gates."""
    lifecycle = _advance_to(StrategyLifecycleState.RESEARCH)

    for to_state in (
        StrategyLifecycleState.PAPER,
        StrategyLifecycleState.LIVE_CANDIDATE,
        StrategyLifecycleState.LIMITED_LIVE,
    ):
        with pytest.raises(StrategyLifecycleValidationError, match="not permitted"):
            lifecycle.transition_to(
                transition_id=_uuid(50 + len(to_state.value)),
                to_state=to_state,
                decided_at=DECIDED_AT + timedelta(hours=1),
                actor="codex",
                evidence=(_evidence(value=50 + len(to_state.value)),),
            )


def test_limited_live_requires_approval_record_and_risk_envelope() -> None:
    """The record-only limited-live state needs both owner approval and a risk envelope."""
    lifecycle = _advance_to(StrategyLifecycleState.LIVE_CANDIDATE)

    with pytest.raises(StrategyLifecycleValidationError, match="approval record"):
        lifecycle.transition_to(
            transition_id=_uuid(20),
            to_state=StrategyLifecycleState.LIMITED_LIVE,
            decided_at=DECIDED_AT + timedelta(hours=2),
            actor="owner",
            evidence=(_evidence("limited_live_packet", 20),),
        )

    with pytest.raises(StrategyLifecycleValidationError, match="risk envelope"):
        lifecycle.transition_to(
            transition_id=_uuid(21),
            to_state=StrategyLifecycleState.LIMITED_LIVE,
            decided_at=DECIDED_AT + timedelta(hours=2),
            actor="owner",
            evidence=(_evidence("limited_live_packet", 21),),
            approval_record=_approval(),
        )


def test_approval_record_and_risk_envelope_are_rejected_on_other_transitions() -> None:
    """Live-approval controls cannot be attached to unrelated lifecycle transitions."""
    with pytest.raises(StrategyLifecycleValidationError, match="only valid"):
        _transition(
            to_state=StrategyLifecycleState.RESEARCH,
            approval_record=_approval(),
            risk_envelope=_risk_envelope(),
        )


@pytest.mark.parametrize(
    ("factory", "expected_message"),
    [
        (
            lambda: EvidenceReference(
                kind="bad kind",
                uri="urn:autonomous-trading:evidence:bad:1",
                sha256="a" * 64,
                schema_name="bad.schema",
                schema_version=1,
            ),
            "kind",
        ),
        (
            lambda: EvidenceReference(
                kind="promotion_evidence",
                uri="not a uri",
                sha256="a" * 64,
                schema_name="promotion.schema",
                schema_version=1,
            ),
            "uri",
        ),
        (
            lambda: EvidenceReference(
                kind="promotion_evidence",
                uri="urn:autonomous-trading:evidence:bad:1",
                sha256="A" * 64,
                schema_name="promotion.schema",
                schema_version=1,
            ),
            "sha256",
        ),
        (
            lambda: RiskEnvelope(
                allowed_symbols=("AAA", "AAA"),
                max_gross_exposure_fraction=Decimal("0.25"),
                max_single_position_fraction=Decimal("0.10"),
                expires_at=DECIDED_AT,
            ),
            "duplicates",
        ),
        (
            lambda: ApprovalRecord(
                approved_by="owner",
                approved_at=DECIDED_AT,
                approval_reference=_evidence("validation_report", 1),
            ),
            "owner_approval",
        ),
    ],
)
def test_invalid_boundary_values_fail_closed(
    factory: Callable[[], object],
    expected_message: str,
) -> None:
    """Boundary objects reject malformed identifiers, duplicate symbols, and bad approval kind."""
    with pytest.raises(StrategyLifecycleValidationError, match=expected_message):
        factory()


def test_transition_boundaries_reject_non_utc_time_and_duplicate_evidence() -> None:
    """Transitions require UTC time and unambiguous evidence references."""
    with pytest.raises(StrategyLifecycleValidationError, match="timezone-aware UTC"):
        StrategyLifecycle.initialize(STRATEGY_ID).transition_to(
            transition_id=_uuid(1),
            to_state=StrategyLifecycleState.RESEARCH,
            decided_at=datetime(2026, 6, 25, tzinfo=timezone(timedelta(hours=1))),
            actor="codex",
        )

    duplicate = _evidence(value=10)
    with pytest.raises(StrategyLifecycleValidationError, match="duplicates"):
        _transition(
            from_state=StrategyLifecycleState.RESEARCH,
            to_state=StrategyLifecycleState.BACKTESTED,
            evidence=(duplicate, duplicate),
        )


def test_lifecycle_history_is_immutable_and_replay_is_deterministic() -> None:
    """History snapshots and frozen records cannot mutate authoritative lifecycle state."""
    lifecycle = StrategyLifecycle.initialize(STRATEGY_ID).transition_to(
        transition_id=_uuid(1),
        to_state=StrategyLifecycleState.RESEARCH,
        decided_at=DECIDED_AT,
        actor="codex",
    )
    transition = lifecycle.history()[0]
    mutated_snapshot = lifecycle.history()
    mutated_snapshot += (_transition(transition_id=_uuid(99), sequence=2),)

    replayed = StrategyLifecycle.replay(
        strategy_id=STRATEGY_ID,
        transitions=lifecycle.history(),
    )

    assert lifecycle.history() == (transition,)
    assert replayed == lifecycle
    with pytest.raises(FrozenInstanceError):
        transition.to_state = StrategyLifecycleState.PAPER  # pyright: ignore[reportAttributeAccessIssue]


def test_replay_rejects_mismatched_strategy_sequence_and_state() -> None:
    """Replay fails closed when append order contradicts transition evidence."""
    mismatched_strategy = _transition(strategy_id="strategy-beta")
    with pytest.raises(StrategyLifecycleIntegrityError, match="strategy_id"):
        StrategyLifecycle.replay(strategy_id=STRATEGY_ID, transitions=(mismatched_strategy,))

    wrong_sequence = _transition(sequence=2)
    with pytest.raises(StrategyLifecycleIntegrityError, match="sequence"):
        StrategyLifecycle.replay(strategy_id=STRATEGY_ID, transitions=(wrong_sequence,))

    wrong_from_state = _transition(
        from_state=StrategyLifecycleState.RESEARCH,
        to_state=StrategyLifecycleState.BACKTESTED,
        evidence=(_evidence(),),
    )
    with pytest.raises(StrategyLifecycleIntegrityError, match="from_state"):
        StrategyLifecycle.replay(strategy_id=STRATEGY_ID, transitions=(wrong_from_state,))


def test_transition_to_audit_event_uses_registry_schema() -> None:
    """Lifecycle transitions can be rendered as immutable audit events."""
    lifecycle = _advance_to(StrategyLifecycleState.BACKTESTED)
    transition = lifecycle.history()[-1]
    audit_event = transition.to_audit_event(
        event_id=_uuid(700),
        correlation_id=_uuid(701),
        actor=AuditActor(kind=ActorKind.AGENT, identifier="codex"),
    )
    restored = AuditEvent.from_json(audit_event.to_json())
    payload = restored.payload.to_mapping()

    assert restored.event_type == STRATEGY_LIFECYCLE_AUDIT_EVENT_TYPE
    assert restored.payload.schema_name == STRATEGY_LIFECYCLE_AUDIT_SCHEMA_NAME
    assert payload["strategy_id"] == STRATEGY_ID
    assert payload["to_state"] == StrategyLifecycleState.BACKTESTED.value
    assert payload["content_sha256"] == transition.content_sha256
    assert "broker" not in restored.to_json().lower()


def test_transition_digest_is_deterministic_and_material() -> None:
    """Identical transition inputs hash identically and material changes alter the digest."""
    first = _transition()
    same = _transition()
    changed = _transition(actor="different")

    assert first.content_sha256 == same.content_sha256
    assert first.content_sha256 != changed.content_sha256


@given(
    from_state=st.sampled_from(STRATEGY_LIFECYCLE_STATES),
    to_state=st.sampled_from(STRATEGY_LIFECYCLE_STATES),
)
def test_generated_state_pairs_match_declared_policy(
    from_state: StrategyLifecycleState,
    to_state: StrategyLifecycleState,
) -> None:
    """All generated state pairs are accepted only when explicitly declared legal."""
    expected_legal = (from_state, to_state) in set(LEGAL_STRATEGY_LIFECYCLE_TRANSITIONS)
    controls = _transition_controls(from_state, to_state)

    if expected_legal:
        transition = _transition(from_state=from_state, to_state=to_state, **controls)
        assert is_legal_strategy_lifecycle_transition(from_state, to_state)
        assert transition.from_state is from_state
        assert transition.to_state is to_state
    else:
        with pytest.raises(StrategyLifecycleValidationError):
            _transition(from_state=from_state, to_state=to_state, **controls)
        assert not is_legal_strategy_lifecycle_transition(from_state, to_state)
