#!/usr/bin/env python3
"""Uninstall libro-wcag for a target AI agent."""

from __future__ import annotations

import argparse
import sys
import shutil
from pathlib import Path

SKILL_NAME = 'libro-wcag'
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
    parser = argparse.ArgumentParser(description='Uninstall libro-wcag for a target AI agent.')
    parser.add_argument('--agent', required=True, choices=ALL_AGENTS)
    parser.add_argument('--dest', help='Destination directory. When --agent all is used, this becomes the base directory.')
    return parser.parse_args()


def uninstall(destination: Path) -> None:
    if destination.exists():
        try:
            shutil.rmtree(destination)
        except PermissionError as exc:
            raise RuntimeError(
                f"Failed to remove installation at {destination}: permission denied ({exc})"
            ) from exc
        except OSError as exc:
            detail = exc.strerror or str(exc)
            raise RuntimeError(
                f"Failed to remove installation at {destination}: {detail}"
            ) from exc


def uninstall_all(base_destination: Path | None) -> None:
    for agent in SUPPORTED_AGENTS:
        destination = (base_destination / agent / SKILL_NAME) if base_destination else default_destination(agent)
        uninstall(destination)


def main() -> int:
    args = parse_args()
    try:
        if args.agent == 'all':
            base_destination = Path(args.dest) if args.dest else None
            uninstall_all(base_destination)
            print('Removed all installed agent bundles.')
            return 0

        destination = Path(args.dest) if args.dest else default_destination(args.agent)
        uninstall(destination)
        print(f'Removed installation for {args.agent}: {destination}')
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
