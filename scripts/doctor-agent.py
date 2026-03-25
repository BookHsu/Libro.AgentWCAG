#!/usr/bin/env python3
"""Verify a libro-wcag installation for a target AI agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / 'skills' / 'libro-wcag' / 'scripts'
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from shared_constants import get_product_provenance

SKILL_NAME = 'libro-wcag'
SUPPORTED_AGENTS = ('codex', 'claude', 'gemini', 'copilot')
ALL_AGENTS = SUPPORTED_AGENTS + ('all',)
REQUIRED_MANIFEST_FIELDS = ('skill_entrypoint', 'adapter_prompt', 'usage_example', 'failure_guide', 'e2e_example')
REQUIRED_PROVENANCE_FIELDS = ('product_name', 'product_version', 'source_revision')


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
    parser = argparse.ArgumentParser(description='Verify libro-wcag for a target AI agent.')
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


def verify_manifest_provenance(manifest: dict[str, object]) -> dict[str, object]:
    expected = get_product_provenance()
    payload = {
        'verified': False,
        'missing_manifest_fields': [],
        'mismatched_fields': [],
        'expected': {
            'product_name': expected['product_name'],
            'product_version': expected['product_version'],
            'source_revision': expected['source_revision'],
        },
    }

    for field in REQUIRED_PROVENANCE_FIELDS:
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            payload['missing_manifest_fields'].append(field)
            continue
        if value != expected[field]:
            payload['mismatched_fields'].append(
                {
                    'field': field,
                    'expected': expected[field],
                    'actual': value,
                }
            )

    provenance_block = manifest.get('provenance')
    if not isinstance(provenance_block, dict):
        payload['missing_manifest_fields'].append('provenance')
    else:
        if provenance_block.get('version_source') != expected['version_source']:
            payload['mismatched_fields'].append(
                {
                    'field': 'provenance.version_source',
                    'expected': expected['version_source'],
                    'actual': provenance_block.get('version_source'),
                }
            )
        if provenance_block.get('source_revision_source') != expected['source_revision_source']:
            payload['mismatched_fields'].append(
                {
                    'field': 'provenance.source_revision_source',
                    'expected': expected['source_revision_source'],
                    'actual': provenance_block.get('source_revision_source'),
                }
            )

    payload['verified'] = not payload['missing_manifest_fields'] and not payload['mismatched_fields']
    return payload


def _installed_product_from_manifest(manifest: dict[str, object]) -> dict[str, object]:
    installed = {
        'product_name': manifest.get('product_name'),
        'product_version': manifest.get('product_version'),
        'source_revision': manifest.get('source_revision'),
    }
    if 'build_timestamp' in manifest:
        installed['build_timestamp'] = manifest.get('build_timestamp')
    provenance = manifest.get('provenance')
    if isinstance(provenance, dict):
        installed['provenance'] = provenance
    return installed


def _build_version_consistency(
    expected_provenance: dict[str, str],
    manifest: dict[str, object] | None,
    manifest_provenance: dict[str, object],
) -> dict[str, object]:
    consistency = {
        'verified': False,
        'expected': {
            'product_version': expected_provenance['product_version'],
            'source_revision': expected_provenance['source_revision'],
        },
        'installed': {},
        'matches': {
            'product_version': False,
            'source_revision': False,
        },
    }
    if manifest is None:
        return consistency

    installed = _installed_product_from_manifest(manifest)
    consistency['installed'] = installed
    consistency['matches'] = {
        'product_version': installed.get('product_version') == expected_provenance['product_version'],
        'source_revision': installed.get('source_revision') == expected_provenance['source_revision'],
    }
    consistency['verified'] = bool(manifest_provenance.get('verified')) and all(consistency['matches'].values())
    return consistency


def doctor(destination: Path, verify_manifest_integrity_mode: bool) -> dict[str, object]:
    manifest_path = destination / 'install-manifest.json'
    expected_provenance = get_product_provenance()
    result = {
        'destination': str(destination),
        'exists': destination.exists(),
        'skill_md': (destination / 'SKILL.md').exists(),
        'manifest': manifest_path.exists(),
        'adapter_prompt': False,
        'expected_product': {
            'product_name': expected_provenance['product_name'],
            'product_version': expected_provenance['product_version'],
            'source_revision': expected_provenance['source_revision'],
        },
        'installed_product': {},
        'manifest_provenance': {
            'verified': False,
            'missing_manifest_fields': ['install-manifest.json'],
            'mismatched_fields': [],
            'expected': {
                'product_name': expected_provenance['product_name'],
                'product_version': expected_provenance['product_version'],
                'source_revision': expected_provenance['source_revision'],
            },
        },
        'version_consistency': {
            'verified': False,
            'expected': {
                'product_version': expected_provenance['product_version'],
                'source_revision': expected_provenance['source_revision'],
            },
            'installed': {},
            'matches': {
                'product_version': False,
                'source_revision': False,
            },
        },
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
        result['installed_product'] = _installed_product_from_manifest(manifest)
        result['manifest_provenance'] = verify_manifest_provenance(manifest)
        result['version_consistency'] = _build_version_consistency(
            expected_provenance,
            manifest,
            result['manifest_provenance'],
        )
        if verify_manifest_integrity_mode:
            result['manifest_integrity'] = verify_manifest_integrity(destination, manifest)
    return result


def run_for_agent(agent: str, destination: Path, verify_manifest_integrity_mode: bool) -> bool:
    result = doctor(destination, verify_manifest_integrity_mode)
    checks = [
        result['exists'],
        result['skill_md'],
        result['manifest'],
        result['adapter_prompt'],
        result['manifest_provenance']['verified'],
        result['version_consistency']['verified'],
    ]
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
