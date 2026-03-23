# Resilient Run Patterns

This guide documents resilient CLI patterns for `run_accessibility_audit.py` in CI or local automation.

## New runtime resilience flags

- `--scanner-retry-attempts <N>`: number of attempts per scanner (`axe`, `lighthouse`) for transient failures.
- `--scanner-retry-backoff-seconds <seconds>`: initial backoff delay. Each retry doubles delay up to the internal cap.

`run_meta` now includes:

- `retry_policy`: configured attempts and backoff.
- `scanner_retries`: per-scanner attempt count, retry count, and final status.

## CI pattern: audit-only

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target https://example.com \
  --execution-mode audit-only \
  --output-language en \
  --output-dir out/audit-only \
  --scanner-retry-attempts 2 \
  --scanner-retry-backoff-seconds 1
```

Use when you only need findings and report artifacts, without remediation actions.

## CI pattern: suggest-only

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target https://example.com \
  --execution-mode suggest-only \
  --output-language en \
  --output-dir out/suggest-only \
  --scanner-retry-attempts 3 \
  --scanner-retry-backoff-seconds 1
```

Use when transient scanner/runtime issues are common and you still want stable suggestion output.

## CI pattern: apply-fixes (local target)

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target docs/testing/realistic-sample/mixed-findings.html \
  --execution-mode apply-fixes \
  --output-language en \
  --output-dir out/apply-fixes \
  --scanner-retry-attempts 3 \
  --scanner-retry-backoff-seconds 1
```

Use for deterministic local-file remediation in supported file types.

## Deterministic smoke pattern with mock payloads

When scanner runtimes are not guaranteed in CI:

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target docs/testing/realistic-sample/mixed-findings.html \
  --execution-mode apply-fixes \
  --output-language en \
  --output-dir out/mock-smoke \
  --mock-axe-json docs/testing/realistic-sample/scanner-fixtures/axe.mock.json \
  --mock-lighthouse-json docs/testing/realistic-sample/scanner-fixtures/lighthouse.mock.json
```

This bypasses runtime scanner invocation while keeping contract/report behavior stable.

## Reproducible dependency-audit lane

Run dependency checks before scanner execution to reduce supply-chain drift.

### Local lane

```powershell
python -m pip install --upgrade pip
python -m pip install pyyaml pip-audit
python -m pip-audit --strict --desc

mkdir -p .ci/scanner-toolchain
npm install --prefix .ci/scanner-toolchain --package-lock-only @axe-core/cli@4.10.2 lighthouse@12.3.0
npm audit --prefix .ci/scanner-toolchain --audit-level=high --json > out/dependency/npm-audit.json
```

### CI lane policy (pass/fail)

- `pip-audit --strict` must return exit code `0` to pass.
- `npm audit --audit-level=high` must return exit code `0` to pass.
- If either audit fails, stop WCAG scan steps and open remediation ticket with lockfile diff + audit output.

### Remediation workflow

1. Patch vulnerable packages by updating pinned versions in lock artifacts.
2. Re-run dependency audit lane until both checks pass.
3. Re-run `--preflight-only` and retain updated `version_provenance` metadata.
4. Continue WCAG scanner lane only after dependency audit lane is green.

## CI policy controls

Use policy flags to gate CI outcomes and tune rule scope without code changes:

- `--report-format json|sarif`: choose machine-readable output for pipelines and PR annotation tooling.
- `--fail-on critical|serious|moderate`: return deterministic non-zero exit code when unresolved findings meet the threshold.
- `--include-rule` / `--ignore-rule`: include or suppress normalized rule ids (repeatable).
- `--policy-config <path.json>`: load `report_format`, `fail_on`, `include_rules`, and `ignore_rules` from a JSON file.

### Example: SARIF + severity gate

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target docs/testing/realistic-sample/mixed-findings.html \
  --execution-mode suggest-only \
  --output-dir out/ci-policy \
  --report-format sarif \
  --fail-on serious
```

### Example: project policy config

```json
{
  "report_format": "json",
  "fail_on": "moderate",
  "include_rules": ["image-alt", "button-name"],
  "ignore_rules": ["meta-viewport"]
}
```


## Baseline diff mode

Use baseline diff mode to gate only newly introduced accessibility debt while allowing pre-existing debt to be tracked separately.

- `--baseline-report <wcag-report.json>`: load a prior committed report as baseline.
- `--fail-on-new-only`: with `--fail-on`, evaluate only newly introduced unresolved findings compared to baseline.

### Example: fail only on new serious debt

```powershell
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target docs/testing/realistic-sample/mixed-findings.html \
  --execution-mode suggest-only \
  --output-dir out/baseline-gate \
  --fail-on serious \
  --baseline-report .ci/wcag-baseline.json \
  --fail-on-new-only
```

The output report includes `run_meta.baseline_diff` with introduced/resolved/persistent counts.

## GitHub Actions integration (artifacts + PR annotation)

A reusable workflow example is available at `docs/examples/ci/github-actions-wcag-ci-sample.yml`.
For the formal live real-scanner PR gate and evidence contract, see `docs/release/real-scanner-ci-lane.md` and `.github/workflows/libro-agent-wcag-real-scanner.yml`.

Key integration points:

- Upload `wcag-report.json`, `wcag-report.md`, and `wcag-report.sarif` as build artifacts.
- Set `retention-days` for report retention policy.
- Use SARIF upload to annotate pull requests in GitHub code scanning UI.


## Triage workflow (`new`, `persistent`, `resolved`)

Use `run_meta.baseline_diff` and the latest report findings to classify each unresolved issue:

- `new`: signature appears in `introduced_signatures`.
- `persistent`: signature appears in `persistent_signatures`.
- `resolved`: signature appears in `resolved_signatures`.

### Sample review checklist

- Verify scope and ownership: confirm file path, feature area, and assignee.
- Validate severity and impact: check `rule_id`, WCAG citation, and scanner evidence.
- Confirm fix strategy: `apply-fixes`, assisted remediation, or manual-only follow-up.
- Capture verification evidence: include rerun result or before/after artifact path.
- Record decision status: `new`, `persistent`, or `resolved` in PR or issue tracker.
- For `persistent` debt, review `run_meta.baseline_diff.waiver_review` and enforce `--waiver-expiry-mode fail` on release lanes when renewal evidence is missing/expired.

### Ownership handoff checklist

- Triage owner prepares handoff note with `rule_id`, target selector, severity, and status.
- Receiving owner acknowledges ETA and risk level (`critical`, `serious`, `moderate`, `minor`).
- Add acceptance criteria for closure (expected scanner result and artifact paths).
- After implementation, rerun audit and update baseline snapshot if debt was intentionally accepted.
- Close handoff only when report status and issue tracker state are aligned.

## Risk calibration gate

Use historical evidence to suppress noisy high-severity triage drift:

- `--risk-calibration-source <path>` accepts a report/artifact JSON file or a directory of report JSON files.
- `--risk-calibration-mode warn` records downgrade notes when evidence is missing/stale/conflicting and continues the run.
- `--risk-calibration-mode strict` fails with exit code `46` when currently triggered high-severity rules are statistically unstable.

Example release-lane command:

```bash
python skills/libro-agent-wcag/scripts/run_accessibility_audit.py \
  --target https://example.com \
  --output-dir out/risk-calibration \
  --fail-on serious \
  --risk-calibration-source .ci/risk-calibration \
  --risk-calibration-mode strict
```

The run writes calibration evidence to `run_meta.risk_calibration`, including fallback reason and strict gate status.
