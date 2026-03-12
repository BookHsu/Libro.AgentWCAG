#!/usr/bin/env python3
"""Run axe and Lighthouse scans, then emit normalized WCAG outputs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import url2pathname

from auto_fix import (
    apply_report_fixes,
    supports_apply_fixes_target,
    target_to_local_path,
    write_diff,
    write_snapshot,
)
from wcag_workflow import normalize_report, resolve_contract, to_markdown_table, write_report_files

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_SCANNER_RETRY_ATTEMPTS = 1
DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS = 0.5
MAX_SCANNER_RETRY_BACKOFF_SECONDS = 5.0
ALLOWED_URL_SCHEMES = {"http", "https", "file"}
PREFLIGHT_TOOL_CHECKS = (
    ("npx", ["npx", "--version"]),
    ("@axe-core/cli", ["npx", "--no-install", "@axe-core/cli", "--version"]),
    ("lighthouse", ["npx", "--no-install", "lighthouse", "--version"]),
)
SEVERITY_RANK = {"critical": 4, "serious": 3, "moderate": 2, "minor": 1, "info": 0}
FAIL_ON_EXIT_CODES = {"critical": 42, "serious": 43, "moderate": 44}


def _extract_version_line(output: str) -> str | None:
    for line in output.splitlines():
        value = line.strip()
        if value:
            return value
    return None


def _run_command(command: list[str], timeout_seconds: int) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"command timed out after {timeout_seconds} seconds"
    except FileNotFoundError as err:
        return False, f"command not found: {err.filename or command[0]}"
    if completed.returncode == 0:
        return True, completed.stdout
    error = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
    return False, error


def _is_transient_scanner_error(error_message: str | None) -> bool:
    text = (error_message or "").lower()
    return any(
        token in text
        for token in (
            "timed out",
            "econnreset",
            "econnrefused",
            "eai_again",
            "temporarily unavailable",
            "temporary failure",
            "network",
        )
    )


def _run_scanner_with_retry(
    scanner: str,
    runner: Callable[[], tuple[dict[str, Any] | None, str | None]],
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    attempts = max(1, retry_attempts)
    initial_backoff = max(0.0, retry_backoff_seconds)
    transient_error = False
    data: dict[str, Any] | None = None
    error: str | None = None

    for attempt in range(1, attempts + 1):
        data, error = runner()
        if data is not None and not error:
            return data, None, {
                "tool": scanner,
                "attempts": attempt,
                "retry_count": attempt - 1,
                "succeeded": True,
                "last_error": "",
                "transient_error": False,
            }

        transient_error = _is_transient_scanner_error(error)
        should_retry = attempt < attempts and transient_error
        if not should_retry:
            break

        if initial_backoff > 0:
            delay = min(
                initial_backoff * (2 ** (attempt - 1)),
                MAX_SCANNER_RETRY_BACKOFF_SECONDS,
            )
            time.sleep(delay)

    return data, error, {
        "tool": scanner,
        "attempts": attempt,
        "retry_count": attempt - 1,
        "succeeded": False,
        "last_error": error or "unknown error",
        "transient_error": transient_error,
    }


def _try_run_axe(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    axe_json = output_dir / "axe.raw.json"
    command = ["npx", "@axe-core/cli", target, "--save", str(axe_json)]
    ok, result = _run_command(command, timeout_seconds)
    if not ok:
        return None, result
    if not axe_json.exists():
        return None, "axe did not generate output json"
    with axe_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _try_run_lighthouse(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    lighthouse_json = output_dir / "lighthouse.raw.json"
    command = [
        "npx",
        "lighthouse",
        target,
        "--only-categories=accessibility",
        "--output=json",
        f"--output-path={lighthouse_json}",
        "--chrome-flags=--headless=new",
    ]
    ok, result = _run_command(command, timeout_seconds)
    if not ok:
        return None, result
    if not lighthouse_json.exists():
        return None, "lighthouse did not generate output json"
    with lighthouse_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _resolve_target_for_scanners(target: str) -> str:
    local_path = Path(target)
    if local_path.exists():
        return local_path.resolve().as_uri()
    parsed = urlparse(target)
    if parsed.scheme:
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            raise ValueError(f"Unsupported target scheme: {parsed.scheme}")
        if parsed.scheme == "file":
            if parsed.netloc not in {"", "localhost"}:
                raise ValueError(f"Unsupported file target host: {parsed.netloc}")
            file_path = Path(url2pathname(parsed.path))
            if not file_path.exists():
                raise ValueError(f"Target file does not exist: {target}")
        return target
    if "://" in target:
        raise ValueError(f"Unsupported target scheme in: {target}")
    raise ValueError(f"Target must be an existing local file or a valid URL: {target}")


def _tool_available(tool: str) -> bool:
    return shutil.which(tool) is not None


def run_preflight_checks(timeout_seconds: int) -> dict[str, Any]:
    results: list[dict[str, str]] = []
    tools: dict[str, dict[str, str]] = {}
    ok = True
    for name, command in PREFLIGHT_TOOL_CHECKS:
        command_text = " ".join(command)
        resolved_command = shutil.which(command[0]) or ""
        if not _tool_available(command[0]):
            message = f'{command[0]} is not available in PATH'
            entry = {
                "tool": name,
                "status": "error",
                "message": message,
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
            }
            results.append(entry)
            tools[name] = {
                "status": "error",
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
                "message": message,
            }
            ok = False
            continue
        command_ok, output = _run_command(command, timeout_seconds)
        status = "ok" if command_ok else "error"
        message = (output or "").strip() or ("available" if command_ok else "check failed")
        version = _extract_version_line(output) if command_ok else ""
        entry = {
            "tool": name,
            "status": status,
            "message": message,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
        }
        results.append(entry)
        tools[name] = {
            "status": status,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
            "message": message,
        }
        ok = ok and command_ok
    return {"ok": ok, "checks": results, "tools": tools}


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def _load_policy_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        raise ValueError(f'policy config file does not exist: {path}')
    payload = json.loads(config_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('--policy-config must point to a JSON object')
    return payload


def _load_baseline_report(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    baseline_path = Path(path)
    if not baseline_path.exists():
        raise ValueError(f'baseline report file does not exist: {path}')
    payload = json.loads(baseline_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('--baseline-report must point to a JSON object')
    findings = payload.get('findings')
    if findings is None:
        payload['findings'] = []
    elif not isinstance(findings, list):
        raise ValueError('--baseline-report JSON must include findings as a list')
    return payload

def _normalize_rule_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f'{name} must be a list of rule ids')
    return [item.strip() for item in value if item.strip()]


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

def _finding_signature(finding: dict[str, Any]) -> str:
    rule_id = str(finding.get('rule_id', '')).strip()
    changed_target = str(finding.get('changed_target', '')).strip()
    return f'{rule_id}|{changed_target}'


def _unresolved_finding_signatures(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    signatures: dict[str, dict[str, Any]] = {}
    for finding in report.get('findings', []):
        if finding.get('status') == 'fixed':
            continue
        signatures[_finding_signature(finding)] = finding
    return signatures


def _build_baseline_diff(current_report: dict[str, Any], baseline_report: dict[str, Any]) -> dict[str, Any]:
    current_findings = _unresolved_finding_signatures(current_report)
    baseline_findings = _unresolved_finding_signatures(baseline_report)
    current_keys = set(current_findings)
    baseline_keys = set(baseline_findings)
    introduced_keys = sorted(current_keys - baseline_keys)
    resolved_keys = sorted(baseline_keys - current_keys)
    persistent_keys = sorted(current_keys & baseline_keys)

    return {
        'current_unresolved_count': len(current_keys),
        'baseline_unresolved_count': len(baseline_keys),
        'introduced_count': len(introduced_keys),
        'resolved_count': len(resolved_keys),
        'persistent_count': len(persistent_keys),
        'introduced_signatures': introduced_keys,
        'resolved_signatures': resolved_keys,
        'persistent_signatures': persistent_keys,
        'introduced_findings': [current_findings[key] for key in introduced_keys],
    }

def _report_to_sarif(report: dict[str, Any], contract_target: str, local_target: Path | None) -> dict[str, Any]:
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

        results.append(
            {
                'ruleId': rule_id,
                'level': _sarif_level_from_severity(str(finding.get('severity', 'info'))),
                'message': {'text': ' | '.join(message_parts)},
                'locations': [
                    {
                        'physicalLocation': {
                            'artifactLocation': {
                                'uri': location_uri,
                            }
                        }
                    }
                ],
                'properties': {
                    'finding_id': finding.get('id'),
                    'status': finding.get('status'),
                    'sc': finding.get('sc', []),
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
                        'name': 'libro-agent-wcag',
                        'rules': list(rules.values()),
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
    parser.add_argument("--target", required=True)
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
        "--baseline-report",
        help="Optional prior JSON report to compare unresolved debt and detect newly introduced findings.",
    )
    parser.add_argument(
        "--fail-on-new-only",
        action="store_true",
        help="When used with --fail-on and --baseline-report, fail only on newly introduced debt.",
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
        "--preflight-only",
        action="store_true",
        help="Check runtime tooling availability (npx, axe, lighthouse) and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy_config = _load_policy_config(args.policy_config)
    baseline_report = _load_baseline_report(args.baseline_report)
    config_report_format = policy_config.get('report_format')
    config_fail_on = policy_config.get('fail_on')
    config_include = _normalize_rule_list(policy_config.get('include_rules'), 'include_rules')
    config_ignore = _normalize_rule_list(policy_config.get('ignore_rules'), 'ignore_rules')

    if config_report_format and config_report_format not in {'json', 'sarif'}:
        raise ValueError('policy-config report_format must be one of: json, sarif')
    if config_fail_on and config_fail_on not in {'critical', 'serious', 'moderate'}:
        raise ValueError('policy-config fail_on must be one of: critical, serious, moderate')

    report_format = args.report_format or config_report_format or 'json'
    fail_on = args.fail_on or config_fail_on
    include_rules = config_include + [item.strip() for item in args.include_rule if item.strip()]
    ignore_rules = config_ignore + [item.strip() for item in args.ignore_rule if item.strip()]

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
    if args.fail_on_new_only and not args.fail_on:
        raise ValueError('--fail-on-new-only requires --fail-on')
    if args.fail_on_new_only and not args.baseline_report:
        raise ValueError('--fail-on-new-only requires --baseline-report')

    if args.preflight_only:
        preflight = run_preflight_checks(args.timeout)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0 if preflight["ok"] else 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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
                }
            ],
            "tools": {
                "runtime": {
                    "status": "skipped",
                    "command": "",
                    "resolved_command": "",
                    "version": "",
                    "message": "scanner tooling preflight skipped due to mock or skip flags",
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
    report['run_meta']['preflight'] = preflight
    report['run_meta']['retry_policy'] = {
        'attempts': args.scanner_retry_attempts,
        'initial_backoff_seconds': args.scanner_retry_backoff_seconds,
        'max_backoff_seconds': MAX_SCANNER_RETRY_BACKOFF_SECONDS,
    }
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
            'include_rules': include_rules,
            'ignore_rules': ignore_rules,
            'before_filter_count': before_policy_count,
            'after_filter_count': after_policy_count,
        }
        report['run_meta']['notes'].append(
            f'Rule policy filter applied: {before_policy_count} -> {after_policy_count} findings.'
        )

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
    if baseline_report:
        baseline_diff = _build_baseline_diff(report, baseline_report)
        report['run_meta']['baseline_diff'] = {
            **baseline_diff,
            'baseline_report_path': args.baseline_report,
        }
        report['run_meta']['notes'].append(
            (
                'Baseline diff: introduced='
                f"{baseline_diff['introduced_count']}, "
                f"resolved={baseline_diff['resolved_count']}, "
                f"persistent={baseline_diff['persistent_count']}."
            )
        )

    output_json = output_dir / 'wcag-report.json'
    output_md = output_dir / 'wcag-report.md'
    if report_format == 'json':
        write_report_files(report, str(output_json), str(output_md))
        machine_output = output_json
    else:
        output_sarif = output_dir / 'wcag-report.sarif'
        output_sarif.write_text(
            json.dumps(_report_to_sarif(report, contract.target, local_target), ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(to_markdown_table(report), encoding='utf-8')
        machine_output = output_sarif

    if fail_on:
        gate_report = report
        gate_scope = 'all-unresolved'
        if args.fail_on_new_only:
            introduced_signatures = set((baseline_diff or {}).get('introduced_signatures', []))
            gate_report = {
                **report,
                'findings': [
                    item for item in report.get('findings', []) if _finding_signature(item) in introduced_signatures
                ],
            }
            gate_scope = 'introduced-only'
        should_fail, exit_code = _resolve_fail_threshold(gate_report, fail_on)
        report['run_meta']['policy_gate'] = {
            'fail_on': fail_on,
            'failed': should_fail,
            'exit_code': exit_code if should_fail else 0,
            'scope': gate_scope,
        }
        if report_format == 'json':
            write_report_files(report, str(output_json), str(output_md))
        elif machine_output.suffix == '.sarif':
            output_sarif = machine_output
            output_sarif.write_text(
                json.dumps(_report_to_sarif(report, contract.target, local_target), ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            output_md.write_text(to_markdown_table(report), encoding='utf-8')
    else:
        should_fail, exit_code = False, 0

    print(f'Saved machine-readable report ({report_format}): {machine_output}')
    print(f'Saved Markdown table: {output_md}')
    if report['run_meta']['notes']:
        print('Notes:')
        for note in report['run_meta']['notes']:
            print(f'- {note}')
    if should_fail:
        print(f'Policy gate failed: unresolved finding severity >= {fail_on}')
        return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

