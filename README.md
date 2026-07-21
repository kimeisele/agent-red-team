# Agent Red Team

**Request-driven federation security-audit node.**

> Audits are **request-driven only**. This node MUST NOT audit any
> Federation repository without an explicit, attributable request.
> See the authoritative
> [Audit Request and Disclosure Policy](docs/authority/AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md).

## Mission

Agent Red Team inspects peer federation repositories for exploitable
weaknesses, unsafe code patterns, governance gaps, and architectural
risks. It produces evidence-backed remediation reports with confirmed,
reproducible findings.

The node operates as a federation citizen — it publishes an authority feed,
participates in peer discovery, and can send and receive NADI messages —
but its primary function is security auditing.

## Architecture

The project follows an architecture-first, slice-by-slice development model.
Each slice is specified in a normative issue, translated into an executable
implementation issue, reviewed independently, and merged.

### Implemented Foundation: Transactional Run-Event Persistence

The first architectural slice is merged:

- SQLite-backed event store with ACID transactions (WAL mode)
- Deterministic canonical JSON serialization and SHA-256 content digests
- Single public operation: `EventRepository.record_run_event(...)` with
  idempotent replay, conflict detection, and commit-uncertainty recovery
- Six-table schema: `schema_migrations`, `analysis_subjects`, `audit_runs`,
  `audit_events`, `run_state`, `idempotency_records`
- Per-database-path process lock for safe concurrent initialization
- Dedicated acceptance test coverage, exercised by the full repository
  test suite

Architecture: [Issue #25](https://github.com/kimeisele/agent-red-team/issues/25)
Implementation: [PR #27](https://github.com/kimeisele/agent-red-team/pull/27)

### Deferred (Future Slices)

Findings, observations, verification attempts, carry-forward, artifact storage,
hash-chained event verification, analyzer sandboxing, and pipeline orchestration
are deferred. The normative architecture issue (#25) documents the complete
design and explicit deferred list.

### Pipeline Architecture

The target architecture is a 9-phase modular audit pipeline:

```
Request Intake → Validation → Authorization → Planning →
Module Execution → Finding Normalization →
Disclosure Classification → Report Rendering → Delivery
```

See [`docs/architecture/MODULAR_AUDIT_PIPELINE.md`](docs/architecture/MODULAR_AUDIT_PIPELINE.md).

Each audit module satisfies the `AuditModule` Protocol (`src/agent_red_team/contracts.py`):
it receives a validated request and a local repository snapshot, and returns
normalised findings. Modules are read-only by default.

## Repository Layout

```
src/agent_red_team/
  models.py              Domain types (AuditRequest, Finding, AuditReport)
  contracts.py           AuditModule Protocol
  pipeline.py            PipelinePhase enum
  persistence/           Slice-1 persistence foundation
    repository.py          EventRepository (single public operation)
    migration.py           Schema migration v1
    connection.py          SQLite connection factory + utc_timestamp()
    serialization.py       Canonical JSON + SHA-256 helpers
    models.py              RecordRunEventResult, error types
  modules/               Audit modules (placeholder)

docs/
  authority/             Charter, policy, capability manifest
  architecture/          Pipeline design, institutional architecture vision

tests/                   pytest suite
scripts/                 Federation utilities (setup, discovery, NADI)
schemas/                 JSON Schema (audit request v1, audit report v1)
.well-known/             Auto-generated federation descriptors
data/federation/         Peer descriptors, NADI inbox/outbox
```

## Install and Test

```bash
# Requirements: Python >= 3.11
pip install -e ".[test]"

# Run the full test suite
python -m pytest tests/ -q

# Lint
python -m ruff check .
```

## Federation Integration

Agent Red Team is a node in the [Agent Internet](https://github.com/kimeisele/agent-internet)
federation. Federation capabilities include:

- **Descriptor publishing:** `.well-known/agent-federation.json` and `.well-known/agent.json`
  are auto-generated from `docs/authority/capabilities.json`
- **Peer discovery:** `scripts/discover_federation_peers.py` and weekly CI workflow
- **Authority feeds:** `scripts/export_authority_feed.py` with SHA-256 content verification
- **NADI transport:** `scripts/nadi_send.py` for outbox-based messaging; relay via
  [steward-federation](https://github.com/kimeisele/steward-federation)

These capabilities serve the security-audit mission. Audit requests, findings,
and reports are not transmitted over federation transport in Slice 1.

## Authority and Decision-Making

Authoritative documents (in precedence order):

1. [Audit Request and Disclosure Policy](docs/authority/AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md)
2. [Charter](docs/authority/charter.md)
3. Normative architecture issues (currently [#25](https://github.com/kimeisele/agent-red-team/issues/25))
4. [Modular Audit Pipeline](docs/architecture/MODULAR_AUDIT_PIPELINE.md) specification

Engineering workflow and agent roles are defined in [AGENTS.md](AGENTS.md).

## Legacy: Federation Template Origins

After merging your setup PR, the federation workflows will automatically
regenerate `.well-known/agent-federation.json`, the agent card, and the
authority feed manifest.

This repository was originally created from a
[federation-node template](https://github.com/kimeisele/agent-template). The
federation infrastructure (descriptors, peer discovery, NADI transport,
authority feeds) remains functional.
