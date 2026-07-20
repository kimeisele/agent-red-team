# Audit Report Template

> Fill in all required fields.  See the authoritative
> [Audit Request and Disclosure Policy](../authority/AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md).

| Field | Value |
|---|---|
| **Report ID** | `RPT-YYYY-MMDD-###` |
| **Request ID** | `REQ-YYYY-MMDD-###` |
| **Target Repository** | `owner/repo` |
| **Target Ref** | Audited branch or SHA |
| **Audit Module** | Module that produced this report |
| **Generated At** | ISO 8601 timestamp |
| **Disclosure Classification** | `public` / `private-security-advisory` / `confidential` |

## Summary

<!-- One-paragraph summary of all findings -->

## Findings

<!-- Repeat this block for each finding -->

### Finding `F-###`

| Field | Value |
|---|---|
| **Finding ID** | `F-YYYY-MMDD-###` |
| **Severity** | `critical` / `high` / `medium` / `low` / `informational` |
| **Affected Location** | File path and line reference |
| **Confidence** | `confirmed` / `likely` / `possible` |

#### Evidence

<!-- Reproducible observations, tool output, or configuration excerpts -->

#### Impact

<!-- What an attacker or failure could achieve -->

#### Reproduction Steps

<!-- Step-by-step to verify the finding. Must not require destructive actions. -->

#### Recommended Remediation

<!-- Concrete, actionable fix -->

#### Open Uncertainties

<!-- Unresolved questions or assumptions -->
