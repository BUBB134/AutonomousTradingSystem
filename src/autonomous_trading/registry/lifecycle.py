"""Versioned, append-only strategy lifecycle state machine."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from autonomous_trading.audit import (
    AUDIT_EVENT_SCHEMA_VERSION,
    AuditActor,
    AuditEvent,
    AuditPayload,
)

STRATEGY_LIFECYCLE_SCHEMA_VERSION = 1
STRATEGY_LIFECYCLE_AUDIT_SCHEMA_NAME = "registry.strategy_lifecycle_transition"
STRATEGY_LIFECYCLE_AUDIT_EVENT_TYPE = "registry.strategy_lifecycle.transition"

_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}\Z")
_SCHEMA_NAME_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+){0,15}\Z")
_EVIDENCE_KIND_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+){0,15}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_URI_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]{1,511}\Z")
_SYMBOL_PATTERN = re.compile(r"[A-Z][A-Z0-9.-]{0,31}\Z")
_MIN_REASON_LENGTH = 1
_MAX_REASON_LENGTH = 512
_ZERO = Decimal("0")
_ONE = Decimal("1")


class StrategyLifecycleError(ValueError):
    """Base class for invalid or contradictory lifecycle data."""


class StrategyLifecycleValidationError(StrategyLifecycleError):
    """Raised when lifecycle data fails a schema or transition rule."""


class StrategyLifecycleIntegrityError(StrategyLifecycleError):
    """Raised when replayed lifecycle history contradicts existing state."""


class StrategyLifecycleState(StrEnum):
    """Strategy lifecycle states recorded by the registry."""

    PROPOSED = "PROPOSED"
    RESEARCH = "RESEARCH"
    BACKTESTED = "BACKTESTED"
    VALIDATED = "VALIDATED"
    PAPER = "PAPER"
    LIVE_CANDIDATE = "LIVE_CANDIDATE"
    LIMITED_LIVE = "LIMITED_LIVE"
    RETIRED = "RETIRED"


STRATEGY_LIFECYCLE_STATES: tuple[StrategyLifecycleState, ...] = (
    StrategyLifecycleState.PROPOSED,
    StrategyLifecycleState.RESEARCH,
    StrategyLifecycleState.BACKTESTED,
    StrategyLifecycleState.VALIDATED,
    StrategyLifecycleState.PAPER,
    StrategyLifecycleState.LIVE_CANDIDATE,
    StrategyLifecycleState.LIMITED_LIVE,
    StrategyLifecycleState.RETIRED,
)

_LEGAL_TRANSITIONS: dict[StrategyLifecycleState, frozenset[StrategyLifecycleState]] = {
    StrategyLifecycleState.PROPOSED: frozenset(
        {StrategyLifecycleState.RESEARCH, StrategyLifecycleState.RETIRED}
    ),
    StrategyLifecycleState.RESEARCH: frozenset(
        {StrategyLifecycleState.BACKTESTED, StrategyLifecycleState.RETIRED}
    ),
    StrategyLifecycleState.BACKTESTED: frozenset(
        {StrategyLifecycleState.VALIDATED, StrategyLifecycleState.RETIRED}
    ),
    StrategyLifecycleState.VALIDATED: frozenset(
        {StrategyLifecycleState.PAPER, StrategyLifecycleState.RETIRED}
    ),
    StrategyLifecycleState.PAPER: frozenset(
        {StrategyLifecycleState.LIVE_CANDIDATE, StrategyLifecycleState.RETIRED}
    ),
    StrategyLifecycleState.LIVE_CANDIDATE: frozenset(
        {StrategyLifecycleState.LIMITED_LIVE, StrategyLifecycleState.RETIRED}
    ),
    StrategyLifecycleState.LIMITED_LIVE: frozenset({StrategyLifecycleState.RETIRED}),
    StrategyLifecycleState.RETIRED: frozenset(),
}

LEGAL_STRATEGY_LIFECYCLE_TRANSITIONS: tuple[
    tuple[StrategyLifecycleState, StrategyLifecycleState], ...
] = tuple(
    (from_state, to_state)
    for from_state in STRATEGY_LIFECYCLE_STATES
    for to_state in sorted(_LEGAL_TRANSITIONS[from_state], key=lambda state: state.value)
)

_PROMOTION_TRANSITIONS = frozenset(
    {
        (StrategyLifecycleState.RESEARCH, StrategyLifecycleState.BACKTESTED),
        (StrategyLifecycleState.BACKTESTED, StrategyLifecycleState.VALIDATED),
        (StrategyLifecycleState.VALIDATED, StrategyLifecycleState.PAPER),
        (StrategyLifecycleState.PAPER, StrategyLifecycleState.LIVE_CANDIDATE),
        (StrategyLifecycleState.LIVE_CANDIDATE, StrategyLifecycleState.LIMITED_LIVE),
    }
)


def _validate_identifier(name: str, value: str) -> None:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise StrategyLifecycleValidationError(f"{name} has an invalid identifier")


def _validate_named_identifier(name: str, value: str, pattern: re.Pattern[str]) -> None:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise StrategyLifecycleValidationError(f"{name} has an invalid identifier")


def _validate_positive_int(name: str, value: int) -> None:
    if type(value) is not int or value <= 0:
        raise StrategyLifecycleValidationError(f"{name} must be a positive integer")


def _validate_schema_version(name: str, value: int, expected: int) -> None:
    if type(value) is not int or value != expected:
        raise StrategyLifecycleValidationError(f"{name} must be {expected}")


def _canonical_timestamp(value: datetime, *, name: str) -> str:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise StrategyLifecycleValidationError(f"{name} must be a timezone-aware UTC datetime")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validate_decimal(
    name: str,
    value: Decimal,
    *,
    minimum: Decimal = _ZERO,
    maximum: Decimal = _ONE,
    minimum_inclusive: bool = False,
) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise StrategyLifecycleValidationError(f"{name} must be a finite decimal")
    minimum_valid = value >= minimum if minimum_inclusive else value > minimum
    if not minimum_valid:
        qualifier = "at least" if minimum_inclusive else "greater than"
        raise StrategyLifecycleValidationError(f"{name} must be {qualifier} {minimum}")
    if value > maximum:
        raise StrategyLifecycleValidationError(f"{name} must be at most {maximum}")


def _canonical_decimal(value: Decimal) -> str:
    sign, digits, exponent = value.as_tuple()
    if type(exponent) is not int:
        raise StrategyLifecycleValidationError("risk-envelope decimals must be finite")
    if all(digit == 0 for digit in digits):
        return "0e0"

    significant_digits = list(digits)
    adjusted_exponent = exponent
    while significant_digits[-1] == 0:
        significant_digits.pop()
        adjusted_exponent += 1

    coefficient = "".join(str(digit) for digit in significant_digits)
    prefix = "-" if sign else ""
    return f"{prefix}{coefficient}e{adjusted_exponent}"


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256_mapping(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def is_legal_strategy_lifecycle_transition(
    from_state: StrategyLifecycleState,
    to_state: StrategyLifecycleState,
) -> bool:
    """Return whether the state pair is permitted by the closed lifecycle policy."""
    if (
        type(from_state) is not StrategyLifecycleState
        or type(to_state) is not StrategyLifecycleState
    ):
        return False
    return to_state in _LEGAL_TRANSITIONS[from_state]


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """A machine-readable reference to immutable lifecycle or promotion evidence."""

    kind: str
    uri: str
    sha256: str
    schema_name: str
    schema_version: int

    def __post_init__(self) -> None:
        _validate_named_identifier("evidence.kind", self.kind, _EVIDENCE_KIND_PATTERN)
        _validate_named_identifier("evidence.uri", self.uri, _URI_PATTERN)
        _validate_named_identifier("evidence.sha256", self.sha256, _SHA256_PATTERN)
        _validate_named_identifier("evidence.schema_name", self.schema_name, _SCHEMA_NAME_PATTERN)
        _validate_positive_int("evidence.schema_version", self.schema_version)

    def to_mapping(self) -> dict[str, object]:
        """Return a deterministic representation for hashes and audit payloads."""
        return {
            "kind": self.kind,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "sha256": self.sha256,
            "uri": self.uri,
        }


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    """Explicit owner approval evidence for the record-only limited-live state."""

    approved_by: str
    approved_at: datetime
    approval_reference: EvidenceReference

    def __post_init__(self) -> None:
        _validate_identifier("approval.approved_by", self.approved_by)
        _canonical_timestamp(self.approved_at, name="approval.approved_at")
        if type(self.approval_reference) is not EvidenceReference:
            raise StrategyLifecycleValidationError(
                "approval.approval_reference must be an EvidenceReference"
            )
        if self.approval_reference.kind != "owner_approval":
            raise StrategyLifecycleValidationError(
                "approval.approval_reference.kind must be owner_approval"
            )

    def to_mapping(self) -> dict[str, object]:
        """Return a deterministic representation for hashes and audit payloads."""
        return {
            "approval_reference": self.approval_reference.to_mapping(),
            "approved_at": _canonical_timestamp(self.approved_at, name="approval.approved_at"),
            "approved_by": self.approved_by,
        }


@dataclass(frozen=True, slots=True)
class RiskEnvelope:
    """Machine-readable constraints required before recording limited-live approval."""

    allowed_symbols: tuple[str, ...]
    max_gross_exposure_fraction: Decimal
    max_single_position_fraction: Decimal
    expires_at: datetime

    def __post_init__(self) -> None:
        if type(self.allowed_symbols) is not tuple or not self.allowed_symbols:
            raise StrategyLifecycleValidationError(
                "risk_envelope.allowed_symbols must be a non-empty tuple"
            )
        if len(set(self.allowed_symbols)) != len(self.allowed_symbols):
            raise StrategyLifecycleValidationError(
                "risk_envelope.allowed_symbols must not contain duplicates"
            )
        for symbol in self.allowed_symbols:
            _validate_named_identifier("risk_envelope.allowed_symbols", symbol, _SYMBOL_PATTERN)
        _validate_decimal(
            "risk_envelope.max_gross_exposure_fraction",
            self.max_gross_exposure_fraction,
        )
        _validate_decimal(
            "risk_envelope.max_single_position_fraction",
            self.max_single_position_fraction,
        )
        if self.max_single_position_fraction > self.max_gross_exposure_fraction:
            raise StrategyLifecycleValidationError(
                "risk_envelope.max_single_position_fraction must not exceed "
                "max_gross_exposure_fraction"
            )
        _canonical_timestamp(self.expires_at, name="risk_envelope.expires_at")

    def to_mapping(self) -> dict[str, object]:
        """Return a deterministic representation for hashes and audit payloads."""
        return {
            "allowed_symbols": list(self.allowed_symbols),
            "expires_at": _canonical_timestamp(
                self.expires_at,
                name="risk_envelope.expires_at",
            ),
            "max_gross_exposure_fraction": _canonical_decimal(self.max_gross_exposure_fraction),
            "max_single_position_fraction": _canonical_decimal(self.max_single_position_fraction),
        }


@dataclass(frozen=True, slots=True)
class StrategyLifecycleTransition:
    """An immutable, content-addressed strategy lifecycle transition."""

    schema_version: int
    transition_id: UUID
    strategy_id: str
    sequence: int
    from_state: StrategyLifecycleState
    to_state: StrategyLifecycleState
    decided_at: datetime
    actor: str
    evidence: tuple[EvidenceReference, ...] = ()
    approval_record: ApprovalRecord | None = None
    risk_envelope: RiskEnvelope | None = None
    reason: str = ""
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_schema_version(
            "transition.schema_version",
            self.schema_version,
            STRATEGY_LIFECYCLE_SCHEMA_VERSION,
        )
        if type(self.transition_id) is not UUID:
            raise StrategyLifecycleValidationError("transition.transition_id must be a UUID")
        _validate_identifier("transition.strategy_id", self.strategy_id)
        _validate_positive_int("transition.sequence", self.sequence)
        if type(self.from_state) is not StrategyLifecycleState:
            raise StrategyLifecycleValidationError(
                "transition.from_state must be a StrategyLifecycleState"
            )
        if type(self.to_state) is not StrategyLifecycleState:
            raise StrategyLifecycleValidationError(
                "transition.to_state must be a StrategyLifecycleState"
            )
        _canonical_timestamp(self.decided_at, name="transition.decided_at")
        _validate_identifier("transition.actor", self.actor)
        if type(self.evidence) is not tuple:
            raise StrategyLifecycleValidationError("transition.evidence must be a tuple")
        for reference in self.evidence:
            if type(reference) is not EvidenceReference:
                raise StrategyLifecycleValidationError(
                    "transition.evidence must contain EvidenceReference values"
                )
        _validate_unique_evidence(self.evidence)
        if self.approval_record is not None and type(self.approval_record) is not ApprovalRecord:
            raise StrategyLifecycleValidationError(
                "transition.approval_record must be an ApprovalRecord"
            )
        if self.risk_envelope is not None and type(self.risk_envelope) is not RiskEnvelope:
            raise StrategyLifecycleValidationError(
                "transition.risk_envelope must be a RiskEnvelope"
            )
        if type(self.reason) is not str:
            raise StrategyLifecycleValidationError("transition.reason must be a string")
        if self.reason and not _MIN_REASON_LENGTH <= len(self.reason) <= _MAX_REASON_LENGTH:
            raise StrategyLifecycleValidationError(
                f"transition.reason must be at most {_MAX_REASON_LENGTH} characters"
            )
        _validate_transition_requirements(
            from_state=self.from_state,
            to_state=self.to_state,
            decided_at=self.decided_at,
            evidence=self.evidence,
            approval_record=self.approval_record,
            risk_envelope=self.risk_envelope,
        )
        object.__setattr__(self, "content_sha256", _sha256_mapping(self._body_mapping()))

    def _body_mapping(self) -> dict[str, object]:
        return {
            "actor": self.actor,
            "approval_record": (
                self.approval_record.to_mapping() if self.approval_record is not None else None
            ),
            "decided_at": _canonical_timestamp(
                self.decided_at,
                name="transition.decided_at",
            ),
            "evidence": [reference.to_mapping() for reference in self.evidence],
            "from_state": self.from_state.value,
            "reason": self.reason,
            "risk_envelope": (
                self.risk_envelope.to_mapping() if self.risk_envelope is not None else None
            ),
            "schema_version": self.schema_version,
            "sequence": self.sequence,
            "strategy_id": self.strategy_id,
            "to_state": self.to_state.value,
            "transition_id": str(self.transition_id),
        }

    def to_mapping(self) -> dict[str, object]:
        """Return transition evidence including its deterministic content digest."""
        payload = self._body_mapping()
        payload["content_sha256"] = self.content_sha256
        return payload

    def to_audit_event(
        self,
        *,
        event_id: UUID,
        correlation_id: UUID,
        actor: AuditActor,
    ) -> AuditEvent:
        """Render the transition as an immutable audit event without side effects."""
        return AuditEvent(
            schema_version=AUDIT_EVENT_SCHEMA_VERSION,
            event_id=event_id,
            occurred_at=self.decided_at,
            actor=actor,
            event_type=STRATEGY_LIFECYCLE_AUDIT_EVENT_TYPE,
            correlation_id=correlation_id,
            payload=AuditPayload.from_mapping(
                schema_name=STRATEGY_LIFECYCLE_AUDIT_SCHEMA_NAME,
                schema_version=STRATEGY_LIFECYCLE_SCHEMA_VERSION,
                values=self.to_mapping(),
            ),
        )


def _validate_unique_evidence(evidence: tuple[EvidenceReference, ...]) -> None:
    evidence_keys = [
        (
            reference.kind,
            reference.uri,
            reference.schema_name,
            reference.schema_version,
        )
        for reference in evidence
    ]
    if len(set(evidence_keys)) != len(evidence_keys):
        raise StrategyLifecycleValidationError(
            "transition.evidence must not contain duplicates or conflicting digests "
            "for one artifact reference"
        )


def _validate_transition_requirements(
    *,
    from_state: StrategyLifecycleState,
    to_state: StrategyLifecycleState,
    decided_at: datetime,
    evidence: tuple[EvidenceReference, ...],
    approval_record: ApprovalRecord | None,
    risk_envelope: RiskEnvelope | None,
) -> None:
    if not is_legal_strategy_lifecycle_transition(from_state, to_state):
        raise StrategyLifecycleValidationError(
            f"transition from {from_state.value} to {to_state.value} is not permitted"
        )
    if (from_state, to_state) in _PROMOTION_TRANSITIONS and not evidence:
        raise StrategyLifecycleValidationError(
            "promotion transitions require machine-readable evidence references"
        )
    if to_state is StrategyLifecycleState.LIMITED_LIVE:
        if approval_record is None:
            raise StrategyLifecycleValidationError("LIMITED_LIVE requires an approval record")
        if risk_envelope is None:
            raise StrategyLifecycleValidationError("LIMITED_LIVE requires a risk envelope")
        if approval_record.approved_at > decided_at:
            raise StrategyLifecycleValidationError(
                "LIMITED_LIVE approval_record.approved_at must not be after transition.decided_at"
            )
        if risk_envelope.expires_at <= decided_at:
            raise StrategyLifecycleValidationError(
                "LIMITED_LIVE risk_envelope.expires_at must be after transition.decided_at"
            )
    elif approval_record is not None or risk_envelope is not None:
        raise StrategyLifecycleValidationError(
            "approval records and risk envelopes are only valid for LIMITED_LIVE transitions"
        )


@dataclass(frozen=True, slots=True)
class StrategyLifecycle:
    """Immutable strategy lifecycle history with append-only transition semantics."""

    strategy_id: str
    current_state: StrategyLifecycleState = StrategyLifecycleState.PROPOSED
    transitions: tuple[StrategyLifecycleTransition, ...] = ()

    def __post_init__(self) -> None:
        _validate_identifier("lifecycle.strategy_id", self.strategy_id)
        if type(self.current_state) is not StrategyLifecycleState:
            raise StrategyLifecycleValidationError(
                "lifecycle.current_state must be a StrategyLifecycleState"
            )
        if type(self.transitions) is not tuple:
            raise StrategyLifecycleValidationError("lifecycle.transitions must be a tuple")
        expected_from_state = StrategyLifecycleState.PROPOSED
        seen_transition_ids: set[UUID] = set()
        previous_decided_at: datetime | None = None
        for index, transition in enumerate(self.transitions, start=1):
            if type(transition) is not StrategyLifecycleTransition:
                raise StrategyLifecycleValidationError(
                    "lifecycle.transitions must contain StrategyLifecycleTransition values"
                )
            if transition.transition_id in seen_transition_ids:
                raise StrategyLifecycleIntegrityError(
                    f"transition_id {transition.transition_id} appears more than once"
                )
            seen_transition_ids.add(transition.transition_id)
            if transition.strategy_id != self.strategy_id:
                raise StrategyLifecycleIntegrityError(
                    "transition strategy_id does not match lifecycle strategy_id"
                )
            if transition.sequence != index:
                raise StrategyLifecycleIntegrityError(
                    "transition sequence does not match append order"
                )
            if transition.from_state is not expected_from_state:
                raise StrategyLifecycleIntegrityError(
                    "transition from_state does not match prior lifecycle state"
                )
            if previous_decided_at is not None and transition.decided_at < previous_decided_at:
                raise StrategyLifecycleIntegrityError(
                    "transition decided_at precedes the prior transition in append order"
                )
            previous_decided_at = transition.decided_at
            expected_from_state = transition.to_state
        if self.current_state is not expected_from_state:
            raise StrategyLifecycleIntegrityError(
                "lifecycle current_state does not match transition history"
            )

    @classmethod
    def initialize(cls, strategy_id: str) -> StrategyLifecycle:
        """Create a proposed lifecycle with no transition history."""
        return cls(strategy_id=strategy_id)

    @classmethod
    def replay(
        cls,
        *,
        strategy_id: str,
        transitions: Iterable[StrategyLifecycleTransition],
    ) -> StrategyLifecycle:
        """Rebuild lifecycle state from append-ordered transition evidence."""
        transition_tuple = tuple(transitions)
        current_state = (
            transition_tuple[-1].to_state if transition_tuple else StrategyLifecycleState.PROPOSED
        )
        return cls(
            strategy_id=strategy_id,
            current_state=current_state,
            transitions=transition_tuple,
        )

    def history(self) -> tuple[StrategyLifecycleTransition, ...]:
        """Return append-ordered transition evidence without mutable storage."""
        return self.transitions

    def append(self, transition: StrategyLifecycleTransition) -> StrategyLifecycle:
        """Return a new lifecycle with one verified transition appended."""
        return StrategyLifecycle.replay(
            strategy_id=self.strategy_id,
            transitions=(*self.transitions, transition),
        )

    def transition_to(
        self,
        *,
        transition_id: UUID,
        to_state: StrategyLifecycleState,
        decided_at: datetime,
        actor: str,
        evidence: Iterable[EvidenceReference] = (),
        approval_record: ApprovalRecord | None = None,
        risk_envelope: RiskEnvelope | None = None,
        reason: str = "",
    ) -> StrategyLifecycle:
        """Return a new lifecycle with a deterministic transition appended."""
        transition = StrategyLifecycleTransition(
            schema_version=STRATEGY_LIFECYCLE_SCHEMA_VERSION,
            transition_id=transition_id,
            strategy_id=self.strategy_id,
            sequence=len(self.transitions) + 1,
            from_state=self.current_state,
            to_state=to_state,
            decided_at=decided_at,
            actor=actor,
            evidence=tuple(evidence),
            approval_record=approval_record,
            risk_envelope=risk_envelope,
            reason=reason,
        )
        return self.append(transition)
