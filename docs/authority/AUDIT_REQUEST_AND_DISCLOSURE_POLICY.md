# AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md

> Authoritative operating rule for kimeisele/agent-red-team — version 1.0.0

## 1. Binding Operating Rule

**Agent Red Team MUST NOT initiate an audit of another Federation
repository without an explicit, attributable audit request defining
the target and permitted scope.**

An audit begins only after an explicit request from a Federation node
or its authorised operator. Self-initiated, speculative, or
undirected audits are prohibited regardless of technical capability.

## 2. Required Audit Request Fields

Every audit request must contain at minimum:

| Field | Description |
|---|---|
| **Target repository** | Full `owner/repo` to be audited |
| **Requesting node / operator** | Attributable Federation node or human operator |
| **Permitted audit scope** | Files, subsystems, or concerns in scope |
| **Audit type** | e.g. code review, governance gap analysis, workflow audit, architecture risk assessment |
| **Permitted non-destructive methods** | Static analysis, configuration inspection, manual review, safe reproduction |
| **Disclosure channel** | Public issue, private Security Advisory, or confidential report |
| **Point of contact** | Who receives findings and coordinates remediation |

## 3. Default Permissions

### Allowed by default

- Static code analysis (linting, pattern matching, unsafe-code detection)
- Workflow and permission inspection
- Governance and configuration review
- Safe, non-destructive reproduction steps
- Evidence collection from publicly available repository data

### Prohibited by default

- Destructive exploitation of confirmed vulnerabilities
- Production manipulation of target systems or repositories
- Use or storage of discovered secrets beyond immediate disclosure
- Scans of external infrastructure not owned by the target repository
- Public disclosure of exploitable details without coordinated disclosure

## 4. Reporting and Disclosure

### Non-sensitive findings

Quality issues, governance gaps, architectural risks, and
configuration problems that do NOT expose an immediately exploitable
weakness:

- **Channel:** Public GitHub Issue in the target repository, or
  public audit report in this repository.
- **Timeline:** Standard responsible disclosure (no embargo required).

### Exploitable vulnerabilities, secrets, or auth bypasses

Confirmed exploitable weaknesses, exposed credentials, authentication
flaws, or concrete exploit paths:

- **Channel:** Private GitHub Security Advisory, or confidential
  direct message to the designated point of contact.
- **Prohibition:** No public exploit details before remediation or
  explicit release authorisation.
- **Timeline:** Coordinate with the point of contact. Default to
  private disclosure with a reasonable remediation window.

## 5. Report Structure

Every audit report must include:

1. **Severity** — Critical / High / Medium / Low / Informational
2. **Affected file / location** — Exact path and line references
3. **Evidence** — Reproducible observations, configuration excerpts,
   tool output
4. **Impact** — What an attacker or failure could achieve
5. **Reproduction steps** — Step-by-step to verify the finding
6. **Recommended remediation** — Concrete, actionable fix
7. **Confidence** — Confirmed / Likely / Possible
8. **Open uncertainties** — Unresolved questions or assumptions

## 6. Relationship to Federation Governance

This policy is subject to the Federation baseline governance
(`agent-federation-baseline-v1`) and the Agent Internet principles.
It may be superseded by Federation-wide audit standards when those
are adopted.
