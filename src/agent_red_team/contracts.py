"""Audit module contract (Protocol / Interface).

Each module must satisfy this narrow contract.  No module may:
- expand its scope autonomously,
- mutate the target repository by default,
- write secrets into logs or reports.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import AuditRequest, Finding


@runtime_checkable
class AuditModule(Protocol):
    """Contract that every audit module must implement."""

    # Module metadata
    module_name: str
    module_version: str
    supported_audit_types: list[str]

    # Required permissions (read-only by default)
    requires_write_access: bool

    def execute(self, request: AuditRequest, snapshot_path: str) -> list[Finding]:
        """Execute the audit module.

        Args:
            request: Validated, authorised audit request.
            snapshot_path: Path to a local repository snapshot.

        Returns:
            Zero or more normalised findings.  An empty list means
            no issues were found.
        """
        ...
