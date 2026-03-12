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

A reusable workflow example is available at `docs/release/github-actions-wcag-ci-sample.yml`.

Key integration points:

- Upload `wcag-report.json`, `wcag-report.md`, and `wcag-report.sarif` as build artifacts.
- Set `retention-days` for report retention policy.
- Use SARIF upload to annotate pull requests in GitHub code scanning UI.

