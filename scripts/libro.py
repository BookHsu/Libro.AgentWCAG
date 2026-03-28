#!/usr/bin/env python3
"""Unified CLI entrypoint for Libro.AgentWCAG."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "libro-wcag"
SUPPORTED_AGENTS = ("codex", "claude", "gemini", "copilot")
ALL_AGENTS = SUPPORTED_AGENTS + ("all",)
MCP_CLIENTS = ("claude", "copilot", "gemini")
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
AUDIT_SCRIPT = REPO_ROOT / "skills" / "libro-wcag" / "scripts" / "run_accessibility_audit.py"


def workspace_destination(agent: str, workspace_root: Path) -> Path:
    return workspace_root / f".{agent}" / "skills" / SKILL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="libro",
        description="Unified CLI for installing and validating Libro.AgentWCAG across AI agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install libro-wcag for an agent.")
    install_parser.add_argument("agent", choices=ALL_AGENTS)
    install_parser.add_argument("--dest", help="Destination directory. When agent=all, this becomes the base directory.")
    install_parser.add_argument(
        "--workspace-root",
        help="Install into a project workspace root using .<agent>/skills/libro-wcag.",
    )
    install_parser.add_argument(
        "--emit-mcp-config",
        action="append",
        default=[],
        choices=MCP_CLIENTS,
        help="Write a workspace-local MCP config for claude, copilot, or gemini. Requires --workspace-root.",
    )
    install_parser.add_argument("--force", action="store_true", help="Replace an existing installation.")

    doctor_parser = subparsers.add_parser("doctor", help="Verify a libro-wcag installation.")
    doctor_parser.add_argument("agent", choices=ALL_AGENTS)
    doctor_parser.add_argument("--dest", help="Destination directory. When agent=all, this becomes the base directory.")
    doctor_parser.add_argument(
        "--workspace-root",
        help="Verify a project workspace installation under .<agent>/skills/libro-wcag.",
    )
    doctor_parser.add_argument(
        "--verify-manifest-integrity",
        action="store_true",
        help="Verify adapter and companion entrypoint hashes from install-manifest.json.",
    )
    doctor_parser.add_argument(
        "--check-scanners",
        action="store_true",
        help="Verify scanner toolchain (Node.js, npx, axe, lighthouse) is available.",
    )

    remove_parser = subparsers.add_parser("remove", help="Remove a libro-wcag installation.")
    remove_parser.add_argument("agent", choices=ALL_AGENTS)
    remove_parser.add_argument("--dest", help="Destination directory. When agent=all, this becomes the base directory.")
    remove_parser.add_argument(
        "--workspace-root",
        help="Remove a project workspace installation under .<agent>/skills/libro-wcag.",
    )

    audit_parser = subparsers.add_parser(
        "audit",
        help="Run a WCAG accessibility audit on a target page or file.",
        add_help=False,
    )
    audit_parser.add_argument("target", nargs="?", help="URL or local file path to audit.")

    args, remaining = parser.parse_known_args()
    args._remaining = remaining
    return args


def run_script(script_name: str, args: list[str]) -> int:
    completed = subprocess.run([sys.executable, str(SCRIPT_DIR / script_name), *args], check=False)
    return completed.returncode


def run_script_for_workspace_agents(
    script_name: str,
    command_agent: str,
    workspace_root: Path,
    extra_args: list[str],
) -> int:
    agents = SUPPORTED_AGENTS if command_agent == "all" else (command_agent,)
    status = 0
    for agent in agents:
        destination = workspace_destination(agent, workspace_root)
        returncode = run_script(script_name, ["--agent", agent, "--dest", str(destination), *extra_args])
        if returncode != 0:
            status = returncode
    return status


def handle_install(args: argparse.Namespace) -> int:
    command = ["--agent", args.agent]
    if args.dest:
        command.extend(["--dest", args.dest])
    if args.workspace_root:
        command.extend(["--workspace-root", args.workspace_root])
    for client in args.emit_mcp_config:
        command.extend(["--emit-mcp-config", client])
    if args.force:
        command.append("--force")
    return run_script("install-agent.py", command)


def handle_doctor(args: argparse.Namespace) -> int:
    extra_args: list[str] = []
    if args.verify_manifest_integrity:
        extra_args.append("--verify-manifest-integrity")
    if args.check_scanners:
        extra_args.append("--check-scanners")
    if args.workspace_root:
        return run_script_for_workspace_agents(
            "doctor-agent.py",
            args.agent,
            Path(args.workspace_root),
            extra_args,
        )
    command = ["--agent", args.agent]
    if args.dest:
        command.extend(["--dest", args.dest])
    command.extend(extra_args)
    return run_script("doctor-agent.py", command)


def handle_remove(args: argparse.Namespace) -> int:
    if args.workspace_root:
        return run_script_for_workspace_agents(
            "uninstall-agent.py",
            args.agent,
            Path(args.workspace_root),
            [],
        )
    command = ["--agent", args.agent]
    if args.dest:
        command.extend(["--dest", args.dest])
    return run_script("uninstall-agent.py", command)


def handle_audit(args: argparse.Namespace) -> int:
    command = [sys.executable, str(AUDIT_SCRIPT)]
    if args.target:
        command.extend(["--target", args.target])
    command.extend(args._remaining)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return completed.returncode


def main() -> int:
    args = parse_args()
    if args.command == "install":
        return handle_install(args)
    if args.command == "doctor":
        return handle_doctor(args)
    if args.command == "remove":
        return handle_remove(args)
    if args.command == "audit":
        return handle_audit(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
