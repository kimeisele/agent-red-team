# MODULAR_AUDIT_PIPELINE.md

> Architecture specification — version 1.0.0

## Pipeline Phases

```
Request Intake
  → Request Validation
    → Authorization and Scope Gate
      → Audit Planning
        → Audit Module Execution
          → Finding Normalization
            → Disclosure Classification
              → Report Rendering
                → Delivery
```

## Module Contract

Each audit module implements a narrow contract:

| Field | Description |
|---|---|
| **Module metadata** | Name, version, supported audit types |
| **Required permissions** | What the module needs (read-only by default) |
| **Input** | Validated audit request + repository snapshot |
| **Output** | Zero or more normalised findings |

### Module Constraints

- A module MUST NOT expand its scope beyond the authorised request.
- A module MUST NOT mutate the target repository by default.
- A module MUST NOT write secrets or credentials into logs or reports.
- Findings MUST be classified before publication.
- Sensitive findings MUST NOT pass through a public renderer before disclosure classification.

## Future Audit Modules

| Module | Audit Types |
|---|---|
| `governance` | Governance gap analysis, ruleset and permission review |
| `workflows` | GitHub Actions / workflow inspection |
| `dependencies` | Dependency and supply-chain analysis |
| `secrets` | Secrets exposure detection |
| `code-safety` | Static code safety review |
| `federation-contracts` | Federation descriptor and protocol validation |
| `architecture` | Architecture risk assessment |

## Security Invariants

1. **Scope enforcement** — No module may expand its authorised scope autonomously.
2. **Read-only default** — Modules are read-only by default; mutation requires explicit, auditable authorisation.
3. **Secret safety** — No secret, token, or credential may appear in logs, reports, or commit messages.
4. **Classification gate** — Every finding must pass through disclosure classification before rendering.
5. **Public/private separation** — Sensitive findings must not be routed through a public renderer.
6. **Honest incompleteness** — A failed or incomplete audit run must not be reported as a complete success.
7. **Uncertainty preservation** — Uncertainty and open questions must be retained in the output.
8. **Stable correlation** — Request, findings, and report must be correlatable via stable IDs.

## Data Flow

```text
Request (JSON Schema v1)
  → Parser/Validator
    → ValidatedAuditRequest
      → Authorisation Gate
        → AuditPlan (selected modules, ordered phases)
          → Per-module: (request + snapshot) → [Finding]
            → FindingNormalizer (canonical form)
              → DisclosureClassifier (public / private / confidential)
                → ReportRenderer (human-readable + machine-readable)
                  → DeliveryAdapter (issue, advisory, confidential channel)
```
