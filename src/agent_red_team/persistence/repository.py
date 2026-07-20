"""Event repository — ``record_run_event`` and related read/recovery paths.

This module owns the Slice-1 transactional persistence contract.  Every
multi-table mutation goes through :meth:`EventRepository.record_run_event`.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_red_team.persistence.connection import connect
from agent_red_team.persistence.migration import apply as apply_migration
from agent_red_team.persistence.models import (
    IdempotencyConflictError,
    IntegrityError,
    RecordRunEventResult,
)
from agent_red_team.persistence.serialization import (
    analysis_subject_id as compute_subject_id,
    canonical_json_text,
    payload_digest,
    request_digest,
    sha256_hex,
)

logger = logging.getLogger(__name__)

_COMPLETED_STATUS = "COMPLETED"


class EventRepository:
    """Transactional run-event persistence.

    A repository instance owns one SQLite database file and serialises all
    writes through a process-local lock.  The database is created (or
    opened) and migrated on initialisation.

    Thread-safe for single-process use.  Not safe for multi-process access.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._lock = threading.Lock()

        conn = connect(self._db_path)
        try:
            apply_migration(conn)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_run_event(
        self,
        *,
        target_repository: str,
        subject_type: str,
        subject_path: str,
        request_id: str,
        target_revision: str,
        operation_type: str,
        idempotency_key: str,
        correlation_id: str,
        causation_id: str | None,
        event_type: str,
        event_payload: dict,
        current_phase: str,
        phase_status: str,
    ) -> RecordRunEventResult:
        """Persist one audit event atomically (per Issue #25 / #26).

        Returns:
            RecordRunEventResult — ``idempotent_replay=True`` when the
            operation was already committed.

        Raises:
            IdempotencyConflictError: same key, different request digest.
            IntegrityError: stored data fails payload or referential
                integrity verification.
            ValueError: *event_payload* is not canonicalizable (NaN etc.).
            sqlite3.Error: database-level failure.
        """
        # ---- pre-transaction validation (no db mutation) ---------------
        _canonical = canonical_json_text(event_payload)
        _payload_hash = payload_digest(event_payload)
        _digest = request_digest(
            target_repository=target_repository,
            subject_type=subject_type,
            subject_path=subject_path,
            request_id=request_id,
            target_revision=target_revision,
            operation_type=operation_type,
            correlation_id=correlation_id,
            causation_id=causation_id,
            event_type=event_type,
            event_payload=event_payload,
            current_phase=current_phase,
            phase_status=phase_status,
        )
        _subj_id = compute_subject_id(target_repository, subject_type, subject_path)
        _now = _utcnow()

        with self._lock:
            conn = connect(self._db_path)
            try:
                # ---- idempotency check ---------------------------------
                row = conn.execute(
                    "SELECT request_digest, result_reference "
                    "FROM idempotency_records "
                    "WHERE operation_type = ? AND idempotency_key = ?",
                    (operation_type, idempotency_key),
                ).fetchone()

                if row is not None:
                    stored_digest, result_ref = row
                    if stored_digest != _digest:
                        raise IdempotencyConflictError(
                            f"Idempotency key {operation_type}:{idempotency_key!r} "
                            f"already used with a different request"
                        )
                    return self._reconstruct_result(
                        conn, result_ref, _subj_id, current_phase, phase_status
                    )

                # ---- new operation -------------------------------------
                _ensure_subject(
                    conn, _subj_id, target_repository, subject_type,
                    subject_path, _now,
                )
                audit_run_id = _resolve_or_create_run(
                    conn, _subj_id, request_id, target_revision, _now,
                )
                event_id = str(uuid.uuid4())

                conn.execute(
                    "INSERT INTO audit_events "
                    "(event_id, correlation_id, causation_id, audit_run_id, "
                    "event_type, timestamp, payload, payload_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id, correlation_id, causation_id, audit_run_id,
                        event_type, _now, _canonical, _payload_hash,
                    ),
                )

                conn.execute(
                    "INSERT INTO run_state "
                    "(audit_run_id, current_phase, phase_status, updated_at) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(audit_run_id) DO UPDATE SET "
                    "current_phase = excluded.current_phase, "
                    "phase_status  = excluded.phase_status, "
                    "updated_at    = excluded.updated_at",
                    (audit_run_id, current_phase, phase_status, _now),
                )

                conn.execute(
                    "INSERT INTO idempotency_records "
                    "(operation_type, idempotency_key, request_digest, "
                    "status, result_reference, created_at, completed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        operation_type, idempotency_key, _digest,
                        _COMPLETED_STATUS, event_id, _now, _now,
                    ),
                )

                conn.commit()

                return RecordRunEventResult(
                    analysis_subject_id=_subj_id,
                    audit_run_id=audit_run_id,
                    event_id=event_id,
                    payload_hash=_payload_hash,
                    current_phase=current_phase,
                    phase_status=phase_status,
                    idempotent_replay=False,
                )

            except IdempotencyConflictError:
                conn.rollback()
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Commit-uncertainty recovery
    # ------------------------------------------------------------------

    def record_run_event_with_recovery(
        self,
        *,
        target_repository: str,
        subject_type: str,
        subject_path: str,
        request_id: str,
        target_revision: str,
        operation_type: str,
        idempotency_key: str,
        correlation_id: str,
        causation_id: str | None,
        event_type: str,
        event_payload: dict,
        current_phase: str,
        phase_status: str,
    ) -> RecordRunEventResult:
        """Public entry point with commit-uncertainty recovery.

        On a deterministic rollback the exception propagates.  On an
        ambiguous connection error during / after ``COMMIT``, the method
        re-opens the database and resolves the outcome via the idempotency
        record.  This is the preferred call-site for production code.
        """
        _uncertain = False
        _last_exc: Exception | None = None

        try:
            return self.record_run_event(
                target_repository=target_repository,
                subject_type=subject_type,
                subject_path=subject_path,
                request_id=request_id,
                target_revision=target_revision,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                causation_id=causation_id,
                event_type=event_type,
                event_payload=event_payload,
                current_phase=current_phase,
                phase_status=phase_status,
            )
        except IdempotencyConflictError:
            raise
        except Exception as exc:
            _last_exc = exc
            if _is_commit_uncertain(exc):
                _uncertain = True
            else:
                raise

        if not _uncertain:
            raise _last_exc  # type: ignore[misc]  # pragma: no cover

        # ---- uncertain outcome: reopen and resolve ----------------------
        _digest = request_digest(
            target_repository=target_repository,
            subject_type=subject_type,
            subject_path=subject_path,
            request_id=request_id,
            target_revision=target_revision,
            operation_type=operation_type,
            correlation_id=correlation_id,
            causation_id=causation_id,
            event_type=event_type,
            event_payload=event_payload,
            current_phase=current_phase,
            phase_status=phase_status,
        )
        _subj_id = compute_subject_id(target_repository, subject_type, subject_path)

        conn = connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT request_digest, result_reference "
                "FROM idempotency_records "
                "WHERE operation_type = ? AND idempotency_key = ?",
                (operation_type, idempotency_key),
            ).fetchone()

            if row is None:
                logger.info(
                    "Commit-uncertain recovery: no record for %s:%s — retrying",
                    operation_type, idempotency_key,
                )
                return self.record_run_event(
                    target_repository=target_repository,
                    subject_type=subject_type,
                    subject_path=subject_path,
                    request_id=request_id,
                    target_revision=target_revision,
                    operation_type=operation_type,
                    idempotency_key=idempotency_key,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    event_type=event_type,
                    event_payload=event_payload,
                    current_phase=current_phase,
                    phase_status=phase_status,
                )

            stored_digest, result_ref = row
            if stored_digest != _digest:
                raise IdempotencyConflictError(
                    f"Idempotency key {operation_type}:{idempotency_key!r} "
                    f"already used with a different request"
                )

            logger.info(
                "Commit-uncertain recovery: found record for %s:%s",
                operation_type, idempotency_key,
            )
            return self._reconstruct_result(
                conn, result_ref, _subj_id, current_phase, phase_status,
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reconstruct_result(
        self,
        conn: sqlite3.Connection,
        result_reference: str,
        subject_id: str,
        current_phase: str,
        phase_status: str,
    ) -> RecordRunEventResult:
        """Read back a committed event and verify payload integrity."""
        row = conn.execute(
            "SELECT event_id, audit_run_id, payload, payload_hash "
            "FROM audit_events WHERE event_id = ?",
            (result_reference,),
        ).fetchone()

        if row is None:
            raise IntegrityError(
                f"Idempotency record references missing event "
                f"{result_reference!r}"
            )

        event_id, audit_run_id, stored_payload, stored_hash = row

        if _payload_digest_from_text(stored_payload) != stored_hash:
            raise IntegrityError(
                f"Payload hash mismatch for event {event_id!r}"
            )

        return RecordRunEventResult(
            analysis_subject_id=subject_id,
            audit_run_id=audit_run_id,
            event_id=event_id,
            payload_hash=stored_hash,
            current_phase=current_phase,
            phase_status=phase_status,
            idempotent_replay=True,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_digest_from_text(payload_text: str) -> str:
    """SHA-256 of the exact stored payload text bytes."""
    return sha256_hex(payload_text.encode("utf-8"))


def _ensure_subject(
    conn: sqlite3.Connection,
    subject_id: str,
    target_repository: str,
    subject_type: str,
    subject_path: str,
    now: str,
) -> None:
    """Idempotently create the analysis_subject row."""
    conn.execute(
        "INSERT OR IGNORE INTO analysis_subjects "
        "(analysis_subject_id, target_repository, subject_type, "
        "subject_path, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (subject_id, target_repository, subject_type, subject_path, now),
    )


def _resolve_or_create_run(
    conn: sqlite3.Connection,
    subject_id: str,
    request_id: str,
    target_revision: str,
    now: str,
) -> str:
    """Return existing ``audit_run_id`` or create a new one."""
    row = conn.execute(
        "SELECT audit_run_id FROM audit_runs "
        "WHERE analysis_subject_id = ? AND request_id = ?",
        (subject_id, request_id),
    ).fetchone()
    if row is not None:
        return row[0]

    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO audit_runs "
        "(audit_run_id, analysis_subject_id, request_id, "
        "started_at, target_revision, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, subject_id, request_id, now, target_revision, "IN_PROGRESS"),
    )
    return run_id


def _is_commit_uncertain(exc: Exception) -> bool:
    """Return ``True`` when *exc* may have occurred during/after COMMIT.

    Conservative heuristic for Slice 1.  Connection drops, I/O errors, or
    bus errors during the commit phase leave the database in an unknown
    state.
    """
    import sqlite3

    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc).lower()
        return any(
            kw in msg
            for kw in ("disk i/o", "database is locked", "protocol", "connection")
        )
    if isinstance(exc, OSError):
        return True
    return False
