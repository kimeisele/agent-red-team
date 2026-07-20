"""Event repository — ``record_run_event`` with built-in commit-uncertainty
recovery.

This module owns the Slice-1 transactional persistence contract.  Every
multi-table mutation goes through the single public entry point
:meth:`EventRepository.record_run_event`.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from pathlib import Path

from agent_red_team.persistence.connection import connect, utc_timestamp
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

# ---------------------------------------------------------------------------
# Shared per-database-path process lock registry
# ---------------------------------------------------------------------------

_path_locks: dict[str, threading.Lock] = {}
_path_locks_lock = threading.Lock()


def _get_path_lock(db_path: Path) -> threading.Lock:
    resolved = str(db_path.resolve())
    with _path_locks_lock:
        if resolved not in _path_locks:
            _path_locks[resolved] = threading.Lock()
        return _path_locks[resolved]


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class EventRepository:
    """Transactional run-event persistence with built-in commit-uncertainty
    recovery.

    A repository instance owns one SQLite database file.  All writes are
    serialised through a per-database-path process-local lock, so two
    ``EventRepository`` instances targeting the same resolved path share the
    same lock.

    Thread-safe for single-process use.  Not safe for multi-process access.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._lock = _get_path_lock(self._db_path)

        with self._lock:
            conn = connect(self._db_path)
            try:
                apply_migration(conn)
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Public API (single normative operation)
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
        """Persist one audit event atomically with built-in recovery.

        Includes: explicit ``BEGIN IMMEDIATE``, idempotency check, conflict
        detection, commit-uncertainty recovery with a single bounded retry,
        and payload-integrity verification on replay.

        Returns:
            RecordRunEventResult — ``idempotent_replay=True`` when the
            operation was already committed.

        Raises:
            IdempotencyConflictError: same key, different request digest.
            IntegrityError: stored data fails integrity or a revision
                mismatch is detected on an existing run.
            ValueError: non-canonicalizable payload.
            sqlite3.Error: database-level failure.
        """
        # Pre-transaction validation (no db mutation).
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

        with self._lock:
            return self._record_run_event_locked(
                target_repository=target_repository,
                subject_type=subject_type,
                subject_path=subject_path,
                subj_id=_subj_id,
                request_id=request_id,
                target_revision=target_revision,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                causation_id=causation_id,
                event_type=event_type,
                event_payload=event_payload,
                canonical_payload=_canonical,
                payload_hash=_payload_hash,
                digest=_digest,
                current_phase=current_phase,
                phase_status=phase_status,
            )

    # ------------------------------------------------------------------
    # Private — called inside self._lock
    # ------------------------------------------------------------------

    def _record_run_event_locked(
        self,
        *,
        target_repository: str,
        subject_type: str,
        subject_path: str,
        subj_id: str,
        request_id: str,
        target_revision: str,
        operation_type: str,
        idempotency_key: str,
        correlation_id: str,
        causation_id: str | None,
        event_type: str,
        event_payload: dict,
        canonical_payload: str,
        payload_hash: str,
        digest: str,
        current_phase: str,
        phase_status: str,
        _is_retry: bool = False,
    ) -> RecordRunEventResult:
        """Core implementation — MUST be called inside ``self._lock``."""

        conn: sqlite3.Connection | None = None
        commit_started = False

        try:
            conn = connect(self._db_path)

            # ---- BEGIN IMMEDIATE ---------------------------------------
            conn.execute("BEGIN IMMEDIATE")

            # ---- idempotency check -------------------------------------
            row = conn.execute(
                "SELECT request_digest, result_reference "
                "FROM idempotency_records "
                "WHERE operation_type = ? AND idempotency_key = ?",
                (operation_type, idempotency_key),
            ).fetchone()

            if row is not None:
                stored_digest, result_ref = row
                if stored_digest != digest:
                    raise IdempotencyConflictError(
                        f"Idempotency key {operation_type}:{idempotency_key!r} "
                        f"already used with a different request"
                    )
                # Same digest — idempotent replay.
                conn.rollback()
                conn.close()
                conn = None
                return self._reconstruct_result(digest, result_ref, subj_id,
                                                current_phase, phase_status)

            # ---- subject + run resolution ------------------------------
            _ensure_subject(
                conn, subj_id, target_repository, subject_type,
                subject_path,
            )
            audit_run_id = _resolve_or_create_run(
                conn, subj_id, request_id, target_revision,
            )
            event_id = str(uuid.uuid4())
            now = utc_timestamp()

            # ---- insert event ------------------------------------------
            conn.execute(
                "INSERT INTO audit_events "
                "(event_id, correlation_id, causation_id, audit_run_id, "
                "event_type, timestamp, payload, payload_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id, correlation_id, causation_id, audit_run_id,
                    event_type, now, canonical_payload, payload_hash,
                ),
            )

            # ---- upsert run_state --------------------------------------
            conn.execute(
                "INSERT INTO run_state "
                "(audit_run_id, current_phase, phase_status, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(audit_run_id) DO UPDATE SET "
                "current_phase = excluded.current_phase, "
                "phase_status  = excluded.phase_status, "
                "updated_at    = excluded.updated_at",
                (audit_run_id, current_phase, phase_status, now),
            )

            # ---- insert idempotency record -----------------------------
            conn.execute(
                "INSERT INTO idempotency_records "
                "(operation_type, idempotency_key, request_digest, "
                "status, result_reference, created_at, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    operation_type, idempotency_key, digest,
                    _COMPLETED_STATUS, event_id, now, now,
                ),
            )

            # ---- COMMIT ------------------------------------------------
            commit_started = True
            conn.commit()
            conn.close()
            conn = None

            return RecordRunEventResult(
                analysis_subject_id=subj_id,
                audit_run_id=audit_run_id,
                event_id=event_id,
                payload_hash=payload_hash,
                current_phase=current_phase,
                phase_status=phase_status,
                idempotent_replay=False,
            )

        except IdempotencyConflictError:
            self._safe_rollback(conn)
            raise
        except Exception as exc:
            if not commit_started:
                # Deterministic rollback — propagate.
                self._safe_rollback(conn)
                raise
            # commit_started=True: outcome is uncertain.
            logger.warning(
                "Commit-uncertain failure for %s:%s: %s",
                operation_type, idempotency_key, exc,
            )
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        # ---- commit-uncertain recovery (still under self._lock) --------
        return self._resolve_uncertain_commit(
            target_repository=target_repository,
            subject_type=subject_type,
            subject_path=subject_path,
            subj_id=subj_id,
            request_id=request_id,
            target_revision=target_revision,
            operation_type=operation_type,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            causation_id=causation_id,
            event_type=event_type,
            event_payload=event_payload,
            canonical_payload=canonical_payload,
            payload_hash=payload_hash,
            digest=digest,
            current_phase=current_phase,
            phase_status=phase_status,
            _is_retry=_is_retry,
        )

    # ------------------------------------------------------------------
    # Commit-uncertainty resolution (still under lock)
    # ------------------------------------------------------------------

    def _resolve_uncertain_commit(
        self,
        *,
        target_repository: str,
        subject_type: str,
        subject_path: str,
        subj_id: str,
        request_id: str,
        target_revision: str,
        operation_type: str,
        idempotency_key: str,
        correlation_id: str,
        causation_id: str | None,
        event_type: str,
        event_payload: dict,
        canonical_payload: str,
        payload_hash: str,
        digest: str,
        current_phase: str,
        phase_status: str,
        _is_retry: bool,
    ) -> RecordRunEventResult:
        """Reopen database and resolve via idempotency record.

        MUST be called inside ``self._lock``.
        """

        conn = connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT request_digest, result_reference "
                "FROM idempotency_records "
                "WHERE operation_type = ? AND idempotency_key = ?",
                (operation_type, idempotency_key),
            ).fetchone()

            if row is None:
                # COMMIT did not succeed — retry once.
                if _is_retry:
                    raise IntegrityError(
                        f"Commit-uncertain recovery: no idempotency record "
                        f"after retry for {operation_type}:{idempotency_key!r}"
                    )
                logger.info(
                    "Commit-uncertain: no record for %s:%s — retrying once",
                    operation_type, idempotency_key,
                )
                conn.close()
                return self._record_run_event_locked(
                    target_repository=target_repository,
                    subject_type=subject_type,
                    subject_path=subject_path,
                    subj_id=subj_id,
                    request_id=request_id,
                    target_revision=target_revision,
                    operation_type=operation_type,
                    idempotency_key=idempotency_key,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    event_type=event_type,
                    event_payload=event_payload,
                    canonical_payload=canonical_payload,
                    payload_hash=payload_hash,
                    digest=digest,
                    current_phase=current_phase,
                    phase_status=phase_status,
                    _is_retry=True,
                )

            stored_digest, result_ref = row
            if stored_digest != digest:
                raise IdempotencyConflictError(
                    f"Idempotency key {operation_type}:{idempotency_key!r} "
                    f"already used with a different request"
                )

            logger.info(
                "Commit-uncertain: found committed record for %s:%s",
                operation_type, idempotency_key,
            )
            return self._reconstruct_result(
                digest, result_ref, subj_id, current_phase, phase_status,
            )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Replay / integrity read
    # ------------------------------------------------------------------

    def _reconstruct_result(
        self,
        digest: str,
        result_reference: str,
        subject_id: str,
        current_phase: str,
        phase_status: str,
    ) -> RecordRunEventResult:
        """Read back a committed event and verify payload integrity."""

        conn = connect(self._db_path)
        try:
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
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_rollback(conn: sqlite3.Connection | None) -> None:
        if conn is None:
            return
        try:
            conn.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _payload_digest_from_text(payload_text: str) -> str:
    return sha256_hex(payload_text.encode("utf-8"))


def _ensure_subject(
    conn: sqlite3.Connection,
    subject_id: str,
    target_repository: str,
    subject_type: str,
    subject_path: str,
) -> None:
    now = utc_timestamp()
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
) -> str:
    row = conn.execute(
        "SELECT audit_run_id, target_revision FROM audit_runs "
        "WHERE analysis_subject_id = ? AND request_id = ?",
        (subject_id, request_id),
    ).fetchone()

    if row is not None:
        existing_run_id, existing_revision = row
        if existing_revision != target_revision:
            raise IntegrityError(
                f"Run revision mismatch for subject {subject_id!r} "
                f"request {request_id!r}: stored {existing_revision!r}, "
                f"incoming {target_revision!r}"
            )
        return existing_run_id

    run_id = str(uuid.uuid4())
    now = utc_timestamp()
    conn.execute(
        "INSERT INTO audit_runs "
        "(audit_run_id, analysis_subject_id, request_id, "
        "started_at, target_revision, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, subject_id, request_id, now, target_revision, "IN_PROGRESS"),
    )
    return run_id
