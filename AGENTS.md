# AGENTS.md

Instructions for AI coding agents working on this repository.

## Repository Mission

**Agent Red Team** is a request-driven federation security-audit node. It inspects
peer repositories for exploitable weaknesses, unsafe code patterns, governance
gaps, and architectural risks, then produces evidence-backed remediation reports.

**Audits are request-driven.** This repository MUST NOT audit any federation
repository without an explicit, attributable request. See the authoritative
[Audit Request and Disclosure Policy](docs/authority/AUDIT_REQUEST_AND_DISCLOSURE_POLICY.md).

## Repository Memory Principle

Conversation history is not authoritative. Engineering intelligence MUST be
externalized into repository artifacts:

- architecture decisions, scope boundaries, and approved invariants → **normative issues**
- executable implementation contracts → **implementation issues**
- code, tests, schemas → **committed source**
- review findings and corrections → **PR descriptions and review comments**
- unresolved questions and deferred work → **open issues with clear status**

A future engineer MUST be able to reconstruct the project state from the
repository alone. Do not leave essential decisions only in terminal output or
chat. When a decision is made, write it into the appropriate artifact.

## Authority Hierarchy

When interpreting project direction, apply this precedence order:

1. Repository-wide security and governance policies (see `docs/authority/`)
2. Applicable normative architecture issues, ADRs, or specifications
3. Approved implementation issues
4. Accepted review decisions (PR descriptions and reviewer findings)
5. Committed implementation and tests
6. Descriptive documentation (README, AGENTS.md)
7. Chat or agent-generated assumptions

Conflicts between artifacts at different levels MUST be escalated and resolved in
a repository artifact (issue comment, specification update, or PR review) rather
than silently interpreted. If an implementation issue conflicts with a normative
architecture issue, the architecture issue wins.

## Agent Roles

### Lead Engineer Agent

Responsible for high-level direction, architecture, and quality:

- Reconnaissance: inspect the repository, its issues, PRs, tests, and
  authoritative documents to reconstruct current state
- Architecture and invariant analysis: identify what is approved, deferred,
  and forbidden
- Defining scope and non-scope in normative or implementation issues
- Independently reviewing Builder output — inspect actual diffs, tests, and
  GitHub artifacts rather than trusting delivery reports alone
- Deciding whether work is merge-ready and authorizing merges
- Preventing scope drift, unsupported architecture, and speculative
  implementation

### Builder Agent

Responsible for focused implementation of a single authorized issue:

- Read all referenced authority before coding
- Create a dedicated branch from `main`
- Keep the diff narrow — no unrelated refactoring
- Add or update tests alongside implementation
- Run required quality gates (`pytest`, `ruff`, `py_compile`)
- Open a draft PR with exact evidence (test counts, SHAs, quality-gate output)
- Stop before merge unless separately authorized

The Builder MUST NOT invent architecture, broaden scope, rewrite unrelated
systems, merge its own work, or implement deferred capabilities.

## Restart Protocol

When entering this repository after a pause (hours, days, or months):

1. Read `AGENTS.md` (this file).
2. Read `README.md` for project orientation.
3. Inspect `docs/authority/` for binding policies and charter.
4. Inspect `docs/architecture/` for design specifications.
5. Inspect open issues. Classify each as:
   - **Normative** — defines approved architecture or scope (e.g., Issue #25)
   - **Executable** — specifies a concrete implementation task
   - **Exploratory** — asks a question without implementation mandate
   - **Blocked** — depends on unresolved decisions
6. Inspect recently merged PRs to understand what was built and why.
7. Confirm the current `main` branch state.
8. Run the baseline quality gates: `pytest tests/ -q`, `ruff check .`
9. Summarize the reconstructed state: what is implemented, what is deferred,
   what decisions remain unresolved, and what the next authorized step is.

Do not begin implementation until a sufficiently precise implementation issue
exists or explicit authorization is given.

Distinguish carefully between:

- **Current implemented truth** — what the code on `main` actually does
- **Normative desired truth** — what architecture issues or specifications
  say SHOULD exist
- **Proposed future work** — open issues not yet approved for implementation
- **Historical evidence** — closed issues and merged PRs are permanent records
  of decisions and implementation. They may remain authoritative for the work
  they governed. Closure or merge alone does not mean supersession.
  Supersession MUST be explicit in a higher- or equal-authority repository
  artifact.

## Engineering Workflow

The stable lifecycle for architectural or cross-cutting work:

1. **Reconnaissance** — read the repository, issues, authoritative documents
2. **Normative specification** — a Lead Engineer writes or updates a
   specification in a repository artifact (issue, ADR, or spec document)
3. **Independent review** — another agent verifies the specification
4. **Implementation issue** — a precise, executable issue translating the
   specification into a concrete scope with acceptance tests
5. **Builder implementation** — a Builder creates a branch, implements only
   the approved scope, and opens a draft PR
6. **Independent code review** — a Lead Engineer inspects diffs, tests, and
   quality-gate results, requests corrections, and verifies they are applied
7. **Quality gates** — full test suite, linting, compilation checks
8. **Merge authorization** — explicit approval by a Lead Engineer
9. **Post-merge verification** — confirm main is green, issue is closed,
   branch is cleaned up

Not every task needs every artifact. Simple fixes with obvious scope may proceed
directly to implementation. But architectural decisions, new capabilities, or
cross-cutting changes MUST NOT jump directly from vague intent to implementation.

## Scope and Stop Boundaries

Agents working in this repository MUST observe these boundaries:

- No speculative implementation. Build only what is explicitly authorized.
- No unrelated refactoring. Keep each PR focused on its approved scope.
- No silent expansion into capabilities deferred by the applicable normative
  authority artifact.
- No auditing a repository without an explicit, attributable request.
- No merge by the implementation agent unless explicitly authorized.
- No claiming tests were run without reporting exact commands and results.
- No treating generated files as editable sources when authoritative sources exist
  (e.g., `.well-known/` files are auto-generated from `scripts/render_*.py` and
  `docs/authority/capabilities.json`).
- Preserve current public contracts unless an authority artifact approves a change.

## Verification Expectations

When reporting results, agents MUST:

- Inspect actual files and diffs (not rely solely on memory or prior reports)
- Run the repository's configured tests and linting
- Distinguish pre-existing failures from newly introduced failures
- Report exact commands, counts, and relevant commit SHAs
- Verify post-merge state when responsible for closure
- Not rely solely on self-reported delivery summaries from other agents

Configured quality gates (`pyproject.toml`):

```bash
python -m pytest tests/ -q       # test suite (pytest >= 8.0)
python -m ruff check .            # lint (ruff >= 0.5)
python -m py_compile <modules>    # Python compile check
```

## Current-State Discovery

To discover the current project state, an agent MUST inspect the repository
rather than relying on this document for transient facts.

Issue #25, Issue #26, and PR #27 together demonstrate the working pattern:
architecture specification → implementation contract → reviewed implementation
→ merge. They are examples of the workflow, not permanent global authority for
all future work.

## Federation Inheritance

This repository operates as a node in the
[agent-internet](https://github.com/kimeisele/agent-internet) federation mesh.
Federation capabilities (descriptor publishing, peer discovery, authority feeds,
NADI transport) remain active and are configured through the scripts in
`scripts/` and the descriptors in `docs/authority/` and `.well-known/`.

The security-audit mission is the primary purpose of this node. Federation
integration serves that mission. Generic federation-node template instructions
do not apply unless they are explicitly referenced in the current architecture.
