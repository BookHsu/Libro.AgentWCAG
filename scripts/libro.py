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
AUDIT_EXAMPLES = """Examples:
  libro audit https://example.com
  libro audit .\\src\\index.html --execution-mode suggest-only
  libro audit .\\src\\index.html --execution-mode apply-fixes --dry-run
  libro audit --preflight-only
"""
SCAN_EXAMPLES = """Examples:
  libro scan .\\pages --parallel 4
  libro scan .\\pages --execution-mode audit-only --output-dir .\\wcag-reports
"""
REPORT_EXAMPLES = """Examples:
  libro report .\\out\\wcag-report.json --format terminal
  libro report .\\wcag-reports --format html --output .\\out\\wcag-summary.html
  libro report .\\wcag-reports --format terminal --no-color
"""


def workspace_destination(agent: str, workspace_root: Path) -> Path:
    return workspace_root / f".{agent}" / "skills" / SKILL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="libro",
        description="Unified CLI for installing and validating Libro.AgentWCAG across AI agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=AUDIT_EXAMPLES,
    )
    audit_parser.add_argument("target", nargs="?", help="URL or local file path to audit.")
    audit_parser.add_argument(
        "--print-examples",
        action="store_true",
        help="Print common audit examples and exit.",
    )

    scan_parser = subparsers.add_parser(
        "scan",
        help="Batch-scan multiple targets for WCAG accessibility issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=SCAN_EXAMPLES,
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
    scan_parser.add_argument(
        "--print-examples",
        action="store_true",
        help="Print common batch-scan examples and exit.",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Aggregate multiple wcag-report.json files into a summary report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=REPORT_EXAMPLES,
    )
    report_parser.add_argument(
        "inputs",
        nargs="+",
        help="Paths to wcag-report.json files or directories containing them.",
    )
    report_parser.add_argument(
        "--format",
        choices=("json", "terminal", "markdown", "html", "csv", "badge"),
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
    report_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color in terminal report output.",
    )
    report_parser.add_argument(
        "--print-examples",
        action="store_true",
        help="Print common report examples and exit.",
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


def _resolve_paths(
    inputs: list[str],
    dir_patterns: tuple[str, ...] = ("*",),
    filename_filter: str | None = None,
) -> list[Path]:
    """Resolve file paths from inputs: files, directories, and glob patterns.

    Args:
        inputs: Raw path strings from CLI args.
        dir_patterns: Glob patterns to match when expanding directories.
        filename_filter: If set, only match this exact filename when recursing.
    """
    import glob as glob_mod

    paths: list[Path] = []
    for raw_input in inputs:
        p = Path(raw_input)
        if p.is_file():
            paths.append(p)
        elif p.is_dir():
            if filename_filter:
                found = sorted(p.rglob(filename_filter))
                paths.extend(found)
            else:
                for pattern in dir_patterns:
                    paths.extend(sorted(p.rglob(pattern)))
        else:
            expanded = glob_mod.glob(raw_input, recursive=True)
            for g in sorted(expanded):
                gp = Path(g)
                if gp.is_file():
                    paths.append(gp)
    return paths


def _resolve_scan_targets(args: argparse.Namespace) -> list[str]:
    """Resolve scan targets from CLI args: inputs + optional --targets file."""
    targets: list[str] = []

    # From --targets file (one per line)
    if args.targets:
        targets_file = Path(args.targets)
        if targets_file.is_file():
            for line in targets_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    targets.append(line)

    # From positional inputs: directories expand to HTML files
    found = _resolve_paths(
        args.inputs,
        dir_patterns=("*.html", "*.htm", "*.xhtml"),
    )
    targets.extend(str(p) for p in found)
    return targets


def handle_scan(args: argparse.Namespace) -> int:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if args.print_examples:
        print(SCAN_EXAMPLES.rstrip())
        return 0

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


def _resolve_report_paths(inputs: list[str]) -> list[Path]:
    """Find wcag-report.json files from input paths/directories."""
    paths = _resolve_paths(inputs, filename_filter="wcag-report.json")
    if not paths:
        for raw_input in inputs:
            p = Path(raw_input)
            if p.is_dir():
                print(f"Warning: no wcag-report.json found under {p}", file=sys.stderr)
    return paths


def _write_output(text: str, output_path: str | None) -> None:
    """Write renderer output to file or stdout."""
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(text, encoding="utf-8")
        print(f"Aggregate report written to {output_path}")
    else:
        print(text)


def handle_report(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(REPO_ROOT / "skills" / "libro-wcag" / "scripts"))
    from aggregate_report import build_aggregate_report, load_reports, write_aggregate_json
    from report_renderers import render_badge, render_csv, render_html, render_markdown, render_terminal

    if args.print_examples:
        print(REPORT_EXAMPLES.rstrip())
        return 0

    report_paths = _resolve_report_paths(args.inputs)
    if not report_paths:
        print("Error: no report files found.", file=sys.stderr)
        return 1

    reports = load_reports(report_paths)

    baseline_reports = None
    if args.baseline:
        baseline_paths = _resolve_report_paths([args.baseline])
        if baseline_paths:
            baseline_reports = load_reports(baseline_paths)

    aggregate = build_aggregate_report(reports, baseline_reports=baseline_reports)

    # Dispatch table: format -> renderer callable
    # Each entry returns the output text given (aggregate, reports, language).
    format_renderers = {
        "terminal": lambda: render_terminal(aggregate, language=args.language, use_color=not args.no_color),
        "markdown": lambda: render_markdown(aggregate, language=args.language),
        "html": lambda: render_html(aggregate, language=args.language),
        "csv": lambda: render_csv(reports, aggregate=aggregate),
        "badge": lambda: render_badge(aggregate),
    }

    fmt = args.format
    if fmt == "json":
        if args.output:
            write_aggregate_json(aggregate, Path(args.output))
            print(f"Aggregate report written to {args.output}")
        else:
            import json as json_mod
            print(json_mod.dumps(aggregate, ensure_ascii=False, indent=2))
    else:
        renderer = format_renderers.get(fmt, format_renderers["terminal"])
        _write_output(renderer(), args.output)

    return 0


def handle_audit(args: argparse.Namespace) -> int:
    if args.print_examples:
        print(AUDIT_EXAMPLES.rstrip())
        return 0

    command = [sys.executable, str(AUDIT_SCRIPT)]
    if args.target:
        command.extend(["--target", args.target])
    command.extend(args._remaining)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return completed.returncode


_COMMAND_HANDLERS = {
    "install": handle_install,
    "doctor": handle_doctor,
    "remove": handle_remove,
    "audit": handle_audit,
    "scan": handle_scan,
    "report": handle_report,
}


def main() -> int:
    args = parse_args()
    handler = _COMMAND_HANDLERS.get(args.command)
    if handler is None:
        raise ValueError(f"Unsupported command: {args.command}")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
