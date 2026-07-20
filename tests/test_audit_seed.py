"""Tests for audit seed — schemas, templates, examples, and policy.

No network requests.  No real audit logic.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"
DOCS = ROOT / "docs"
TEMPLATES = DOCS / "templates"
ISSUE_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "audit-request.yml"


# ── helpers ────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


_REQUEST_SCHEMA = _load_json(SCHEMAS / "audit-request.v1.schema.json")
_REPORT_SCHEMA = _load_json(SCHEMAS / "audit-report.v1.schema.json")
_REQUEST_VALIDATOR = Draft202012Validator(_REQUEST_SCHEMA)
_REPORT_VALIDATOR = Draft202012Validator(_REPORT_SCHEMA)


def _errors(validator: Draft202012Validator, instance: dict) -> list[str]:
    return [e.message for e in validator.iter_errors(instance)]


# ── Schema validation tests ────────────────────────────────────────────────


class TestAuditRequestSchema:
    """Real JSON Schema validation for audit-request.v1.schema.json."""

    def test_valid_example_validates(self) -> None:
        """The example audit request validates against the schema."""
        request = _load_json(EXAMPLES / "audit-request.example.json")
        errs = _errors(_REQUEST_VALIDATOR, request)
        assert not errs, f"Unexpected validation errors: {errs}"

    def test_missing_target_repository_rejected(self) -> None:
        """Request without target_repository fails validation."""
        request = _load_json(EXAMPLES / "audit-request.example.json")
        del request["target_repository"]
        errs = _errors(_REQUEST_VALIDATOR, request)
        assert errs

    def test_invalid_disclosure_channel_rejected(self) -> None:
        """Request with invalid disclosure_channel fails validation."""
        request = _load_json(EXAMPLES / "audit-request.example.json")
        request["disclosure_channel"] = "invalid-channel"
        errs = _errors(_REQUEST_VALIDATOR, request)
        assert errs

    def test_unknown_additional_property_rejected(self) -> None:
        """Request with unknown additional field fails validation."""
        request = _load_json(EXAMPLES / "audit-request.example.json")
        request["unknown_field"] = "should be rejected"
        errs = _errors(_REQUEST_VALIDATOR, request)
        assert errs

    def test_no_secret_fields_in_schema(self) -> None:
        """The schema must not have secret-like field names."""
        props = _REQUEST_SCHEMA.get("properties", {})
        secretish = {"token", "secret", "password", "api_key", "credential", "private_key"}
        for key in props:
            for s in secretish:
                assert s not in key.lower(), f"Secret-like field found: {key}"


class TestAuditReportSchema:
    """Real JSON Schema validation for audit-report.v1.schema.json."""

    def test_valid_example_validates(self) -> None:
        """The example audit report validates against the schema."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        errs = _errors(_REPORT_VALIDATOR, report)
        assert not errs, f"Unexpected validation errors: {errs}"

    def test_missing_request_id_rejected(self) -> None:
        """Report without request_id fails validation."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        del report["request_id"]
        errs = _errors(_REPORT_VALIDATOR, report)
        assert errs

    def test_finding_without_evidence_rejected(self) -> None:
        """Finding without evidence fails validation."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        del report["findings"][0]["evidence"]
        errs = _errors(_REPORT_VALIDATOR, report)
        assert errs

    def test_finding_without_open_uncertainties_rejected(self) -> None:
        """Finding without open_uncertainties fails validation."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        del report["findings"][0]["open_uncertainties"]
        errs = _errors(_REPORT_VALIDATOR, report)
        assert errs

    def test_invalid_severity_rejected(self) -> None:
        """Finding with invalid severity fails validation."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        report["findings"][0]["severity"] = "unknown"
        errs = _errors(_REPORT_VALIDATOR, report)
        assert errs

    def test_missing_disclosure_classification_rejected(self) -> None:
        """Report without disclosure_classification fails validation."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        del report["disclosure_classification"]
        errs = _errors(_REPORT_VALIDATOR, report)
        assert errs

    def test_unknown_finding_property_rejected(self) -> None:
        """Finding with unknown additional field fails validation."""
        report = _load_json(EXAMPLES / "audit-report.example.json")
        report["findings"][0]["unknown_field"] = "should be rejected"
        errs = _errors(_REPORT_VALIDATOR, report)
        assert errs


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
        """models.py imports cleanly from installed package."""
        from agent_red_team.models import (
            Severity, Confidence, Finding,
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
            open_uncertainties="",
        )
        assert finding.finding_id == "F-001"

    def test_contracts_import(self) -> None:
        """contracts.py imports cleanly from installed package."""
        from agent_red_team.contracts import AuditModule
        assert AuditModule is not None

    def test_pipeline_import(self) -> None:
        """pipeline.py imports cleanly from installed package."""
        from agent_red_team.pipeline import PipelinePhase
        assert len(list(PipelinePhase)) == 9
