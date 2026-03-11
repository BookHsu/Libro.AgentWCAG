#!/usr/bin/env python3
"""Verify a libro-agent-wcag installation for a target AI agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SKILL_NAME = 'libro-agent-wcag'
SUPPORTED_AGENTS = ('codex', 'claude', 'gemini', 'copilot')
ALL_AGENTS = SUPPORTED_AGENTS + ('all',)


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
    return parser.parse_args()


def doctor(destination: Path) -> dict[str, object]:
    manifest_path = destination / 'install-manifest.json'
    result = {
        'destination': str(destination),
        'exists': destination.exists(),
        'skill_md': (destination / 'SKILL.md').exists(),
        'manifest': manifest_path.exists(),
        'adapter_prompt': False,
    }
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        result['manifest_data'] = manifest
        result['adapter_prompt'] = (destination / manifest['adapter_prompt']).exists()
    return result


def run_for_agent(agent: str, destination: Path) -> bool:
    result = doctor(destination)
    status = all([result['exists'], result['skill_md'], result['manifest'], result['adapter_prompt']])
    print(json.dumps({'agent': agent, 'ok': status, **result}, indent=2, ensure_ascii=False))
    return status


def main() -> int:
    args = parse_args()
    if args.agent == 'all':
        base_destination = Path(args.dest) if args.dest else None
        statuses = []
        for agent in SUPPORTED_AGENTS:
            destination = (base_destination / agent / SKILL_NAME) if base_destination else default_destination(agent)
            statuses.append(run_for_agent(agent, destination))
        return 0 if all(statuses) else 1

    destination = Path(args.dest) if args.dest else default_destination(args.agent)
    return 0 if run_for_agent(args.agent, destination) else 1


if __name__ == '__main__':
    raise SystemExit(main())
