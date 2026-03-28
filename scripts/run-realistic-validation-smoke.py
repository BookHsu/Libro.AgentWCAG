#!/usr/bin/env python3
"""Run install -> invoke -> audit smoke flow on the realistic validation sample."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = REPO_ROOT / 'docs' / 'testing' / 'realistic-sample' / 'mixed-findings.html'
DEFAULT_AXE_MOCK = REPO_ROOT / 'docs' / 'testing' / 'realistic-sample' / 'scanner-fixtures' / 'axe.mock.json'
DEFAULT_LIGHTHOUSE_MOCK = REPO_ROOT / 'docs' / 'testing' / 'realistic-sample' / 'scanner-fixtures' / 'lighthouse.mock.json'
DEFAULT_ARTIFACT_DIR = REPO_ROOT / 'docs' / 'testing' / 'realistic-sample' / 'artifacts'


def _run(command: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return completed.returncode, completed.stdout + completed.stderr


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run realistic validation smoke scenario.')
    parser.add_argument('--agent', default='codex', choices=['codex', 'claude', 'gemini', 'copilot'])
    parser.add_argument('--sample', default=str(DEFAULT_SAMPLE))
    parser.add_argument('--axe-mock', default=str(DEFAULT_AXE_MOCK))
    parser.add_argument('--lighthouse-mock', default=str(DEFAULT_LIGHTHOUSE_MOCK))
    parser.add_argument('--artifact-dir', default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument('--keep-temp', action='store_true')
    return parser.parse_args()


def _load_json_artifact(path: Path, description: str) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f'{description} is missing: {path}')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as err:
        raise ValueError(
            f'{description} is not valid JSON: {path} ({err.msg} at line {err.lineno}, column {err.colno})'
        ) from err
    if not isinstance(payload, dict):
        raise ValueError(f'{description} must be a JSON object: {path}')
    return payload


def main() -> int:
    args = parse_args()
    sample = Path(args.sample)
    axe_mock = Path(args.axe_mock)
    lighthouse_mock = Path(args.lighthouse_mock)
    artifact_dir = Path(args.artifact_dir)

    if not sample.exists() or not axe_mock.exists() or not lighthouse_mock.exists():
        raise FileNotFoundError('Realistic sample or mock scanner fixtures are missing.')

    temp_root = REPO_ROOT / '.tmp-realistic-smoke'
    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)

    install_dir = temp_root / 'installed'
    run_dir = temp_root / 'run'
    run_dir.mkdir(parents=True, exist_ok=True)
    working_target = run_dir / sample.name
    working_target.write_text(sample.read_text(encoding='utf-8'), encoding='utf-8')

    steps: list[dict[str, object]] = []

    install_cmd = [sys.executable, 'scripts/install-agent.py', '--agent', args.agent, '--dest', str(install_dir), '--force']
    install_code, install_log = _run(install_cmd, REPO_ROOT)
    steps.append({'name': 'install', 'command': install_cmd, 'exit_code': install_code})
    if install_code != 0:
        print(install_log)
        return install_code

    doctor_cmd = [sys.executable, 'scripts/doctor-agent.py', '--agent', args.agent, '--dest', str(install_dir)]
    doctor_code, doctor_log = _run(doctor_cmd, REPO_ROOT)
    steps.append({'name': 'doctor', 'command': doctor_cmd, 'exit_code': doctor_code})
    if doctor_code != 0:
        print(doctor_log)
        return doctor_code

    output_dir = run_dir / 'audit-output'
    audit_cmd = [
        sys.executable,
        'skills/libro-wcag/scripts/run_accessibility_audit.py',
        '--target',
        str(working_target),
        '--output-dir',
        str(output_dir),
        '--execution-mode',
        'apply-fixes',
        '--wcag-version',
        '2.2',
        '--output-language',
        'en',
        '--mock-axe-json',
        str(axe_mock),
        '--mock-lighthouse-json',
        str(lighthouse_mock),
    ]
    audit_code, audit_log = _run(audit_cmd, REPO_ROOT)
    steps.append({'name': 'audit', 'command': audit_cmd, 'exit_code': audit_code})
    if audit_code != 0:
        print(audit_log)
        return audit_code

    artifact_dir.mkdir(parents=True, exist_ok=True)
    copy_map = {
        output_dir / 'wcag-report.json': artifact_dir / 'wcag-report.sample.json',
        output_dir / 'wcag-report.md': artifact_dir / 'wcag-report.sample.md',
        output_dir / 'wcag-fixes.diff': artifact_dir / 'wcag-fixes.sample.diff',
        output_dir / 'wcag-fixed-report.snapshot.json': artifact_dir / 'wcag-fixed-report.sample.snapshot.json',
    }
    for source, destination in copy_map.items():
        if source.exists():
            shutil.copyfile(source, destination)

    report = _load_json_artifact(output_dir / 'wcag-report.json', 'Audit report')
    summary = {
        'sample_target': str(sample),
        'steps': steps,
        'artifacts': [str(path) for path in copy_map.values() if path.exists()],
        'fixed_findings': report['summary']['fixed_findings'],
        'manual_required_count': report['summary']['manual_required_count'],
        'auto_fixed_count': report['summary']['auto_fixed_count'],
        'files_modified': report['run_meta']['files_modified'],
    }
    (artifact_dir / 'smoke-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.keep_temp:
        print(f'Temporary run directory retained: {temp_root}')
    else:
        shutil.rmtree(temp_root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
