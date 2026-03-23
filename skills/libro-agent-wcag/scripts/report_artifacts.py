#!/usr/bin/env python3
"""Artifact and output helpers for accessibility audit orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from baseline_governance import _sha256_file, _utc_timestamp
from shared_constants import REPORT_SCHEMA_VERSION, get_product_provenance

REPORT_SCHEMA_NAME = 'libro-agent-wcag-report'
REPORT_SCHEMA_FILENAME = f'wcag-report-{REPORT_SCHEMA_VERSION}.schema.json'


def _report_schema_source_path() -> Path:
    return Path(__file__).resolve().parents[1] / 'schemas' / REPORT_SCHEMA_FILENAME


def _stage_report_schema_artifact(output_dir: Path) -> tuple[dict[str, Any], Path]:
    schema_source_path = _report_schema_source_path()
    if not schema_source_path.exists():
        raise FileNotFoundError(f'report schema file is missing: {schema_source_path}')
    schema_dir = output_dir / 'schemas'
    schema_dir.mkdir(parents=True, exist_ok=True)
    staged_path = schema_dir / REPORT_SCHEMA_FILENAME
    staged_path.write_text(schema_source_path.read_text(encoding='utf-8'), encoding='utf-8')
    metadata = {
        'name': REPORT_SCHEMA_NAME,
        'version': REPORT_SCHEMA_VERSION,
        'artifact': str(staged_path),
        'compatibility': f"^{REPORT_SCHEMA_VERSION.split('.')[0]}.0.0",
    }
    return metadata, staged_path


def _build_report_output_paths(output_dir: Path, report_format: str) -> dict[str, Path]:
    output_json = output_dir / 'wcag-report.json'
    output_md = output_dir / 'wcag-report.md'
    machine_output = output_json if report_format == 'json' else output_dir / 'wcag-report.sarif'
    return {
        'output_json': output_json,
        'output_md': output_md,
        'machine_output': machine_output,
    }


def _collect_artifact_paths(
    *,
    report_format: str,
    machine_output: Path,
    output_json: Path,
    output_md: Path,
    staged_schema_path: Path,
    debt_trend_path: Path,
    scanner_stability_path: Path,
    axe_raw: Path,
    lighthouse_raw: Path,
    effective_policy_output: Path | None = None,
    replay_summary_path: Path | None = None,
    replay_diff_path: Path | None = None,
    diff_path: Path | None = None,
    snapshot_path: Path | None = None,
) -> dict[str, Path]:
    artifact_paths: dict[str, Path] = {
        'markdown-report': output_md,
        'report-schema': staged_schema_path,
        'debt-trend': debt_trend_path,
        'scanner-stability': scanner_stability_path,
        'axe-raw': axe_raw,
        'lighthouse-raw': lighthouse_raw,
    }
    if report_format == 'json':
        artifact_paths['machine-report-json'] = output_json
    else:
        artifact_paths['machine-report-sarif'] = machine_output
    if effective_policy_output is not None:
        artifact_paths['effective-policy'] = effective_policy_output
    if replay_summary_path is not None:
        artifact_paths['replay-summary'] = replay_summary_path
    if replay_diff_path is not None:
        artifact_paths['replay-diff'] = replay_diff_path
    if diff_path is not None:
        artifact_paths['fixes-diff'] = diff_path
    if snapshot_path is not None:
        artifact_paths['fixes-snapshot'] = snapshot_path
    return artifact_paths


def _build_artifact_manifest(
    *,
    output_dir: Path,
    report_format: str,
    target: str,
    artifact_paths: dict[str, Path],
    baseline_evidence: dict[str, Any] | None,
) -> tuple[dict[str, Any], Path]:
    product_provenance = get_product_provenance()
    artifacts: list[dict[str, Any]] = []
    for kind in sorted(artifact_paths):
        path = artifact_paths[kind]
        if not path.exists() or not path.is_file():
            continue
        artifacts.append(
            {
                'kind': kind,
                'path': str(path),
                'size_bytes': path.stat().st_size,
                'sha256': _sha256_file(path),
            }
        )

    manifest: dict[str, Any] = {
        'generated_at': _utc_timestamp(),
        'generator': {
            'name': 'run_accessibility_audit.py',
            'product_name': product_provenance['product_name'],
            'version': REPORT_SCHEMA_VERSION,
            'product_version': product_provenance['product_version'],
            'version_source': product_provenance['version_source'],
            'source_revision': product_provenance['source_revision'],
            'source_revision_source': product_provenance['source_revision_source'],
            'report_schema_version': REPORT_SCHEMA_VERSION,
        },
        'target': target,
        'report_format': report_format,
        'artifact_count': len(artifacts),
        'artifacts': artifacts,
    }
    if 'build_timestamp' in product_provenance:
        manifest['generator']['build_timestamp'] = product_provenance['build_timestamp']
        manifest['generator']['build_timestamp_source'] = product_provenance['build_timestamp_source']
    if baseline_evidence:
        manifest['baseline_evidence'] = {
            'mode': baseline_evidence.get('mode'),
            'report_hash': baseline_evidence.get('report_hash'),
            'chain_hash': baseline_evidence.get('chain_hash'),
            'baseline_report_hash': baseline_evidence.get('baseline_report_hash'),
            'baseline_verification': baseline_evidence.get('baseline_verification', {}),
        }

    manifest_path = output_dir / 'artifact-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest, manifest_path


def _build_compact_summary(
    report: dict[str, Any],
    report_format: str,
    machine_output: Path,
    output_md: Path,
    should_fail: bool,
    fail_on: str | None,
    exit_code: int,
) -> dict[str, Any]:
    summary = report.get('summary', {})
    product_metadata = report.get('run_meta', {}).get('product', {})
    compact: dict[str, Any] = {
        'status': 'failed' if should_fail else 'ok',
        'report_format': report_format,
        'machine_output': str(machine_output),
        'markdown_output': str(output_md),
        'total_findings': summary.get('total_findings', 0),
        'fixed_findings': summary.get('fixed_findings', 0),
        'manual_required_count': summary.get('manual_required_count', 0),
    }
    if product_metadata:
        compact['product'] = {
            'name': product_metadata.get('name'),
            'product_version': product_metadata.get('product_version'),
            'source_revision': product_metadata.get('source_revision'),
            'report_schema_version': product_metadata.get('report_schema_version'),
        }
        if 'build_timestamp' in product_metadata:
            compact['product']['build_timestamp'] = product_metadata.get('build_timestamp')
    if fail_on:
        policy_gate = report.get('run_meta', {}).get('policy_gate', {})
        compact['policy_gate'] = {
            'fail_on': fail_on,
            'failed': bool(policy_gate.get('failed', False)),
            'exit_code': int(policy_gate.get('exit_code', 0)),
            'scope': policy_gate.get('scope', 'all-unresolved'),
        }
    baseline_diff = report.get('run_meta', {}).get('baseline_diff')
    if baseline_diff:
        compact['baseline_diff'] = {
            'introduced_count': baseline_diff.get('introduced_count', 0),
            'resolved_count': baseline_diff.get('resolved_count', 0),
            'persistent_count': baseline_diff.get('persistent_count', 0),
        }
        waiver_review = baseline_diff.get('waiver_review')
        if waiver_review:
            compact['waiver_review'] = {
                'accepted_count': waiver_review.get('accepted_count', 0),
                'expired_count': waiver_review.get('expired_count', 0),
                'missing_count': waiver_review.get('missing_count', 0),
                'valid_count': waiver_review.get('valid_count', 0),
            }
    findings_cap = report.get('run_meta', {}).get('findings_cap')
    if findings_cap:
        compact['findings_cap'] = findings_cap
    scanner_capabilities = summary.get('scanner_capabilities')
    if scanner_capabilities:
        compact['scanner_capabilities'] = scanner_capabilities
    effective_policy = report.get('run_meta', {}).get('policy_effective')
    if effective_policy:
        compact['policy_effective'] = effective_policy
    policy_rule_overlap = report.get('run_meta', {}).get('policy_rule_overlap')
    if policy_rule_overlap:
        compact['policy_rule_overlap'] = policy_rule_overlap
    baseline_evidence = report.get('run_meta', {}).get('baseline_evidence')
    if baseline_evidence:
        compact['baseline_evidence'] = {
            'mode': baseline_evidence.get('mode'),
            'baseline_verification': baseline_evidence.get('baseline_verification', {}),
        }
    artifact_manifest = report.get('run_meta', {}).get('artifact_manifest')
    if artifact_manifest:
        compact['artifact_manifest'] = artifact_manifest
    waiver_gate = report.get('run_meta', {}).get('waiver_gate')
    if waiver_gate:
        compact['waiver_gate'] = waiver_gate
    debt_trend = summary.get('debt_trend')
    if debt_trend:
        compact['debt_trend'] = debt_trend
    risk_calibration = report.get('run_meta', {}).get('risk_calibration')
    if risk_calibration:
        compact['risk_calibration'] = {
            'mode': risk_calibration.get('mode'),
            'applied': bool(risk_calibration.get('applied')),
            'downgrade_reason': risk_calibration.get('downgrade_reason'),
            'unstable_high_severity_rules': risk_calibration.get('unstable_high_severity_rules', []),
        }
    replay_verification = report.get('run_meta', {}).get('replay_verification')
    if replay_verification:
        compact['replay_verification'] = replay_verification
    scanner_stability = report.get('run_meta', {}).get('scanner_stability')
    if scanner_stability:
        compact['scanner_stability'] = {
            'mode': scanner_stability.get('mode'),
            'window': scanner_stability.get('window'),
            'comparison': scanner_stability.get('comparison', {}),
            'gate': scanner_stability.get('gate', {}),
        }
    compact['exit_code'] = exit_code
    return compact


def _emit_summary_only_stdout(compact_summary: dict[str, Any]) -> None:
    print(json.dumps(compact_summary, ensure_ascii=False))


__all__ = [
    'REPORT_SCHEMA_FILENAME',
    'REPORT_SCHEMA_NAME',
    'REPORT_SCHEMA_VERSION',
    '_build_artifact_manifest',
    '_build_compact_summary',
    '_build_report_output_paths',
    '_collect_artifact_paths',
    '_emit_summary_only_stdout',
    '_report_schema_source_path',
    '_stage_report_schema_artifact',
]
