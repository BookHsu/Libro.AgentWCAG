#!/usr/bin/env python3
"""Unified CLI entrypoint for Libro.AgentWCAG."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, NamedTuple
from urllib.parse import urlparse

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
SCAN_LOG_NAME = "scan-output.log"


class ScanExecutionResult(NamedTuple):
    target: str
    returncode: int
    target_dir: Path
    log_path: Path | None
    summary: str


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


def _print_examples_if_requested(print_examples: bool, examples: str) -> bool:
    if not print_examples:
        return False
    print(examples.rstrip())
    return True


def _ensure_skill_scripts_on_path() -> None:
    skill_scripts_dir = str(REPO_ROOT / "skills" / "libro-wcag" / "scripts")
    if skill_scripts_dir not in sys.path:
        sys.path.insert(0, skill_scripts_dir)


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
    deduped: list[str] = []
    seen: set[str] = set()
    for target in targets:
        normalized = os.path.normcase(target) if os.name == "nt" else target
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(target)
    return deduped


def _scan_target_label(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme and parsed.scheme not in {"", "file"}:
        path_name = Path(parsed.path).stem if parsed.path else ""
        host_name = parsed.netloc.replace(".", "-")
        return "-".join(part for part in [host_name, path_name] if part) or "target"
    return Path(target).stem or "target"


def _scan_target_dir_name(target: str, index: int) -> str:
    label = _scan_target_label(target)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-._") or f"target-{index}"
    stable_suffix = hashlib.sha1(target.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{stable_suffix}"


def _write_scan_log(target_dir: Path, stdout: str, stderr: str) -> Path | None:
    content_parts = []
    if stdout.strip():
        content_parts.append("=== STDOUT ===\n" + stdout.rstrip())
    if stderr.strip():
        content_parts.append("=== STDERR ===\n" + stderr.rstrip())
    if not content_parts:
        return None
    log_path = target_dir / SCAN_LOG_NAME
    log_path.write_text("\n\n".join(content_parts) + "\n", encoding="utf-8")
    return log_path


def _summarize_scan_output(stdout: str, stderr: str, *, max_lines: int = 3) -> str:
    source = stderr if stderr.strip() else stdout
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not lines:
        return "No stderr/stdout captured."
    tail = lines[-max_lines:]
    return " | ".join(tail)


def _stdout_supports_unicode() -> bool:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "🔴░".encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def _scan_target_dir(output_dir: Path, target: str, index: int) -> Path:
    target_dir = output_dir / _scan_target_dir_name(target, index)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _scan_command(target: str, execution_mode: str, target_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(AUDIT_SCRIPT),
        "--target",
        target,
        "--execution-mode",
        execution_mode,
        "--output-dir",
        str(target_dir),
    ]


def _run_scan_target(
    target: str,
    index: int,
    *,
    output_dir: Path,
    execution_mode: str,
) -> ScanExecutionResult:
    target_dir = _scan_target_dir(output_dir, target, index)
    result = subprocess.run(
        _scan_command(target, execution_mode, target_dir),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_path = _write_scan_log(target_dir, result.stdout, result.stderr)
    summary = _summarize_scan_output(result.stdout, result.stderr)
    return ScanExecutionResult(
        target=target,
        returncode=result.returncode,
        target_dir=target_dir,
        log_path=log_path,
        summary=summary,
    )


def _print_scan_progress(result: ScanExecutionResult, completed_count: int, total_targets: int) -> None:
    if result.returncode != 0:
        print(f"  [{completed_count}/{total_targets}] FAIL ({result.returncode}): {result.target}")
        if result.log_path is not None:
            print(f"     log: {result.log_path}")
        print(f"     summary: {result.summary}")
        return
    print(f"  [{completed_count}/{total_targets}] OK: {result.target}")
    print(f"     output: {result.target_dir}")


def _print_scan_summary(output_dir: Path, total_targets: int, errors: list[ScanExecutionResult]) -> int:
    print(f"\nCompleted: {total_targets - len(errors)}/{total_targets} succeeded")
    if errors:
        print(f"Failed: {len(errors)} target(s)")
        for result in errors:
            print(f"  - {result.target} (exit code {result.returncode})")
            if result.log_path is not None:
                print(f"    log: {result.log_path}")
            print(f"    summary: {result.summary}")
        return 1
    print(f"Reports written to: {output_dir}/")
    return 0


def handle_scan(args: argparse.Namespace) -> int:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if _print_examples_if_requested(args.print_examples, SCAN_EXAMPLES):
        return 0

    targets = _resolve_scan_targets(args)
    if not targets:
        print("Error: no scan targets found.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    execution_mode = args.execution_mode
    parallel = max(1, args.parallel)

    errors: list[ScanExecutionResult] = []
    completed_count = 0

    print(f"Scanning {len(targets)} target(s) with parallelism={parallel}...")
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = [
            executor.submit(
                _run_scan_target,
                target,
                i,
                output_dir=output_dir,
                execution_mode=execution_mode,
            )
            for i, target in enumerate(targets)
        ]
        for future in as_completed(futures):
            result = future.result()
            completed_count += 1
            if result.returncode != 0:
                errors.append(result)
            _print_scan_progress(result, completed_count, len(targets))

    return _print_scan_summary(output_dir, len(targets), errors)


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
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        print(f"Aggregate report written to {output_path}")
    else:
        print(text)


def _write_json_output(
    payload: Any,
    output_path: str | None,
    file_writer: Callable[[Any, Path], None],
) -> None:
    if output_path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_writer(payload, destination)
        print(f"Aggregate report written to {output_path}")
        return
    import json as json_mod

    print(json_mod.dumps(payload, ensure_ascii=False, indent=2))


def _should_use_terminal_color(*, output_path: str | None, no_color: bool) -> bool:
    if no_color:
        return False
    if output_path:
        return True
    return _stdout_supports_unicode()


def _load_report_runtime() -> dict[str, Callable[..., Any]]:
    _ensure_skill_scripts_on_path()
    from aggregate_report import build_aggregate_report, load_reports, write_aggregate_json
    from report_renderers import render_badge, render_csv, render_html, render_markdown, render_terminal

    return {
        "build_aggregate_report": build_aggregate_report,
        "load_reports": load_reports,
        "write_aggregate_json": write_aggregate_json,
        "render_terminal": render_terminal,
        "render_markdown": render_markdown,
        "render_html": render_html,
        "render_csv": render_csv,
        "render_badge": render_badge,
    }


def _load_optional_baseline(
    baseline: str | None,
    load_reports: Callable[[list[Path]], Any],
) -> Any | None:
    if not baseline:
        return None
    baseline_paths = _resolve_report_paths([baseline])
    if not baseline_paths:
        return None
    return load_reports(baseline_paths)


def _render_report_output(
    fmt: str,
    *,
    aggregate: Any,
    reports: Any,
    language: str,
    use_color: bool,
    runtime: dict[str, Callable[..., Any]],
) -> str:
    if fmt == "terminal":
        return runtime["render_terminal"](aggregate, language=language, use_color=use_color)
    if fmt == "markdown":
        return runtime["render_markdown"](aggregate, language=language)
    if fmt == "html":
        return runtime["render_html"](aggregate, language=language)
    if fmt == "csv":
        return runtime["render_csv"](reports, aggregate=aggregate)
    if fmt == "badge":
        return runtime["render_badge"](aggregate)
    return runtime["render_terminal"](aggregate, language=language, use_color=use_color)


def handle_report(args: argparse.Namespace) -> int:
    if _print_examples_if_requested(args.print_examples, REPORT_EXAMPLES):
        return 0

    report_paths = _resolve_report_paths(args.inputs)
    if not report_paths:
        print("Error: no report files found.", file=sys.stderr)
        return 1

    runtime = _load_report_runtime()
    reports = runtime["load_reports"](report_paths)
    baseline_reports = _load_optional_baseline(args.baseline, runtime["load_reports"])
    aggregate = runtime["build_aggregate_report"](reports, baseline_reports=baseline_reports)
    use_color = _should_use_terminal_color(output_path=args.output, no_color=args.no_color)

    if args.format == "json":
        _write_json_output(aggregate, args.output, runtime["write_aggregate_json"])
    else:
        rendered = _render_report_output(
            args.format,
            aggregate=aggregate,
            reports=reports,
            language=args.language,
            use_color=use_color,
            runtime=runtime,
        )
        _write_output(rendered, args.output)

    return 0


def handle_audit(args: argparse.Namespace) -> int:
    if _print_examples_if_requested(args.print_examples, AUDIT_EXAMPLES):
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
