# Audit Request Template

> Fill in all required fields.  See the authoritative
> [Audit Request and Disclosure Policy](../authority/AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md).

| Field | Value |
|---|---|
| **Request ID** | `REQ-YYYY-MMDD-###` |
| **Target Repository** | `owner/repo` |
| **Target Ref** | `main` or commit SHA |
| **Requester** | Federation node or operator |
| **Permitted Scope** | Files, subsystems, or concerns |
| **Audit Types** | See enumerated list |
| **Permitted Methods** | See enumerated list |
| **Excluded Methods** | Methods explicitly excluded |
| **Disclosure Channel** | `public-issue` / `private-security-advisory` / `confidential-report` |
| **Point of Contact** | Who receives findings |
| **Created At** | ISO 8601 timestamp |

## Scope

<!-- List files, subsystems, or concerns in scope -->

## Exclusions

<!-- List files or areas explicitly out of scope -->

## Authorisation Statement

<!-- Explicit statement that this request authorises only the described scope -->

## Audit Types

Select from:

- `code-review` — Static code analysis for unsafe patterns
- `governance-gap-analysis` — Branch protection, rulesets, permissions
- `workflow-audit` — GitHub Actions and CI/CD inspection
- `architecture-risk-assessment` — Structural and design risk review
- `dependency-and-supply-chain` — Dependency analysis
- `secrets-exposure` — Credential and secret detection
- `federation-contracts` — Federation descriptor and protocol validation

## Permitted Methods

Select from:

- `static-analysis` — Linting, pattern matching, unsafe-code detection
- `workflow-inspection` — Workflow and permission review
- `governance-review` — Configuration and ruleset review
- `safe-reproduction` — Non-destructive reproduction steps
- `dependency-analysis` — Supply-chain and version analysis
- `federation-contract-validation` — Schema and protocol validation

## Confirmations

- [ ] I confirm that submitting this request authorises only the explicitly described audit scope.
- [ ] I confirm that destructive tests are not authorised by this request.
- [ ] I understand that secrets must not be included in this request.
- [ ] I agree to the Audit Request and Disclosure Policy.
