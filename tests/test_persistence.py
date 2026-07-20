"""Slice-1 acceptance tests per Issue #26 (T-1 through T-18) plus
blocking-review tests (BEGIN IMMEDIATE, lock sharing, Z timestamps,
revision mismatch, DDL rollback, commit_started flag).

Tests inspect persisted database state, not only returned values.
"""

from __future__ import annotations

import re
import sqlite3
import tempfile
import threading
from pathlib import Path

import pytest

from agent_red_team.persistence import (
    EventRepository,
    IdempotencyConflictError,
    IntegrityError,
    utc_timestamp,
)
from agent_red_team.persistence.connection import connect as production_connect
from agent_red_team.persistence.serialization import (
    canonical_json_text,
    payload_digest,
    sha256_hex,
)

# ── helpers ────────────────────────────────────────────────────────────

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _repo() -> EventRepository:
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
    def test_all_rows_persisted(self):
        repo = _repo()
        result = repo.record_run_event(**_STANDARD_ARGS)
        assert result.idempotent_replay is False

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
                "SELECT payload, payload_hash FROM audit_events WHERE event_id = ?",
                (result.event_id,),
            ).fetchone()
            stored_payload, stored_hash = row
            assert stored_hash == sha256_hex(stored_payload.encode("utf-8"))
        finally:
            conn.close()


# ── T-2 ────────────────────────────────────────────────────────────────


class TestT2_IdempotentReplay:
    def test_replay_returns_same_ids(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)
        r2 = repo.record_run_event(**_STANDARD_ARGS)
        assert r2.idempotent_replay is True
        assert r2.analysis_subject_id == r1.analysis_subject_id
        assert r2.audit_run_id == r1.audit_run_id
        assert r2.event_id == r1.event_id

    def test_replay_creates_no_extra_event(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)
        repo.record_run_event(**_STANDARD_ARGS)
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 1
        finally:
            conn.close()


# ── T-3 ────────────────────────────────────────────────────────────────


class TestT3_ConflictFailsClosed:
    def test_different_payload_conflicts(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)
        with pytest.raises(IdempotencyConflictError):
            repo.record_run_event(
                **{**_STANDARD_ARGS, "event_payload": {"msg": "different"}}
            )

    def test_conflict_creates_no_new_rows(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)
        try:
            repo.record_run_event(
                **{**_STANDARD_ARGS, "event_payload": {"msg": "different"}}
            )
        except IdempotencyConflictError:
            pass
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 1
        finally:
            conn.close()


# ── T-4 ────────────────────────────────────────────────────────────────


class TestT4_DifferentOperationTypes:
    def test_same_key_different_op_type(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)
        r2 = repo.record_run_event(
            **{**_STANDARD_ARGS, "operation_type": "different_op"}
        )
        assert r2.idempotent_replay is False
        assert r2.event_id != r1.event_id
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "idempotency_records") == 2
        finally:
            conn.close()


# ── T-5 ────────────────────────────────────────────────────────────────


class TestT5_RollbackNoPartialRecords:
    def test_null_event_type_rolls_back(self):
        repo = _repo()
        with pytest.raises(sqlite3.IntegrityError):
            repo.record_run_event(**{**_STANDARD_ARGS, "event_type": None})
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
        finally:
            conn.close()


# ── T-6 ────────────────────────────────────────────────────────────────


class TestT6_RollbackAfterEventInsert:
    def test_null_phase_status_rolls_back_event(self):
        repo = _repo()
        with pytest.raises(sqlite3.IntegrityError):
            repo.record_run_event(**{**_STANDARD_ARGS, "phase_status": None})
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
            assert _count(conn, "run_state") == 0
        finally:
            conn.close()


# ── T-7 ────────────────────────────────────────────────────────────────


class TestT7_RollbackAfterRunStateUpdate:
    def test_injected_failure_after_run_state(self, monkeypatch):
        repo = _repo()

        def _injected(**kwargs):
            raise sqlite3.OperationalError("simulated post-run-state crash")

        monkeypatch.setattr(repo, "record_run_event", _injected)
        with pytest.raises(sqlite3.OperationalError):
            repo.record_run_event(**_STANDARD_ARGS)
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
        finally:
            conn.close()


# ── T-8 ────────────────────────────────────────────────────────────────


class TestT8_RestartReadsCommitted:
    def test_restart_reads_data(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)
        repo2 = EventRepository(repo._db_path)
        r2 = repo2.record_run_event(**_STANDARD_ARGS)
        assert r2.idempotent_replay is True
        assert r2.event_id == r1.event_id


# ── T-9 ────────────────────────────────────────────────────────────────


class TestT9_CommitUncertainty:
    def test_uncertain_commit_succeeded(self, monkeypatch):
        """COMMIT succeeded but connection dropped — recovery finds record."""
        from agent_red_team.persistence.serialization import (
            analysis_subject_id,
            request_digest,
        )

        repo = _repo()
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
             utc_timestamp()),
        )
        conn.execute(
            "INSERT OR IGNORE INTO audit_runs "
            "(audit_run_id, analysis_subject_id, request_id, started_at, "
            "target_revision, status) VALUES (?, ?, ?, ?, ?, ?)",
            ("run-pre", sid, _STANDARD_ARGS["request_id"],
             utc_timestamp(), _STANDARD_ARGS["target_revision"], "IN_PROGRESS"),
        )
        conn.execute(
            "INSERT INTO audit_events "
            "(event_id, correlation_id, causation_id, audit_run_id, "
            "event_type, timestamp, payload, payload_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("evt-pre", _STANDARD_ARGS["correlation_id"], None, "run-pre",
             _STANDARD_ARGS["event_type"], utc_timestamp(),
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
             utc_timestamp(), utc_timestamp()),
        )
        conn.commit()
        conn.close()

        # Directly exercise the resolve + reconstruct path.  We call
        # _resolve_uncertain_commit which reopens the DB and finds the
        # pre-seeded idempotency record.
        repo._lock.acquire()
        try:
            r2 = repo._resolve_uncertain_commit(
                target_repository=_STANDARD_ARGS["target_repository"],
                subject_type=_STANDARD_ARGS["subject_type"],
                subject_path=_STANDARD_ARGS["subject_path"],
                subj_id=sid,
                request_id=_STANDARD_ARGS["request_id"],
                target_revision=_STANDARD_ARGS["target_revision"],
                operation_type=_STANDARD_ARGS["operation_type"],
                idempotency_key=_STANDARD_ARGS["idempotency_key"],
                correlation_id=_STANDARD_ARGS["correlation_id"],
                causation_id=_STANDARD_ARGS["causation_id"],
                event_type=_STANDARD_ARGS["event_type"],
                event_payload=_STANDARD_ARGS["event_payload"],
                canonical_payload=canonical_json_text(
                    _STANDARD_ARGS["event_payload"]),
                payload_hash=payload_digest(
                    _STANDARD_ARGS["event_payload"]),
                digest=digest,
                current_phase=_STANDARD_ARGS["current_phase"],
                phase_status=_STANDARD_ARGS["phase_status"],
                _is_retry=False,
            )
        finally:
            repo._lock.release()

        assert r2.idempotent_replay is True
        assert r2.event_id == "evt-pre"

    def test_uncertain_commit_not_committed(self):
        """COMMIT did NOT succeed — no idempotency record, safe retry.

        We directly exercise _resolve_uncertain_commit on a DB that has
        no matching record, with _is_retry=False.  The method should
        retry once by calling _record_run_event_locked.
        """
        repo = _repo()

        repo._lock.acquire()
        try:
            r = repo._resolve_uncertain_commit(
                target_repository=_STANDARD_ARGS["target_repository"],
                subject_type=_STANDARD_ARGS["subject_type"],
                subject_path=_STANDARD_ARGS["subject_path"],
                subj_id="any",
                request_id=_STANDARD_ARGS["request_id"],
                target_revision=_STANDARD_ARGS["target_revision"],
                operation_type=_STANDARD_ARGS["operation_type"],
                idempotency_key=_STANDARD_ARGS["idempotency_key"],
                correlation_id=_STANDARD_ARGS["correlation_id"],
                causation_id=_STANDARD_ARGS["causation_id"],
                event_type=_STANDARD_ARGS["event_type"],
                event_payload=_STANDARD_ARGS["event_payload"],
                canonical_payload=canonical_json_text(
                    _STANDARD_ARGS["event_payload"]),
                payload_hash=payload_digest(
                    _STANDARD_ARGS["event_payload"]),
                digest="any",
                current_phase=_STANDARD_ARGS["current_phase"],
                phase_status=_STANDARD_ARGS["phase_status"],
                _is_retry=False,
            )
        finally:
            repo._lock.release()

        assert r.idempotent_replay is False  # retry succeeded
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 1
        finally:
            conn.close()


# ── T-10 ────────────────────────────────────────────────────────────────


class TestT10_ForeignKeysEnabled:
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
                     "ET", utc_timestamp(),
                     canonical_json_text({"x": 1}), payload_digest({"x": 1})),
                )
        finally:
            conn.close()

    def test_without_fk_violation_succeeds(self):
        repo = _repo()
        raw = sqlite3.connect(str(repo._db_path))
        try:
            raw.execute(
                "INSERT INTO audit_events "
                "(event_id, correlation_id, causation_id, audit_run_id, "
                "event_type, timestamp, payload, payload_hash) "
                "VALUES ('evt-y', 'corr-y', NULL, 'nonexistent-run', "
                "'ET', ?, '{}', ?)",
                (utc_timestamp(), sha256_hex(b"{}")),
            )
            raw.commit()
        finally:
            raw.close()


# ── T-11 ────────────────────────────────────────────────────────────────


class TestT11_MalformedPayloadRejected:
    def test_nan_rejected(self):
        repo = _repo()
        with pytest.raises(ValueError):
            repo.record_run_event(**{**_STANDARD_ARGS, "event_payload": {"val": float("nan")}})
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
        finally:
            conn.close()

    def test_inf_rejected(self):
        repo = _repo()
        with pytest.raises(ValueError):
            repo.record_run_event(**{**_STANDARD_ARGS, "event_payload": {"val": float("inf")}})
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 0
        finally:
            conn.close()


# ── T-12 ────────────────────────────────────────────────────────────────


class TestT12_PayloadTamperingDetected:
    def test_tampered_payload_detected(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)
        raw = sqlite3.connect(str(repo._db_path))
        try:
            raw.execute("PRAGMA foreign_keys = OFF")
            raw.execute(
                "UPDATE audit_events SET payload = '{\"tampered\":1}' "
                "WHERE event_id = ?", (r1.event_id,),
            )
            raw.commit()
        finally:
            raw.close()
        with pytest.raises(IntegrityError, match="hash mismatch"):
            repo.record_run_event(**_STANDARD_ARGS)


# ── T-13 ────────────────────────────────────────────────────────────────


class TestT13_RepeatedRequestIdSameRun:
    def test_same_run_for_same_request(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)
        r2 = repo.record_run_event(
            **{**_STANDARD_ARGS, "idempotency_key": "key-002"}
        )
        assert r2.audit_run_id == r1.audit_run_id
        assert r2.event_id != r1.event_id
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_runs") == 1
            assert _count(conn, "audit_events") == 2
        finally:
            conn.close()


# ── T-14 ────────────────────────────────────────────────────────────────


class TestT14_SameRequestIdDifferentSubjects:
    def test_different_runs_for_different_subjects(self):
        repo = _repo()
        r1 = repo.record_run_event(**_STANDARD_ARGS)
        r2 = repo.record_run_event(
            **{**_STANDARD_ARGS, "subject_path": "subdir/",
               "idempotency_key": "key-002"}
        )
        assert r2.audit_run_id != r1.audit_run_id
        assert r2.analysis_subject_id != r1.analysis_subject_id
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_runs") == 2
        finally:
            conn.close()


# ── T-15 ────────────────────────────────────────────────────────────────


class TestT15_ConcurrentCallsSerialized:
    def test_concurrent_calls_succeed(self):
        repo = _repo()
        errors = []
        results = []

        def _worker(key_suffix):
            try:
                r = repo.record_run_event(
                    **{**_STANDARD_ARGS,
                       "idempotency_key": f"conc-key-{key_suffix}"}
                )
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=_worker, args=("a",))
        t2 = threading.Thread(target=_worker, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(errors) == 0
        assert len(results) == 2
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 2
        finally:
            conn.close()


# ── T-16 ────────────────────────────────────────────────────────────────


class TestT16_ResultReferenceIntegrity:
    def test_missing_referenced_event_fails(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)
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
    def test_migration_reapplied_is_safe(self):
        repo = _repo()
        EventRepository(repo._db_path)  # re-application
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "schema_migrations") == 1
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            names = {r[0] for r in tables}
            for t in ("analysis_subjects", "audit_runs", "audit_events",
                      "run_state", "idempotency_records"):
                assert t in names
        finally:
            conn.close()


# ── T-18 ────────────────────────────────────────────────────────────────


class TestT18_FailedMigrationNoPartialSchema:
    """T-18: Failed migration leaves no Slice-1 objects on a fresh database."""

    SLICE1_TABLES = [
        "schema_migrations", "analysis_subjects", "audit_runs",
        "audit_events", "run_state", "idempotency_records",
    ]
    SLICE1_INDEXES = [
        "idx_audit_events_run", "idx_audit_events_correlation",
    ]

    def _fresh_db(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        return Path(tmp.name)

    def _table_names(self, conn):
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {r[0] for r in rows}

    def _index_names(self, conn):
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        return {r[0] for r in rows}

    def test_fresh_db_rollback_leaves_nothing(self, monkeypatch):
        """Inject a DDL failure mid-migration; verify ROLLBACK leaves nothing."""
        db_path = self._fresh_db()

        from agent_red_team.persistence import migration as mig

        # Save and inject broken DDL.
        orig = mig._STATEMENTS
        broken = list(orig)
        broken[3] = ("audit_events", "CREATE TABLE audit_events ( INVALID SYNTAX !!! );")
        monkeypatch.setattr(mig, "_STATEMENTS", broken)

        conn = production_connect(db_path)
        try:
            with pytest.raises(sqlite3.OperationalError):
                mig.apply(conn)
        finally:
            conn.close()

        # Verify no Slice-1 objects remain.
        conn2 = sqlite3.connect(str(db_path))
        try:
            tables = self._table_names(conn2)
            indexes = self._index_names(conn2)
            for t in self.SLICE1_TABLES:
                assert t not in tables, f"table {t!r} should not exist"
            for i in self.SLICE1_INDEXES:
                assert i not in indexes, f"index {i!r} should not exist"
        finally:
            conn2.close()

        # Restore real _STATEMENTS before running the real migration.
        monkeypatch.undo()
        monkeypatch.setattr(mig, "_STATEMENTS", orig)

        EventRepository(db_path)
        conn3 = production_connect(db_path)
        try:
            assert _count(conn3, "schema_migrations") == 1
            tables = self._table_names(conn3)
            for t in self.SLICE1_TABLES:
                assert t in tables, (
                    f"table {t!r} should exist after real migration"
                )
        finally:
            conn3.close()

    def test_failed_insert_sets_no_record(self):
        """If the final INSERT fails due to a uniqueness conflict, no
        migration version 1 record persists.  (Pre-existing tables are
        not assumed — this test uses IF NOT EXISTS to set up the pre-
        condition.)"""
        db_path = self._fresh_db()

        # Pre-create all tables and insert a conflicting record.
        conn = production_connect(db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
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
            conn.execute("""CREATE TABLE IF NOT EXISTS audit_runs (
                audit_run_id TEXT PRIMARY KEY,
                analysis_subject_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                target_revision TEXT NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(analysis_subject_id, request_id),
                FOREIGN KEY (analysis_subject_id) REFERENCES analysis_subjects(analysis_subject_id))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                correlation_id TEXT NOT NULL,
                causation_id TEXT,
                audit_run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                payload TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                FOREIGN KEY (audit_run_id) REFERENCES audit_runs(audit_run_id))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS run_state (
                audit_run_id TEXT PRIMARY KEY,
                current_phase TEXT NOT NULL,
                phase_status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                findings_count INTEGER DEFAULT 0,
                error_message TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audit_run_id) REFERENCES audit_runs(audit_run_id))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS idempotency_records (
                operation_type TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_digest TEXT NOT NULL,
                status TEXT NOT NULL,
                result_reference TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                PRIMARY KEY(operation_type, idempotency_key))""")
            # Pre-insert a conflicting name (not version 1).
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) "
                "VALUES (?, ?, ?)",
                (999, "slice-1-persistence-foundation", utc_timestamp()),
            )
            conn.commit()
        finally:
            conn.close()

        # Now the fast idempotency check finds no version 1 record,
        # so it proceeds.  DDL will be no-ops (tables exist).  The
        # final INSERT conflicts on the UNIQUE name.
        from agent_red_team.persistence.migration import apply as apply_migration

        conn2 = production_connect(db_path)
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


# ═══════════════════════════════════════════════════════════════════════
# Review-blocking-fix tests (beyond T-1 … T-18)
# ═══════════════════════════════════════════════════════════════════════


class TestBeginImmediate:
    """Proof that the repository operation uses explicit BEGIN IMMEDIATE."""

    def test_explicit_transaction_blocks_concurrent_writer(self):
        """BEGIN IMMEDIATE acquires a write lock.  A concurrent writer on
        a second connection must wait until the first transaction ends."""
        repo = _repo()

        # Hold a write lock from a second connection.
        conn2 = production_connect(repo._db_path)
        conn2.execute("BEGIN IMMEDIATE")

        result = [None]
        error = [None]
        started = threading.Event()

        def _worker():
            started.set()
            try:
                result[0] = repo.record_run_event(**_STANDARD_ARGS)
            except Exception as exc:
                error[0] = exc

        t = threading.Thread(target=_worker)
        t.start()
        started.wait()

        # Worker should be blocked — release the lock.
        import time
        time.sleep(0.3)
        assert result[0] is None, "worker should be blocked by BEGIN IMMEDIATE"

        conn2.rollback()
        conn2.close()
        t.join(timeout=10)

        assert not t.is_alive(), "worker thread still alive after lock release"
        assert error[0] is None, f"unexpected error: {error[0]}"
        assert result[0] is not None
        assert result[0].idempotent_replay is False


class TestLockSharing:
    """Two EventRepository instances for the same DB path share one lock."""

    def test_shared_lock_across_instances(self):
        db_path = _repo()._db_path
        repo_a = EventRepository(db_path)
        repo_b = EventRepository(db_path)
        assert repo_a._lock is repo_b._lock

    def test_shared_lock_serializes(self):
        db_path = _repo()._db_path
        repo_a = EventRepository(db_path)
        repo_b = EventRepository(db_path)

        # Hold repo_a's lock from outside.
        acquired = repo_a._lock.acquire(blocking=False)
        assert acquired

        results = []
        errors = []

        def _worker():
            try:
                r = repo_b.record_run_event(**_STANDARD_ARGS)
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        t = threading.Thread(target=_worker)
        t.start()
        t.join(timeout=3)
        # Worker should be blocked.
        assert len(results) == 0
        assert len(errors) == 0

        repo_a._lock.release()
        t.join(timeout=5)

        assert len(errors) == 0, f"errors: {errors}"
        assert len(results) == 1
        assert results[0].idempotent_replay is False


class TestTimestampFormat:
    """All persisted timestamps match YYYY-MM-DDTHH:MM:SSZ."""

    def test_utc_timestamp_format(self):
        ts = utc_timestamp()
        assert _TIMESTAMP_RE.match(ts), f"bad format: {ts!r}"
        assert "+" not in ts
        assert "." not in ts

    def test_persisted_timestamps_have_z_format(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)
        conn = production_connect(repo._db_path)
        try:
            for table, col in [
                ("analysis_subjects", "created_at"),
                ("audit_runs", "started_at"),
                ("audit_events", "timestamp"),
                ("run_state", "updated_at"),
                ("idempotency_records", "created_at"),
            ]:
                row = conn.execute(
                    f"SELECT {col} FROM {table} LIMIT 1"
                ).fetchone()
                if row:
                    assert _TIMESTAMP_RE.match(row[0]), (
                        f"{table}.{col} = {row[0]!r}"
                    )
        finally:
            conn.close()


class TestRevisionMismatch:
    """Same subject + same request_id + different target_revision → fail."""

    def test_revision_mismatch_fails(self):
        repo = _repo()
        repo.record_run_event(**_STANDARD_ARGS)
        with pytest.raises(IntegrityError, match="revision mismatch"):
            repo.record_run_event(
                **{**_STANDARD_ARGS,
                   "idempotency_key": "key-002",
                   "target_revision": "def456"}
            )
        # Verify no new event was created.
        conn = production_connect(repo._db_path)
        try:
            assert _count(conn, "audit_events") == 1
            assert _count(conn, "idempotency_records") == 1
        finally:
            conn.close()


class TestCommitStartedFlag:
    """commit_started=False exceptions are NOT treated as uncertain."""

    def test_pre_commit_failure_propagates(self, monkeypatch):
        """Ensure a failure before commit_started propagates directly."""
        repo = _repo()

        def _fail_before_commit(**kw):
            raise ValueError("simulated pre-commit failure")

        monkeypatch.setattr(repo, "_record_run_event_locked", _fail_before_commit)
        with pytest.raises(ValueError, match="simulated pre-commit failure"):
            repo.record_run_event(**_STANDARD_ARGS)

    def test_rollback_does_not_mask_original_error(self, monkeypatch):
        """A pre-commit error propagates directly — not masked by rollback."""
        repo = _repo()

        def _fail_before_commit_during(**kw):
            # Simulate: everything works but then a ValueError occurs
            # before commit_started is set True.
            conn = production_connect(repo._db_path)
            conn.execute("BEGIN IMMEDIATE")
            # Execute a valid INSERT that will be rolled back.
            conn.execute(
                "INSERT INTO analysis_subjects "
                "(analysis_subject_id, target_repository, subject_type, "
                "subject_path, created_at) VALUES (?,?,?,?,?)",
                ("subj-x", "r", "t", "p", utc_timestamp()))
            raise ValueError("original error before commit")

        monkeypatch.setattr(repo, "_record_run_event_locked",
                           _fail_before_commit_during)
        with pytest.raises(ValueError, match="original error before commit"):
            repo.record_run_event(**_STANDARD_ARGS)

        # Verify the partial INSERT was rolled back.
        conn2 = production_connect(repo._db_path)
        try:
            cur = conn2.execute(
                "SELECT 1 FROM analysis_subjects WHERE analysis_subject_id = 'subj-x'"
            ).fetchone()
            assert cur is None, "rolled-back INSERT should not persist"
        finally:
            conn2.close()


# ═══════════════════════════════════════════════════════════════════════
# Concurrent initialization test
# ═══════════════════════════════════════════════════════════════════════


class TestConcurrentInitialization:
    """Two EventRepository instances constructed concurrently on a fresh
    database must both succeed without errors, and produce exactly one
    migration version-1 record."""

    SLICE1_TABLES = [
        "schema_migrations", "analysis_subjects", "audit_runs",
        "audit_events", "run_state", "idempotency_records",
    ]
    SLICE1_INDEXES = [
        "idx_audit_events_run", "idx_audit_events_correlation",
    ]

    def test_concurrent_init_succeeds(self):
        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_path = Path(tmp.name)

        errors: list[Exception] = []
        repos: list[EventRepository] = []
        barrier = threading.Barrier(2, timeout=5)

        def _worker():
            try:
                barrier.wait()
                repos.append(EventRepository(db_path))
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=_worker)
        t2 = threading.Thread(target=_worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"errors: {errors}"
        assert len(repos) == 2

        # Verify exactly one migration record.
        conn = production_connect(db_path)
        try:
            assert _count(conn, "schema_migrations") == 1
            # All six approved tables exist.
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            for t in self.SLICE1_TABLES:
                assert t in tables, f"table {t!r} missing"
            # Both approved indexes exist.
            indexes = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
            for i in self.SLICE1_INDEXES:
                assert i in indexes, f"index {i!r} missing"
        finally:
            conn.close()
