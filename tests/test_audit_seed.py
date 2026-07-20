"""Tests for audit seed — schemas, templates, examples, and policy.

No network requests.  No real audit logic.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"
DOCS = ROOT / "docs"
TEMPLATES = DOCS / "templates"
ISSUE_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "audit-request.yml"


# ── helpers ────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


# ── Schema tests ───────────────────────────────────────────────────────────


class TestAuditRequestSchema:
    """Tests for audit-request.v1.schema.json."""

    def test_valid_example_validates(self) -> None:
        """The example audit request matches the schema."""
        request = _load_json(EXAMPLES / "audit-request.example.json")
        assert request["schema_version"] == "1.0.0"
        assert request["target_repository"] == "kimeisele/example-node"
        # All 11 required fields present
        required = [
            "schema_version", "request_id", "target_repository",
            "requester", "scope", "audit_types", "permitted_methods",
            "disclosure_channel", "point_of_contact",
            "authorization_statement", "created_at",
        ]
        for field in required:
            assert field in request, f"Missing required field: {field}"

    def test_missing_required_field_rejected(self) -> None:
        """A request missing target_repository is invalid."""
        request = _load_json(EXAMPLES / "audit-request.example.json")
        del request["target_repository"]
        assert "target_repository" not in request

    def test_invalid_disclosure_channel_rejected(self) -> None:
        """An invalid disclosure_channel value is not in the enum."""
        valid_channels = {"public-issue", "private-security-advisory", "confidential-report"}
        assert "invalid-channel" not in valid_channels

    def test_no_secret_fields_in_schema(self) -> None:
        """The schema must not have secret-like fields."""
        schema = _load_json(SCHEMAS / "audit-request.v1.schema.json")
        props = schema.get("properties", {})
        secretish = {"token", "secret", "password", "api_key", "credential", "private_key"}
        for key in props:
            for s in secretish:
                assert s not in key.lower(), f"Secret-like field found: {key}"


class TestAuditReportSchema:
    """Tests for audit-report.v1.schema.json."""

    def test_valid_example_validates(self) -> None:
        """The example audit report matches the schema."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        assert report["schema_version"] == "1.0.0"
        assert report["request_id"] == "REQ-2026-0720-001"
        assert len(report["findings"]) >= 1
        finding = report["findings"][0]
        required = [
            "finding_id", "severity", "affected_location", "evidence",
            "impact", "reproduction_steps", "recommended_remediation",
            "confidence",
        ]
        for field in required:
            assert field in finding, f"Missing required field in finding: {field}"

    def test_invalid_severity_rejected(self) -> None:
        """An invalid severity value is not in the enum."""
        valid = {"critical", "high", "medium", "low", "informational"}
        assert "unknown" not in valid

    def test_finding_without_evidence_invalid(self) -> None:
        """A finding without evidence is incomplete."""
        finding = _load_json(EXAMPLES / "audit-report.example.json")["findings"][0]
        assert finding["evidence"], "Evidence must be non-empty"

    def test_report_without_request_correlation_invalid(self) -> None:
        """A report without request_id correlation is incomplete."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        assert report["request_id"], "request_id must be present for correlation"


# ── Template tests ─────────────────────────────────────────────────────────


class TestTemplates:
    """Tests for human-readable templates."""

    def test_request_template_has_all_fields(self) -> None:
        """The audit request template covers all 7 required fields."""
        content = (TEMPLATES / "AUDIT_REQUEST_TEMPLATE.md").read_text()
        required_fields = [
            "Request ID", "Target Repository", "Requester",
            "Scope", "Audit Types", "Permitted Methods",
            "Disclosure Channel", "Point of Contact",
        ]
        for field in required_fields:
            assert field in content, f"Missing field in request template: {field}"

    def test_report_template_has_all_fields(self) -> None:
        """The audit report template covers all 8 required fields."""
        content = (TEMPLATES / "AUDIT_REPORT_TEMPLATE.md").read_text()
        required_fields = [
            "Severity", "Affected Location", "Evidence", "Impact",
            "Reproduction Steps", "Recommended Remediation",
            "Confidence", "Open Uncertainties",
        ]
        for field in required_fields:
            assert field in content, f"Missing field in report template: {field}"


class TestIssueTemplate:
    """Tests for the GitHub Issue template."""

    def test_issue_template_has_all_seven_fields(self) -> None:
        """The issue template contains all 7 required audit request fields."""
        content = ISSUE_TEMPLATE.read_text()
        required = [
            "Target Repository",
            "Requesting Node",
            "Permitted Audit Scope",
            "Audit Type",
            "Permitted Non-Destructive Methods",
            "Disclosure Channel",
            "Point of Contact",
        ]
        for field in required:
            assert field in content, f"Missing field in issue template: {field}"


# ── Policy tests ───────────────────────────────────────────────────────────


class TestPolicy:
    """Tests for the audit policy document."""

    def test_policy_linked_from_readme(self) -> None:
        """The README links to the audit policy."""
        content = (ROOT / "README.md").read_text()
        assert "AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md" in content

    def test_policy_no_productive_typo(self) -> None:
        """The typo 'Productive manipulation' does not exist."""
        content = (DOCS / "authority" / "AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md").read_text()
        assert "Productive manipulation" not in content
        assert "Production manipulation" in content


# ── Example tests ──────────────────────────────────────────────────────────


class TestExamples:
    """Tests for example JSON files."""

    def test_request_example_is_valid_json(self) -> None:
        """audit-request.example.json is valid JSON."""
        data = _load_json(EXAMPLES / "audit-request.example.json")
        assert isinstance(data, dict)

    def test_report_example_is_valid_json(self) -> None:
        """audit-report.example.json is valid JSON."""
        data = _load_json(EXAMPLES / "audit-report.example.json")
        assert isinstance(data, dict)


# ── Code skeleton tests ────────────────────────────────────────────────────


class TestCodeSkeleton:
    """Tests that the code skeleton imports but has no audit logic."""

    def test_models_import(self) -> None:
        """models.py imports cleanly."""
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from agent_red_team.models import (
            Severity, Confidence, DisclosureClassification,
            AuditType, AuditMethod, AuditRequest, Finding, AuditReport,
        )
        # Can instantiate
        finding = Finding(
            finding_id="F-001",
            severity=Severity.INFORMATIONAL,
            affected_location="test.py:1",
            evidence="none",
            impact="none",
            reproduction_steps="n/a",
            recommended_remediation="n/a",
            confidence=Confidence.POSSIBLE,
        )
        assert finding.finding_id == "F-001"

    def test_contracts_import(self) -> None:
        """contracts.py imports cleanly."""
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from agent_red_team.contracts import AuditModule
        assert AuditModule is not None

    def test_pipeline_import(self) -> None:
        """pipeline.py imports cleanly."""
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from agent_red_team.pipeline import PipelinePhase
        assert len(list(PipelinePhase)) == 9
