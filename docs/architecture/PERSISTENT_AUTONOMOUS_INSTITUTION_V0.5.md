PERSISTENT AUTONOMOUS COMPUTATIONAL INSTITUTION

Architectural Vision Assessment v0.5 — Final Review Candidate

document:
  status: FINAL_PRE_DESIGN_REVIEW_CANDIDATE
  audience: Final Senior Lead Engineering Agent
  pilot_domain: autonomous_software_security_auditing
  purpose:
    - test_whether_persistent_institutional_capability_exists
    - falsify_institutional_complexity_before_building_it
    - isolate_the_value_of_claims_lineage_and_invalidation
    - define_a_minimal_sufficient_architecture
    - preserve_future_architectural_optionality
  implementation_authority: LIMITED_POC_ONLY
  freeze_scope:
    freeze:
      - central_research_questions
      - safety_invariants
      - trust_boundaries
      - normalized_finding_boundary
      - minimal_analysis_subject_contract
      - run_record_contract
      - terminal_outcome_vocabulary
      - benchmark_principles
      - falsification_criteria
    do_not_freeze:
      - generalized_claim_ontology
      - semantic_claim_identity
      - full_lineage_model
      - semantic_invalidation_engine
      - graph_database
      - event_sourcing
      - workflow_engine
      - agent_organization
      - learned_routing
      - generalized_audit_package

⸻

0. EXECUTIVE CORRECTION

v0.4.1 correctly identified semantic invalidation as the central research risk.

It nevertheless placed substantial claim, lineage, verification and institutional machinery before the cheapest decisive test of that risk.

v0.5 reverses that sequence.

Do not construct the institution
and then test whether its load-bearing mechanism works.
First build the smallest system capable of showing
whether persistent reuse and selective invalidation
provide value beyond ordinary finding tracking.

The initial target is therefore not the complete institution.

The initial target is:

a Minimal Sufficient Architecture
that can defeat or justify the institutional hypothesis.

⸻

1. CENTRAL RESEARCH QUESTIONS

Q1
Can justified security conclusions be preserved and reused
across repository evolution without unsafe carry-forward?
Q2
Can the system autonomously detect when a prior conclusion
no longer deserves trust?
Q3
Does managed institutional structure provide measurable value
beyond:
- analyzer reruns,
- exact caches,
- SARIF history,
- stable finding fingerprints,
- deterministic reopening,
- retrieval,
- and repeated model triage?
Q4
Can the system reach honest epistemic and procedural closure
without mandatory human participation and without rewarding
false certainty?

The architecture is justified only if Q3 produces a material positive result.

⸻

2. STRONGEST COUNTERHYPOTHESIS

counterhypothesis:
  statement: >
    Analyzer execution, SARIF normalization, longitudinal finding
    fingerprints, deterministic reopening, historical triage state,
    bounded retrieval and falsification-oriented verification provide
    most of the useful persistence at a fraction of the complexity of
    a generalized institutional claim and lineage system.
  consequence_if_supported: >
    Do not build the generalized institutional layer.
  confidence: PLAUSIBLE_AND_UNTESTED

This counterhypothesis must be treated as a serious candidate architecture, not a weak baseline designed to lose.

⸻

3. MINIMAL SUFFICIENT ARCHITECTURE

3.1 Purpose

The Minimal Sufficient Architecture, abbreviated MSA, is the first executable architecture.

It must test:

* longitudinal finding identity,
* safe state carry-forward,
* deterministic reopening,
* regression detection,
* autonomous falsification,
* abstention,
* and the marginal need for richer institutional machinery.

3.2 Components

MinimalSufficientArchitecture:
  analyzer_runner:
    purpose:
      - execute_one_or_more_existing_security_analyzers
      - preserve_raw_outputs
      - record_versions_and_configuration
  normalized_finding_adapter:
    purpose:
      - map_analyzer_outputs_to_a_stable_boundary
      - prefer_SARIF_where_supported
      - preserve_tool_specific_extensions
  analysis_subject_lite:
    purpose:
      - identify_the_minimum_relevant_technical_subject
  finding_fingerprinter:
    purpose:
      - track_probable_finding_identity_across_repository_evolution
  slice_fingerprinter:
    purpose:
      - detect_changes_in_the_relevant_source_to_sink_neighborhood
  longitudinal_state_store:
    purpose:
      - preserve_runs_findings_outcomes_and_carry_forward_decisions
  governed_artifact_store:
    purpose:
      - preserve_raw_tool_output
      - preserve_relevant_code_regions
      - preserve_test_or_exploit_evidence
  falsification_harness:
    purpose:
      - attempt_runtime_reproduction_in_a_sandbox
      - produce_machine_observable_results
  semantic_triage_resource:
    purpose:
      - interpret_ambiguity
      - generate_tests
      - explain_results
      - never_serve_as_standalone_confirmation
  policy_evaluator:
    purpose:
      - determine_reporting_and_operational_effects
      - default_to_report_only_in_the_PoC
  benchmark_harness:
    purpose:
      - compare_against_independent_ground_truth
      - measure_false_carry_forward_and_reopening_behavior

3.3 Minimal data objects

AnalysisSubjectLite:
  required:
    - repository_identity
    - commit_hash
    - worktree_patch_hash_or_clean_state
    - lockfile_hashes
    - relevant_runtime_version
    - analyzer_identity_and_version
    - relevant_framework_model_version
  optional:
    - platform
    - generated_artifact_hashes
    - relevant_feature_flags
    - container_image
    - dependency_resolution_snapshot
RunRecord:
  required:
    - run_id
    - analysis_subject_ref
    - analyzer_configuration
    - input_refs
    - output_refs
    - timestamps
    - resource_usage
    - terminal_status
NormalizedFinding:
  required:
    - finding_id
    - analyzer
    - rule_id
    - vulnerability_class
    - primary_location
    - source_locations
    - sink_location
    - trace
    - finding_fingerprint
    - relevant_slice_hash
    - raw_output_ref
FindingState:
  values:
    - new
    - reproduced
    - not_reproduced
    - inconclusive
    - unsupported
    - abstained
    - fixed
    - reopened
    - carried_forward
VerificationAttempt:
  required:
    - verification_id
    - finding_ref
    - method
    - inputs
    - outputs
    - result
    - limitations
    - oracle_type
Artifact:
  required:
    - artifact_id
    - type
    - content_hash
    - tenant_scope
    - retention_class
    - payload_location

No generalized Claim object is required in the first implementation.

⸻

4. INITIAL REUSE AND INVALIDATION RULE

The first invalidation mechanism must be deliberately crude, deterministic and falsifiable.

Carry forward a prior finding state only when:
1. the finding fingerprint still matches,
2. the relevant dataflow or code-slice hash is unchanged,
3. the relevant analyzer and framework model remain qualified,
4. no registered invalidation event affects the finding.

Otherwise:

reopen and reanalyze

This mechanism is intentionally conservative.

It does not attempt general semantic equivalence.

Its purpose is to establish a strong null baseline against which semantic invalidation must later compete.

⸻

5. PER-CLAIM RELEVANCE WITHOUT A CLAIM ONTOLOGY

Analysis subjects contain many possible dimensions.

Requiring exact equality across every dimension would destroy reuse.

Therefore reuse must be scoped by a relevance mask.

RelevanceMask:
  possible_dimensions:
    - source_slice
    - dependencies
    - runtime
    - platform
    - analyzer_version
    - framework_model
    - build_configuration
    - feature_flags
    - external_evidence
  semantics: >
    A conclusion may be reused only when the dimensions registered
    as relevant to that conclusion remain equivalent.

In the initial system, the relevance mask may be attached to:

* a finding type,
* a verification method,
* or a finding record.

It does not require full atomic claim decomposition.

⸻

6. FALSIFICATION-FIRST VERIFICATION

Autonomous verification must not rely primarily on agreement among models.

Machine agreement is not proof.
Different model names are not evidence independence.
Different providers do not guarantee independent training data,
assumptions or failure modes.

Verification priority:

1. independently checkable proof object
2. reproducible runtime counterexample or exploit
3. deterministic analyzer trace with validated semantics
4. heterogeneous tool evidence
5. semantic model analysis
6. model consensus

Model consensus alone cannot promote a finding to verified.

6.1 Realistic epistemic outcomes

outcomes:
  reproduced:
    meaning: >
      A relevant security behavior was demonstrated under the
      recorded AnalysisSubject and sandbox conditions.
  refuted_under_tested_conditions:
    meaning: >
      A specific hypothesis was falsified under recorded conditions.
      This does not prove universal safety.
  not_reproduced:
    meaning: >
      The attempted reproduction failed.
      This is not equivalent to absence of vulnerability.
  inconclusive:
    meaning: >
      Available evidence does not justify a positive or negative conclusion.
  unsupported:
    meaning: >
      The system lacks required language, framework, build or runtime support.
  abstained:
    meaning: >
      The system intentionally declined to conclude because uncertainty,
      evidence quality or policy thresholds were insufficient.

6.2 Claims that may be strongly verified

Potentially strong machine-verifiable cases:

* concrete runtime exploit reproduction,
* existence of a particular source-to-sink path under a validated analyzer model,
* syntax or type facts,
* satisfiable path constraints in a supported fragment,
* verification of a proof object by a qualified checker,
* regression against a known reproducer.

Potentially non-verifiable or only conditionally verifiable cases:

* universal absence of sanitizer bypasses,
* full absence of command injection across unknown runtime behavior,
* business-impact conclusions,
* completeness of repository coverage,
* security of unsupported dynamic behavior,
* intent of code authors,
* safety under unobserved deployment configurations.

These may remain inconclusive.

⸻

7. AUTONOMY AND CLOSURE

closure:
  epistemic:
    meaning: >
      The system reaches the most justified available conclusion,
      including inconclusive, unsupported or abstained.
  procedural:
    meaning: >
      The audit run terminates correctly without mandatory human intervention.
  operational:
    meaning: >
      Consequential actions occur only under explicit policy authority.
  governance:
    meaning: >
      Purpose, values, risk tolerance and authority delegation are
      not silently inferred by the audit process.

Humans are not required runtime terminators.

Humans may still define:

* purpose,
* policy,
* external benchmark labels,
* risk tolerance,
* and authority boundaries.

The PoC must default to:

autonomous analysis and reporting
without autonomous code modification, deployment or risk acceptance

⸻

8. METRIC CORRECTION

Raw closure rate is not a success metric by itself.

A system can increase closure rate merely by becoming overconfident.

Primary autonomy metrics:

autonomy_metrics:
  - false_certainty_rate
  - correct_abstention_rate
  - unsafe_positive_conclusion_rate
  - unsafe_negative_conclusion_rate
  - unsupported_scope_detection
  - hidden_human_dependency_rate
  - procedural_completion_rate

Inconclusive and abstained must not automatically count as failures.

A useful system may correctly abstain more often than a reckless system.

⸻

9. EXPERIMENTAL DESIGN

9.1 Required null baselines

null_baselines:
  N0_full_reanalysis:
    behavior:
      - rerun_everything
      - reuse_no_prior_conclusion
  N1_exact_subject_cache:
    behavior:
      - reuse_only_on_exact_AnalysisSubject_match
      - otherwise_reanalyze
  N2_finding_fingerprint_tracking:
    behavior:
      - carry_forward_on_stable_finding_fingerprint
      - otherwise_reopen
  N3_fingerprint_plus_slice_hash:
    behavior:
      - carry_forward_only_when_fingerprint_and_slice_hash_match
      - otherwise_reopen

Institutional mechanisms must first outperform N3.

9.2 Corrected ablations

experimental_ablations:
  A0:
    system: N3
  A1:
    adds:
      - additional_semantic_triage
    control:
      - equal_compute_budget_without_structured_claims
  A2:
    adds:
      - atomic_structured_claims
    control:
      - equal_context_and_equal_compute_unstructured_representation
  A3:
    adds:
      - explicit_lineage_graph
    control:
      - equivalent_raw_evidence_bundle_without_graph_structure
  A4:
    adds:
      - explicit_verification_records
    control:
      - equal_number_of_verification_attempts_without_institutional_record_structure
  A5:
    adds:
      - semantic_change_impact_analysis
    control:
      - conservative_reopen_on_any_relevant_slice_change
  A6:
    adds:
      - selective_atomic_reverification
    control:
      - reverify_entire_finding
  A7:
    adds:
      - institution_grade_execution_journal
    control:
      - minimal_RunRecord_with_equivalent_execution_count

Each arm must control for:

* model calls,
* token budget,
* analyzer executions,
* context volume,
* verification attempts,
* wall-clock budget,
* and retrieval depth.

Without compute- and context-matched controls, causal claims are invalid.

9.3 Longitudinal measurement

Lineage, invalidation and selective reverification must be evaluated primarily on repeated visits to evolving repositories.

They cannot be judged meaningfully from first-audit performance alone.

⸻

10. EARLY INVALIDATION PROBE

Semantic invalidation must be tested before building generalized institutional machinery.

Phase 0A — Cheap invalidation probe

Create a narrow corpus containing:

* unchanged vulnerable flows,
* irrelevant changes,
* source changes,
* sink changes,
* sanitizer changes,
* wrapper refactoring,
* function rename and move,
* inlining,
* dependency-only changes,
* analyzer-model changes,
* runtime-version changes,
* false fixes,
* regressions.

Compare:

full reanalysis
versus
fingerprint carry-forward
versus
fingerprint + slice hash
versus
one minimal semantic impact heuristic

Measure:

* unsafe carry-forward,
* unnecessary reopening,
* analysis cost,
* regression detection,
* and implementation complexity.

Decision rule:

If the minimal semantic heuristic does not materially outperform
fingerprint + slice hash, defer generalized semantic invalidation.

This probe precedes generalized claim decomposition.

⸻

11. SEMANTIC INVALIDATION

General semantic invalidation is not assumed to be solvable.

It is treated as:

semantic_invalidation:
  nature:
    - heuristic
    - domain_specific
    - potentially_probabilistic
    - never_universally_complete
  primary_question: >
    Can a bounded impact classifier reduce unnecessary reanalysis
    without causing unacceptable unsafe reuse?

Possible invalidation events:

InvalidationEvent:
  event_type:
    - source_change
    - dependency_change
    - runtime_change
    - build_change
    - analyzer_change
    - rule_change
    - framework_model_change
    - policy_change
    - evidence_retraction
    - verifier_disqualification
    - tool_bug_discovery

Default behavior under uncertain impact:

reopen

Semantic preservation must be demonstrated, not assumed.

Full reanalysis remains preferable when:

* reanalysis is inexpensive,
* impact classification is uncertain,
* the finding is high severity,
* the analysis surface is small,
* or the cost of unsafe reuse exceeds reanalysis cost.

⸻

12. CLAIMS: DEFERRED, NOT REJECTED

Structured claims may later be justified.

They are not part of the first mandatory architecture.

Reasons for deferral:

Claim identity across refactoring depends on semantic continuity.
Semantic continuity is itself part of the unresolved invalidation problem.
Freezing claim keys before testing that problem creates circular lock-in.

Atomic claims should be introduced only when measured evidence shows that whole-finding state is too coarse.

Entry conditions may include:

* excessive unnecessary reopening,
* inability to preserve unaffected sub-conclusions,
* need for partial finding invalidation,
* repeated reuse of the same atomic fact,
* or inability to explain why a finding state changed.

12.1 Provisional future claim structure

If introduced:

Claim:
  - claim_id
  - subject_ref
  - predicate
  - object_or_value
  - qualifiers
  - natural_language_rendering
  - validity_scope
  - dependencies
  - schema_version

Claim-key semantics remain experimental until validated across refactorings.

⸻

13. FINDING COMPOSITION

Do not create a custom security logic language in the first PoC.

Finding derivation should prefer:

existing analyzer rules
existing query languages
existing rule engines
or minimal versioned boolean metadata

Candidates:

* CodeQL queries,
* Semgrep rules,
* Soufflé,
* OPA for policy,
* simple versioned application logic.

Only build a custom FindingDefinition language if existing systems cannot express required composition and this limitation is demonstrated empirically.

⸻

14. ANALYSIS SUBJECT EQUIVALENCE

Exact AnalysisSubject equality is not always required.

Equivalence depends on the finding and verification method.

subject_equivalence:
  exact:
    meaning: every_registered_dimension_matches
  relevance_masked:
    meaning: all_dimensions_relevant_to_the_conclusion_match
  unknown:
    meaning: relevance_or_equivalence_cannot_be_established
    action: reopen

For the JavaScript command-injection pilot, likely required dimensions are:

required_pilot_dimensions:
  - repository_and_commit
  - uncommitted_patch_state
  - lockfile_hash
  - Node_runtime_major_or_exact_version_as_required
  - analyzer_version
  - analyzer_rule_version
  - relevant_framework_model_version

Likely optional dimensions:

optional_pilot_dimensions:
  - cpu_architecture
  - container_image
  - environment_variables
  - feature_flags
  - generated_artifacts
  - external_service_snapshots

Optional dimensions become required only when a finding declares dependency on them.

Sensitive values should normally be represented through qualified hashes or references, not copied into the canonical record.

⸻

15. EVIDENCE INDEPENDENCE

Independence is often unknowable for model-based evidence.

The architecture must represent unknown independence honestly.

independence_profile:
  dimensions:
    - source
    - method
    - implementation
    - model_family
    - provider
    - environment
    - oracle
    - upstream_evidence
    - shared_assumptions
  allowed_values:
    - distinct
    - partially_shared
    - shared
    - unknown
    - not_applicable

No composite independence score is defined.

For LLM-only confirmation:

default independence status: unknown or shared

Independent verification status should generally require one of:

* a deterministic oracle,
* an independently checkable proof,
* a runtime reproducer,
* a materially distinct analyzer implementation,
* or an external benchmark oracle.

Adversarial model review may improve critique quality but does not by itself establish independence.

⸻

16. REPRODUCIBILITY

Use an internal profile and an optional simplified display.

ReproducibilityProfile:
  - auditable
  - inputs_preserved
  - outputs_preserved
  - environment_reconstructable
  - components_available
  - reexecutable
  - deterministic
  - semantically_stable
  - bitwise_stable

Optional summary labels:

R0 auditable
R1 reexecutable
R2 semantically reproducible
R3 bitwise reproducible

The profile, not the summary label, controls technical decisions.

⸻

17. TRUSTED COMPUTING BASE

Separate two Trusted Computing Bases.

17.1 Runtime TCB

runtime_tcb_candidates:
  - identity_and_hashing
  - canonical_relational_store
  - artifact_access_control
  - sandbox_boundary
  - policy_enforcement_boundary
  - signature_or_attestation_verification

Analyzers and models should preferably remain:

untrusted evidence producers

A proof checker belongs to the Runtime TCB only for guarantees derived from its proofs.

17.2 Scientific TCB

scientific_tcb:
  - benchmark_dataset_generation
  - reference_labels
  - exploit_oracle
  - measurement_harness
  - metric_implementation
  - contamination_controls

A failure in the Scientific TCB invalidates experimental conclusions even when runtime behavior is correct.

Both TCBs must be:

* minimal,
* versioned,
* tested,
* and independently inspectable.

⸻

18. DATA GOVERNANCE

For the PoC, mandatory foundations are:

mandatory_from_day_one:
  - tenant_scope
  - secret_detection_before_external_transmission
  - artifact_classification
  - access_control
  - retention_class
  - deletion_capability
  - audit_of_external_model_payloads

Deferred unless real deployment requires them:

defer:
  - legal_hold_automation
  - generalized_regulatory_workflows
  - complex_crypto_shredding_orchestration
  - multi_region_retention_policy
  - universal_data_lineage_governance

Principle:

Institutional accountability may preserve metadata,
hashes and deletion records without preserving
every sensitive payload indefinitely.

External model calls must record:

* which artifacts or excerpts were transmitted,
* provider,
* data-handling policy,
* and redaction status.

⸻

19. OPEN-SOURCE ADOPTION

open_source_decisions:
  Semgrep:
    decision: ADOPT_OR_ADAPT
    purpose:
      - fast_rule_based_detection
      - initial_command_injection_baseline
  CodeQL:
    decision: EVALUATE_AND_WRAP
    purpose:
      - dataflow_analysis
      - stronger_semantic_queries
    caution:
      - licensing_and_ecosystem_lock_in
  Joern:
    decision: EVALUATE
    purpose:
      - analyzer_native_graph_and_query_capability
    caution:
      - operational_complexity
  SARIF:
    decision: ADOPT
    purpose:
      - normalized_finding_exchange
      - baseline_diffing
      - interoperability
  SQLite:
    decision: ADOPT_FOR_POC
    purpose:
      - runs
      - findings
      - states
      - verification_attempts
  PostgreSQL:
    decision: DEFER
    entry_condition:
      - concurrency_or_scale_requires_it
  OPA:
    decision: DEFER_OR_WRAP_MINIMALLY
    purpose:
      - operational_policy
    entry_condition:
      - policy_complexity_exceeds_simple_rule_tables
  Souffle:
    decision: DEFER
    purpose:
      - future_symbolic_rules
  Temporal_or_workflow_engine:
    decision: DEFER
    entry_condition:
      - retries_leases_compensation_or_long_running_workflows_are_measured_needs
  Graph_database:
    decision: REJECT_FOR_INITIAL_POC
  Custom_event_sourcing:
    decision: REJECT_FOR_INITIAL_POC
  Git_or_existing_CAS:
    decision: ADAPT
    purpose:
      - content_identity
      - source_history
    caution:
      - sensitive_payload_governance
  in_toto_SLSA_Sigstore:
    decision: DEFER
    entry_condition:
      - artifact_attestation_becomes_required

Likely original work, if validated:

potential_novelty:
  - safe_longitudinal_reuse_contract
  - relevance_masked_analysis_subject_equivalence
  - evidence_aware_carry_forward
  - generic_invalidation_event_semantics
  - calibrated_autonomous_abstention
  - measured_transition_from_findings_to_atomic_claims

Most other components are integration work.

⸻

20. LONGITUDINAL BENCHMARK

The benchmark must include irregular repository evolution.

events:
  - vulnerability_introduction
  - irrelevant_change
  - partial_fix
  - complete_fix
  - false_fix
  - regression
  - rename
  - move
  - inline
  - wrapper_introduction
  - dependency_only_change
  - runtime_change
  - configuration_change
  - analyzer_rule_change
  - branch_divergence
  - cherry_pick
  - revert
  - merge_commit
  - generated_code_change
  - vulnerability_migration
  - simultaneous_fix_and_new_vulnerability

Required sets:

development
validation
blind evaluation

At least part of the blind set must be:

* newly generated,
* privately held until evaluation,
* or semantically mutated enough to reduce training contamination.

⸻

21. BENCHMARK ORACLE

The benchmark oracle must be external to the runtime system.

oracle_sources:
  preferred:
    - seeded_vulnerability
    - reproducible_exploit
    - independently_checkable_test
    - confirmed_fix_and_regression_history
  supplemental:
    - independent_expert_annotation
    - adjudicated_reference_label
  prohibited:
    - system_claim_as_its_own_ground_truth
    - model_consensus_without_external_basis
    - hidden_runtime_human_rescue

The exploit harness itself has a false-negative risk.

Therefore record:

oracle_quality:
  - supported_environment
  - setup_success
  - coverage_limitations
  - known_false_negative_cases
  - oracle_version

not reproduced must never automatically equal safe.

⸻

22. RISK-WEIGHTED METRICS

primary_metrics:
  detection:
    - precision
    - recall
    - severity_weighted_false_negative_cost
  longitudinal_reuse:
    - correct_carry_forward_rate
    - unsafe_carry_forward_rate
    - unnecessary_reopen_rate
    - regression_detection_rate
  invalidation:
    - invalidation_recall
    - invalidation_precision
    - missed_invalidation_expected_loss
    - reanalysis_cost_saved
  autonomy:
    - false_certainty_rate
    - correct_abstention_rate
    - unsupported_scope_detection
    - procedural_completion_rate
    - hidden_human_dependency_rate
  verification:
    - reproducible_exploit_rate
    - oracle_false_negative_rate
    - model_only_confirmation_rate
    - correlated_error_detection
  efficiency:
    - cost_per_confirmed_finding
    - compute_per_repository_revision
    - storage_growth
    - additional_complexity_per_feature

For critical findings:

invalidation recall is generally more important
than invalidation precision

The exact weighting must be declared before evaluation.

⸻

23. POINTS OF NO RETURN

23.1 Claim identity schema

risk: HIGH
recommendation:
  - do_not_freeze_atomic_claim_keys_yet
  - begin_with_finding_identity
  - add_claims_behind_a_versioned_boundary_only_after_measured_need

23.2 AnalysisSubject identity

risk: HIGH
recommendation:
  - freeze_only_AnalysisSubjectLite
  - support_relevance_masks
  - avoid_exact_equality_across_irrelevant_dimensions

23.3 Analyzer-native representation

risk: MEDIUM_HIGH
recommendation:
  - maintain_normalized_SARIF_or_equivalent_boundary
  - avoid_making_CodeQL_or_Joern_the_canonical_institutional_schema

23.4 Event sourcing

risk: HIGH
recommendation:
  - defer
  - use_relational_records_and_minimal_run_log

23.5 Graph database

risk: MEDIUM_HIGH
recommendation:
  - defer
  - use_analyzer_native_graphs_and_rebuildable_exports

23.6 Workflow engine

risk: MEDIUM_HIGH
recommendation:
  - defer_until_durable_workflow_requirements_are_observed

23.7 Tenant model

risk: HIGH_IF_OMITTED
recommendation:
  - include_tenant_scope_from_day_one
  - defer_complex_multi_tenant_operations

23.8 Custom policy language

risk: MEDIUM
recommendation:
  - start_with_simple_versioned_rules
  - adopt_OPA_only_when_policy_complexity_justifies_it

⸻

24. IMPLEMENTATION SEQUENCE

Phase 0 — Experimental foundation

produce:
  - benchmark_subjects
  - independent_oracles
  - contamination_controls
  - null_baselines_N0_to_N3
  - compute_and_context_matching_rules
  - numerical_success_thresholds
  - runtime_TCB
  - scientific_TCB

Phase 1 — Minimal analyzer pipeline

build:
  - AnalysisSubjectLite
  - analyzer_runner
  - SARIF_or_normalized_finding_adapter
  - RunRecord
  - relational_finding_history
  - governed_artifact_storage

Phase 2 — Longitudinal identity

build:
  - finding_fingerprint
  - relevant_slice_hash
  - exact_cache
  - deterministic_carry_forward
  - deterministic_reopening
  - regression_tracking

Phase 3 — Falsification harness

build:
  - sandboxed_reproducer
  - marker_payload_tests
  - environment_qualification
  - reproduced_not_reproduced_inconclusive_outcomes
  - semantic_triage_as_non_authoritative_support

Phase 4 — Early invalidation experiment

compare:
  - full_reanalysis
  - exact_subject_cache
  - fingerprint_tracking
  - fingerprint_plus_slice_hash
  - one_minimal_semantic_impact_heuristic

Decision gate:

Do not proceed to generalized claims or semantic invalidation
unless a measured gap justifies them.

Phase 5 — Controlled institutional ablations

Possible additions, one at a time:

candidates:
  - atomic_claim_decomposition
  - explicit_lineage_structure
  - verification_records
  - scoped_invalidation
  - selective_atomic_reverification

Every addition requires:

* compute-matched control,
* context-matched control,
* measured marginal gain,
* and complexity accounting.

Phase 6 — Optional institutional mechanisms

Only after demonstrated need:

optional:
  - advanced_audit_packages
  - policy_engine
  - durable_workflow_engine
  - execution_journal
  - persistent_roles
  - symbolic_rule_externalization
  - graph_projection_service

⸻

25. NUMERICAL GATES

Exact values must be finalized during Phase 0, but the decision logic must follow this form.

example_gates:
  unsafe_reuse:
    requirement: >
      Must remain below a strict severity-weighted threshold.
  institutional_gain:
    requirement: >
      Must materially outperform fingerprint-plus-slice-hash baseline
      after compute and context are matched.
  invalidation_value:
    requirement: >
      Reduction in unnecessary reanalysis must exceed the implementation,
      storage and ongoing correctness cost of impact analysis.
  autonomous_integrity:
    requirement: >
      Added automation must not increase false certainty beyond
      the predeclared tolerance.
  abstention:
    requirement: >
      Correct abstention is accepted as successful epistemic behavior.
  complexity:
    requirement: >
      Every added layer must justify its marginal operational burden.

Possible verdicts:

PROCEED
NARROW
REMAIN_AT_MSA
ADD_ATOMIC_CLAIMS
ADD_SCOPED_INVALIDATION
REDESIGN
REJECT

⸻

26. WHAT MUST NOT BE BUILT BEFORE EVIDENCE EXISTS

No generalized knowledge graph.
No persistent society of agents.
No universal claim ontology.
No generalized semantic invalidation engine.
No learned compute router.
No custom security logic language.
No full event sourcing.
No graph database.
No institution-grade workflow engine.
No automated knowledge promotion.
No autonomous code modification.
No autonomous risk acceptance.

These are future possibilities, not assumptions.

⸻

27. THREE HARDEST RESEARCH PROBLEMS

1. Safe semantic continuity

Can the system determine that a prior conclusion remains valid
after source, dependency, environment or analysis-model changes
without solving an intractable semantic-equivalence problem?

2. Autonomous verification without false independence

Can machine verification produce justified confidence
when models and tools may share hidden assumptions,
implementations, training data and framework models?

3. Demonstrating institutional causality

Can measured improvements be causally attributed to
claims, lineage and invalidation rather than extra compute,
extra context, repeated analysis or better retrieval?

⸻

28. SUCCESS DEFINITION

The project succeeds only if it demonstrates all of the following:

success:
  - prior_results_can_be_reused_safely_in_measurable_cases
  - stale_results_are_detected_with_acceptable_risk
  - the_system_abstains_when_evidence_is_insufficient
  - autonomy_does_not_depend_on_hidden_human_rescue
  - institutional_features_beat_compute_matched_controls
  - benefits_exceed_storage_and_operational_complexity
  - simpler_baselines_cannot_capture_most_of_the_value

The project does not succeed merely because:

* it stores more information,
* it produces more structured reports,
* several models agree,
* a graph can be queried,
* findings persist across commits,
* or a large system outperforms a small system using more compute.

⸻

29. FINAL SENIOR REVIEW REQUEST

request:
  verdict_options:
    - APPROVE_V0_5_FOR_PRE_DESIGN_FREEZE
    - APPROVE_WITH_MAXIMUM_FIVE_REQUIRED_CHANGES
    - NARROW_TO_MSA
    - REDESIGN
    - REJECT
  evaluate:
    - whether_MSA_is_sufficient_to_test_the_primary_hypotheses
    - whether_any_frozen_contract_is_premature
    - whether_the_null_baselines_are_strong_enough
    - whether_compute_and_context_controls_enable_causal_interpretation
    - whether_falsification_first_verification_is_credible
    - whether_the_early_invalidation_probe_retires_risk_soon_enough
    - whether_the_runtime_and_scientific_TCBs_are_minimal
    - whether_the_PoC_can_be_built_without_hidden_human_dependency
  produce:
    - executive_verdict
    - strongest_remaining_criticism
    - fatal_freeze_blockers
    - maximum_five_required_changes
    - minimal_executable_PoC_boundary
    - numerical_threshold_recommendations
    - open_source_component_decisions
    - point_of_no_return_warnings
    - explicit_freeze_recommendation

Review rules:

Do not optimize for agreement.
Attempt to defeat the institutional hypothesis.
Prefer a simpler system whenever evidence does not justify complexity.
Do not recommend generalized claims, graphs, agents, journals
or semantic invalidation merely because they are architecturally elegant.
Do not treat model consensus as independent verification.
Do not reward forced closure over honest abstention.
Do not begin production implementation.

⸻
