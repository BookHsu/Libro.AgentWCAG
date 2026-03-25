#!/usr/bin/env python3
"""Run axe and Lighthouse scans, then emit normalized WCAG outputs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_fix import (
    apply_report_fixes,
    supports_apply_fixes_target,
    target_to_local_path,
    write_diff,
    write_snapshot,
)
from advanced_gates import (
    DEFAULT_SCANNER_STABILITY_WINDOW,
    HIGH_SEVERITY_LEVELS,
    RISK_CALIBRATION_EXIT_CODE,
    RISK_CALIBRATION_MODES,
    SCANNER_STABILITY_MODES,
    _build_replay_diff_markdown,
    _build_replay_verification_summary,
    _build_scanner_stability_payload,
    _evaluate_risk_calibration,
    _load_replay_source_report,
    _resolve_advanced_gate_exit_code,
)
from baseline_governance import (
    BASELINE_EVIDENCE_MODES,
    BASELINE_SELECTOR_CANONICALIZATION_MODES,
    BASELINE_TARGET_NORMALIZATION_MODES,
    DEBT_STATE_ACCEPTED,
    DEBT_STATE_NEW,
    DEBT_STATE_REGRESSED,
    DEBT_STATE_RETIRED,
    DEBT_TREND_SCHEMA_VERSION,
    DEBT_WAIVER_REQUIRED_FIELDS,
    WAIVER_EXPIRY_EXIT_CODE,
    WAIVER_EXPIRY_MODES,
    _build_baseline_diff,
    _build_baseline_signature_config,
    _build_debt_transition_summary,
    _build_debt_trend_payload,
    _build_run_baseline_evidence,
    _coerce_non_negative_int,
    _compute_report_evidence_hash,
    _finding_signature_with_config,
    _empty_debt_trend_counts,
    _evaluate_debt_waiver_review,
    _load_baseline_report,
    _tag_findings_with_debt_state,
    _validate_debt_waivers,
)
from policy_controls import (
    ALLOWED_POLICY_CONFIG_KEYS,
    POLICY_BUNDLES,
    POLICY_CONFIG_KEY_SPECS,
    POLICY_PRESETS,
    _build_effective_policy,
    _build_rule_sources,
    _find_rule_policy_overlaps,
    _load_policy_config,
    _merge_rule_list,
    _normalize_rule_list,
    _policy_config_keys_payload,
    _policy_presets_payload,
    _policy_value_source,
    _resolve_effective_policy_path,
    _resolve_policy_bundle,
    _resolve_policy_preset,
)
from report_artifacts import (
    _build_artifact_manifest,
    _build_compact_summary,
    _build_report_output_paths,
    _collect_artifact_paths,
    _emit_summary_only_stdout,
    _stage_report_schema_artifact,
)
from scanner_runtime import (
    DEFAULT_SCANNER_RETRY_ATTEMPTS,
    DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS,
    MAX_SCANNER_RETRY_BACKOFF_SECONDS,
    NPX_EXECUTABLE,
    PREFLIGHT_TOOL_CHECKS,
    _build_scanner_capabilities,
    _build_version_provenance,
    _extract_version_line,
    _is_transient_scanner_error,
    _resolve_npx_executable,
    _resolve_target_for_scanners,
    _run_command,
    _run_scanner_with_retry,
    _tool_available,
    _try_run_axe,
    _try_run_lighthouse,
    run_preflight_checks,
)
from shared_constants import REPORT_SCHEMA_VERSION, get_product_provenance
from wcag_workflow import normalize_report, resolve_contract, to_markdown_table, write_report_files

DEFAULT_TIMEOUT_SECONDS = 120
SEVERITY_RANK = {"critical": 4, "serious": 3, "moderate": 2, "minor": 1, "info": 0}
FAIL_ON_EXIT_CODES = {"critical": 42, "serious": 43, "moderate": 44}
FINDING_SORT_MODES = {"severity", "rule", "target"}
DEFAULT_DEBT_TREND_WINDOW = 5
def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()

def _rebuild_summary(report: dict[str, Any]) -> None:
    findings = report.get('findings', [])
    fixes = report.get('fixes', [])
    summary = report.setdefault('summary', {})
    summary['total_findings'] = len(findings)
    summary['fixed_findings'] = sum(1 for item in findings if item.get('status') == 'fixed')
    summary['auto_fixed_count'] = summary['fixed_findings']
    summary['needs_manual_review'] = sum(1 for item in findings if item.get('status') == 'needs-review')
    summary['manual_required_count'] = sum(1 for item in findings if item.get('manual_review_required'))
    summary.setdefault('diff_summary', [])
    summary.setdefault('before_after_targets', [])
    summary.setdefault('change_summary', [])
    summary.setdefault('fix_blockers', [])
    summary['remediation_lifecycle'] = {
        'planned': sum(1 for item in fixes if item.get('status') == 'planned'),
        'implemented': sum(1 for item in fixes if item.get('status') == 'implemented'),
        'verified': sum(1 for item in fixes if item.get('status') == 'verified'),
        'manual_review_required': sum(1 for item in fixes if item.get('manual_review_required')),
    }



def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float) and value.is_integer():
        return int(value) if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            parsed = int(text)
            return parsed if parsed > 0 else None
    return None


def _finding_sort_key(finding: dict[str, Any], sort_mode: str) -> tuple[Any, ...]:
    severity = str(finding.get('severity', 'info'))
    severity_rank = SEVERITY_RANK.get(severity, 0)
    rule_id = str(finding.get('rule_id', ''))
    target = str(finding.get('changed_target', ''))
    source = str(finding.get('source', ''))
    issue_id = str(finding.get('id', ''))
    source_line = _coerce_positive_int(finding.get('source_line')) or 10**9
    source_column = _coerce_positive_int(finding.get('source_column')) or 10**9

    if sort_mode == 'rule':
        return (rule_id, target, -severity_rank, source_line, source_column, source, issue_id)
    if sort_mode == 'target':
        return (target, rule_id, -severity_rank, source_line, source_column, source, issue_id)
    return (-severity_rank, rule_id, target, source_line, source_column, source, issue_id)


def _sort_report_findings(report: dict[str, Any], sort_mode: str) -> None:
    findings = sorted(
        report.get('findings', []),
        key=lambda item: _finding_sort_key(item, sort_mode),
    )
    report['findings'] = findings


def _cap_report_findings(report: dict[str, Any], max_findings: int) -> dict[str, int]:
    if max_findings <= 0:
        raise ValueError('--max-findings must be >= 1')

    findings = report.get('findings', [])
    before_count = len(findings)
    if before_count <= max_findings:
        return {'before': before_count, 'after': before_count, 'truncated': 0}

    capped = findings[:max_findings]
    kept_ids = {item.get('id') for item in capped}
    report['findings'] = capped
    report['fixes'] = [item for item in report.get('fixes', []) if item.get('finding_id') in kept_ids]
    report['citations'] = [item for item in report.get('citations', []) if item.get('finding_id') in kept_ids]

    summary = report.setdefault('summary', {})
    summary['change_summary'] = [
        item for item in summary.get('change_summary', []) if item.get('finding_id') in kept_ids
    ]
    summary['fix_blockers'] = [
        item for item in summary.get('fix_blockers', []) if item.get('finding_id') in kept_ids
    ]
    _rebuild_summary(report)
    return {'before': before_count, 'after': len(capped), 'truncated': before_count - len(capped)}

def _apply_rule_policy(
    report: dict[str, Any],
    include_rules: list[str],
    ignore_rules: list[str],
) -> tuple[int, int]:
    include_set = {item for item in include_rules if item}
    ignore_set = {item for item in ignore_rules if item}
    finding_ids = {
        finding['id']
        for finding in report.get('findings', [])
        if (not include_set or finding.get('rule_id') in include_set)
        and finding.get('rule_id') not in ignore_set
    }
    before_count = len(report.get('findings', []))
    report['findings'] = [item for item in report.get('findings', []) if item.get('id') in finding_ids]
    report['fixes'] = [item for item in report.get('fixes', []) if item.get('finding_id') in finding_ids]
    report['citations'] = [item for item in report.get('citations', []) if item.get('finding_id') in finding_ids]

    summary = report.setdefault('summary', {})
    summary['change_summary'] = [
        item for item in summary.get('change_summary', []) if item.get('finding_id') in finding_ids
    ]
    summary['fix_blockers'] = [
        item for item in summary.get('fix_blockers', []) if item.get('finding_id') in finding_ids
    ]
    _rebuild_summary(report)
    return before_count, len(report.get('findings', []))


def _sarif_level_from_severity(severity: str) -> str:
    if severity in {'critical', 'serious'}:
        return 'error'
    if severity == 'moderate':
        return 'warning'
    return 'note'


def _build_report_product_metadata() -> dict[str, Any]:
    product_provenance = get_product_provenance()
    metadata: dict[str, Any] = {
        'name': product_provenance['product_name'],
        'product_version': product_provenance['product_version'],
        'version_source': product_provenance['version_source'],
        'source_revision': product_provenance['source_revision'],
        'source_revision_source': product_provenance['source_revision_source'],
        'report_schema_version': REPORT_SCHEMA_VERSION,
    }
    if 'build_timestamp' in product_provenance:
        metadata['build_timestamp'] = product_provenance['build_timestamp']
        metadata['build_timestamp_source'] = product_provenance['build_timestamp_source']
    return metadata


def _append_markdown_report_metadata(output_md: Path, product_metadata: dict[str, Any]) -> None:
    lines = [
        '',
        '## Report Metadata',
        '',
        f"- Product: {product_metadata['name']}",
        f"- Product version: {product_metadata['product_version']}",
        f"- Source revision: {product_metadata['source_revision']}",
        f"- Report schema version: {product_metadata['report_schema_version']}",
    ]
    if product_metadata.get('build_timestamp'):
        lines.append(f"- Build timestamp: {product_metadata['build_timestamp']}")
    existing = output_md.read_text(encoding='utf-8').rstrip()
    output_md.write_text(existing + '\n' + '\n'.join(lines) + '\n', encoding='utf-8')


def _report_to_sarif(
    report: dict[str, Any],
    contract_target: str,
    local_target: Path | None,
    product_metadata: dict[str, Any],
) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    location_uri = local_target.as_posix() if local_target else contract_target

    for finding in report.get('findings', []):
        rule_id = str(finding.get('rule_id', 'unknown'))
        if rule_id not in rules:
            rules[rule_id] = {
                'id': rule_id,
                'name': rule_id,
                'shortDescription': {'text': rule_id},
                'properties': {
                    'severity': finding.get('severity', 'info'),
                    'wcag': finding.get('sc', []),
                },
            }
        message_parts = [str(finding.get('current', rule_id))]
        selector = str(finding.get('changed_target', '')).strip()
        if selector and selector != 'unknown':
            message_parts.append(f'selector: {selector}')

        physical_location: dict[str, Any] = {
            'artifactLocation': {
                'uri': location_uri,
            }
        }
        source_line = _coerce_positive_int(finding.get('source_line'))
        source_column = _coerce_positive_int(finding.get('source_column'))
        if source_line is not None:
            region: dict[str, int] = {'startLine': source_line}
            if source_column is not None:
                region['startColumn'] = source_column
            physical_location['region'] = region

        results.append(
            {
                'ruleId': rule_id,
                'level': _sarif_level_from_severity(str(finding.get('severity', 'info'))),
                'message': {'text': ' | '.join(message_parts)},
                'locations': [
                    {
                        'physicalLocation': physical_location,
                    }
                ],
                'properties': {
                    'finding_id': finding.get('id'),
                    'status': finding.get('status'),
                    'sc': finding.get('sc', []),
                    'source_line': source_line,
                    'source_column': source_column,
                },
            }
        )

    return {
        '$schema': 'https://json.schemastore.org/sarif-2.1.0.json',
        'version': '2.1.0',
        'runs': [
            {
                'tool': {
                    'driver': {
                        'name': 'libro-wcag',
                        'version': product_metadata['product_version'],
                        'rules': list(rules.values()),
                        'properties': {
                            'product_name': product_metadata['name'],
                            'source_revision': product_metadata['source_revision'],
                            'report_schema_version': product_metadata['report_schema_version'],
                        },
                    }
                },
                'results': results,
            }
        ],
    }


def _resolve_fail_threshold(report: dict[str, Any], fail_on: str) -> tuple[bool, int]:
    threshold_rank = SEVERITY_RANK[fail_on]
    for finding in report.get('findings', []):
        if finding.get('status') == 'fixed':
            continue
        severity = str(finding.get('severity', 'info'))
        if SEVERITY_RANK.get(severity, 0) >= threshold_rank:
            return True, FAIL_ON_EXIT_CODES[fail_on]
    return False, 0


def _write_machine_report_outputs(
    *,
    report: dict[str, Any],
    report_format: str,
    output_json: Path,
    output_md: Path,
    machine_output: Path,
    contract_target: str,
    local_target: Path | None,
    product_metadata: dict[str, Any],
) -> None:
    if report_format == 'json':
        write_report_files(report, str(output_json), str(output_md))
        _append_markdown_report_metadata(output_md, product_metadata)
        return

    machine_output.write_text(
        json.dumps(
            _report_to_sarif(report, contract_target, local_target, product_metadata),
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(to_markdown_table(report), encoding='utf-8')
    _append_markdown_report_metadata(output_md, product_metadata)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WCAG audit with axe+Lighthouse.")
    parser.add_argument("--task-mode", default="modify", choices=["create", "modify"])
    parser.add_argument(
        "--execution-mode",
        default="suggest-only",
        choices=["audit-only", "suggest-only", "apply-fixes"],
    )
    parser.add_argument("--wcag-version", default="2.1", choices=["2.0", "2.1", "2.2"])
    parser.add_argument("--conformance-level", default="AA", choices=["A", "AA", "AAA"])
    parser.add_argument("--target")
    parser.add_argument("--output-language", default="zh-TW")
    parser.add_argument("--output-dir", default="out")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--report-format",
        choices=["json", "sarif"],
        default=None,
        help="Primary machine-readable output format.",
    )
    parser.add_argument(
        "--fail-on",
        choices=["critical", "serious", "moderate"],
        default=None,
        help="Fail with deterministic exit code when unresolved findings reach this severity.",
    )
    parser.add_argument(
        "--include-rule",
        action="append",
        default=[],
        help="Include only specific normalized rule ids (repeatable).",
    )
    parser.add_argument(
        "--ignore-rule",
        action="append",
        default=[],
        help="Ignore specific normalized rule ids (repeatable).",
    )
    parser.add_argument(
        "--policy-config",
        help="Optional JSON file with report_format/fail_on/include_rules/ignore_rules.",
    )
    parser.add_argument(
        "--policy-preset",
        choices=sorted(POLICY_PRESETS),
        default=None,
        help="Optional policy preset (strict|balanced|legacy) for deterministic fail-on and rule filters.",
    )
    parser.add_argument(
        "--policy-bundle",
        choices=sorted(POLICY_BUNDLES),
        default=None,
        help="Optional policy bundle template (strict-web-app|legacy-content|marketing-site).",
    )
    parser.add_argument(
        "--list-policy-presets",
        action="store_true",
        help="Print available policy presets and exit.",
    )
    parser.add_argument(
        "--list-policy-config-keys",
        action="store_true",
        help="Print supported --policy-config keys and exit.",
    )
    parser.add_argument(
        "--explain-policy",
        action="store_true",
        help="Include effective merged policy settings in run metadata and summary output.",
    )
    parser.add_argument(
        "--strict-rule-overlap",
        action="store_true",
        help="Fail when any rule id appears in both include and ignore policy lists.",
    )
    parser.add_argument(
        "--write-effective-policy",
        nargs="?",
        const="AUTO",
        default=None,
        help="Write effective merged policy JSON (optional path; defaults to <output-dir>/wcag-effective-policy.json).",
    )
    parser.add_argument(
        "--baseline-report",
        help="Optional prior JSON report to compare unresolved debt and detect newly introduced findings.",
    )
    parser.add_argument(
        "--baseline-include-target",
        action="store_true",
        help="Include normalized report target value in baseline signatures for stricter comparison.",
    )
    parser.add_argument(
        "--baseline-target-normalization",
        choices=sorted(BASELINE_TARGET_NORMALIZATION_MODES),
        default="none",
        help="Normalization mode for report target when --baseline-include-target is enabled.",
    )
    parser.add_argument(
        "--baseline-selector-canonicalization",
        choices=sorted(BASELINE_SELECTOR_CANONICALIZATION_MODES),
        default="none",
        help="Selector canonicalization mode used when building baseline signatures.",
    )
    parser.add_argument(
        "--baseline-evidence-mode",
        choices=sorted(BASELINE_EVIDENCE_MODES),
        default="none",
        help="Baseline evidence integrity mode (none|hash|hash-chain) for tamper/staleness checks.",
    )
    parser.add_argument(
        "--waiver-expiry-mode",
        choices=sorted(WAIVER_EXPIRY_MODES),
        default="warn",
        help="Expired baseline debt waiver handling: ignore, warn, or fail.",
    )
    parser.add_argument(
        "--fail-on-new-only",
        action="store_true",
        help="When used with --fail-on and --baseline-report, fail only on newly introduced debt.",
    )
    parser.add_argument(
        "--debt-trend-window",
        type=int,
        default=DEFAULT_DEBT_TREND_WINDOW,
        help="Number of historical baseline trend points to keep in debt-trend artifact output.",
    )
    parser.add_argument(
        "--risk-calibration-source",
        default=None,
        help="JSON report/artifact file or directory used to compute per-rule risk calibration precision.",
    )
    parser.add_argument(
        "--risk-calibration-mode",
        choices=sorted(RISK_CALIBRATION_MODES),
        default="off",
        help="Risk calibration gate mode: off, warn, or strict.",
    )
    parser.add_argument(
        "--replay-verify-from",
        default=None,
        help="Directory containing prior run artifacts (wcag-report.json) for replay verification.",
    )
    parser.add_argument(
        "--stability-baseline",
        default=None,
        help="Path to prior scanner stability baseline report or scanner-stability.json artifact.",
    )
    parser.add_argument(
        "--stability-mode",
        choices=sorted(SCANNER_STABILITY_MODES),
        default="off",
        help="Scanner stability gate mode: off, warn, or fail.",
    )
    parser.add_argument(
        "--scanner-retry-attempts",
        type=int,
        default=DEFAULT_SCANNER_RETRY_ATTEMPTS,
        help="Retry attempts per scanner for transient runtime failures (minimum: 1).",
    )
    parser.add_argument(
        "--scanner-retry-backoff-seconds",
        type=float,
        default=DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS,
        help="Initial retry backoff in seconds for transient scanner failures.",
    )
    parser.add_argument("--skip-axe", action="store_true")
    parser.add_argument("--skip-lighthouse", action="store_true")
    parser.add_argument("--mock-axe-json")
    parser.add_argument("--mock-lighthouse-json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--max-findings",
        type=int,
        default=None,
        help="Limit findings included in output artifacts after deterministic sorting.",
    )
    parser.add_argument(
        "--sort-findings",
        choices=sorted(FINDING_SORT_MODES),
        default="severity",
        help="Deterministic sort mode for report findings before optional truncation.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print compact JSON summary to stdout while still writing full report artifacts.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Check runtime tooling availability (npx, axe, lighthouse) and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_policy_presets:
        print(json.dumps(_policy_presets_payload(), ensure_ascii=False, indent=2))
        return 0
    if args.list_policy_config_keys:
        print(json.dumps(_policy_config_keys_payload(), ensure_ascii=False, indent=2))
        return 0
    if not args.target and not args.preflight_only:
        raise ValueError('--target is required unless --list-policy-presets or --list-policy-config-keys is used')

    policy_config = _load_policy_config(args.policy_config)
    baseline_report = _load_baseline_report(args.baseline_report)
    policy_bundle = _resolve_policy_bundle(args.policy_bundle)
    policy_preset = _resolve_policy_preset(args.policy_preset)
    config_report_format = policy_config.get('report_format')
    config_fail_on = policy_config.get('fail_on')
    config_include = _normalize_rule_list(policy_config.get('include_rules'), 'include_rules')
    config_ignore = _normalize_rule_list(policy_config.get('ignore_rules'), 'ignore_rules')

    if config_report_format and config_report_format not in {'json', 'sarif'}:
        raise ValueError('policy-config report_format must be one of: json, sarif')
    if config_fail_on and config_fail_on not in {'critical', 'serious', 'moderate'}:
        raise ValueError('policy-config fail_on must be one of: critical, serious, moderate')

    bundle_fail_on = policy_bundle.get('fail_on')
    bundle_include = _normalize_rule_list(policy_bundle.get('include_rules'), 'bundle.include_rules')
    bundle_ignore = _normalize_rule_list(policy_bundle.get('ignore_rules'), 'bundle.ignore_rules')

    preset_fail_on = policy_preset.get('fail_on')
    preset_include = _normalize_rule_list(policy_preset.get('include_rules'), 'preset.include_rules')
    preset_ignore = _normalize_rule_list(policy_preset.get('ignore_rules'), 'preset.ignore_rules')

    cli_include_rules = [item.strip() for item in args.include_rule if item.strip()]
    cli_ignore_rules = [item.strip() for item in args.ignore_rule if item.strip()]

    report_format = args.report_format or config_report_format or 'json'
    fail_on = args.fail_on or config_fail_on or preset_fail_on or bundle_fail_on
    include_rules = _merge_rule_list(
        bundle_include,
        preset_include,
        config_include,
        cli_include_rules,
    )
    ignore_rules = _merge_rule_list(
        bundle_ignore,
        preset_ignore,
        config_ignore,
        cli_ignore_rules,
    )
    overlapping_rules = _find_rule_policy_overlaps(include_rules, ignore_rules)
    if overlapping_rules and args.strict_rule_overlap:
        raise ValueError(
            '--strict-rule-overlap detected rule ids present in both include and ignore lists: '
            + ", ".join(overlapping_rules)
        )
    policy_sources = {
        'report_format': _policy_value_source(args.report_format, config_report_format, None, None, 'default'),
        'fail_on': _policy_value_source(args.fail_on, config_fail_on, preset_fail_on, bundle_fail_on, 'unset'),
        'include_rules': _build_rule_sources(bundle_include, preset_include, config_include, cli_include_rules),
        'ignore_rules': _build_rule_sources(bundle_ignore, preset_ignore, config_ignore, cli_ignore_rules),
    }

    if args.skip_axe and args.mock_axe_json:
        raise ValueError('--skip-axe cannot be combined with --mock-axe-json')
    if args.skip_lighthouse and args.mock_lighthouse_json:
        raise ValueError('--skip-lighthouse cannot be combined with --mock-lighthouse-json')
    if args.dry_run and args.execution_mode != 'apply-fixes':
        raise ValueError('--dry-run is only supported when --execution-mode is apply-fixes')
    if args.scanner_retry_attempts < 1:
        raise ValueError('--scanner-retry-attempts must be >= 1')
    if args.scanner_retry_backoff_seconds < 0:
        raise ValueError('--scanner-retry-backoff-seconds must be >= 0')
    if args.max_findings is not None and args.max_findings < 1:
        raise ValueError('--max-findings must be >= 1')
    if args.debt_trend_window < 1:
        raise ValueError('--debt-trend-window must be >= 1')
    if args.fail_on_new_only and not args.fail_on:
        raise ValueError('--fail-on-new-only requires --fail-on')
    if args.fail_on_new_only and not args.baseline_report:
        raise ValueError('--fail-on-new-only requires --baseline-report')
    if args.replay_verify_from and not Path(args.replay_verify_from).exists():
        raise ValueError('--replay-verify-from directory does not exist: ' + str(args.replay_verify_from))
    if args.stability_baseline and not Path(args.stability_baseline).exists():
        raise ValueError('--stability-baseline path does not exist: ' + str(args.stability_baseline))

    if args.preflight_only:
        preflight = run_preflight_checks(args.timeout)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0 if preflight["ok"] else 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    effective_policy_output = _resolve_effective_policy_path(args.write_effective_policy, output_dir)
    schema_metadata, staged_schema_path = _stage_report_schema_artifact(output_dir)
    baseline_signature_config = _build_baseline_signature_config(args)
    effective_policy = _build_effective_policy(
        report_format=report_format,
        fail_on=fail_on,
        include_rules=include_rules,
        ignore_rules=ignore_rules,
        policy_bundle=policy_bundle,
        policy_preset=policy_preset,
        policy_config_path=args.policy_config,
        policy_sources=policy_sources,
        fail_on_new_only=bool(args.fail_on_new_only),
        baseline_report_path=args.baseline_report,
        baseline_signature_config=baseline_signature_config,
        baseline_evidence_mode=args.baseline_evidence_mode,
        waiver_expiry_mode=args.waiver_expiry_mode,
        risk_calibration_mode=args.risk_calibration_mode,
        risk_calibration_source=args.risk_calibration_source,
        stability_mode=args.stability_mode,
        stability_baseline=args.stability_baseline,
        overlapping_rules=overlapping_rules,
    )

    contract = resolve_contract(
        {
            "task_mode": args.task_mode,
            "execution_mode": args.execution_mode,
            "wcag_version": args.wcag_version,
            "conformance_level": args.conformance_level,
            "target": args.target,
            "output_language": args.output_language,
        }
    )
    local_target = target_to_local_path(contract.target)
    scanner_target = _resolve_target_for_scanners(contract.target)

    preflight_required = not (
        (args.skip_axe or args.mock_axe_json) and (args.skip_lighthouse or args.mock_lighthouse_json)
    )
    if preflight_required:
        preflight = run_preflight_checks(args.timeout)
    else:
        preflight = {
            "ok": True,
            "checks": [
                {
                    "tool": "runtime",
                    "status": "skipped",
                    "message": "scanner tooling preflight skipped due to mock or skip flags",
                    "command": "",
                    "resolved_command": "",
                    "version": "",
                    "version_provenance": {
                        "source": "skipped",
                        "command": "",
                        "resolved_command": "",
                        "version": "",
                    },
                }
            ],
            "tools": {
                "runtime": {
                    "status": "skipped",
                    "command": "",
                    "resolved_command": "",
                    "version": "",
                    "message": "scanner tooling preflight skipped due to mock or skip flags",
                    "version_provenance": {
                        "source": "skipped",
                        "command": "",
                        "resolved_command": "",
                        "version": "",
                    },
                }
            },
        }

    axe_data = None
    axe_error = None
    scanner_retry_runs: list[dict[str, Any]] = []
    if args.mock_axe_json:
        axe_data = json.loads(Path(args.mock_axe_json).read_text(encoding='utf-8'))
    elif not args.skip_axe:
        axe_data, axe_error, axe_retry = _run_scanner_with_retry(
            'axe',
            lambda: _try_run_axe(scanner_target, output_dir, args.timeout),
            args.scanner_retry_attempts,
            args.scanner_retry_backoff_seconds,
        )
        scanner_retry_runs.append(axe_retry)

    lighthouse_data = None
    lighthouse_error = None
    if args.mock_lighthouse_json:
        lighthouse_data = json.loads(Path(args.mock_lighthouse_json).read_text(encoding='utf-8'))
    elif not args.skip_lighthouse:
        lighthouse_data, lighthouse_error, lighthouse_retry = _run_scanner_with_retry(
            'lighthouse',
            lambda: _try_run_lighthouse(
                scanner_target,
                output_dir,
                args.timeout,
            ),
            args.scanner_retry_attempts,
            args.scanner_retry_backoff_seconds,
        )
        scanner_retry_runs.append(lighthouse_retry)

    report = normalize_report(
        contract=contract,
        axe_data=axe_data,
        lighthouse_data=lighthouse_data,
        axe_error=axe_error,
        lighthouse_error=lighthouse_error,
        axe_skipped=args.skip_axe,
        lighthouse_skipped=args.skip_lighthouse,
    )
    product_metadata = _build_report_product_metadata()
    report['run_meta']['product'] = product_metadata
    report['run_meta']['product_version'] = product_metadata['product_version']
    report['run_meta']['source_revision'] = product_metadata['source_revision']
    report['run_meta']['preflight'] = preflight
    report['report_schema'] = schema_metadata
    report['run_meta']['report_schema_version'] = REPORT_SCHEMA_VERSION
    report['run_meta']['report_schema_artifact'] = str(staged_schema_path)
    report['run_meta']['retry_policy'] = {
        'attempts': args.scanner_retry_attempts,
        'initial_backoff_seconds': args.scanner_retry_backoff_seconds,
        'max_backoff_seconds': MAX_SCANNER_RETRY_BACKOFF_SECONDS,
    }
    if policy_preset:
        report['run_meta']['policy_preset'] = policy_preset
    if policy_bundle:
        report['run_meta']['policy_bundle'] = policy_bundle
    if args.explain_policy:
        report['run_meta']['policy_effective'] = effective_policy
        report.setdefault('summary', {})['policy_effective'] = {
            'report_format': effective_policy['report_format'],
            'fail_on': effective_policy['fail_on'],
            'bundle': effective_policy['bundle'],
            'preset': effective_policy['preset'],
            'include_rule_count': len(effective_policy['include_rules']),
            'ignore_rule_count': len(effective_policy['ignore_rules']),
            'overlapping_rule_count': len(effective_policy.get('overlapping_rules', [])),
        }
    if effective_policy_output is not None:
        effective_policy_output.parent.mkdir(parents=True, exist_ok=True)
        effective_policy_output.write_text(json.dumps(effective_policy, ensure_ascii=False, indent=2), encoding='utf-8')
        report['run_meta']['effective_policy_artifact'] = str(effective_policy_output)
        report['run_meta']['notes'].append(
            f'Saved effective policy artifact: {effective_policy_output}'
        )
    if scanner_retry_runs:
        report['run_meta']['scanner_retries'] = scanner_retry_runs
        retried_tools = [item['tool'] for item in scanner_retry_runs if item.get('retry_count', 0) > 0]
        if retried_tools:
            report['run_meta']['notes'].append(
                f"Retried scanner execution for transient errors: {', '.join(sorted(set(retried_tools)))}."
            )
    if not preflight['ok']:
        report['run_meta']['notes'].append(
            'Preflight checks detected tooling issues; scanner results may be incomplete.'
        )

    before_policy_count, after_policy_count = _apply_rule_policy(report, include_rules, ignore_rules)
    if include_rules or ignore_rules:
        report['run_meta']['policy'] = {
            'bundle': policy_bundle.get('name'),
            'preset': policy_preset.get('name'),
            'include_rules': include_rules,
            'ignore_rules': ignore_rules,
            'overlapping_rules': overlapping_rules,
            'rule_overlap_resolution': 'ignore-rules-win',
            'before_filter_count': before_policy_count,
            'after_filter_count': after_policy_count,
        }
        report['run_meta']['notes'].append(
            f'Rule policy filter applied: {before_policy_count} -> {after_policy_count} findings.'
        )
    if overlapping_rules:
        report['run_meta']['policy_rule_overlap'] = {
            'overlapping_rules': overlapping_rules,
            'resolution': 'ignore-rules-win',
        }
        report['run_meta']['notes'].append(
            'Rule policy overlap detected (ignore-rules-win): ' + ", ".join(overlapping_rules)
        )

    diff_path: Path | None = None
    snapshot_path: Path | None = None
    if contract.execution_mode == 'apply-fixes':
        if args.dry_run:
            diff_path = output_dir / 'wcag-fixes.dry-run.diff'
            snapshot_path = output_dir / 'wcag-fixed-report.dry-run.snapshot.json'
        else:
            diff_path = output_dir / 'wcag-fixes.diff'
            snapshot_path = output_dir / 'wcag-fixed-report.snapshot.json'

        if local_target is None:
            report['run_meta']['notes'].append('apply-fixes skipped: target is not a local file path.')
            _remove_if_exists(diff_path)
            _remove_if_exists(snapshot_path)
        elif not supports_apply_fixes_target(local_target):
            report['run_meta']['notes'].append(
                f'apply-fixes skipped: unsupported local target extension "{local_target.suffix or "<none>"}".'
            )
            _remove_if_exists(diff_path)
            _remove_if_exists(snapshot_path)
        else:
            report, diff_text = apply_report_fixes(local_target, report, dry_run=args.dry_run)
            if diff_text:
                write_diff(diff_text, diff_path)
                diff_type = 'projected-unified-diff' if args.dry_run else 'unified-diff'
                report['run_meta'].setdefault('diff_artifacts', []).append(
                    {'path': str(diff_path), 'type': diff_type}
                )
                if args.dry_run:
                    report['run_meta']['notes'].append(
                        f'Saved projected auto-fix diff (--dry-run): {diff_path}'
                    )
                else:
                    report['run_meta']['notes'].append(f'Saved auto-fix diff: {diff_path}')
                write_snapshot(report, snapshot_path)
            else:
                _remove_if_exists(diff_path)
                _remove_if_exists(snapshot_path)

    baseline_diff: dict[str, Any] | None = None
    waiver_review: dict[str, Any] | None = None
    debt_transitions: dict[str, Any] | None = None
    if baseline_report:
        baseline_diff = _build_baseline_diff(report, baseline_report, baseline_signature_config)
        debt_transitions = _build_debt_transition_summary(baseline_diff)
        waiver_review = _evaluate_debt_waiver_review(baseline_diff, baseline_report)
        _tag_findings_with_debt_state(report, baseline_diff, baseline_signature_config)
        report['run_meta']['baseline_diff'] = {
            **baseline_diff,
            'baseline_report_path': args.baseline_report,
            'debt_transitions': debt_transitions,
            'waiver_review': waiver_review,
        }
        report.setdefault('summary', {})['debt_transitions'] = debt_transitions
        report['summary']['waiver_review'] = {
            'accepted_count': waiver_review.get('accepted_count', 0),
            'valid_count': waiver_review.get('valid_count', 0),
            'expired_count': waiver_review.get('expired_count', 0),
            'missing_count': waiver_review.get('missing_count', 0),
        }
        report['run_meta']['notes'].append(
            (
                'Baseline diff: introduced='
                f"{baseline_diff['introduced_count']}, "
                f"resolved={baseline_diff['resolved_count']}, "
                f"persistent={baseline_diff['persistent_count']}."
            )
        )
        if waiver_review['expired_count'] > 0:
            report['run_meta']['notes'].append(
                'Baseline waiver review: '
                f"{waiver_review['expired_count']} expired waiver(s) need renewal or retirement."
            )
        if waiver_review['missing_count'] > 0:
            report['run_meta']['notes'].append(
                'Baseline waiver review: '
                f"{waiver_review['missing_count']} accepted signature(s) missing waiver metadata."
            )

    baseline_evidence: dict[str, Any] | None = None
    if args.baseline_evidence_mode != 'none':
        baseline_evidence = _build_run_baseline_evidence(
            report=report,
            baseline_report=baseline_report,
            signature_config=baseline_signature_config,
            evidence_mode=args.baseline_evidence_mode,
        )
        report['run_meta']['baseline_evidence'] = baseline_evidence
        report.setdefault('summary', {})['baseline_evidence'] = {
            'mode': baseline_evidence.get('mode'),
            'baseline_verification': baseline_evidence.get('baseline_verification', {}),
        }
        if baseline_report:
            report['run_meta']['notes'].append(
                'Baseline evidence verification: '
                + ('passed' if baseline_evidence['baseline_verification'].get('verified') else 'missing declaration')
                + f" (mode={args.baseline_evidence_mode})."
            )

    _sort_report_findings(report, args.sort_findings)
    report['run_meta']['sorting'] = {
        'mode': args.sort_findings,
        'deterministic': True,
        'finding_count': len(report.get('findings', [])),
    }

    gate_findings = list(report.get('findings', []))
    risk_calibration_gate_failed = False
    risk_calibration = _evaluate_risk_calibration(
        report=report,
        source_path=args.risk_calibration_source,
        mode=args.risk_calibration_mode,
    )
    if (
        args.risk_calibration_mode == 'strict'
        and risk_calibration.get('applied')
        and risk_calibration.get('unstable_high_severity_rules')
    ):
        risk_calibration_gate_failed = True
    risk_calibration['gate'] = {
        'mode': args.risk_calibration_mode,
        'failed': risk_calibration_gate_failed,
        'exit_code': RISK_CALIBRATION_EXIT_CODE if risk_calibration_gate_failed else 0,
    }
    report['run_meta']['risk_calibration'] = risk_calibration
    report.setdefault('summary', {})['risk_calibration'] = {
        'mode': risk_calibration.get('mode'),
        'applied': bool(risk_calibration.get('applied')),
        'downgrade_reason': risk_calibration.get('downgrade_reason'),
        'unstable_high_severity_rule_count': len(risk_calibration.get('unstable_high_severity_rules', [])),
    }
    if risk_calibration.get('applied'):
        report['run_meta']['notes'].append(
            'Risk calibration applied: '
            f"{len(risk_calibration.get('rules', []))} rules evaluated, "
            f"{len(risk_calibration.get('unstable_high_severity_rules', []))} unstable high-severity rule(s)."
        )
    elif args.risk_calibration_mode != 'off':
        downgrade_reason = str(risk_calibration.get('downgrade_reason') or 'missing-evidence')
        downgrade_message = str((risk_calibration.get('source_meta') or {}).get('message') or '').strip()
        note = (
            'Risk calibration downgraded '
            f'({downgrade_reason}): {downgrade_message}. '
            'Continuing without calibration gate.'
        )
        report['run_meta']['notes'].append(note)

    if args.max_findings is not None:
        findings_cap = _cap_report_findings(report, args.max_findings)
        report['run_meta']['findings_cap'] = {
            'max_findings': args.max_findings,
            **findings_cap,
        }
        if findings_cap['truncated'] > 0:
            report['run_meta']['notes'].append(
                f"Applied --max-findings={args.max_findings}: truncated {findings_cap['truncated']} findings."
            )
    scanner_capabilities = _build_scanner_capabilities(preflight, report, args, axe_data, lighthouse_data)
    report['run_meta']['scanner_capabilities'] = scanner_capabilities
    report.setdefault('summary', {})['scanner_capabilities'] = {
        'available_scanners': sorted(
            [name for name, details in scanner_capabilities['scanners'].items() if details.get('available')]
        ),
        'unavailable_scanners': sorted(
            [name for name, details in scanner_capabilities['scanners'].items() if not details.get('available')]
        ),
        'available_rule_count': scanner_capabilities['available_rule_count'],
    }
    replay_summary_path: Path | None = None
    replay_diff_path: Path | None = None
    replay_verification: dict[str, Any] | None = None
    if args.replay_verify_from:
        replay_dir = Path(args.replay_verify_from)
        replay_source_report, replay_source_path = _load_replay_source_report(replay_dir)
        replay_verification = _build_replay_verification_summary(
            current_report=report,
            replay_source_report=replay_source_report,
            replay_source_path=replay_source_path,
            replay_source_dir=replay_dir,
        )
        replay_summary_path = output_dir / 'replay-summary.json'
        replay_diff_path = output_dir / 'replay-diff.md'
        replay_summary_path.write_text(json.dumps(replay_verification, ensure_ascii=False, indent=2), encoding='utf-8')
        _build_replay_diff_markdown(replay_verification, replay_diff_path)
        report['run_meta']['replay_verification'] = {
            'source_report_dir': str(replay_dir),
            'summary_path': str(replay_summary_path),
            'diff_path': str(replay_diff_path),
            'status_counts': replay_verification.get('status_counts', {}),
            'non_deterministic_reasons': replay_verification.get('non_deterministic_reasons', []),
            'gate': replay_verification.get('gate', {}),
        }
        report.setdefault('summary', {})['replay_verification'] = {
            'status_counts': replay_verification.get('status_counts', {}),
            'non_deterministic_count': replay_verification.get('status_counts', {}).get('non-deterministic', 0),
            'gate_failed': bool(replay_verification.get('gate', {}).get('failed')),
        }
        report['run_meta']['notes'].append(
            'Replay verification: '
            f"resolved={replay_verification['status_counts']['resolved']}, "
            f"unchanged={replay_verification['status_counts']['unchanged']}, "
            f"regressed={replay_verification['status_counts']['regressed']}, "
            f"non-deterministic={replay_verification['status_counts']['non-deterministic']}."
        )
    scanner_stability = _build_scanner_stability_payload(
        now_utc=datetime.now(timezone.utc),
        mode=args.stability_mode,
        current_report=report,
        baseline_path=args.stability_baseline,
    )
    scanner_stability_path = output_dir / 'scanner-stability.json'
    scanner_stability_path.write_text(json.dumps(scanner_stability, ensure_ascii=False, indent=2), encoding='utf-8')
    scanner_stability_comparison = scanner_stability.get('comparison', {})
    scanner_stability_gate = scanner_stability.get('gate', {})
    report['run_meta']['scanner_stability'] = {
        'schema_version': scanner_stability.get('schema_version'),
        'mode': scanner_stability.get('mode'),
        'artifact_path': str(scanner_stability_path),
        'window': scanner_stability.get('window'),
        'baseline_source': scanner_stability.get('baseline_source'),
        'history_meta': scanner_stability.get('history_meta', {}),
        'approved_bounds': scanner_stability.get('approved_bounds', {}),
        'comparison': {
            'evaluated_signature_count': scanner_stability_comparison.get('evaluated_signature_count', 0),
            'breach_count': scanner_stability_comparison.get('breach_count', 0),
            'max_delta': scanner_stability_comparison.get('max_delta', 0),
            'scanner_capability_changed': bool(scanner_stability_comparison.get('scanner_capability_changed')),
            'previous_scanners': scanner_stability_comparison.get('previous_scanners', []),
            'current_scanners': scanner_stability_comparison.get('current_scanners', []),
        },
        'gate': scanner_stability_gate,
        'points': scanner_stability.get('points', []),
    }
    report.setdefault('summary', {})['scanner_stability'] = {
        'mode': scanner_stability.get('mode'),
        'window': scanner_stability.get('window'),
        'breach_count': scanner_stability_comparison.get('breach_count', 0),
        'max_delta': scanner_stability_comparison.get('max_delta', 0),
        'scanner_capability_changed': bool(scanner_stability_comparison.get('scanner_capability_changed')),
        'gate_failed': bool(scanner_stability_gate.get('failed')),
    }

    scanner_stability_downgrade = str(scanner_stability_gate.get('downgrade_reason') or '')
    if scanner_stability_downgrade == 'missing-history' and args.stability_mode != 'off':
        report['run_meta']['notes'].append(
            'Scanner stability downgraded (missing-history): provide --stability-baseline with scanner-stability.json '
            'or a prior wcag-report.json containing run_meta.scanner_stability.'
        )
    elif scanner_stability_downgrade == 'scanner-capability-changed':
        report['run_meta']['notes'].append(
            'Scanner stability downgraded (scanner-capability-changed): '
            'baseline scanners and current scanners differ; comparison is informational only.'
        )
    elif args.stability_mode != 'off':
        report['run_meta']['notes'].append(
            'Scanner stability: '
            f"breaches={scanner_stability_comparison.get('breach_count', 0)}, "
            f"max_delta={scanner_stability_comparison.get('max_delta', 0)} "
            f"(window={scanner_stability.get('window')}, mode={args.stability_mode})."
        )
        if args.stability_mode == 'warn' and scanner_stability_comparison.get('breach_count', 0) > 0:
            report['run_meta']['notes'].append(
                'Scanner stability warning: volatility exceeds approved bounds under --stability-mode=warn.'
            )

    report_output_paths = _build_report_output_paths(output_dir, report_format)
    output_json = report_output_paths['output_json']
    output_md = report_output_paths['output_md']
    machine_output = report_output_paths['machine_output']
    _write_machine_report_outputs(
        report=report,
        report_format=report_format,
        output_json=output_json,
        output_md=output_md,
        machine_output=machine_output,
        contract_target=contract.target,
        local_target=local_target,
        product_metadata=product_metadata,
    )

    if fail_on:
        gate_report = {'findings': gate_findings}
        gate_scope = 'all-unresolved'
        if args.fail_on_new_only:
            introduced_signatures = set((baseline_diff or {}).get('introduced_signatures', []))
            report_target = str(report.get('target', {}).get('value', '')).strip()
            gate_report = {
                'findings': [
                    item
                    for item in gate_findings
                    if _finding_signature_with_config(item, baseline_signature_config, report_target)
                    in introduced_signatures
                ],
            }
            gate_scope = 'introduced-only'
        should_fail, exit_code = _resolve_fail_threshold(gate_report, fail_on)
        report['run_meta']['policy_gate'] = {
            'fail_on': fail_on,
            'failed': should_fail,
            'exit_code': exit_code if should_fail else 0,
            'scope': gate_scope,
            'evaluated_findings': len(gate_report.get('findings', [])),
        }
        _write_machine_report_outputs(
            report=report,
            report_format=report_format,
            output_json=output_json,
            output_md=output_md,
            machine_output=machine_output,
            contract_target=contract.target,
            local_target=local_target,
            product_metadata=product_metadata,
        )
    else:
        should_fail, exit_code = False, 0

    waiver_gate = {
        'mode': args.waiver_expiry_mode,
        'evaluated_count': waiver_review.get('accepted_count', 0) if waiver_review else 0,
        'expired_count': waiver_review.get('expired_count', 0) if waiver_review else 0,
        'failed': False,
        'exit_code': 0,
    }
    if waiver_review and args.waiver_expiry_mode in {'warn', 'fail'} and waiver_review.get('expired_count', 0) > 0:
        if args.waiver_expiry_mode == 'warn':
            report['run_meta']['notes'].append(
                'Waiver expiry gate warning: expired waivers detected; renew or retire accepted debt.'
            )
        else:
            waiver_gate['failed'] = True
            waiver_gate['exit_code'] = WAIVER_EXPIRY_EXIT_CODE
            should_fail = True
            exit_code = WAIVER_EXPIRY_EXIT_CODE
            report['run_meta']['notes'].append(
                'Waiver expiry gate failed: expired waivers detected under --waiver-expiry-mode=fail.'
            )
    report['run_meta']['waiver_gate'] = waiver_gate

    advanced_gate_failed, advanced_gate_exit_code, advanced_gate_notes = _resolve_advanced_gate_exit_code(
        risk_calibration=risk_calibration,
        replay_verification=replay_verification,
        scanner_stability=report['run_meta'].get('scanner_stability'),
    )
    if advanced_gate_failed and not should_fail:
        should_fail = True
        exit_code = advanced_gate_exit_code
    report['run_meta']['notes'].extend(advanced_gate_notes)

    debt_trend_payload = _build_debt_trend_payload(
        now_utc=datetime.now(timezone.utc),
        window=args.debt_trend_window,
        baseline_report=baseline_report,
        baseline_report_path=args.baseline_report,
        debt_transitions=debt_transitions,
        waiver_review=waiver_review,
    )
    debt_trend_path = output_dir / 'debt-trend.json'
    debt_trend_path.write_text(json.dumps(debt_trend_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    trend_summary = debt_trend_payload.get('summary', {})
    report['run_meta']['debt_trend'] = {
        'schema_version': debt_trend_payload.get('schema_version'),
        'window': debt_trend_payload.get('window'),
        'artifact_path': str(debt_trend_path),
        'latest_counts': trend_summary.get('latest_counts', _empty_debt_trend_counts()),
        'delta_from_previous': trend_summary.get('delta_from_previous', _empty_debt_trend_counts()),
        'history_meta': debt_trend_payload.get('history_meta', {}),
    }
    report.setdefault('summary', {})['debt_trend'] = {
        'window': debt_trend_payload.get('window'),
        'latest_counts': trend_summary.get('latest_counts', _empty_debt_trend_counts()),
        'delta_from_previous': trend_summary.get('delta_from_previous', _empty_debt_trend_counts()),
        'history_points_used': trend_summary.get('history_points_used', 0),
    }
    history_reset_reason = str((debt_trend_payload.get('history_meta') or {}).get('history_reset_reason') or '')
    if history_reset_reason:
        report['run_meta']['notes'].append(
            'Debt trend history reset reason: ' + history_reset_reason
        )
    report['run_meta']['notes'].append(
        f"Debt trend: new={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_NEW]}, "
        f"accepted={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_ACCEPTED]}, "
        f"retired={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_RETIRED]}, "
        f"regressed={report['summary']['debt_trend']['latest_counts'][DEBT_STATE_REGRESSED]} "
        f"(window={args.debt_trend_window})."
    )

    artifact_manifest_path = output_dir / 'artifact-manifest.json'
    report['run_meta']['artifact_manifest'] = {
        'path': str(artifact_manifest_path),
        'algorithm': 'sha256',
    }
    _write_machine_report_outputs(
        report=report,
        report_format=report_format,
        output_json=output_json,
        output_md=output_md,
        machine_output=machine_output,
        contract_target=contract.target,
        local_target=local_target,
        product_metadata=product_metadata,
    )

    axe_raw = output_dir / 'axe.raw.json'
    lighthouse_raw = output_dir / 'lighthouse.raw.json'
    artifact_paths = _collect_artifact_paths(
        report_format=report_format,
        machine_output=machine_output,
        output_json=output_json,
        output_md=output_md,
        staged_schema_path=staged_schema_path,
        debt_trend_path=debt_trend_path,
        scanner_stability_path=scanner_stability_path,
        axe_raw=axe_raw,
        lighthouse_raw=lighthouse_raw,
        effective_policy_output=effective_policy_output,
        replay_summary_path=replay_summary_path,
        replay_diff_path=replay_diff_path,
        diff_path=diff_path,
        snapshot_path=snapshot_path,
    )

    _, manifest_path = _build_artifact_manifest(
        output_dir=output_dir,
        report_format=report_format,
        target=contract.target,
        artifact_paths=artifact_paths,
        baseline_evidence=baseline_evidence,
    )
    report['run_meta']['artifact_manifest']['path'] = str(manifest_path)

    if args.summary_only:
        compact_summary = _build_compact_summary(
            report=report,
            report_format=report_format,
            machine_output=machine_output,
            output_md=output_md,
            should_fail=should_fail,
            fail_on=fail_on,
            exit_code=exit_code,
        )
        _emit_summary_only_stdout(compact_summary)
    else:
        print(f'Saved machine-readable report ({report_format}): {machine_output}')
        print(f'Saved Markdown table: {output_md}')
        if report['run_meta']['notes']:
            print('Notes:')
            for note in report['run_meta']['notes']:
                print(f'- {note}')
        if should_fail:
            if report['run_meta'].get('waiver_gate', {}).get('failed'):
                print('Waiver gate failed: one or more accepted debt waivers are expired.')
            elif report['run_meta'].get('risk_calibration', {}).get('gate', {}).get('failed'):
                print('Risk calibration gate failed: unstable high-severity rule outcomes detected.')
            elif report['run_meta'].get('replay_verification', {}).get('gate', {}).get('failed'):
                print('Replay verification gate failed: high-severity regressed findings detected.')
            elif report['run_meta'].get('scanner_stability', {}).get('gate', {}).get('failed'):
                print('Scanner stability gate failed: volatility exceeded approved bounds.')
            elif fail_on:
                print(f'Policy gate failed: unresolved finding severity >= {fail_on}')
    if should_fail:
        return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
