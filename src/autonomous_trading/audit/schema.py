"""Immutable, versioned audit schemas with deterministic integrity evidence."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import cast
from uuid import UUID

AUDIT_EVENT_SCHEMA_VERSION = 1
REDACTED_VALUE = "[REDACTED]"

_EVENT_TYPE_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+){0,15}\Z")
_SCHEMA_NAME_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+){0,15}\Z")
_ACTOR_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}\Z")
_CAMEL_BOUNDARY_PATTERN = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_SEPARATOR_PATTERN = re.compile(r"[^A-Za-z0-9]+")
_SENSITIVE_TOKENS = frozenset(
    {
        "authorization",
        "credential",
        "credentials",
        "password",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
)
_SENSITIVE_COMPACT_KEYS = frozenset(
    {
        "accesskey",
        "apikey",
        "privatekey",
        "refreshtoken",
        "sessiontoken",
    }
)
_MIN_JSON_INTEGER = -(2**63)
_MAX_JSON_INTEGER = 2**63 - 1


class AuditError(ValueError):
    """Base class for invalid or unverifiable audit data."""


class AuditValidationError(AuditError):
    """Raised when audit data does not satisfy the versioned schema."""


class AuditIntegrityError(AuditError):
    """Raised when audit content fails integrity or replay checks."""


class ActorKind(StrEnum):
    """Supported attributable actor categories."""

    AGENT = "agent"
    OPERATOR = "operator"
    SERVICE = "service"
    SYSTEM = "system"


def _validate_positive_int(name: str, value: int) -> None:
    if type(value) is not int or value <= 0:
        raise AuditValidationError(f"{name} must be a positive integer")


def _validate_identifier(name: str, value: str, pattern: re.Pattern[str]) -> None:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise AuditValidationError(f"{name} has an invalid identifier")


def _is_sensitive_key(key: str) -> bool:
    separated = _CAMEL_BOUNDARY_PATTERN.sub("_", key)
    tokens = tuple(token.lower() for token in _KEY_SEPARATOR_PATTERN.split(separated) if token)
    compact = "".join(tokens)
    return bool(_SENSITIVE_TOKENS.intersection(tokens)) or compact in _SENSITIVE_COMPACT_KEYS


def _normalise_json_value(value: object, *, path: str) -> object:
    if value is None or type(value) is bool or type(value) is str:
        return value
    if type(value) is int:
        if not _MIN_JSON_INTEGER <= value <= _MAX_JSON_INTEGER:
            raise AuditValidationError(f"{path} integer must fit signed 64-bit range")
        return value
    if type(value) in {list, tuple}:
        items = cast(list[object] | tuple[object, ...], value)
        return [
            _normalise_json_value(item, path=f"{path}[{index}]") for index, item in enumerate(items)
        ]
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        normalised: dict[str, object] = {}
        for key, item in mapping.items():
            if type(key) is not str:
                raise AuditValidationError(f"{path} keys must be strings")
            item_path = f"{path}.{key}"
            if _is_sensitive_key(key) and item != REDACTED_VALUE:
                raise AuditValidationError(
                    f"{item_path} must be omitted or set to {REDACTED_VALUE!r}"
                )
            normalised[key] = _normalise_json_value(item, path=item_path)
        return normalised
    raise AuditValidationError(
        f"{path} must contain only JSON strings, signed 64-bit integers, booleans, "
        "null, arrays, or objects"
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _duplicate_rejecting_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise AuditValidationError(f"audit JSON contains duplicate key {key!r}")
        value[key] = item
    return value


def _reject_float(value: str) -> object:
    raise AuditValidationError(f"audit JSON floating-point value {value!r} is not supported")


def _reject_constant(value: str) -> object:
    raise AuditValidationError(f"audit JSON constant {value!r} is not supported")


def _parse_json(data: str | bytes) -> object:
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AuditValidationError("audit JSON must be valid UTF-8") from error
    elif type(data) is str:
        text = data
    else:
        raise AuditValidationError("audit JSON must be text or UTF-8 bytes")

    try:
        return json.loads(
            text,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except AuditValidationError:
        raise
    except (json.JSONDecodeError, ValueError) as error:
        raise AuditValidationError(f"audit JSON is invalid: {error}") from error


def _require_object(value: object, path: str) -> dict[str, object]:
    if type(value) is not dict:
        raise AuditValidationError(f"{path} must be an object")
    return cast(dict[str, object], value)


def _require_mapping(value: object, path: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise AuditValidationError(f"{path} must be a mapping")
    return cast(Mapping[object, object], value)


def _require_exact_fields(
    value: Mapping[str, object],
    expected: frozenset[str],
    path: str,
) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    failures: list[str] = []
    if missing:
        failures.append(f"missing fields: {', '.join(missing)}")
    if unknown:
        failures.append(f"unknown fields: {', '.join(unknown)}")
    if failures:
        raise AuditValidationError(f"{path} has {'; '.join(failures)}")


def _require_string(value: Mapping[str, object], key: str, path: str) -> str:
    candidate = value[key]
    if type(candidate) is not str:
        raise AuditValidationError(f"{path}.{key} must be a string")
    return candidate


def _require_integer(value: Mapping[str, object], key: str, path: str) -> int:
    candidate = value[key]
    if type(candidate) is not int:
        raise AuditValidationError(f"{path}.{key} must be an integer")
    return candidate


def _parse_uuid(value: str, path: str) -> UUID:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise AuditValidationError(f"{path} must be a canonical UUID") from error
    if str(parsed) != value:
        raise AuditValidationError(f"{path} must be a canonical UUID")
    return parsed


def _canonical_timestamp(value: datetime) -> str:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise AuditValidationError("occurred_at must be a timezone-aware UTC datetime")
    canonical = value.astimezone(UTC)
    return canonical.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise AuditValidationError("audit_event.occurred_at must use canonical UTC Z notation")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as error:
        raise AuditValidationError(
            "audit_event.occurred_at must be an ISO-8601 timestamp"
        ) from error
    if _canonical_timestamp(parsed) != value:
        raise AuditValidationError(
            "audit_event.occurred_at must use canonical microsecond UTC form"
        )
    return parsed


@dataclass(frozen=True, slots=True)
class AuditActor:
    """An explicitly attributed source of an audit event."""

    kind: ActorKind
    identifier: str

    def __post_init__(self) -> None:
        if type(self.kind) is not ActorKind:
            raise AuditValidationError("actor.kind must be an ActorKind")
        _validate_identifier("actor.identifier", self.identifier, _ACTOR_IDENTIFIER_PATTERN)


@dataclass(frozen=True, slots=True)
class AuditPayload:
    """An immutable canonical JSON payload with an owning schema."""

    schema_name: str
    schema_version: int
    canonical_json: str
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_identifier("payload.schema_name", self.schema_name, _SCHEMA_NAME_PATTERN)
        _validate_positive_int("payload.schema_version", self.schema_version)
        if type(self.canonical_json) is not str:
            raise AuditValidationError("payload.canonical_json must be a string")
        parsed = _require_object(_parse_json(self.canonical_json), "payload.values")
        normalised = _normalise_json_value(parsed, path="payload.values")
        canonical_json = _canonical_json(normalised)
        if self.canonical_json != canonical_json:
            raise AuditValidationError("payload.canonical_json must use canonical JSON encoding")
        object.__setattr__(self, "sha256", _sha256(canonical_json))

    @classmethod
    def from_mapping(
        cls,
        *,
        schema_name: str,
        schema_version: int,
        values: Mapping[str, object],
    ) -> AuditPayload:
        """Create an immutable payload detached from caller-owned mappings."""
        normalised = _normalise_json_value(
            _require_mapping(values, "payload.values"),
            path="payload.values",
        )
        return cls(
            schema_name=schema_name,
            schema_version=schema_version,
            canonical_json=_canonical_json(normalised),
        )

    def to_mapping(self) -> dict[str, object]:
        """Return a fresh mutable copy without exposing stored state."""
        return _require_object(_parse_json(self.canonical_json), "payload.values")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """An immutable attributable audit event with deterministic integrity evidence."""

    schema_version: int
    event_id: UUID
    occurred_at: datetime
    actor: AuditActor
    event_type: str
    correlation_id: UUID
    payload: AuditPayload
    integrity_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or (
            self.schema_version != AUDIT_EVENT_SCHEMA_VERSION
        ):
            raise AuditValidationError(f"schema_version must be {AUDIT_EVENT_SCHEMA_VERSION}")
        if type(self.event_id) is not UUID:
            raise AuditValidationError("event_id must be a UUID")
        _canonical_timestamp(self.occurred_at)
        if type(self.actor) is not AuditActor:
            raise AuditValidationError("actor must be an AuditActor")
        _validate_identifier("event_type", self.event_type, _EVENT_TYPE_PATTERN)
        if type(self.correlation_id) is not UUID:
            raise AuditValidationError("correlation_id must be a UUID")
        if type(self.payload) is not AuditPayload:
            raise AuditValidationError("payload must be an AuditPayload")
        object.__setattr__(self, "integrity_sha256", _sha256(self._canonical_body_json()))

    def _body(self) -> dict[str, object]:
        return {
            "actor": {
                "identifier": self.actor.identifier,
                "kind": self.actor.kind.value,
            },
            "correlation_id": str(self.correlation_id),
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": _canonical_timestamp(self.occurred_at),
            "payload": {
                "schema_name": self.payload.schema_name,
                "schema_version": self.payload.schema_version,
                "sha256": self.payload.sha256,
                "values": self.payload.to_mapping(),
            },
            "schema_version": self.schema_version,
        }

    def _canonical_body_json(self) -> str:
        return _canonical_json(self._body())

    def to_json(self) -> str:
        """Serialize the event as canonical JSON including its integrity digest."""
        envelope = self._body()
        envelope["integrity_sha256"] = self.integrity_sha256
        return _canonical_json(envelope)

    @classmethod
    def from_json(cls, data: str | bytes) -> AuditEvent:
        """Parse and verify an untrusted serialized audit event."""
        document = _require_object(_parse_json(data), "audit_event")
        _require_exact_fields(
            document,
            frozenset(
                {
                    "actor",
                    "correlation_id",
                    "event_id",
                    "event_type",
                    "integrity_sha256",
                    "occurred_at",
                    "payload",
                    "schema_version",
                }
            ),
            "audit_event",
        )

        actor_document = _require_object(document["actor"], "audit_event.actor")
        _require_exact_fields(
            actor_document,
            frozenset({"identifier", "kind"}),
            "audit_event.actor",
        )
        actor_kind_value = _require_string(actor_document, "kind", "audit_event.actor")
        try:
            actor_kind = ActorKind(actor_kind_value)
        except ValueError as error:
            supported = ", ".join(kind.value for kind in ActorKind)
            raise AuditValidationError(
                f"audit_event.actor.kind must be one of: {supported}"
            ) from error

        payload_document = _require_object(document["payload"], "audit_event.payload")
        _require_exact_fields(
            payload_document,
            frozenset({"schema_name", "schema_version", "sha256", "values"}),
            "audit_event.payload",
        )
        payload_values = _require_object(
            payload_document["values"],
            "audit_event.payload.values",
        )
        payload = AuditPayload.from_mapping(
            schema_name=_require_string(
                payload_document,
                "schema_name",
                "audit_event.payload",
            ),
            schema_version=_require_integer(
                payload_document,
                "schema_version",
                "audit_event.payload",
            ),
            values=payload_values,
        )
        serialized_payload_digest = _require_string(
            payload_document,
            "sha256",
            "audit_event.payload",
        )
        if not hmac.compare_digest(payload.sha256, serialized_payload_digest):
            raise AuditIntegrityError("audit payload digest does not match its content")

        event = cls(
            schema_version=_require_integer(document, "schema_version", "audit_event"),
            event_id=_parse_uuid(
                _require_string(document, "event_id", "audit_event"),
                "audit_event.event_id",
            ),
            occurred_at=_parse_timestamp(_require_string(document, "occurred_at", "audit_event")),
            actor=AuditActor(
                kind=actor_kind,
                identifier=_require_string(
                    actor_document,
                    "identifier",
                    "audit_event.actor",
                ),
            ),
            event_type=_require_string(document, "event_type", "audit_event"),
            correlation_id=_parse_uuid(
                _require_string(document, "correlation_id", "audit_event"),
                "audit_event.correlation_id",
            ),
            payload=payload,
        )
        serialized_event_digest = _require_string(
            document,
            "integrity_sha256",
            "audit_event",
        )
        if not hmac.compare_digest(event.integrity_sha256, serialized_event_digest):
            raise AuditIntegrityError("audit event digest does not match its content")
        canonical_input = data.decode("utf-8") if isinstance(data, bytes) else data
        if event.to_json() != canonical_input:
            raise AuditValidationError("audit event must use canonical JSON encoding")
        return event
