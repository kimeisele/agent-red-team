"""Slice-1 result and error types.

These are the only new public types introduced by the persistence layer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordRunEventResult:
    """Result returned by :func:`EventRepository.record_run_event`.

    All fields are populated for both new operations and idempotent replays.
    """

    analysis_subject_id: str
    audit_run_id: str
    event_id: str
    payload_hash: str
    current_phase: str
    phase_status: str
    idempotent_replay: bool


class IdempotencyConflictError(Exception):
    """Raised when the same idempotency key is reused with a different request."""


class IntegrityError(Exception):
    """Raised when stored data fails integrity verification.

    This covers payload-hash mismatch, missing referenced events, foreign-key
    corruption, and other internal consistency failures.
    """
