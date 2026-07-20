"""Slice-1 persistence foundation — transactional run-event storage.

Exports are intentionally minimal.  Only the approved public contract is exposed.
"""

from agent_red_team.persistence.connection import utc_timestamp
from agent_red_team.persistence.models import (
    IdempotencyConflictError,
    IntegrityError,
    RecordRunEventResult,
)
from agent_red_team.persistence.repository import EventRepository

__all__ = [
    "EventRepository",
    "IdempotencyConflictError",
    "IntegrityError",
    "RecordRunEventResult",
    "utc_timestamp",
]
