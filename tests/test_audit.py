"""Tests for immutable append-only audit schemas and replay semantics."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from autonomous_trading.audit import (
    AUDIT_EVENT_SCHEMA_VERSION,
    REDACTED_VALUE,
    ActorKind,
    AuditActor,
    AuditEvent,
    AuditIntegrityError,
    AuditPayload,
    AuditValidationError,
    InMemoryAuditLog,
)

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
CORRELATION_ID = UUID("22222222-2222-4222-8222-222222222222")
OCCURRED_AT = datetime(2026, 6, 22, 12, 30, 45, 123456, tzinfo=UTC)


def _event(
    *,
    event_id: UUID = EVENT_ID,
    event_type: str = "experiment.created",
    values: dict[str, object] | None = None,
) -> AuditEvent:
    return AuditEvent(
        schema_version=AUDIT_EVENT_SCHEMA_VERSION,
        event_id=event_id,
        occurred_at=OCCURRED_AT,
        actor=AuditActor(kind=ActorKind.AGENT, identifier="codex"),
        event_type=event_type,
        correlation_id=CORRELATION_ID,
        payload=AuditPayload.from_mapping(
            schema_name="experiment.lifecycle",
            schema_version=1,
            values=values or {"experiment_id": "exp-001", "attempt": 1},
        ),
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def test_audit_event_round_trip_is_canonical_and_attributable() -> None:
    """A complete event round trips with stable IDs, UTC time, actor, and payload schema."""
    event = _event()

    serialized = event.to_json()
    restored = AuditEvent.from_json(serialized)
    document = json.loads(serialized)

    assert restored == event
    assert restored.to_json() == serialized
    assert document["event_id"] == str(EVENT_ID)
    assert document["correlation_id"] == str(CORRELATION_ID)
    assert document["occurred_at"] == "2026-06-22T12:30:45.123456Z"
    assert document["actor"] == {"identifier": "codex", "kind": "agent"}
    assert document["payload"]["schema_name"] == "experiment.lifecycle"
    assert len(document["integrity_sha256"]) == 64


def test_payload_is_detached_and_event_is_immutable() -> None:
    """Caller-owned structures and returned copies cannot mutate recorded evidence."""
    values: dict[str, object] = {
        "experiment_id": "exp-001",
        "checks": [{"name": "chronology", "passed": True}],
    }
    payload = AuditPayload.from_mapping(
        schema_name="experiment.validation",
        schema_version=1,
        values=values,
    )
    event = AuditEvent(
        schema_version=1,
        event_id=EVENT_ID,
        occurred_at=OCCURRED_AT,
        actor=AuditActor(kind=ActorKind.SERVICE, identifier="validator"),
        event_type="validation.completed",
        correlation_id=CORRELATION_ID,
        payload=payload,
    )
    original_json = event.to_json()

    values["experiment_id"] = "tampered"
    returned = payload.to_mapping()
    returned["experiment_id"] = "also-tampered"

    assert event.to_json() == original_json
    assert payload.to_mapping()["experiment_id"] == "exp-001"
    with pytest.raises(FrozenInstanceError):
        event.event_type = "tampered"  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("password", "plain-text"),
        ("api_key", "key-value"),
        ("refreshToken", "token-value"),
        ("nested", {"credentials": {"username": "user", "password": "value"}}),
    ],
)
def test_unredacted_sensitive_payload_values_fail_closed(key: str, value: object) -> None:
    """Sensitive-looking payload fields cannot contain raw values at any depth."""
    with pytest.raises(AuditValidationError, match="must be omitted or set"):
        AuditPayload.from_mapping(
            schema_name="operator.action",
            schema_version=1,
            values={key: value},
        )


def test_explicit_redaction_marker_is_serialized_without_secret_value() -> None:
    """Sensitive field presence may be recorded only with the explicit marker."""
    payload = AuditPayload.from_mapping(
        schema_name="operator.action",
        schema_version=1,
        values={"authorization": REDACTED_VALUE, "action": "pause"},
    )

    assert payload.to_mapping() == {
        "action": "pause",
        "authorization": REDACTED_VALUE,
    }
    assert "plain-text" not in payload.canonical_json


@pytest.mark.parametrize(
    "value",
    [
        1.5,
        {"price": 1.5},
        {"too_large": 2**63},
        {"bad_key": {1: "not-a-string-key"}},
        {"unsupported": object()},
    ],
)
def test_unsupported_or_non_portable_payload_values_fail_closed(value: object) -> None:
    """Payloads reject floats, oversized integers, invalid keys, and arbitrary objects."""
    with pytest.raises(AuditValidationError):
        AuditPayload.from_mapping(
            schema_name="experiment.result",
            schema_version=1,
            values={"value": value},
        )


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("schema_version", 2, "schema_version must be 1"),
        ("event_id", "not-a-uuid", "event_id must be a UUID"),
        ("occurred_at", datetime(2026, 6, 22), "timezone-aware UTC"),
        (
            "occurred_at",
            datetime(2026, 6, 22, tzinfo=timezone(timedelta(hours=1))),
            "timezone-aware UTC",
        ),
        ("event_type", "Experiment Created", "invalid identifier"),
        ("correlation_id", "not-a-uuid", "correlation_id must be a UUID"),
    ],
)
def test_invalid_event_boundaries_fail_closed(
    field: str,
    value: object,
    expected_message: str,
) -> None:
    """Version, identity, timestamp, and event-type boundaries are strict."""
    arguments: dict[str, object] = {
        "schema_version": 1,
        "event_id": EVENT_ID,
        "occurred_at": OCCURRED_AT,
        "actor": AuditActor(kind=ActorKind.AGENT, identifier="codex"),
        "event_type": "experiment.created",
        "correlation_id": CORRELATION_ID,
        "payload": AuditPayload.from_mapping(
            schema_name="experiment.lifecycle",
            schema_version=1,
            values={"experiment_id": "exp-001"},
        ),
    }
    arguments[field] = value

    with pytest.raises(AuditValidationError, match=expected_message):
        AuditEvent(**arguments)  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    ("kind", "identifier"),
    [
        ("agent", "codex"),
        (ActorKind.AGENT, ""),
        (ActorKind.AGENT, "contains spaces"),
    ],
)
def test_invalid_actor_boundaries_fail_closed(kind: object, identifier: str) -> None:
    """Actors require an explicit supported kind and stable identifier."""
    with pytest.raises(AuditValidationError):
        AuditActor(
            kind=kind,  # pyright: ignore[reportArgumentType]
            identifier=identifier,
        )


@pytest.mark.parametrize(
    ("schema_name", "schema_version"),
    [
        ("Experiment Lifecycle", 1),
        ("experiment.lifecycle", 0),
        ("experiment.lifecycle", True),
    ],
)
def test_invalid_payload_schema_identity_fails_closed(
    schema_name: str,
    schema_version: int,
) -> None:
    """Payload schemas are explicit, stable, and positively versioned."""
    with pytest.raises(AuditValidationError):
        AuditPayload.from_mapping(
            schema_name=schema_name,
            schema_version=schema_version,
            values={},
        )


def test_event_field_tampering_is_detected() -> None:
    """Changing an event field without its digest is rejected before replay."""
    document = json.loads(_event().to_json())
    document["event_type"] = "experiment.deleted"

    with pytest.raises(AuditIntegrityError, match="event digest"):
        AuditEvent.from_json(_canonical_json(document))


def test_payload_tampering_is_detected_independently() -> None:
    """Changing payload content without its payload digest is rejected."""
    document = json.loads(_event().to_json())
    document["payload"]["values"]["attempt"] = 2

    with pytest.raises(AuditIntegrityError, match="payload digest"):
        AuditEvent.from_json(_canonical_json(document))


def test_digest_tampering_is_detected() -> None:
    """A substituted event digest cannot pass verification."""
    document = json.loads(_event().to_json())
    document["integrity_sha256"] = "0" * 64

    with pytest.raises(AuditIntegrityError, match="event digest"):
        AuditEvent.from_json(_canonical_json(document))


def test_unknown_missing_duplicate_and_noncanonical_fields_fail_closed() -> None:
    """Serialized boundaries reject schema drift, ambiguity, and alternate encodings."""
    serialized = _event().to_json()
    document = json.loads(serialized)

    unknown = dict(document)
    unknown["unexpected"] = True
    with pytest.raises(AuditValidationError, match="unknown fields: unexpected"):
        AuditEvent.from_json(_canonical_json(unknown))

    missing = dict(document)
    missing.pop("actor")
    with pytest.raises(AuditValidationError, match="missing fields: actor"):
        AuditEvent.from_json(_canonical_json(missing))

    duplicate = serialized.replace(
        '"event_type":"experiment.created"',
        '"event_type":"experiment.created","event_type":"experiment.created"',
        1,
    )
    with pytest.raises(AuditValidationError, match="duplicate key"):
        AuditEvent.from_json(duplicate)

    with pytest.raises(AuditValidationError, match="canonical JSON"):
        AuditEvent.from_json(json.dumps(document, indent=2, sort_keys=True))


def test_malformed_non_utf8_and_floating_json_fail_closed() -> None:
    """Parser failures stay inside the public audit error boundary."""
    with pytest.raises(AuditValidationError, match="valid UTF-8"):
        AuditEvent.from_json(b"\xff")
    with pytest.raises(AuditValidationError, match="JSON is invalid"):
        AuditEvent.from_json("{")

    serialized = _event().to_json().replace('"attempt":1', '"attempt":1.0')
    with pytest.raises(AuditValidationError, match="floating-point"):
        AuditEvent.from_json(serialized)


def test_append_order_is_authoritative_and_snapshots_do_not_mutate_log() -> None:
    """The log preserves first-append order independently of event timestamps."""
    first = _event(event_id=EVENT_ID)
    second = AuditEvent(
        schema_version=1,
        event_id=UUID("33333333-3333-4333-8333-333333333333"),
        occurred_at=OCCURRED_AT - timedelta(days=1),
        actor=first.actor,
        event_type="experiment.imported",
        correlation_id=CORRELATION_ID,
        payload=first.payload,
    )
    log = InMemoryAuditLog()

    log.append(first)
    log.append(second)
    snapshot = log.events()
    snapshot += (_event(event_id=UUID("44444444-4444-4444-8444-444444444444")),)

    assert log.events() == (first, second)
    assert len(log) == 2
    assert log.get(first.event_id) is first


def test_identical_replay_is_idempotent() -> None:
    """Retrying byte-identical evidence does not create a duplicate record."""
    event = _event()
    log = InMemoryAuditLog()

    first = log.append(event)
    second = log.append(AuditEvent.from_json(event.to_json()))

    assert first == second
    assert log.events() == (event,)


def test_conflicting_replay_fails_closed_without_mutating_log() -> None:
    """Reusing an event ID for different content is rejected atomically."""
    original = _event()
    conflicting = _event(values={"experiment_id": "exp-002"})
    log = InMemoryAuditLog()
    log.append(original)

    with pytest.raises(AuditIntegrityError, match="different content"):
        log.append(conflicting)

    assert log.events() == (original,)


def test_restart_replay_verifies_events_and_preserves_order() -> None:
    """A fresh log rebuilds only from verified canonical serialized events."""
    first = _event()
    second = _event(
        event_id=UUID("33333333-3333-4333-8333-333333333333"),
        event_type="experiment.completed",
        values={"experiment_id": "exp-001", "status": "complete"},
    )
    original = InMemoryAuditLog()
    original.append(first)
    original.append(second)

    restored = InMemoryAuditLog.replay(original.serialize())

    assert restored.events() == (first, second)
    assert restored.serialize() == original.serialize()


def test_restart_replay_rejects_tampered_evidence() -> None:
    """Replay halts instead of admitting a corrupt event."""
    serialized = _event().to_json()
    tampered = serialized.replace('"attempt":1', '"attempt":2')

    with pytest.raises(AuditIntegrityError):
        InMemoryAuditLog.replay((serialized, tampered))


@given(
    count=st.integers(min_value=-(2**63), max_value=2**63 - 1),
    label=st.text(max_size=40),
    flags=st.lists(st.booleans(), max_size=8),
)
def test_generated_payloads_round_trip_deterministically(
    count: int,
    label: str,
    flags: list[bool],
) -> None:
    """Broad exact JSON payloads produce deterministic event evidence."""
    event = _event(values={"count": count, "flags": flags, "label": label})

    restored = AuditEvent.from_json(event.to_json())

    assert restored == event
    assert restored.to_json() == event.to_json()


@given(value=st.integers(min_value=-(2**63), max_value=2**63 - 2))
def test_generated_payload_mutations_are_detected(value: int) -> None:
    """Any generated material payload change invalidates the recorded digest."""
    document = json.loads(_event(values={"count": value}).to_json())
    document["payload"]["values"]["count"] = value + 1

    with pytest.raises(AuditIntegrityError):
        AuditEvent.from_json(_canonical_json(document))
