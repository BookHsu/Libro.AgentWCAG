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

    scan_parser = subparsers.add_parser(
        "scan",
        help="Batch-scan multiple targets for WCAG accessibility issues.",
    )
    scan_parser.add_argument(
        "inputs",
        nargs="+",
        help="Directories, glob patterns, or file paths to scan.",
    )
    scan_parser.add_argument(
        "--targets",
        help="File containing one target path/URL per line.",
    )
    scan_parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel scans (default: 1).",
    )
    scan_parser.add_argument(
        "--output-dir",
        default="wcag-reports",
        help="Root directory for per-target report outputs (default: wcag-reports).",
    )
    scan_parser.add_argument(
        "--execution-mode",
        choices=("audit-only", "suggest-only", "apply-fixes"),
        default="suggest-only",
        help="Execution mode for each audit (default: suggest-only).",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Aggregate multiple wcag-report.json files into a summary report.",
    )
    report_parser.add_argument(
        "inputs",
        nargs="+",
        help="Paths to wcag-report.json files or directories containing them.",
    )
    report_parser.add_argument(
        "--format",
        choices=("json", "terminal", "markdown", "csv", "badge"),
        default="terminal",
        help="Output format (default: terminal).",
    )
    report_parser.add_argument(
        "--output",
        help="Write output to this file instead of stdout.",
    )
    report_parser.add_argument(
        "--language",
        default="zh-TW",
        help="Output language: en or zh-TW (default: zh-TW).",
    )
    report_parser.add_argument(
        "--baseline",
        help="Path to a prior aggregate report JSON or directory for baseline comparison.",
    )

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


def _resolve_scan_targets(args: argparse.Namespace) -> list[str]:
    """Resolve scan targets from CLI args: inputs + optional --targets file."""
    import glob as glob_mod

    targets: list[str] = []

    # From --targets file (one per line)
    if args.targets:
        targets_file = Path(args.targets)
        if targets_file.is_file():
            for line in targets_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    targets.append(line)

    # From positional inputs: directories expand to HTML files, globs expand
    for raw_input in args.inputs:
        p = Path(raw_input)
        if p.is_file():
            targets.append(str(p))
        elif p.is_dir():
            for ext in ("*.html", "*.htm", "*.xhtml"):
                targets.extend(str(f) for f in sorted(p.rglob(ext)))
        else:
            expanded = glob_mod.glob(raw_input, recursive=True)
            for g in sorted(expanded):
                if Path(g).is_file():
                    targets.append(g)
    return targets


def handle_scan(args: argparse.Namespace) -> int:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    targets = _resolve_scan_targets(args)
    if not targets:
        print("Error: no scan targets found.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    execution_mode = args.execution_mode
    parallel = max(1, args.parallel)

    errors: list[tuple[str, int]] = []
    completed_count = 0

    def _run_single_audit(target: str, index: int) -> tuple[str, int]:
        # Compute per-target output directory
        safe_name = Path(target).stem or f"target_{index}"
        target_dir = output_dir / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, str(AUDIT_SCRIPT),
            "--target", target,
            "--execution-mode", execution_mode,
            "--output-dir", str(target_dir),
        ]
        result = subprocess.run(cmd, cwd=REPO_ROOT, check=False, capture_output=True)
        return target, result.returncode

    print(f"Scanning {len(targets)} target(s) with parallelism={parallel}...")
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {
            executor.submit(_run_single_audit, target, i): target
            for i, target in enumerate(targets)
        }
        for future in as_completed(futures):
            target, returncode = future.result()
            completed_count += 1
            if returncode != 0:
                errors.append((target, returncode))
                print(f"  [{completed_count}/{len(targets)}] FAIL ({returncode}): {target}")
            else:
                print(f"  [{completed_count}/{len(targets)}] OK: {target}")

    print(f"\nCompleted: {len(targets) - len(errors)}/{len(targets)} succeeded")
    if errors:
        print(f"Failed: {len(errors)} target(s)")
        for target, code in errors:
            print(f"  - {target} (exit code {code})")
        return 1
    print(f"Reports written to: {output_dir}/")
    return 0


def handle_report(args: argparse.Namespace) -> int:
    import glob as glob_mod
    sys.path.insert(0, str(REPO_ROOT / "skills" / "libro-wcag" / "scripts"))
    from aggregate_report import build_aggregate_report, load_reports, write_aggregate_json
    from report_renderers import render_badge, render_csv, render_markdown, render_terminal

    def _resolve_report_paths(inputs: list[str]) -> list[Path]:
        paths: list[Path] = []
        for raw_input in inputs:
            p = Path(raw_input)
            if p.is_file():
                paths.append(p)
            elif p.is_dir():
                found = sorted(p.rglob("wcag-report.json"))
                if not found:
                    print(f"Warning: no wcag-report.json found under {p}", file=sys.stderr)
                paths.extend(found)
            else:
                expanded = glob_mod.glob(raw_input, recursive=True)
                for g in expanded:
                    gp = Path(g)
                    if gp.is_file():
                        paths.append(gp)
        return paths

    report_paths = _resolve_report_paths(args.inputs)
    if not report_paths:
        print("Error: no report files found.", file=sys.stderr)
        return 1

    reports = load_reports(report_paths)

    # Load baseline if provided
    baseline_reports = None
    if args.baseline:
        baseline_paths = _resolve_report_paths([args.baseline])
        if baseline_paths:
            baseline_reports = load_reports(baseline_paths)

    aggregate = build_aggregate_report(reports, baseline_reports=baseline_reports)

    fmt = args.format
    output_text: str | None = None
    if fmt == "json":
        if args.output:
            write_aggregate_json(aggregate, Path(args.output))
            print(f"Aggregate report written to {args.output}")
        else:
            import json as json_mod
            print(json_mod.dumps(aggregate, ensure_ascii=False, indent=2))
    elif fmt == "markdown":
        output_text = render_markdown(aggregate, language=args.language)
    elif fmt == "csv":
        output_text = render_csv(reports, aggregate=aggregate)
    elif fmt == "badge":
        output_text = render_badge(aggregate)
    else:
        output_text = render_terminal(aggregate, language=args.language)

    if output_text:
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Aggregate report written to {args.output}")
        else:
            print(output_text)

    return 0


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
    if args.command == "scan":
        return handle_scan(args)
    if args.command == "report":
        return handle_report(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
