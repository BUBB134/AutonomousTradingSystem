"""Append-only in-memory audit log semantics."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from .schema import AuditEvent, AuditIntegrityError, AuditValidationError


class InMemoryAuditLog:
    """An append-only event log used for domain semantics and deterministic replay."""

    __slots__ = ("__by_id", "__events")

    def __init__(self) -> None:
        self.__events: list[AuditEvent] = []
        self.__by_id: dict[UUID, AuditEvent] = {}

    def __len__(self) -> int:
        return len(self.__events)

    def append(self, event: AuditEvent) -> AuditEvent:
        """Append once, accept identical replay, and reject conflicting replay."""
        if type(event) is not AuditEvent:
            raise AuditValidationError("audit log accepts only AuditEvent values")
        existing = self.__by_id.get(event.event_id)
        if existing is None:
            self.__events.append(event)
            self.__by_id[event.event_id] = event
            return event
        if existing == event:
            return existing
        raise AuditIntegrityError(f"event_id {event.event_id} was replayed with different content")

    def get(self, event_id: UUID) -> AuditEvent | None:
        """Return an event by stable ID without exposing mutable storage."""
        if type(event_id) is not UUID:
            raise AuditValidationError("event_id must be a UUID")
        return self.__by_id.get(event_id)

    def events(self) -> tuple[AuditEvent, ...]:
        """Return events in authoritative first-append order."""
        return tuple(self.__events)

    def serialize(self) -> tuple[str, ...]:
        """Return canonical serialized events in authoritative append order."""
        return tuple(event.to_json() for event in self.__events)

    @classmethod
    def replay(cls, events: Iterable[str | bytes]) -> InMemoryAuditLog:
        """Rebuild a log from verified serialized events."""
        log = cls()
        for serialized_event in events:
            log.append(AuditEvent.from_json(serialized_event))
        return log
