#!/usr/bin/env python3
"""Advanced gate helpers for accessibility audit orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from baseline_governance import (
    _coerce_non_negative_int,
    _finding_signature_with_config,
    _normalize_signature_target,
)
from shared_constants import REPORT_SCHEMA_VERSION

RISK_CALIBRATION_MODES = {'off', 'warn', 'strict'}
RISK_CALIBRATION_SCHEMA_VERSION = '1.0.0'
RISK_CALIBRATION_EXIT_CODE = 46
RISK_CALIBRATION_MIN_SAMPLES = 3
RISK_CALIBRATION_PRECISION_THRESHOLD = 0.6
REPLAY_VERIFICATION_SCHEMA_VERSION = '1.0.0'
REPLAY_VERIFICATION_EXIT_CODE = 47
SCANNER_STABILITY_MODES = {'off', 'warn', 'fail'}
SCANNER_STABILITY_SCHEMA_VERSION = '1.0.0'
SCANNER_STABILITY_EXIT_CODE = 48
DEFAULT_SCANNER_STABILITY_WINDOW = 5
DEFAULT_SCANNER_STABILITY_MAX_VARIANCE = 0
HIGH_SEVERITY_LEVELS = {'critical', 'serious'}


def _is_actionable_outcome(finding: dict[str, Any]) -> bool:
    status = str(finding.get('status', '')).strip().lower()
    if status not in {'open', 'fixed'}:
        return False
    if bool(finding.get('manual_review_required')):
        return False
    return not bool(str(finding.get('downgrade_reason', '')).strip())


def _extract_rule_signals_from_report(report: dict[str, Any]) -> dict[str, dict[str, int]]:
    signals: dict[str, dict[str, int]] = {}
    findings = report.get('findings')
    if not isinstance(findings, list):
        return signals
    for item in findings:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get('rule_id', '')).strip()
        if not rule_id:
            continue
        severity = str(item.get('severity', 'info')).strip().lower()
        bucket = signals.setdefault(
            rule_id,
            {
                'observations': 0,
                'actionable_count': 0,
                'high_severity_observations': 0,
                'high_severity_actionable_count': 0,
            },
        )
        actionable = _is_actionable_outcome(item)
        bucket['observations'] += 1
        if actionable:
            bucket['actionable_count'] += 1
        if severity in HIGH_SEVERITY_LEVELS:
            bucket['high_severity_observations'] += 1
            if actionable:
                bucket['high_severity_actionable_count'] += 1
    return signals


def _merge_rule_signals(
    aggregate: dict[str, dict[str, int]],
    additional: dict[str, dict[str, int]],
) -> None:
    for rule_id, stats in additional.items():
        bucket = aggregate.setdefault(
            rule_id,
            {
                'observations': 0,
                'actionable_count': 0,
                'high_severity_observations': 0,
                'high_severity_actionable_count': 0,
            },
        )
        bucket['observations'] += int(stats.get('observations', 0))
        bucket['actionable_count'] += int(stats.get('actionable_count', 0))
        bucket['high_severity_observations'] += int(stats.get('high_severity_observations', 0))
        bucket['high_severity_actionable_count'] += int(stats.get('high_severity_actionable_count', 0))


def _load_risk_calibration_source(
    source_path: str | None,
) -> tuple[dict[str, dict[str, int]], dict[str, Any]]:
    if not source_path:
        return {}, {'downgrade_reason': 'missing-evidence', 'message': '--risk-calibration-source is required'}
    source = Path(source_path)
    if not source.exists():
        return {}, {'downgrade_reason': 'missing-evidence', 'message': f'source path does not exist: {source_path}'}

    aggregate: dict[str, dict[str, int]] = {}
    report_files = [source] if source.is_file() else sorted(source.rglob('*.json'))
    if not report_files:
        return {}, {'downgrade_reason': 'missing-evidence', 'message': 'no JSON evidence files found'}

    stale_schema_files: list[str] = []
    parsed_reports = 0
    for report_file in report_files:
        try:
            payload = json.loads(report_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue

        if 'rules' in payload and isinstance(payload.get('rules'), list) and 'findings' not in payload:
            schema_version = str(payload.get('schema_version', '')).strip()
            if schema_version and schema_version != RISK_CALIBRATION_SCHEMA_VERSION:
                return {}, {
                    'downgrade_reason': 'stale-schema',
                    'message': (
                        'risk calibration schema mismatch: '
                        f'{schema_version} != {RISK_CALIBRATION_SCHEMA_VERSION}'
                    ),
                }
            rule_entries = payload.get('rules', [])
            seen_rule_ids: set[str] = set()
            for entry in rule_entries:
                if not isinstance(entry, dict):
                    continue
                rule_id = str(entry.get('rule_id', '')).strip()
                if not rule_id:
                    continue
                if rule_id in seen_rule_ids:
                    return {}, {
                        'downgrade_reason': 'conflicting-rule-ids',
                        'message': f'duplicate rule_id in calibration artifact: {rule_id}',
                    }
                seen_rule_ids.add(rule_id)
                _merge_rule_signals(
                    aggregate,
                    {
                        rule_id: {
                            'observations': _coerce_non_negative_int(entry.get('observations')),
                            'actionable_count': _coerce_non_negative_int(entry.get('actionable_count')),
                            'high_severity_observations': _coerce_non_negative_int(
                                entry.get('high_severity_observations')
                            ),
                            'high_severity_actionable_count': _coerce_non_negative_int(
                                entry.get('high_severity_actionable_count')
                            ),
                        }
                    },
                )
            parsed_reports += 1
            continue

        schema_version = str(((payload.get('report_schema') or {}).get('version'))).strip()
        if schema_version and schema_version != REPORT_SCHEMA_VERSION:
            stale_schema_files.append(str(report_file))
            continue
        _merge_rule_signals(aggregate, _extract_rule_signals_from_report(payload))
        parsed_reports += 1

    if not aggregate:
        if stale_schema_files:
            return {}, {
                'downgrade_reason': 'stale-schema',
                'message': f'no usable evidence after schema filtering ({len(stale_schema_files)} stale files)',
            }
        return {}, {'downgrade_reason': 'missing-evidence', 'message': 'no usable findings in calibration source'}
    return aggregate, {
        'parsed_reports': parsed_reports,
        'scanned_files': len(report_files),
        'stale_schema_file_count': len(stale_schema_files),
    }


def _evaluate_risk_calibration(
    *,
    report: dict[str, Any],
    source_path: str | None,
    mode: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        'schema_version': RISK_CALIBRATION_SCHEMA_VERSION,
        'mode': mode,
        'source_path': source_path or '',
        'min_high_severity_samples': RISK_CALIBRATION_MIN_SAMPLES,
        'high_severity_precision_threshold': RISK_CALIBRATION_PRECISION_THRESHOLD,
        'applied': False,
        'downgrade_reason': None,
        'rules': [],
        'unstable_high_severity_rules': [],
        'source_meta': {},
    }
    if mode == 'off':
        result['applied'] = False
        result['downgrade_reason'] = 'mode-off'
        return result

    signals, source_meta = _load_risk_calibration_source(source_path)
    result['source_meta'] = source_meta
    if not signals:
        result['downgrade_reason'] = str(source_meta.get('downgrade_reason') or 'missing-evidence')
        return result

    current_high_rule_ids = sorted(
        {
            str(item.get('rule_id', '')).strip()
            for item in report.get('findings', [])
            if isinstance(item, dict)
            and str(item.get('severity', 'info')).strip().lower() in HIGH_SEVERITY_LEVELS
            and str(item.get('status', '')).strip().lower() != 'fixed'
            and str(item.get('rule_id', '')).strip()
        }
    )
    result['current_high_severity_rules'] = current_high_rule_ids

    rule_rows: list[dict[str, Any]] = []
    unstable_rules: list[str] = []
    for rule_id in sorted(signals):
        stats = signals[rule_id]
        observations = int(stats.get('observations', 0))
        actionable_count = int(stats.get('actionable_count', 0))
        high_observations = int(stats.get('high_severity_observations', 0))
        high_actionable = int(stats.get('high_severity_actionable_count', 0))
        precision = round((actionable_count / observations), 4) if observations else 0.0
        high_precision = round((high_actionable / high_observations), 4) if high_observations else None
        unstable = bool(
            rule_id in current_high_rule_ids
            and high_observations >= RISK_CALIBRATION_MIN_SAMPLES
            and high_precision is not None
            and high_precision < RISK_CALIBRATION_PRECISION_THRESHOLD
        )
        if unstable:
            unstable_rules.append(rule_id)
        rule_rows.append(
            {
                'rule_id': rule_id,
                'observations': observations,
                'actionable_count': actionable_count,
                'precision': precision,
                'high_severity_observations': high_observations,
                'high_severity_actionable_count': high_actionable,
                'high_severity_precision': high_precision,
                'unstable_high_severity': unstable,
            }
        )

    result['applied'] = True
    result['rules'] = rule_rows
    result['unstable_high_severity_rules'] = unstable_rules
    return result


def _extract_available_scanners(report: dict[str, Any]) -> set[str]:
    scanner_capabilities = report.get('run_meta', {}).get('scanner_capabilities', {})
    scanners = scanner_capabilities.get('scanners', {})
    if not isinstance(scanners, dict):
        return set()
    return {
        name
        for name, info in scanners.items()
        if isinstance(info, dict) and bool(info.get('available'))
    }


def _collect_replay_signature_rows(
    report: dict[str, Any],
    signature_config: dict[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    effective_signature_config = signature_config or {
        'include_target_in_signature': False,
        'target_normalization': 'none',
        'selector_canonicalization': 'none',
    }
    report_target = str(report.get('target', {}).get('value', '')).strip()
    rows: dict[str, dict[str, str]] = {}
    for finding in report.get('findings', []):
        if not isinstance(finding, dict):
            continue
        if finding.get('status') == 'fixed':
            continue
        signature = _finding_signature_with_config(finding, effective_signature_config, report_target)
        rows[signature] = {
            'signature': signature,
            'rule_id': str(finding.get('rule_id', '')).strip(),
            'severity': str(finding.get('severity', 'info')).strip() or 'info',
        }
    return rows


def _load_replay_source_report(replay_dir: Path) -> tuple[dict[str, Any], Path]:
    source_report_path = replay_dir / 'wcag-report.json'
    if not source_report_path.exists():
        raise ValueError(
            '--replay-verify-from must point to a directory containing wcag-report.json: '
            + str(source_report_path)
        )
    payload = json.loads(source_report_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('replay source report must be a JSON object')
    return payload, source_report_path


def _build_replay_diff_markdown(
    replay_summary: dict[str, Any],
    output_path: Path,
) -> None:
    lines = [
        '# Replay Verification Diff',
        '',
        f"- Source report: `{replay_summary.get('source_report_path', '')}`",
        f"- Generated at: `{replay_summary.get('generated_at', '')}`",
        f"- Gate failed: `{replay_summary.get('gate', {}).get('failed', False)}`",
        '',
        '| Signature | Rule | Severity | Replay Status |',
        '|---|---|---|---|',
    ]
    for item in replay_summary.get('findings', []):
        signature = str(item.get('signature', '')).replace('|', '\\|')
        lines.append(
            f"| `{signature}` | `{item.get('rule_id', '')}` | `{item.get('severity', 'info')}` | `{item.get('status', '')}` |"
        )
    output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _build_replay_verification_summary(
    current_report: dict[str, Any],
    replay_source_report: dict[str, Any],
    replay_source_path: Path,
    replay_source_dir: Path,
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    generated_at = (now_utc or datetime.now(timezone.utc)).isoformat().replace('+00:00', 'Z')
    signature_config = {
        'include_target_in_signature': False,
        'target_normalization': 'none',
        'selector_canonicalization': 'none',
    }
    source_rows = _collect_replay_signature_rows(replay_source_report, signature_config)
    current_rows = _collect_replay_signature_rows(current_report, signature_config)
    source_signatures = set(source_rows)
    current_signatures = set(current_rows)

    source_target = _normalize_signature_target(
        str(replay_source_report.get('target', {}).get('value', '')).strip(),
        'path-only',
    )
    current_target = _normalize_signature_target(
        str(current_report.get('target', {}).get('value', '')).strip(),
        'path-only',
    )
    source_scanners = sorted(_extract_available_scanners(replay_source_report))
    current_scanners = sorted(_extract_available_scanners(current_report))

    nondeterministic_reasons: list[str] = []
    target_drift = bool(source_target and current_target and source_target != current_target)
    scanner_drift = source_scanners != current_scanners
    if target_drift:
        nondeterministic_reasons.append(
            f'target-drift: source={source_target} current={current_target}'
        )
    if scanner_drift:
        nondeterministic_reasons.append(
            'scanner-capability-drift: source=' + ','.join(source_scanners) + ' current=' + ','.join(current_scanners)
        )

    findings_rows: list[dict[str, str]] = []
    for signature in sorted(source_signatures - current_signatures):
        source = source_rows[signature]
        findings_rows.append(
            {
                'signature': signature,
                'rule_id': source.get('rule_id', ''),
                'severity': source.get('severity', 'info'),
                'status': 'resolved',
            }
        )
    for signature in sorted(source_signatures & current_signatures):
        current = current_rows[signature]
        findings_rows.append(
            {
                'signature': signature,
                'rule_id': current.get('rule_id', ''),
                'severity': current.get('severity', 'info'),
                'status': 'unchanged',
            }
        )
    for signature in sorted(current_signatures - source_signatures):
        current = current_rows[signature]
        findings_rows.append(
            {
                'signature': signature,
                'rule_id': current.get('rule_id', ''),
                'severity': current.get('severity', 'info'),
                'status': 'non-deterministic' if nondeterministic_reasons else 'regressed',
            }
        )

    status_counts = {
        'resolved': sum(1 for item in findings_rows if item.get('status') == 'resolved'),
        'unchanged': sum(1 for item in findings_rows if item.get('status') == 'unchanged'),
        'regressed': sum(1 for item in findings_rows if item.get('status') == 'regressed'),
        'non-deterministic': sum(1 for item in findings_rows if item.get('status') == 'non-deterministic'),
    }
    high_severity_regressed = [
        item for item in findings_rows
        if item.get('status') == 'regressed' and str(item.get('severity', 'info')) in HIGH_SEVERITY_LEVELS
    ]
    gate_failed = len(high_severity_regressed) > 0
    gate = {
        'failed': gate_failed,
        'exit_code': REPLAY_VERIFICATION_EXIT_CODE if gate_failed else 0,
        'high_severity_regressed_count': len(high_severity_regressed),
        'high_severity_regressed_signatures': [item.get('signature', '') for item in high_severity_regressed],
    }
    return {
        'schema_version': REPLAY_VERIFICATION_SCHEMA_VERSION,
        'source_report_dir': str(replay_source_dir),
        'source_report_path': str(replay_source_path),
        'generated_at': generated_at,
        'source_scanners': source_scanners,
        'current_scanners': current_scanners,
        'non_deterministic_reasons': nondeterministic_reasons,
        'status_counts': status_counts,
        'gate': gate,
        'findings': findings_rows,
    }


def _normalize_stability_scanner(scanner: Any) -> str:
    value = str(scanner or '').strip().lower()
    if value in {'axe', 'lighthouse'}:
        return value
    return ''


def _stability_signature(scanner: str, rule_id: str, target: str) -> str:
    return f'{scanner}|{rule_id}|{target}'


def _parse_stability_signature(signature: str) -> tuple[str, str, str]:
    parts = signature.split('|', 2)
    if len(parts) != 3:
        return '', '', ''
    return parts[0], parts[1], parts[2]


def _sanitize_scanner_stability_row(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    scanner = _normalize_stability_scanner(raw.get('scanner'))
    rule_id = str(raw.get('rule_id', '')).strip()
    target = str(raw.get('target', '')).strip() or 'unknown'
    if not scanner or not rule_id:
        return None
    return {
        'scanner': scanner,
        'rule_id': rule_id,
        'target': target,
        'finding_count': _coerce_non_negative_int(raw.get('finding_count')),
    }


def _sanitize_scanner_stability_point(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    raw_rows = raw.get('rows')
    if not isinstance(raw_rows, list):
        return None
    rows = [row for row in (_sanitize_scanner_stability_row(item) for item in raw_rows) if row is not None]
    available_scanners = sorted(
        {
            scanner
            for scanner in (_normalize_stability_scanner(item) for item in raw.get('available_scanners', []))
            if scanner
        }
    )
    return {
        'recorded_at': str(raw.get('recorded_at', '')).strip() or '',
        'target': str(raw.get('target', '')).strip() or '',
        'available_scanners': available_scanners,
        'rows': rows,
    }


def _extract_scanner_stability_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings = report.get('findings')
    if not isinstance(findings, list):
        return []

    counts: dict[tuple[str, str, str], int] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if finding.get('status') == 'fixed':
            continue
        rule_id = str(finding.get('rule_id', '')).strip()
        if not rule_id:
            continue
        target = str(finding.get('changed_target', '')).strip() or 'unknown'

        source_values = finding.get('sources')
        if not isinstance(source_values, list):
            source_values = [finding.get('source')]
        scanners = {
            scanner
            for scanner in (_normalize_stability_scanner(item) for item in source_values)
            if scanner
        }
        for scanner in scanners:
            key = (scanner, rule_id, target)
            counts[key] = counts.get(key, 0) + 1

    rows = [
        {
            'scanner': scanner,
            'rule_id': rule_id,
            'target': target,
            'finding_count': count,
        }
        for (scanner, rule_id, target), count in counts.items()
    ]
    return sorted(rows, key=lambda item: (item['scanner'], item['rule_id'], item['target']))


def _normalize_scanner_stability_bounds(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            'default_max_variance': DEFAULT_SCANNER_STABILITY_MAX_VARIANCE,
            'per_signature': {},
        }
    default_max = _coerce_non_negative_int(raw.get('default_max_variance'))
    raw_per_signature = raw.get('per_signature')
    per_signature: dict[str, int] = {}
    if isinstance(raw_per_signature, dict):
        for signature, value in raw_per_signature.items():
            key = str(signature).strip()
            if not key:
                continue
            per_signature[key] = _coerce_non_negative_int(value)
    return {
        'default_max_variance': default_max,
        'per_signature': per_signature,
    }


def _extract_historical_scanner_stability_points(
    baseline_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], int]:
    history_meta = {'history_reset_reason': 'missing-history', 'loaded_point_count': 0}
    approved_bounds = _normalize_scanner_stability_bounds(None)
    window = DEFAULT_SCANNER_STABILITY_WINDOW

    if not baseline_payload:
        return [], history_meta, approved_bounds, window

    if 'points' in baseline_payload and isinstance(baseline_payload.get('points'), list):
        schema_version = str(baseline_payload.get('schema_version', '')).strip()
        if schema_version and schema_version != SCANNER_STABILITY_SCHEMA_VERSION:
            return [], {
                'history_reset_reason': 'stability-schema-version-mismatch',
                'baseline_stability_schema_version': schema_version,
                'expected_stability_schema_version': SCANNER_STABILITY_SCHEMA_VERSION,
                'loaded_point_count': 0,
            }, approved_bounds, window

        points = [
            point
            for point in (_sanitize_scanner_stability_point(item) for item in baseline_payload.get('points', []))
            if point is not None
        ]
        history_meta = {
            'history_reset_reason': None,
            'loaded_point_count': len(points),
        }
        approved_bounds = _normalize_scanner_stability_bounds(baseline_payload.get('approved_bounds'))
        window = max(1, _coerce_non_negative_int(baseline_payload.get('window')) or DEFAULT_SCANNER_STABILITY_WINDOW)
        return points, history_meta, approved_bounds, window

    report_schema_version = str(((baseline_payload.get('report_schema') or {}).get('version'))).strip()
    if report_schema_version and report_schema_version != REPORT_SCHEMA_VERSION:
        return [], {
            'history_reset_reason': 'schema-version-mismatch',
            'baseline_report_schema_version': report_schema_version,
            'expected_report_schema_version': REPORT_SCHEMA_VERSION,
            'loaded_point_count': 0,
        }, approved_bounds, window

    run_meta = baseline_payload.get('run_meta')
    if not isinstance(run_meta, dict):
        return [], history_meta, approved_bounds, window
    stability = run_meta.get('scanner_stability')
    if not isinstance(stability, dict):
        return [], history_meta, approved_bounds, window

    schema_version = str(stability.get('schema_version', '')).strip()
    if schema_version and schema_version != SCANNER_STABILITY_SCHEMA_VERSION:
        return [], {
            'history_reset_reason': 'stability-schema-version-mismatch',
            'baseline_stability_schema_version': schema_version,
            'expected_stability_schema_version': SCANNER_STABILITY_SCHEMA_VERSION,
            'loaded_point_count': 0,
        }, approved_bounds, window

    raw_points = stability.get('points')
    if not isinstance(raw_points, list):
        return [], history_meta, approved_bounds, window

    points = [point for point in (_sanitize_scanner_stability_point(item) for item in raw_points) if point is not None]
    history_meta = {'history_reset_reason': None, 'loaded_point_count': len(points)}
    approved_bounds = _normalize_scanner_stability_bounds(stability.get('approved_bounds'))
    window = max(1, _coerce_non_negative_int(stability.get('window')) or DEFAULT_SCANNER_STABILITY_WINDOW)
    return points, history_meta, approved_bounds, window


def _load_stability_baseline_payload(
    baseline_path: str | None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    if not baseline_path:
        return {}, {
            'history_reset_reason': 'missing-history',
            'loaded_point_count': 0,
            'message': '--stability-baseline is not provided',
        }, ''

    source = Path(baseline_path)
    if not source.exists():
        return {}, {
            'history_reset_reason': 'missing-history',
            'loaded_point_count': 0,
            'message': f'stability baseline does not exist: {baseline_path}',
        }, ''

    source_path = source
    if source.is_dir():
        ledger_path = source / 'scanner-stability.json'
        report_path = source / 'wcag-report.json'
        if ledger_path.exists():
            source_path = ledger_path
        elif report_path.exists():
            source_path = report_path
        else:
            return {}, {
                'history_reset_reason': 'missing-history',
                'loaded_point_count': 0,
                'message': 'stability baseline directory is missing scanner-stability.json and wcag-report.json',
            }, str(source)

    try:
        payload = json.loads(source_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}, {
            'history_reset_reason': 'invalid-baseline',
            'loaded_point_count': 0,
            'message': f'failed to parse stability baseline: {source_path}',
        }, str(source_path)

    if not isinstance(payload, dict):
        return {}, {
            'history_reset_reason': 'invalid-baseline',
            'loaded_point_count': 0,
            'message': 'stability baseline must be a JSON object',
        }, str(source_path)

    return payload, {'history_reset_reason': None, 'loaded_point_count': 0}, str(source_path)


def _build_scanner_stability_payload(
    *,
    now_utc: datetime,
    mode: str,
    current_report: dict[str, Any],
    baseline_path: str | None,
) -> dict[str, Any]:
    baseline_payload, baseline_meta, baseline_source_path = _load_stability_baseline_payload(baseline_path)
    history_points, history_meta, approved_bounds, window = _extract_historical_scanner_stability_points(baseline_payload)

    if baseline_meta.get('history_reset_reason'):
        history_meta = {
            **history_meta,
            **baseline_meta,
        }

    current_point = {
        'recorded_at': now_utc.isoformat().replace('+00:00', 'Z'),
        'target': str(current_report.get('target', {}).get('value', '')).strip(),
        'available_scanners': sorted(_extract_available_scanners(current_report)),
        'rows': _extract_scanner_stability_rows(current_report),
    }

    merged_points = history_points + [current_point]
    points = merged_points[-window:]

    series: dict[str, list[int]] = {}
    for point in points:
        for row in point.get('rows', []):
            signature = _stability_signature(row['scanner'], row['rule_id'], row['target'])
            series.setdefault(signature, []).append(_coerce_non_negative_int(row.get('finding_count')))

    variance_rows: list[dict[str, Any]] = []
    for signature, samples in sorted(series.items()):
        scanner, rule_id, target = _parse_stability_signature(signature)
        if not scanner or not rule_id:
            continue
        low = min(samples) if samples else 0
        high = max(samples) if samples else 0
        variance_rows.append(
            {
                'scanner': scanner,
                'rule_id': rule_id,
                'target': target,
                'samples': len(samples),
                'min_count': low,
                'max_count': high,
                'variance': high - low,
                'latest_count': samples[-1] if samples else 0,
            }
        )

    previous_point = points[-2] if len(points) > 1 else None
    current_rows_map = {
        _stability_signature(item['scanner'], item['rule_id'], item['target']): _coerce_non_negative_int(item['finding_count'])
        for item in current_point['rows']
    }
    previous_rows_map: dict[str, int] = {}
    previous_scanners: list[str] = []
    if previous_point:
        previous_rows_map = {
            _stability_signature(item['scanner'], item['rule_id'], item['target']): _coerce_non_negative_int(item['finding_count'])
            for item in previous_point.get('rows', [])
        }
        previous_scanners = sorted(
            {
                scanner
                for scanner in (
                    _normalize_stability_scanner(item) for item in previous_point.get('available_scanners', [])
                )
                if scanner
            }
        )

    signatures = sorted(set(current_rows_map) | set(previous_rows_map))
    breaches: list[dict[str, Any]] = []
    max_delta = 0
    for signature in signatures:
        previous_count = previous_rows_map.get(signature, 0)
        current_count = current_rows_map.get(signature, 0)
        delta = abs(current_count - previous_count)
        allowed = approved_bounds['per_signature'].get(signature, approved_bounds['default_max_variance'])
        max_delta = max(max_delta, delta)
        if delta > allowed:
            scanner, rule_id, target = _parse_stability_signature(signature)
            breaches.append(
                {
                    'signature': signature,
                    'scanner': scanner,
                    'rule_id': rule_id,
                    'target': target,
                    'previous_count': previous_count,
                    'current_count': current_count,
                    'delta': delta,
                    'allowed_max_variance': allowed,
                }
            )

    current_scanners = current_point['available_scanners']
    scanner_capability_changed = bool(previous_point) and previous_scanners != current_scanners

    downgrade_reason: str | None = None
    if mode == 'off':
        downgrade_reason = 'mode-off'
    elif previous_point is None:
        downgrade_reason = 'missing-history'
    elif scanner_capability_changed:
        downgrade_reason = 'scanner-capability-changed'

    gate_failed = mode == 'fail' and downgrade_reason is None and len(breaches) > 0

    return {
        'schema_version': SCANNER_STABILITY_SCHEMA_VERSION,
        'generated_at': now_utc.isoformat().replace('+00:00', 'Z'),
        'mode': mode,
        'baseline_source': baseline_source_path,
        'window': window,
        'points': points,
        'variance_rows': variance_rows,
        'approved_bounds': approved_bounds,
        'comparison': {
            'evaluated_signature_count': len(signatures),
            'breach_count': len(breaches),
            'max_delta': max_delta,
            'breaches': breaches,
            'scanner_capability_changed': scanner_capability_changed,
            'previous_scanners': previous_scanners,
            'current_scanners': current_scanners,
        },
        'history_meta': history_meta,
        'gate': {
            'mode': mode,
            'evaluated': downgrade_reason is None,
            'failed': gate_failed,
            'exit_code': SCANNER_STABILITY_EXIT_CODE if gate_failed else 0,
            'downgrade_reason': downgrade_reason,
        },
    }


def _resolve_advanced_gate_exit_code(
    *,
    risk_calibration: dict[str, Any] | None,
    replay_verification: dict[str, Any] | None,
    scanner_stability: dict[str, Any] | None,
) -> tuple[bool, int, list[str]]:
    notes: list[str] = []
    if risk_calibration and risk_calibration.get('gate', {}).get('failed'):
        notes.append(
            'Risk calibration gate failed: unstable high-severity rules detected under --risk-calibration-mode=strict '
            f"({', '.join(risk_calibration.get('unstable_high_severity_rules', []))})."
        )
    if replay_verification and replay_verification.get('gate', {}).get('failed'):
        notes.append('Replay verification gate failed: high-severity regressed findings were introduced.')
    if scanner_stability and scanner_stability.get('gate', {}).get('failed'):
        notes.append('Scanner stability gate failed: volatility exceeded approved bounds under --stability-mode=fail.')

    if risk_calibration and risk_calibration.get('gate', {}).get('failed'):
        return True, RISK_CALIBRATION_EXIT_CODE, notes
    if replay_verification and replay_verification.get('gate', {}).get('failed'):
        return True, REPLAY_VERIFICATION_EXIT_CODE, notes
    if scanner_stability and scanner_stability.get('gate', {}).get('failed'):
        return True, SCANNER_STABILITY_EXIT_CODE, notes
    return False, 0, notes


__all__ = [
    'DEFAULT_SCANNER_STABILITY_MAX_VARIANCE',
    'DEFAULT_SCANNER_STABILITY_WINDOW',
    'HIGH_SEVERITY_LEVELS',
    'REPLAY_VERIFICATION_EXIT_CODE',
    'REPLAY_VERIFICATION_SCHEMA_VERSION',
    'RISK_CALIBRATION_EXIT_CODE',
    'RISK_CALIBRATION_MIN_SAMPLES',
    'RISK_CALIBRATION_MODES',
    'RISK_CALIBRATION_PRECISION_THRESHOLD',
    'RISK_CALIBRATION_SCHEMA_VERSION',
    'SCANNER_STABILITY_EXIT_CODE',
    'SCANNER_STABILITY_MODES',
    'SCANNER_STABILITY_SCHEMA_VERSION',
    '_build_replay_diff_markdown',
    '_build_replay_verification_summary',
    '_build_scanner_stability_payload',
    '_collect_replay_signature_rows',
    '_evaluate_risk_calibration',
    '_extract_available_scanners',
    '_extract_historical_scanner_stability_points',
    '_extract_rule_signals_from_report',
    '_extract_scanner_stability_rows',
    '_is_actionable_outcome',
    '_load_replay_source_report',
    '_load_risk_calibration_source',
    '_load_stability_baseline_payload',
    '_merge_rule_signals',
    '_normalize_scanner_stability_bounds',
    '_normalize_stability_scanner',
    '_parse_stability_signature',
    '_resolve_advanced_gate_exit_code',
    '_sanitize_scanner_stability_point',
    '_sanitize_scanner_stability_row',
    '_stability_signature',
]
