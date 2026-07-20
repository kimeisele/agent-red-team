"""Canonical JSON serialization and SHA-256 digest utilities.

Deterministic output is required for content-addressed storage and
idempotency-key derivation.  Every helper is a pure function.
"""

from __future__ import annotations

import hashlib
import json


def canonical_json_bytes(value: object) -> bytes:
    """Serialize *value* as canonical UTF-8 JSON bytes.

    The output is deterministic: sorted keys, no ASCII escaping, no NaN /
    Infinity, compact separators.  Callers MUST encode the returned bytes
    as UTF-8 for digest computation (already done here).

    Raises:
        ValueError: *value* contains ``NaN``, ``Infinity``, or
            ``-Infinity``.
        TypeError: *value* is not JSON-serializable.
    """
    text = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def canonical_json_text(value: object) -> str:
    """Return the canonical JSON text (decoded UTF-8)."""
    return canonical_json_bytes(value).decode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Return the full 64-character lowercase SHA-256 hex digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def payload_digest(payload: dict) -> str:
    """Return ``SHA-256(canonical_json_bytes(payload))``."""
    return sha256_hex(canonical_json_bytes(payload))


def request_digest(
    *,
    target_repository: str,
    subject_type: str,
    subject_path: str,
    request_id: str,
    target_revision: str,
    operation_type: str,
    correlation_id: str,
    causation_id: str | None,
    event_type: str,
    event_payload: dict,
    current_phase: str,
    phase_status: str,
) -> str:
    """Compute the canonical operation-request digest.

    Includes all semantic inputs.  Excludes generated IDs, timestamps,
    database IDs, result fields, and the idempotency key itself.
    """
    canonical = {
        "target_repository": target_repository,
        "subject_type": subject_type,
        "subject_path": subject_path,
        "request_id": request_id,
        "target_revision": target_revision,
        "operation_type": operation_type,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "event_type": event_type,
        "event_payload": event_payload,
        "current_phase": current_phase,
        "phase_status": phase_status,
    }
    return sha256_hex(canonical_json_bytes(canonical))


def analysis_subject_id(
    target_repository: str, subject_type: str, subject_path: str
) -> str:
    """Compute the deterministic analysis-subject identity.

    ``SHA-256(target_repository ␀ subject_type ␀ subject_path)``
    """
    raw = f"{target_repository}\0{subject_type}\0{subject_path}"
    return sha256_hex(raw.encode("utf-8"))
