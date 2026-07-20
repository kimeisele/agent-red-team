"""Schema migration — version 1 only.

Creates the six approved Slice-1 tables and indexes inside a single
transaction.  Application is idempotent: re-running on an already-migrated
database is safe and does not re-create existing objects.
"""

from __future__ import annotations

import logging
import sqlite3

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

# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

_CREATE_INDEX_EVENTS_RUN = """
CREATE INDEX IF NOT EXISTS idx_audit_events_run
ON audit_events(audit_run_id);
"""

_CREATE_INDEX_EVENTS_CORRELATION = """
CREATE INDEX IF NOT EXISTS idx_audit_events_correlation
ON audit_events(correlation_id);
"""

# Ordered sequence — dependencies require this order.
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


def apply(conn: sqlite3.Connection) -> None:
    """Apply migration version 1 inside a single transaction.

    Idempotent — safe to call on an already-migrated database.
    The migration row is inserted only after all DDL succeeds.

    SQLite DDL statements auto-commit any pending transaction.  This means
    individual CREATE TABLE statements cannot be rolled back.  The module
    mitigates this by using ``IF NOT EXISTS`` on every DDL statement,
    making re-application safe even after partial failures.
    """
    # Create schema_migrations first so we can check for existing version.
    conn.execute(_CREATE_SCHEMA_MIGRATIONS)

    cur = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?",
        (_MIGRATION_VERSION,),
    )
    if cur.fetchone() is not None:
        logger.debug("Migration v%d already applied — skipping", _MIGRATION_VERSION)
        return

    # Execute all remaining DDL (each uses IF NOT EXISTS).
    for _name, ddl in _STATEMENTS:
        conn.execute(ddl)

    # The INSERT is the only DML — commit explicitly.
    conn.execute(
        "INSERT INTO schema_migrations (version, name, applied_at) "
        "VALUES (?, ?, ?)",
        (
            _MIGRATION_VERSION,
            "slice-1-persistence-foundation",
            _utcnow(),
        ),
    )
    conn.commit()

    logger.info("Migration v%d applied successfully", _MIGRATION_VERSION)


def _utcnow() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
