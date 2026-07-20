"""SQLite connection factory with mandatory PRAGMA configuration.

Every production connection enforces foreign keys, WAL journal mode, and a
finite busy timeout.  Tests may create deliberately misconfigured raw
connections only to prove why these pragmas are required.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Pragma defaults (non-configurable by callers in production)
# ---------------------------------------------------------------------------

_BUSY_TIMEOUT_MS = 5000


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (or create) *db_path* with mandatory pragmas.

    Returns a connection configured with::

        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA busy_timeout = 5000;

    After configuration the factory verifies that ``PRAGMA foreign_keys``
    returns ``1``.  A return value of ``0`` indicates a misconfigured build
    and raises :exc:`RuntimeError`.

    Callers are responsible for closing the connection.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")

    # Verify foreign keys are actually active (defense-in-depth).
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    if row is None or row[0] != 1:
        conn.close()
        raise RuntimeError(
            "SQLite connection refused to enable foreign keys — "
            "build may be compiled with SQLITE_OMIT_FOREIGN_KEY"
        )

    return conn
