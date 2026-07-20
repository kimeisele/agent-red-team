"""Schema migration — version 1 only.

Creates the six approved Slice-1 tables and indexes inside a single
explicit ``BEGIN IMMEDIATE … COMMIT`` transaction.  Application is
idempotent: re-running on an already-migrated database is safe.

The authoritative version check is performed inside the write transaction
to avoid TOCTOU races between concurrent initializers.
"""

from __future__ import annotations

import logging
import sqlite3

from agent_red_team.persistence.connection import utc_timestamp

logger = logging.getLogger(__name__)

_MIGRATION_VERSION = 1

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_CREATE_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version   INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    applied_at TEXT   NOT NULL
);
"""

_CREATE_ANALYSIS_SUBJECTS = """
CREATE TABLE IF NOT EXISTS analysis_subjects (
    analysis_subject_id TEXT PRIMARY KEY,
    target_repository   TEXT NOT NULL,
    subject_type        TEXT NOT NULL,
    subject_path        TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    UNIQUE(target_repository, subject_type, subject_path)
);
"""

_CREATE_AUDIT_RUNS = """
CREATE TABLE IF NOT EXISTS audit_runs (
    audit_run_id        TEXT PRIMARY KEY,
    analysis_subject_id TEXT NOT NULL,
    request_id          TEXT NOT NULL,
    started_at          TEXT NOT NULL,
    completed_at        TEXT,
    target_revision     TEXT NOT NULL,
    status              TEXT NOT NULL,
    UNIQUE(analysis_subject_id, request_id),
    FOREIGN KEY (analysis_subject_id) REFERENCES analysis_subjects(analysis_subject_id)
);
"""

_CREATE_AUDIT_EVENTS = """
CREATE TABLE IF NOT EXISTS audit_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT    NOT NULL UNIQUE,
    correlation_id  TEXT    NOT NULL,
    causation_id    TEXT,
    audit_run_id    TEXT    NOT NULL,
    event_type      TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL,
    payload         TEXT    NOT NULL,
    payload_hash    TEXT    NOT NULL,
    FOREIGN KEY (audit_run_id) REFERENCES audit_runs(audit_run_id)
);
"""

_CREATE_RUN_STATE = """
CREATE TABLE IF NOT EXISTS run_state (
    audit_run_id    TEXT PRIMARY KEY,
    current_phase   TEXT    NOT NULL,
    phase_status    TEXT    NOT NULL,
    started_at      TEXT,
    completed_at    TEXT,
    findings_count  INTEGER DEFAULT 0,
    error_message   TEXT,
    updated_at      TEXT    NOT NULL,
    FOREIGN KEY (audit_run_id) REFERENCES audit_runs(audit_run_id)
);
"""

_CREATE_IDEMPOTENCY_RECORDS = """
CREATE TABLE IF NOT EXISTS idempotency_records (
    operation_type   TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL,
    request_digest   TEXT NOT NULL,
    status           TEXT NOT NULL,
    result_reference TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    completed_at     TEXT NOT NULL,
    PRIMARY KEY(operation_type, idempotency_key)
);
"""

_CREATE_INDEX_EVENTS_RUN = """
CREATE INDEX IF NOT EXISTS idx_audit_events_run
ON audit_events(audit_run_id);
"""

_CREATE_INDEX_EVENTS_CORRELATION = """
CREATE INDEX IF NOT EXISTS idx_audit_events_correlation
ON audit_events(correlation_id);
"""

# Ordered — dependencies require this sequence.
_STATEMENTS: list[tuple[str, str]] = [
    ("schema_migrations", _CREATE_SCHEMA_MIGRATIONS),
    ("analysis_subjects", _CREATE_ANALYSIS_SUBJECTS),
    ("audit_runs", _CREATE_AUDIT_RUNS),
    ("audit_events", _CREATE_AUDIT_EVENTS),
    ("run_state", _CREATE_RUN_STATE),
    ("idempotency_records", _CREATE_IDEMPOTENCY_RECORDS),
    ("idx_audit_events_run", _CREATE_INDEX_EVENTS_RUN),
    ("idx_audit_events_correlation", _CREATE_INDEX_EVENTS_CORRELATION),
]

_TABLE_NAMES = [
    "schema_migrations",
    "analysis_subjects",
    "audit_runs",
    "audit_events",
    "run_state",
    "idempotency_records",
]
_INDEX_NAMES = ["idx_audit_events_run", "idx_audit_events_correlation"]


def apply(conn: sqlite3.Connection) -> None:
    """Apply migration version 1 inside ``BEGIN IMMEDIATE … COMMIT``.

    The authoritative version check is performed inside the write
    transaction.  No preflight check outside the transaction — this
    prevents TOCTOU races when two ``EventRepository`` instances
    initialise concurrently against the same fresh database.

    Idempotent — safe to call on an already-migrated database.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        # 1. Ensure schema_migrations exists (idempotent).
        conn.execute(_CREATE_SCHEMA_MIGRATIONS)

        # 2. Authoritative version check inside the transaction.
        cur = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (_MIGRATION_VERSION,),
        )
        if cur.fetchone() is not None:
            logger.debug("Migration v%d already applied — skipping",
                         _MIGRATION_VERSION)
            conn.commit()
            return

        # 3. Create remaining tables + indexes.
        for _name, ddl in _STATEMENTS[1:]:
            conn.execute(ddl)

        # 4. Record migration version.
        conn.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) "
            "VALUES (?, ?, ?)",
            (
                _MIGRATION_VERSION,
                "slice-1-persistence-foundation",
                utc_timestamp(),
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    logger.info("Migration v%d applied successfully", _MIGRATION_VERSION)
