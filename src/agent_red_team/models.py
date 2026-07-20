"""Type definitions for audit requests, findings, and reports.

These mirror the JSON Schemas in schemas/ and are the canonical
in-code representation.  No audit logic is implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class Confidence(Enum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    POSSIBLE = "possible"


class DisclosureClassification(Enum):
    PUBLIC = "public"
    PRIVATE_SECURITY_ADVISORY = "private-security-advisory"
    CONFIDENTIAL = "confidential"


class AuditType(Enum):
    CODE_REVIEW = "code-review"
    GOVERNANCE_GAP_ANALYSIS = "governance-gap-analysis"
    WORKFLOW_AUDIT = "workflow-audit"
    ARCHITECTURE_RISK_ASSESSMENT = "architecture-risk-assessment"
    DEPENDENCY_SUPPLY_CHAIN = "dependency-and-supply-chain"
    SECRETS_EXPOSURE = "secrets-exposure"
    FEDERATION_CONTRACTS = "federation-contracts"


class AuditMethod(Enum):
    STATIC_ANALYSIS = "static-analysis"
    WORKFLOW_INSPECTION = "workflow-inspection"
    GOVERNANCE_REVIEW = "governance-review"
    SAFE_REPRODUCTION = "safe-reproduction"
    DEPENDENCY_ANALYSIS = "dependency-analysis"
    FEDERATION_CONTRACT_VALIDATION = "federation-contract-validation"


@dataclass
class AuditRequest:
    """Validated audit request matching audit-request.v1.schema.json."""

    schema_version: str
    request_id: str
    target_repository: str
    requester: str
    scope: list[str]
    audit_types: list[AuditType]
    permitted_methods: list[AuditMethod]
    disclosure_channel: str
    point_of_contact: str
    authorization_statement: str
    created_at: str
    target_ref: str | None = None
    exclusions: list[str] = field(default_factory=list)
    excluded_methods: list[str] = field(default_factory=list)


@dataclass
class Finding:
    """A single audit finding matching the report schema."""

    finding_id: str
    severity: Severity
    affected_location: str
    evidence: str
    impact: str
    reproduction_steps: str
    recommended_remediation: str
    confidence: Confidence
    open_uncertainties: str | None = None


@dataclass
class AuditReport:
    """Audit report matching audit-report.v1.schema.json."""

    schema_version: str
    report_id: str
    request_id: str
    target_repository: str
    generated_at: str
    summary: str
    findings: list[Finding]
    target_ref: str | None = None
    audit_module: str | None = None
    disclosure_classification: DisclosureClassification | None = None
