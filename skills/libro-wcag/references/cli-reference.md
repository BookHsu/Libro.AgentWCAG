# CLI Reference

Complete option reference for `run_accessibility_audit.py`. Use this when invoking the audit CLI directly or when an adapter needs to pass advanced options.

## Core Parameters

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--target` | path or URL | *(required)* | Local file path or URL to audit. Local paths are normalized to `file://` URLs before scanner execution. |
| `--task-mode` | `create`, `modify` | `modify` | `create` = draft/generated target; `modify` = existing target. |
| `--execution-mode` | `audit-only`, `suggest-only`, `apply-fixes` | `suggest-only` | Controls whether fixes are proposed or applied. |
| `--wcag-version` | `2.0`, `2.1`, `2.2` | `2.1` | WCAG standard version to audit against. |
| `--conformance-level` | `A`, `AA`, `AAA` | `AA` | Target conformance level. |
| `--output-language` | `en`, `zh-TW` | `zh-TW` | Report language. Other BCP-47 values fall back to `en`. |
| `--output-dir` | path | `out` | Directory for report output files. |
| `--timeout` | seconds (int) | `120` | Global timeout for scanner execution. |

## Policy & Rule Filtering

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--policy-bundle` | `strict-web-app`, `legacy-content`, `marketing-site` | *(none)* | Pre-built policy bundle. |
| `--policy-preset` | `strict`, `balanced`, `legacy` | *(none)* | Named policy preset. |
| `--policy-config` | JSON file path | *(none)* | Custom policy config with `report_format`, `fail_on`, `include_rules`, `ignore_rules`. |
| `--fail-on` | `critical`, `serious`, `moderate` | *(none)* | Fail the run if findings at or above this severity exist. |
| `--include-rule` | rule ID (repeatable) | *(all)* | Only include these normalized rule IDs. |
| `--ignore-rule` | rule ID (repeatable) | *(none)* | Exclude these normalized rule IDs. |
| `--strict-rule-overlap` | flag | `false` | Fail when a rule appears in both include and ignore lists. |
| `--explain-policy` | flag | `false` | Include the effective merged policy in report metadata. |
| `--write-effective-policy` | flag | `false` | Write merged policy JSON alongside the report. |
| `--list-policy-presets` | flag | — | Print available presets and exit. |
| `--list-policy-config-keys` | flag | — | Print supported config keys and exit. |

## Baseline & Debt Management

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--baseline-report` | JSON file path | *(none)* | Prior report for debt trend comparison. |
| `--baseline-include-target` | flag | `false` | Include normalized target in baseline signatures. |
| `--baseline-target-normalization` | mode string | `none` | Target normalization strategy for baseline matching. |
| `--baseline-selector-canonicalization` | mode string | `none` | Selector canonicalization for baseline. |
| `--baseline-evidence-mode` | `none`, `hash`, `hash-chain` | `none` | Evidence hashing for baseline drift detection. |
| `--waiver-expiry-mode` | `ignore`, `warn`, `fail` | `warn` | Behavior when debt waivers expire. |
| `--fail-on-new-only` | flag | `false` | Only fail on newly introduced findings. |
| `--debt-trend-window` | int | `5` | Number of historical data points to retain for debt trend analysis. |

## Advanced Gates

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--risk-calibration-source` | JSON path | *(none)* | Prior report for risk calibration. |
| `--risk-calibration-mode` | `off`, `warn`, `strict` | `off` | Risk calibration enforcement level. |
| `--replay-verify-from` | directory path | *(none)* | Directory with prior run artifacts for replay verification. |
| `--stability-baseline` | JSON path | *(none)* | Prior stability baseline. |
| `--stability-mode` | `off`, `warn`, `fail` | `off` | Stability enforcement level. |

## Report Format & Output

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--report-format` | `json`, `sarif` | *(none)* | Generate an additional SARIF report alongside the standard JSON output. |
| `--summary-only` | flag | `false` | Print a compact JSON summary to stdout instead of full report files. |
| `--max-findings` | int | *(unlimited)* | Limit the number of findings in output. |
| `--sort-findings` | `severity`, `rule`, `target` | `severity` | Sort order for findings. |

## Scanner Control

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--skip-axe` | flag | `false` | Skip the axe scanner. |
| `--skip-lighthouse` | flag | `false` | Skip the Lighthouse scanner. |
| `--scanner-retry-attempts` | int (≥1) | `1` | Number of retry attempts per scanner. |
| `--scanner-retry-backoff-seconds` | float | *(default)* | Backoff between scanner retries. |
| `--mock-axe-json` | JSON file path | *(none)* | Use mock axe output (testing only). |
| `--mock-lighthouse-json` | JSON file path | *(none)* | Use mock Lighthouse output (testing only). |

## Utility

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--dry-run` | flag | `false` | Validate inputs without running scanners. |
| `--preflight-only` | flag | `false` | Check runtime tooling availability and exit. |

## Examples

```bash
# Basic audit with defaults
python scripts/run_accessibility_audit.py --target index.html

# Strict policy bundle with failure gate
python scripts/run_accessibility_audit.py \
  --target https://example.com \
  --policy-bundle strict-web-app \
  --fail-on serious

# Baseline comparison with debt trend
python scripts/run_accessibility_audit.py \
  --target index.html \
  --baseline-report prior-report.json \
  --debt-trend-window 10

# SARIF output for CI integration
python scripts/run_accessibility_audit.py \
  --target index.html \
  --report-format sarif

# Summary-only for scripted pipelines
python scripts/run_accessibility_audit.py \
  --target index.html \
  --summary-only
```
