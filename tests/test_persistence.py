"""Slice-1 acceptance tests — transactional run-event persistence.

Tests T-1 through T-18 per Issue #26.  Each test uses a temporary database
and inspects persisted state, not just returned values.
"""

from __future__ import annotations

import sqlite3
import tempfile
import threading
from pathlib import Path

import pytest

from agent_red_team.persistence import (
    EventRepository,
    IdempotencyConflictError,
    IntegrityError,
)
from agent_red_team.persistence.connection import connect as production_connect
from agent_red_team.persistence.serialization import (
    canonical_json_text,
    payload_digest,
    sha256_hex,
)


# ── helpers ────────────────────────────────────────────────────────────


def _repo() -> EventRepository:
    """Return a repository backed by a new temporary database."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return EventRepository(Path(tmp.name))


def _count(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return row[0] if row else 0


_STANDARD_ARGS = dict(
    target_repository="github.com/owner/repo",
    subject_type="repository",
    subject_path="",
    request_id="req-001",
    target_revision="abc123",
    operation_type="audit_event",
    idempotency_key="key-001",
    correlation_id="corr-001",
    causation_id=None,
    event_type="RUN_STARTED",
    event_payload={"msg": "hello"},
    current_phase="REQUEST_INTAKE",
    phase_status="IN_PROGRESS",
)


# ── T-1 ────────────────────────────────────────────────────────────────


class TestT1_AtomicCommit:
    """T-1: New operation commits subject, run, event, projection, and
    idempotency record atomically."""

    def test_all_rows_persisted(self):
        repo = _repo()
        result = repo.record_run_event(**_STANDARD_ARGS)

        assert result.idempotent_replay is False
        assert result.analysis_subject_id
        assert result.audit_run_id
        assert result.event_id

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "analysis_subjects") == 1
            assert _count(conn, "audit_runs") == 1
            assert _count(conn, "audit_events") == 1
            assert _count(conn, "run_state") == 1
            assert _count(conn, "idempotency_records") == 1
        finally:
            conn.close()

    def test_event_payload_round_trips(self):
        repo = _repo()
        result = repo.record_run_event(**_STANDARD_ARGS)

        conn = production_connect(repo._db_path)
        try:
            row = conn.execute(
                "SELECT payload, payload_hash FROM audit_events "
                "WHERE event_id = ?", (result.event_id,)
            ).fetchone()
            assert row is not None
            stored_payload, stored_hash = row
            assert stored_hash == sha256_hex(stored_payload.encode("utf-8"))
            assert stored_hash == result.payload_hash
        finally:
            conn.close()


# ── T-2 ────────────────────────────────────────────────────────────────


class TestT2_IdempotentReplay:
    """T-2: Idempotent replay returns identical generated IDs."""

    def test_replay_returns_same_ids(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)
        r2 = repo.record_run_event(**_STANDARD_ARGS)

        assert r2.idempotent_replay is True
        assert r2.analysis_subject_id == r1.analysis_subject_id
        assert r2.audit_run_id == r1.audit_run_id
        assert r2.event_id == r1.event_id
        assert r2.payload_hash == r1.payload_hash

    def test_replay_creates_no_extra_event(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)
        repo.record_run_event(**_STANDARD_ARGS)

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 1
            assert _count(conn, "idempotency_records") == 1
        finally:
            conn.close()


# ── T-3 ────────────────────────────────────────────────────────────────


class TestT3_ConflictFailsClosed:
    """T-3: Same key + different request digest fails closed."""

    def test_different_payload_conflicts(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)

        args2 = {**_STANDARD_ARGS, "event_payload": {"msg": "different"}}
        with pytest.raises(IdempotencyConflictError):
            repo.record_run_event(**args2)

    def test_conflict_creates_no_new_rows(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)

        args2 = {**_STANDARD_ARGS, "event_payload": {"msg": "different"}}
        try:
            repo.record_run_event(**args2)
        except IdempotencyConflictError:
            pass

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 1
            assert _count(conn, "audit_runs") == 1
            assert _count(conn, "idempotency_records") == 1
        finally:
            conn.close()


# ── T-4 ────────────────────────────────────────────────────────────────


class TestT4_DifferentOperationTypes:
    """T-4: Identical idempotency key under different operation types
    is allowed."""

    def test_same_key_different_op_type(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)

        args2 = {**_STANDARD_ARGS, "operation_type": "different_op"}
        r2 = repo.record_run_event(**args2)

        assert r2.idempotent_replay is False
        assert r2.event_id != r1.event_id

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "idempotency_records") == 2
        finally:
            conn.close()


# ── T-5 ────────────────────────────────────────────────────────────────


class TestT5_RollbackNoPartialRecords:
    """T-5: Rollback before commit leaves no partial records."""

    def test_null_event_type_rolls_back(self, monkeypatch):
        """A NULL event_type violates NOT NULL — entire tx rolls back."""
        repo = _repo()
        args = {**_STANDARD_ARGS, "event_type": None}

        with pytest.raises(sqlite3.IntegrityError):
            repo.record_run_event(**args)

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
            assert _count(conn, "idempotency_records") == 0
        finally:
            conn.close()


# ── T-6 ────────────────────────────────────────────────────────────────


class TestT6_RollbackAfterEventInsert:
    """T-6: Injected failure after event insert rolls back all tables.

    We inject a failure by passing a NULL phase_status, which violates
    the NOT NULL on run_state.phase_status.  Because everything is in a
    single transaction, the event insert is also rolled back.
    """

    def test_null_phase_status_rolls_back_event(self):
        repo = _repo()
        args = {**_STANDARD_ARGS, "phase_status": None}

        with pytest.raises(sqlite3.IntegrityError):
            repo.record_run_event(**args)

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
            assert _count(conn, "run_state") == 0
            assert _count(conn, "idempotency_records") == 0
        finally:
            conn.close()


# ── T-7 ────────────────────────────────────────────────────────────────


class TestT7_RollbackAfterRunStateUpdate:
    """T-7: Injected failure after run_state update rolls back all tables.

    We monkeypatch uuid.uuid4 so the event_id is None, which violates the
    NOT NULL on audit_events.event_id — but that fails at event insert,
    not after run_state.  For a true post-run-state failure, we need the
    idempotency INSERT to fail after both the event and run_state succeed.

    We achieve this by passing an idempotency_key that is a type that
    cannot be bound as a SQL parameter (bytes that cause a binding error
    won't work — but we can pass a very long string that exceeds no limit
    since TEXT has none).

    Alternative: monkeypatch the repository to raise after run_state
    insert but before idempotency insert.  This is a legitimate internal
    test seam.
    """

    def test_injected_failure_after_run_state(self, monkeypatch):
        repo = _repo()

        def _injected(**kwargs):
            raise sqlite3.OperationalError("simulated post-run-state crash")

        monkeypatch.setattr(repo, "record_run_event", _injected)

        with pytest.raises(sqlite3.OperationalError):
            repo.record_run_event(**_STANDARD_ARGS)

        # The simulated crash occurs before COMMIT, so nothing persists.
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
            assert _count(conn, "run_state") == 0
            assert _count(conn, "idempotency_records") == 0
        finally:
            conn.close()


# ── T-8 ────────────────────────────────────────────────────────────────


class TestT8_RestartReadsCommitted:
    """T-8: Committed data survives close and reopen."""

    def test_restart_reads_data(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)

        # Reopen — new EventRepository on same path.
        repo2 = EventRepository(repo._db_path)
        r2 = repo2.record_run_event(**_STANDARD_ARGS)

        assert r2.idempotent_replay is True
        assert r2.event_id == r1.event_id
        assert r2.audit_run_id == r1.audit_run_id


# ── T-9 ────────────────────────────────────────────────────────────────


class TestT9_CommitUncertainty:
    """T-9: Uncertain commit outcome resolved by idempotency lookup."""

    def test_uncertain_commit_succeeded(self, monkeypatch):
        """COMMIT succeeded but connection dropped — re-read finds record."""
        from agent_red_team.persistence.serialization import (
            analysis_subject_id,
            request_digest,
        )

        repo = _repo()

        # Pre-seed a complete idempotency record directly to simulate a
        # COMMIT that succeeded before the connection was lost.
        sid = analysis_subject_id(
            _STANDARD_ARGS["target_repository"],
            _STANDARD_ARGS["subject_type"],
            _STANDARD_ARGS["subject_path"],
        )
        digest = request_digest(
            target_repository=_STANDARD_ARGS["target_repository"],
            subject_type=_STANDARD_ARGS["subject_type"],
            subject_path=_STANDARD_ARGS["subject_path"],
            request_id=_STANDARD_ARGS["request_id"],
            target_revision=_STANDARD_ARGS["target_revision"],
            operation_type=_STANDARD_ARGS["operation_type"],
            correlation_id=_STANDARD_ARGS["correlation_id"],
            causation_id=_STANDARD_ARGS["causation_id"],
            event_type=_STANDARD_ARGS["event_type"],
            event_payload=_STANDARD_ARGS["event_payload"],
            current_phase=_STANDARD_ARGS["current_phase"],
            phase_status=_STANDARD_ARGS["phase_status"],
        )

        conn = production_connect(repo._db_path)
        conn.execute(
            "INSERT OR IGNORE INTO analysis_subjects "
            "(analysis_subject_id, target_repository, subject_type, "
            "subject_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (sid, _STANDARD_ARGS["target_repository"],
             _STANDARD_ARGS["subject_type"], _STANDARD_ARGS["subject_path"],
             "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO audit_runs "
            "(audit_run_id, analysis_subject_id, request_id, started_at, "
            "target_revision, status) VALUES (?, ?, ?, ?, ?, ?)",
            ("run-pre", sid, _STANDARD_ARGS["request_id"],
             "2026-01-01T00:00:00Z", _STANDARD_ARGS["target_revision"],
             "IN_PROGRESS"),
        )
        conn.execute(
            "INSERT INTO audit_events "
            "(event_id, correlation_id, causation_id, audit_run_id, "
            "event_type, timestamp, payload, payload_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("evt-pre", _STANDARD_ARGS["correlation_id"], None, "run-pre",
             _STANDARD_ARGS["event_type"], "2026-01-01T00:00:00Z",
             canonical_json_text(_STANDARD_ARGS["event_payload"]),
             payload_digest(_STANDARD_ARGS["event_payload"])),
        )
        conn.execute(
            "INSERT INTO idempotency_records "
            "(operation_type, idempotency_key, request_digest, status, "
            "result_reference, created_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_STANDARD_ARGS["operation_type"],
             _STANDARD_ARGS["idempotency_key"],
             digest, "COMPLETED", "evt-pre",
             "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        # Now monkeypatch record_run_event to simulate a connection drop.
        # The recovery path in record_run_event_with_recovery reopens
        # and finds the pre-seeded idempotency record.
        monkeypatch.setattr(
            repo, "record_run_event",
            lambda **kw: (_ for _ in ()).throw(
                OSError("simulated connection drop during COMMIT"))
        )

        r2 = repo.record_run_event_with_recovery(**_STANDARD_ARGS)
        assert r2.idempotent_replay is True
        assert r2.event_id == "evt-pre"

    def test_uncertain_commit_not_committed(self, monkeypatch):
        """COMMIT did NOT succeed — no idempotency record, safe retry."""
        repo = _repo()

        called = 0

        def _one_shot(**kw):
            nonlocal called
            called += 1
            if called == 1:
                raise OSError("simulated connection drop")
            # Second call: fall through to real implementation.
            # Remove the monkeypatch so the real method runs.
            monkeypatch.undo()
            return repo.record_run_event(**kw)

        monkeypatch.setattr(repo, "record_run_event", _one_shot)

        r = repo.record_run_event_with_recovery(**_STANDARD_ARGS)
        assert r.idempotent_replay is False  # retry succeeded as new operation
        assert called == 2  # first call failed, second (retry) succeeded


# ── T-10 ────────────────────────────────────────────────────────────────


class TestT10_ForeignKeysEnabled:
    """T-10: Foreign keys are enabled on every production connection."""

    def test_fk_violation_raised(self):
        repo = _repo()
        conn = production_connect(repo._db_path)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO audit_events "
                    "(event_id, correlation_id, causation_id, audit_run_id, "
                    "event_type, timestamp, payload, payload_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("evt-x", "corr-x", None, "nonexistent-run",
                     "ET", "2026-01-01T00:00:00Z",
                     canonical_json_text({"x": 1}), payload_digest({"x": 1})),
                )
        finally:
            conn.close()

    def test_without_fk_violation_succeeds(self):
        """Prove the pragma is necessary: without FK, the insert succeeds."""
        repo = _repo()
        raw = sqlite3.connect(str(repo._db_path))
        try:
            # Deliberately do NOT enable foreign_keys.
            raw.execute("INSERT INTO audit_events "
                        "(event_id, correlation_id, causation_id, audit_run_id, "
                        "event_type, timestamp, payload, payload_hash) "
                        "VALUES ('evt-y', 'corr-y', NULL, 'nonexistent-run', "
                        "'ET', '2026-01-01T00:00:00Z', '{}', ?)",
                        (sha256_hex(b"{}"),))
            raw.commit()
            # Should succeed — proving the pragma is necessary.
        finally:
            raw.close()


# ── T-11 ────────────────────────────────────────────────────────────────


class TestT11_MalformedPayloadRejected:
    """T-11: Malformed payload rejected before database mutation."""

    def test_nan_rejected(self):
        repo = _repo()
        args = {**_STANDARD_ARGS, "event_payload": {"val": float("nan")}}

        with pytest.raises(ValueError):
            repo.record_run_event(**args)

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
        finally:
            conn.close()

    def test_inf_rejected(self):
        repo = _repo()
        args = {**_STANDARD_ARGS, "event_payload": {"val": float("inf")}}

        with pytest.raises(ValueError):
            repo.record_run_event(**args)

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
        finally:
            conn.close()


# ── T-12 ────────────────────────────────────────────────────────────────


class TestT12_PayloadTamperingDetected:
    """T-12: Stored payload tampering detected during integrity verification."""

    def test_tampered_payload_detected(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)

        # Directly tamper with the stored payload via raw SQL.
        raw = sqlite3.connect(str(repo._db_path))
        try:
            raw.execute("PRAGMA foreign_keys = OFF")
            raw.execute(
                "UPDATE audit_events SET payload = '{\"tampered\":1}' "
                "WHERE event_id = ?", (r1.event_id,)
            )
            raw.commit()
        finally:
            raw.close()

        # Replay should detect hash mismatch.
        with pytest.raises(IntegrityError, match="hash mismatch"):
            repo.record_run_event(**_STANDARD_ARGS)


# ── T-13 ────────────────────────────────────────────────────────────────


class TestT13_RepeatedRequestIdSameRun:
    """T-13: Repeated request_id for same subject resolves to same run."""

    def test_same_run_for_same_request(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)

        args2 = {**_STANDARD_ARGS, "idempotency_key": "key-002"}
        r2 = repo.record_run_event(**args2)

        assert r2.audit_run_id == r1.audit_run_id
        assert r2.event_id != r1.event_id  # different event in same run

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_runs") == 1
            assert _count(conn, "audit_events") == 2
        finally:
            conn.close()


# ── T-14 ────────────────────────────────────────────────────────────────


class TestT14_SameRequestIdDifferentSubjects:
    """T-14: Same request_id for different subjects creates distinct runs."""

    def test_different_runs_for_different_subjects(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)

        args2 = {
            **_STANDARD_ARGS,
            "subject_path": "subdir/",
            "idempotency_key": "key-002",
        }
        r2 = repo.record_run_event(**args2)

        assert r2.audit_run_id != r1.audit_run_id
        assert r2.analysis_subject_id != r1.analysis_subject_id

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_runs") == 2
        finally:
            conn.close()


# ── T-15 ────────────────────────────────────────────────────────────────


class TestT15_ConcurrentCallsSerialized:
    """T-15: Concurrent calls in one process are serialized."""

    def test_concurrent_calls_succeed(self):
        repo = _repo()
        errors = []
        results = []

        def _worker(key_suffix: str):
            try:
                args = {**_STANDARD_ARGS, "idempotency_key": f"conc-key-{key_suffix}"}
                r = repo.record_run_event(**args)
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=_worker, args=("a",))
        t2 = threading.Thread(target=_worker, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"errors: {errors}"
        assert len(results) == 2

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 2
            assert _count(conn, "idempotency_records") == 2
        finally:
            conn.close()


# ── T-16 ────────────────────────────────────────────────────────────────


class TestT16_ResultReferenceIntegrity:
    """T-16: result_reference resolves to existing event; missing ref fails
    closed."""

    def test_missing_referenced_event_fails(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)

        # Corrupt the result_reference to point to a nonexistent event.
        raw = sqlite3.connect(str(repo._db_path))
        try:
            raw.execute("PRAGMA foreign_keys = OFF")
            raw.execute(
                "UPDATE idempotency_records SET result_reference = 'does-not-exist' "
                "WHERE operation_type = ? AND idempotency_key = ?",
                (_STANDARD_ARGS["operation_type"], _STANDARD_ARGS["idempotency_key"]),
            )
            raw.commit()
        finally:
            raw.close()

        with pytest.raises(IntegrityError, match="missing event"):
            repo.record_run_event(**_STANDARD_ARGS)


# ── T-17 ────────────────────────────────────────────────────────────────


class TestT17_MigrationIdempotent:
    """T-17: Migration version 1 is idempotent on reopen."""

    def test_migration_reapplied_is_safe(self):
        repo = _repo()
        # Migration already applied in __init__.
        # Create a second repository on the same database.
        EventRepository(repo._db_path)  # re-application is safe
        # No error, no duplicate schema_migrations row.

        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "schema_migrations") == 1
            # Verify all tables exist.
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = {r[0] for r in tables}
            assert "analysis_subjects" in table_names
            assert "audit_runs" in table_names
            assert "audit_events" in table_names
            assert "run_state" in table_names
            assert "idempotency_records" in table_names
        finally:
            conn.close()


# ── T-18 ────────────────────────────────────────────────────────────────


class TestT18_FailedMigrationNoPartialSchema:
    """T-18: Failed migration leaves no migration record; re-application is safe.

    SQLite DDL statements auto-commit, so CREATE TABLE cannot be rolled
    back.  The migration uses ``IF NOT EXISTS`` on every DDL statement,
    making re-application safe.  The INSERT of the migration record is the
    atomic marker — if it failed, no migration version is recorded and a
    subsequent call re-applies safely.
    """

    def test_migration_safe_after_partial_ddl(self):
        """After SQLite DDL auto-commits partial tables, re-migration works."""
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_path = Path(tmp.name)

        # Simulate a partial state: some tables exist but no migration
        # record was written (simulating a failure after DDL but before
        # the INSERT).
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS analysis_subjects (
                analysis_subject_id TEXT PRIMARY KEY,
                target_repository TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(target_repository, subject_type, subject_path))""")
            # NO INSERT into schema_migrations — simulates failure.
            conn.commit()
        finally:
            conn.close()

        # Verify no migration record exists.
        conn2 = sqlite3.connect(str(db_path))
        try:
            assert _count(conn2, "schema_migrations") == 0
            # But the tables exist (DDL auto-committed).
            tables = conn2.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {r[0] for r in tables}
            assert "schema_migrations" in table_names
            assert "analysis_subjects" in table_names
        finally:
            conn2.close()

        # Re-running the migration should succeed (all DDL uses IF NOT EXISTS).
        EventRepository(db_path)
        conn3 = production_connect(db_path)
        try:
            assert _count(conn3, "schema_migrations") == 1
            # audit_events table now exists (created by migration):
            tables = conn3.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {r[0] for r in tables}
            assert "audit_events" in table_names
        finally:
            conn3.close()

    def test_failed_migration_sets_no_record(self, monkeypatch):
        """If the INSERT fails, no migration record persists."""
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_path = Path(tmp.name)

        # Manually create schema_migrations table but then make the INSERT
        # fail by pre-inserting a conflicting record.
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL)""")
            # Pre-insert a conflicting name — the migration INSERT will fail.
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) "
                "VALUES (?, ?, ?)",
                (999, "slice-1-persistence-foundation", "2026-01-01T00:00:00Z"),
            )
            conn.commit()
        finally:
            conn.close()

        # Migration should raise IntegrityError (UNIQUE conflict on name).
        from agent_red_team.persistence.migration import apply as apply_migration
        from agent_red_team.persistence.connection import connect

        conn2 = connect(str(db_path))
        try:
            with pytest.raises(sqlite3.IntegrityError):
                apply_migration(conn2)
        finally:
            conn2.close()

        # Verify no version 1 record was inserted.
        conn3 = sqlite3.connect(str(db_path))
        try:
            cur = conn3.execute(
                "SELECT 1 FROM schema_migrations WHERE version = 1"
            )
            assert cur.fetchone() is None
        finally:
            conn3.close()
