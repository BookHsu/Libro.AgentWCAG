# `run_accessibility_audit.py` Refactor Plan

This document inventories the current responsibilities in
`skills/libro-wcag/scripts/run_accessibility_audit.py` and defines the
target module split for TODO section `### 1. 重構 run_accessibility_audit.py`.

## Current Responsibility Blocks

The current script mixes these responsibility areas:

1. CLI parsing and contract enforcement
2. Scanner runtime resolution, preflight checks, retry logic, and subprocess execution
3. Policy preset/bundle/config loading and effective policy assembly
4. Baseline diff, debt state, waiver review, debt trend, and evidence hashing
5. Advanced CI gate evaluation for risk calibration, replay verification, and scanner stability
6. Artifact paths, schema staging, compact summary generation, and stdout output
7. Main orchestration for loading inputs, running scanners, normalizing reports, applying fixes, gating, and exit code selection

## Constants Inventory and Ownership

### Keep in `run_accessibility_audit.py`

- `DEFAULT_TIMEOUT_SECONDS`
- `SEVERITY_RANK`
- `FAIL_ON_EXIT_CODES`
- `FINDING_SORT_MODES`

These are still owned by CLI parsing and final exit-threshold orchestration.

### Move to `scanner_runtime.py`

- `DEFAULT_SCANNER_RETRY_ATTEMPTS`
- `DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS`
- `MAX_SCANNER_RETRY_BACKOFF_SECONDS`
- `ALLOWED_URL_SCHEMES`
- `NPX_EXECUTABLE`
- `PREFLIGHT_TOOL_CHECKS`

### Move to `policy_controls.py`

- `POLICY_PRESETS`
- `POLICY_BUNDLES`
- `ALLOWED_POLICY_CONFIG_KEYS`
- `POLICY_CONFIG_KEY_SPECS`

### Move to `baseline_governance.py`

- `BASELINE_TARGET_NORMALIZATION_MODES`
- `BASELINE_SELECTOR_CANONICALIZATION_MODES`
- `BASELINE_EVIDENCE_MODES`
- `WAIVER_EXPIRY_MODES`
- `WAIVER_EXPIRY_EXIT_CODE`
- `DEBT_STATE_NEW`
- `DEBT_STATE_ACCEPTED`
- `DEBT_STATE_RETIRED`
- `DEBT_STATE_REGRESSED`
- `DEBT_WAIVER_REQUIRED_FIELDS`
- `DEBT_TREND_SCHEMA_VERSION`
- `DEFAULT_DEBT_TREND_WINDOW`

### Move to `advanced_gates.py`

- `RISK_CALIBRATION_MODES`
- `RISK_CALIBRATION_SCHEMA_VERSION`
- `RISK_CALIBRATION_EXIT_CODE`
- `RISK_CALIBRATION_MIN_SAMPLES`
- `RISK_CALIBRATION_PRECISION_THRESHOLD`
- `HIGH_SEVERITY_LEVELS`
- `REPLAY_VERIFICATION_SCHEMA_VERSION`
- `REPLAY_VERIFICATION_EXIT_CODE`
- `SCANNER_STABILITY_MODES`
- `SCANNER_STABILITY_SCHEMA_VERSION`
- `SCANNER_STABILITY_EXIT_CODE`
- `DEFAULT_SCANNER_STABILITY_WINDOW`
- `DEFAULT_SCANNER_STABILITY_MAX_VARIANCE`

### Move to `report_artifacts.py`

- `REPORT_SCHEMA_NAME`
- `REPORT_SCHEMA_VERSION`
- `REPORT_SCHEMA_FILENAME`
- `REPORT_SCHEMA_SOURCE_PATH`

## Helper Inventory and Dependency Clusters

### Scanner runtime cluster

- `_resolve_npx_executable()`
- `_extract_version_line()`
- `_build_version_provenance()`
- `_run_command()`
- `_is_transient_scanner_error()`
- `_run_scanner_with_retry()`
- `_try_run_axe()`
- `_try_run_lighthouse()`
- `_resolve_target_for_scanners()`
- `_tool_available()`
- `run_preflight_checks()`

Call dependencies:

- `run_preflight_checks()` uses `_tool_available()`, `_run_command()`,
  `_extract_version_line()`, `_build_version_provenance()`
- `_try_run_axe()` and `_try_run_lighthouse()` use `_run_command()`
- `_run_scanner_with_retry()` uses `_is_transient_scanner_error()`

### Policy controls cluster

- `_load_policy_config()`
- `_normalize_rule_list()`
- `_resolve_policy_preset()`
- `_resolve_policy_bundle()`
- `_policy_presets_payload()`
- `_policy_config_keys_payload()`
- `_build_effective_policy()`
- `_policy_value_source()`
- `_build_rule_sources()`
- `_resolve_effective_policy_path()`
- `_find_rule_policy_overlaps()`
- `_merge_rule_list()`

Call dependencies:

- `_build_effective_policy()` uses `_policy_value_source()`,
  `_build_rule_sources()`
- `_load_policy_config()` depends on policy key constants

### Baseline governance cluster

- `_utc_timestamp()`
- `_sha256_text()`
- `_sha256_file()`
- `_build_baseline_evidence_material()`
- `_compute_report_evidence_hash()`
- `_verify_baseline_report_evidence()`
- `_build_run_baseline_evidence()`
- `_parse_waiver_timestamp()`
- `_validate_debt_waivers()`
- `_load_baseline_report()`
- `_coerce_non_negative_int()`
- `_build_debt_trend_counts()`
- `_empty_debt_trend_counts()`
- `_sanitize_debt_trend_point()`
- `_derive_baseline_point_from_legacy_report()`
- `_extract_historical_debt_trend_points()`
- `_build_debt_trend_payload()`
- `_finding_signature()`
- `_normalize_signature_target()`
- `_canonicalize_signature_selector()`
- `_build_baseline_signature_config()`
- `_finding_signature_with_config()`
- `_unresolved_finding_signatures()`
- `_build_baseline_diff()`
- `_build_debt_transition_summary()`
- `_build_debt_waiver_index()`
- `_evaluate_debt_waiver_review()`
- `_tag_findings_with_debt_state()`

Call dependencies:

- Evidence helpers depend on `_unresolved_finding_signatures()`,
  `_finding_signature_with_config()`, `_sha256_text()`, `_utc_timestamp()`
- Debt trend helpers depend on `_coerce_non_negative_int()`,
  `_build_debt_trend_counts()`, `_empty_debt_trend_counts()`
- Baseline diff helpers depend on `_finding_signature_with_config()`
- Waiver review depends on `_parse_waiver_timestamp()`,
  `_build_debt_waiver_index()`

### Advanced gate cluster

- `_is_actionable_outcome()`
- `_extract_rule_signals_from_report()`
- `_merge_rule_signals()`
- `_load_risk_calibration_source()`
- `_evaluate_risk_calibration()`
- `_extract_available_scanners()`
- `_collect_replay_signature_rows()`
- `_load_replay_source_report()`
- `_build_replay_diff_markdown()`
- `_build_replay_verification_summary()`
- `_normalize_stability_scanner()`
- `_stability_signature()`
- `_parse_stability_signature()`
- `_sanitize_scanner_stability_row()`
- `_sanitize_scanner_stability_point()`
- `_extract_scanner_stability_rows()`
- `_normalize_scanner_stability_bounds()`
- `_extract_historical_scanner_stability_points()`
- `_load_stability_baseline_payload()`
- `_build_scanner_stability_payload()`

Call dependencies:

- Risk calibration depends on `_load_risk_calibration_source()`,
  `_extract_rule_signals_from_report()`, `_merge_rule_signals()`,
  `_is_actionable_outcome()`
- Replay verification depends on `_extract_available_scanners()`,
  `_collect_replay_signature_rows()`, `_load_replay_source_report()`,
  `_build_replay_diff_markdown()`
- Scanner stability depends on `_normalize_stability_scanner()`,
  `_stability_signature()`, `_parse_stability_signature()`,
  `_sanitize_scanner_stability_row()`, `_sanitize_scanner_stability_point()`,
  `_extract_scanner_stability_rows()`, `_normalize_scanner_stability_bounds()`,
  `_extract_historical_scanner_stability_points()`,
  `_load_stability_baseline_payload()`

### Artifact and output cluster

- `_remove_if_exists()`
- `_build_artifact_manifest()`
- `_collect_scanner_rule_ids()`
- `_build_scanner_capabilities()`
- `_rebuild_summary()`
- `_coerce_positive_int()`
- `_finding_sort_key()`
- `_sort_report_findings()`
- `_cap_report_findings()`
- `_build_compact_summary()`
- `_stage_report_schema_artifact()`
- `_report_to_sarif()`

Call dependencies:

- `_build_artifact_manifest()` uses `_utc_timestamp()`, `_sha256_file()`
- `_build_scanner_capabilities()` uses `_collect_scanner_rule_ids()`
- `_sort_report_findings()` uses `_finding_sort_key()`

### Main orchestration / gate resolution

- `_apply_rule_policy()`
- `_sarif_level_from_severity()`
- `_resolve_fail_threshold()`
- `parse_args()`
- `main()`

## Purity and Side-Effect Classification

### Pure logic helpers

- `_extract_version_line()`
- `_build_version_provenance()`
- `_is_transient_scanner_error()`
- `_normalize_rule_list()`
- `_policy_presets_payload()`
- `_policy_config_keys_payload()`
- `_build_effective_policy()`
- `_policy_value_source()`
- `_build_rule_sources()`
- `_find_rule_policy_overlaps()`
- `_merge_rule_list()`
- `_collect_scanner_rule_ids()`
- `_coerce_non_negative_int()`
- `_build_debt_trend_counts()`
- `_empty_debt_trend_counts()`
- `_is_actionable_outcome()`
- `_extract_rule_signals_from_report()`
- `_merge_rule_signals()`
- `_finding_sort_key()`
- `_cap_report_findings()`
- `_apply_rule_policy()`
- `_sarif_level_from_severity()`
- `_finding_signature()`
- `_normalize_signature_target()`
- `_canonicalize_signature_selector()`
- `_build_baseline_signature_config()`
- `_finding_signature_with_config()`
- `_unresolved_finding_signatures()`
- `_build_baseline_diff()`
- `_build_debt_transition_summary()`
- `_extract_available_scanners()`
- `_collect_replay_signature_rows()`
- `_normalize_stability_scanner()`
- `_stability_signature()`
- `_parse_stability_signature()`
- `_resolve_fail_threshold()`

### I/O helpers

- `_run_command()`
- `_try_run_axe()`
- `_try_run_lighthouse()`
- `run_preflight_checks()`
- `_remove_if_exists()`
- `_sha256_file()`
- `_build_artifact_manifest()`
- `_load_policy_config()`
- `_load_baseline_report()`
- `_load_risk_calibration_source()`
- `_load_replay_source_report()`
- `_build_replay_diff_markdown()`
- `_load_stability_baseline_payload()`
- `_stage_report_schema_artifact()`

### Orchestration helpers

- `_run_scanner_with_retry()`
- `_build_run_baseline_evidence()`
- `_build_debt_trend_payload()`
- `_build_scanner_capabilities()`
- `_rebuild_summary()`
- `_sort_report_findings()`
- `_build_compact_summary()`
- `_evaluate_risk_calibration()`
- `_build_replay_verification_summary()`
- `_build_scanner_stability_payload()`
- `parse_args()`
- `main()`

## Functions That Write Files

- `_try_run_axe()` writes `axe.raw.json` through axe CLI
- `_try_run_lighthouse()` writes `lighthouse.raw.json` through Lighthouse CLI
- `_build_artifact_manifest()` writes `artifact-manifest.json`
- `_build_replay_diff_markdown()` writes `replay-diff.md`
- `_stage_report_schema_artifact()` stages schema into `out/schemas/...`
- `main()` writes:
  - `replay-summary.json`
  - `scanner-stability.json`
  - `debt-trend.json`
  - `wcag-report.json`
  - `wcag-report.md`
  - `wcag-report.sarif`
  - effective policy artifact
  - fix diff/snapshot artifacts via `auto_fix`

## Functions That Directly Invoke Subprocess

- `_run_command()`

Indirect subprocess call sites:

- `run_preflight_checks()`
- `_try_run_axe()`
- `_try_run_lighthouse()`

## CLI Contract Fields That Must Not Change

### Flags

- Scanner runtime: `--target`, `--timeout`, `--skip-axe`, `--skip-lighthouse`,
  `--mock-axe-json`, `--mock-lighthouse-json`, `--preflight-only`,
  `--scanner-retry-attempts`, `--scanner-retry-backoff-seconds`
- Policy controls: `--report-format`, `--fail-on`, `--include-rule`,
  `--ignore-rule`, `--policy-config`, `--policy-preset`, `--policy-bundle`,
  `--list-policy-presets`, `--list-policy-config-keys`,
  `--strict-rule-overlap`, `--explain-policy`, `--write-effective-policy`
- Baseline governance: `--baseline-report`, `--fail-on-new-only`,
  `--baseline-include-target`, `--baseline-target-normalization`,
  `--baseline-selector-canonicalization`, `--baseline-evidence-mode`,
  `--waiver-expiry-mode`, `--debt-trend-window`
- Advanced gates: `--risk-calibration-source`,
  `--risk-calibration-mode`, `--replay-verify-from`, `--stability-baseline`,
  `--stability-mode`
- Output controls: `--summary-only`, `--sort-findings`, `--max-findings`,
  `--output-dir`, `--output-language`, execution-mode related flags

### Exit codes

- Severity gates: `42`, `43`, `44`
- Waiver expiry: `45`
- Risk calibration: `46`
- Replay verification: `47`
- Scanner stability: `48`

### Artifact names and paths

- `wcag-report.json`
- `wcag-report.md`
- `wcag-report.sarif`
- `artifact-manifest.json`
- `debt-trend.json`
- `scanner-stability.json`
- `replay-summary.json`
- `replay-diff.md`
- `schemas/wcag-report-1.0.0.schema.json`
- `effective-policy.json` when requested
- fix diff/snapshot artifact names emitted today

### Stable output structures

- `report_schema.version`
- `run_meta.preflight`
- `run_meta.policy_effective`
- `run_meta.baseline_diff`
- finding-level `debt_state`
- `run_meta.debt_trend`
- `run_meta.baseline_evidence`
- `run_meta.risk_calibration`
- `run_meta.replay_verification`
- `run_meta.scanner_stability`
- `run_meta.artifact_manifest`
- `summary_only` compact JSON payload shape

## `run_meta` Assembly Responsibilities

The following helpers or blocks contribute directly to `run_meta`:

- `run_preflight_checks()` populates `run_meta.preflight`
- `_build_effective_policy()` populates `run_meta.policy_effective`
- `_build_baseline_diff()` populates `run_meta.baseline_diff`
- `_tag_findings_with_debt_state()` populates finding-level `debt_state`
- `_build_run_baseline_evidence()` populates `run_meta.baseline_evidence`
- `_evaluate_risk_calibration()` populates `run_meta.risk_calibration`
- `_build_scanner_capabilities()` populates `run_meta.scanner_capabilities`
- `_build_replay_verification_summary()` populates `run_meta.replay_verification`
- `_build_scanner_stability_payload()` populates `run_meta.scanner_stability`
- `_build_debt_trend_payload()` populates `run_meta.debt_trend`
- `_build_artifact_manifest()` populates `run_meta.artifact_manifest`
- `main()` appends operational notes, gating metadata, and file paths

## Before/After Function Mapping

| Current owner | Target owner |
| --- | --- |
| scanner runtime helpers | `scanner_runtime.py` |
| policy resolution helpers | `policy_controls.py` |
| baseline diff / waiver / debt trend / evidence helpers | `baseline_governance.py` |
| risk / replay / stability helpers | `advanced_gates.py` |
| schema staging / manifest / compact summary / output helpers | `report_artifacts.py` |
| `parse_args()`, `_resolve_fail_threshold()`, `main()` | `run_accessibility_audit.py` |

## Target Module Boundaries

### `scanner_runtime.py`

Owns binary resolution, command execution, preflight checks, target scanner
resolution, retry handling, and raw scanner execution.

### `policy_controls.py`

Owns policy presets/bundles/config validation, rule overlap checks, effective
policy assembly, and policy discovery payloads.

### `baseline_governance.py`

Owns baseline report loading, signature normalization, baseline diffing, debt
state transitions, waiver validation/review, trend history management, and
baseline evidence hashing/verification.

### `advanced_gates.py`

Owns risk calibration evidence loading/evaluation, replay verification, scanner
stability history loading/comparison, and advanced gate decision payloads.

### `report_artifacts.py`

Owns schema staging, artifact manifest generation, output-path helpers, finding
sorting/capping, compact summary payloads, summary-only stdout serialization,
and SARIF/report output helpers.

### `shared_constants.py`

Only create if cross-module constants produce duplicated imports or would force
cycles. Candidate contents: report schema version, common debt state names, and
shared timestamp/hash helpers.

## Planned Import Direction

The import direction should stay acyclic:

1. `shared_constants.py` imports nothing from feature modules
2. `scanner_runtime.py`, `policy_controls.py`, `baseline_governance.py`,
   `advanced_gates.py`, and `report_artifacts.py` may import
   `shared_constants.py`
3. `advanced_gates.py` may depend on baseline signature helpers if those are
   promoted into `baseline_governance.py`, but not the reverse
4. `report_artifacts.py` may depend on shared hashing/timestamp helpers, but
   should not import scanner/policy/baseline gate modules
5. `run_accessibility_audit.py` imports all feature modules and remains the CLI
   entrypoint

## Non-Negotiable Compatibility List

- Keep `python skills/libro-wcag/scripts/run_accessibility_audit.py` as
  the supported invocation path
- Preserve existing flag names, defaults, and argparse help text where possible
- Preserve all current exit codes
- Preserve current artifact filenames and schema version
- Preserve compact summary JSON structure for `--summary-only`
- Preserve report schema and `run_meta` field names consumed by tests and docs
- Preserve Windows `npx.cmd` fallback behavior
- Preserve scanner timeout, missing-tool, and runtime-error classification

## Files Expected to Change During Refactor

- `skills/libro-wcag/scripts/run_accessibility_audit.py`
- `skills/libro-wcag/scripts/scanner_runtime.py`
- `skills/libro-wcag/scripts/policy_controls.py`
- `skills/libro-wcag/scripts/baseline_governance.py`
- `skills/libro-wcag/scripts/advanced_gates.py`
- `skills/libro-wcag/scripts/report_artifacts.py`
- `skills/libro-wcag/scripts/shared_constants.py` if needed
- `skills/libro-wcag/scripts/tests/test_runner.py`
- `skills/libro-wcag/scripts/tests/test_cli_flows.py`
- `skills/libro-wcag/scripts/tests/test_real_scanner_ci_lane.py`

## Primary Refactor Risks

1. Existing tests import private helpers directly from the main module, so
   careless extraction will break test contracts even when runtime behavior is
   unchanged.
2. `main()` currently assembles `run_meta`, artifact writes, and gate decisions
   in a single linear flow, so moving helpers without clear data contracts can
   cause subtle output drift.
3. Several helpers cross module boundaries through shared concepts such as
   signatures, timestamps, hash material, and scanner capability metadata.
4. Output compatibility is broader than JSON report files because docs and CI
   examples reference artifact names and paths directly.
