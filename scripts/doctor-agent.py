#!/usr/bin/env python3
"""Verify a libro-agent-wcag installation for a target AI agent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SKILL_NAME = 'libro-agent-wcag'
SUPPORTED_AGENTS = ('codex', 'claude', 'gemini', 'copilot')
ALL_AGENTS = SUPPORTED_AGENTS + ('all',)
REQUIRED_MANIFEST_FIELDS = ('skill_entrypoint', 'adapter_prompt', 'usage_example', 'failure_guide', 'e2e_example')


def default_destination(agent: str) -> Path:
    home = Path.home()
    if agent == 'codex':
        return home / '.codex' / 'skills' / SKILL_NAME
    if agent == 'claude':
        return home / '.claude' / 'skills' / SKILL_NAME
    if agent == 'gemini':
        return home / '.gemini' / 'skills' / SKILL_NAME
    if agent == 'copilot':
        return home / '.copilot' / 'skills' / SKILL_NAME
    raise ValueError(f'Unsupported agent: {agent}')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Verify libro-agent-wcag for a target AI agent.')
    parser.add_argument('--agent', required=True, choices=ALL_AGENTS)
    parser.add_argument('--dest', help='Destination directory. When --agent all is used, this becomes the base directory.')
    parser.add_argument(
        '--verify-manifest-integrity',
        action='store_true',
        help='Verify adapter and companion entrypoint hashes from install-manifest.json.',
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(8192), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest_integrity(destination: Path, manifest: dict[str, object]) -> dict[str, object]:
    integrity_payload = {
        'enabled': True,
        'verified': False,
        'algorithm': None,
        'missing_manifest_fields': [],
        'missing_integrity_fields': [],
        'missing_files': [],
        'hash_mismatches': [],
    }

    missing_manifest_fields = [field for field in REQUIRED_MANIFEST_FIELDS if field not in manifest]
    if missing_manifest_fields:
        integrity_payload['missing_manifest_fields'] = missing_manifest_fields
        return integrity_payload

    manifest_integrity = manifest.get('manifest_integrity')
    if not isinstance(manifest_integrity, dict):
        integrity_payload['missing_integrity_fields'] = ['manifest_integrity']
        return integrity_payload

    algorithm = manifest_integrity.get('algorithm')
    entrypoint_hashes = manifest_integrity.get('entrypoint_hashes')
    integrity_payload['algorithm'] = algorithm

    missing_integrity_fields: list[str] = []
    if algorithm != 'sha256':
        missing_integrity_fields.append('manifest_integrity.algorithm=sha256')
    if not isinstance(entrypoint_hashes, dict):
        missing_integrity_fields.append('manifest_integrity.entrypoint_hashes')
    if missing_integrity_fields:
        integrity_payload['missing_integrity_fields'] = missing_integrity_fields
        return integrity_payload

    for field in REQUIRED_MANIFEST_FIELDS:
        relative_path = Path(str(manifest[field]))
        expected_hash = entrypoint_hashes.get(field)
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            integrity_payload['missing_integrity_fields'].append(f'manifest_integrity.entrypoint_hashes.{field}')
            continue

        target_path = destination / relative_path
        if not target_path.exists():
            integrity_payload['missing_files'].append(str(relative_path).replace('\\', '/'))
            continue

        actual_hash = sha256_file(target_path)
        if actual_hash != expected_hash:
            integrity_payload['hash_mismatches'].append(
                {
                    'field': field,
                    'path': str(relative_path).replace('\\', '/'),
                    'expected': expected_hash,
                    'actual': actual_hash,
                }
            )

    integrity_payload['verified'] = not any(
        [
            integrity_payload['missing_manifest_fields'],
            integrity_payload['missing_integrity_fields'],
            integrity_payload['missing_files'],
            integrity_payload['hash_mismatches'],
        ]
    )
    return integrity_payload


def doctor(destination: Path, verify_manifest_integrity_mode: bool) -> dict[str, object]:
    manifest_path = destination / 'install-manifest.json'
    result = {
        'destination': str(destination),
        'exists': destination.exists(),
        'skill_md': (destination / 'SKILL.md').exists(),
        'manifest': manifest_path.exists(),
        'adapter_prompt': False,
    }
    if verify_manifest_integrity_mode:
        result['manifest_integrity'] = {
            'enabled': True,
            'verified': False,
            'missing_integrity_fields': ['install-manifest.json'],
            'missing_manifest_fields': [],
            'missing_files': [],
            'hash_mismatches': [],
            'algorithm': None,
        }

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        result['manifest_data'] = manifest
        result['adapter_prompt'] = (destination / manifest['adapter_prompt']).exists()
        if verify_manifest_integrity_mode:
            result['manifest_integrity'] = verify_manifest_integrity(destination, manifest)
    return result


def run_for_agent(agent: str, destination: Path, verify_manifest_integrity_mode: bool) -> bool:
    result = doctor(destination, verify_manifest_integrity_mode)
    checks = [result['exists'], result['skill_md'], result['manifest'], result['adapter_prompt']]
    if verify_manifest_integrity_mode:
        checks.append(bool(result['manifest_integrity']['verified']))
    status = all(checks)
    print(json.dumps({'agent': agent, 'ok': status, **result}, indent=2, ensure_ascii=False))
    return status


def main() -> int:
    args = parse_args()
    if args.agent == 'all':
        base_destination = Path(args.dest) if args.dest else None
        statuses = []
        for agent in SUPPORTED_AGENTS:
            destination = (base_destination / agent / SKILL_NAME) if base_destination else default_destination(agent)
            statuses.append(run_for_agent(agent, destination, args.verify_manifest_integrity))
        return 0 if all(statuses) else 1

    destination = Path(args.dest) if args.dest else default_destination(args.agent)
    return 0 if run_for_agent(args.agent, destination, args.verify_manifest_integrity) else 1


if __name__ == '__main__':
    raise SystemExit(main())
