#!/usr/bin/env python3
"""Run axe and Lighthouse scans, then emit normalized WCAG outputs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import url2pathname

from auto_fix import (
    apply_report_fixes,
    supports_apply_fixes_target,
    target_to_local_path,
    write_diff,
    write_snapshot,
)
from wcag_workflow import normalize_report, resolve_contract, write_report_files

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_SCANNER_RETRY_ATTEMPTS = 1
DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS = 0.5
MAX_SCANNER_RETRY_BACKOFF_SECONDS = 5.0
ALLOWED_URL_SCHEMES = {"http", "https", "file"}
PREFLIGHT_TOOL_CHECKS = (
    ("npx", ["npx", "--version"]),
    ("@axe-core/cli", ["npx", "--no-install", "@axe-core/cli", "--version"]),
    ("lighthouse", ["npx", "--no-install", "lighthouse", "--version"]),
)


def _extract_version_line(output: str) -> str | None:
    for line in output.splitlines():
        value = line.strip()
        if value:
            return value
    return None


def _run_command(command: list[str], timeout_seconds: int) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"command timed out after {timeout_seconds} seconds"
    except FileNotFoundError as err:
        return False, f"command not found: {err.filename or command[0]}"
    if completed.returncode == 0:
        return True, completed.stdout
    error = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
    return False, error

def _is_transient_scanner_error(error_message: str | None) -> bool:
    text = (error_message or "").lower()
    return any(
        token in text
        for token in (
            "timed out",
            "econnreset",
            "econnrefused",
            "eai_again",
            "temporarily unavailable",
            "temporary failure",
            "network",
        )
    )


def _run_scanner_with_retry(
    scanner: str,
    runner: Callable[[], tuple[dict[str, Any] | None, str | None]],
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    attempts = max(1, retry_attempts)
    initial_backoff = max(0.0, retry_backoff_seconds)
    transient_error = False
    data: dict[str, Any] | None = None
    error: str | None = None

    for attempt in range(1, attempts + 1):
        data, error = runner()
        if data is not None and not error:
            return data, None, {
                "tool": scanner,
                "attempts": attempt,
                "retry_count": attempt - 1,
                "succeeded": True,
                "last_error": "",
                "transient_error": False,
            }

        transient_error = _is_transient_scanner_error(error)
        should_retry = attempt < attempts and transient_error
        if not should_retry:
            break

        if initial_backoff > 0:
            delay = min(
                initial_backoff * (2 ** (attempt - 1)),
                MAX_SCANNER_RETRY_BACKOFF_SECONDS,
            )
            time.sleep(delay)

    return data, error, {
        "tool": scanner,
        "attempts": attempt,
        "retry_count": attempt - 1,
        "succeeded": False,
        "last_error": error or "unknown error",
        "transient_error": transient_error,
    }

def _try_run_axe(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    axe_json = output_dir / "axe.raw.json"
    command = ["npx", "@axe-core/cli", target, "--save", str(axe_json)]
    ok, result = _run_command(command, timeout_seconds)
    if not ok:
        return None, result
    if not axe_json.exists():
        return None, "axe did not generate output json"
    with axe_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _try_run_lighthouse(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    lighthouse_json = output_dir / "lighthouse.raw.json"
    command = [
        "npx",
        "lighthouse",
        target,
        "--only-categories=accessibility",
        "--output=json",
        f"--output-path={lighthouse_json}",
        "--chrome-flags=--headless=new",
    ]
    ok, result = _run_command(command, timeout_seconds)
    if not ok:
        return None, result
    if not lighthouse_json.exists():
        return None, "lighthouse did not generate output json"
    with lighthouse_json.open("r", encoding="utf-8") as handle:
        return json.load(handle), None


def _resolve_target_for_scanners(target: str) -> str:
    local_path = Path(target)
    if local_path.exists():
        return local_path.resolve().as_uri()
    parsed = urlparse(target)
    if parsed.scheme:
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            raise ValueError(f"Unsupported target scheme: {parsed.scheme}")
        if parsed.scheme == "file":
            if parsed.netloc not in {"", "localhost"}:
                raise ValueError(f"Unsupported file target host: {parsed.netloc}")
            file_path = Path(url2pathname(parsed.path))
            if not file_path.exists():
                raise ValueError(f"Target file does not exist: {target}")
        return target
    if "://" in target:
        raise ValueError(f"Unsupported target scheme in: {target}")
    raise ValueError(f"Target must be an existing local file or a valid URL: {target}")


def _tool_available(tool: str) -> bool:
    return shutil.which(tool) is not None


def run_preflight_checks(timeout_seconds: int) -> dict[str, Any]:
    results: list[dict[str, str]] = []
    tools: dict[str, dict[str, str]] = {}
    ok = True
    for name, command in PREFLIGHT_TOOL_CHECKS:
        command_text = " ".join(command)
        resolved_command = shutil.which(command[0]) or ""
        if not _tool_available(command[0]):
            message = f'{command[0]} is not available in PATH'
            entry = {
                "tool": name,
                "status": "error",
                "message": message,
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
            }
            results.append(entry)
            tools[name] = {
                "status": "error",
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
                "message": message,
            }
            ok = False
            continue
        command_ok, output = _run_command(command, timeout_seconds)
        status = "ok" if command_ok else "error"
        message = (output or "").strip() or ("available" if command_ok else "check failed")
        version = _extract_version_line(output) if command_ok else ""
        entry = {
            "tool": name,
            "status": status,
            "message": message,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
        }
        results.append(entry)
        tools[name] = {
            "status": status,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
            "message": message,
        }
        ok = ok and command_ok
    return {"ok": ok, "checks": results, "tools": tools}


def _remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WCAG audit with axe+Lighthouse.")
    parser.add_argument("--task-mode", default="modify", choices=["create", "modify"])
    parser.add_argument(
        "--execution-mode",
        default="suggest-only",
        choices=["audit-only", "suggest-only", "apply-fixes"],
    )
    parser.add_argument("--wcag-version", default="2.1", choices=["2.0", "2.1", "2.2"])
    parser.add_argument("--conformance-level", default="AA", choices=["A", "AA", "AAA"])
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-language", default="zh-TW")
    parser.add_argument("--output-dir", default="out")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--scanner-retry-attempts",
        type=int,
        default=DEFAULT_SCANNER_RETRY_ATTEMPTS,
        help="Retry attempts per scanner for transient runtime failures (minimum: 1).",
    )
    parser.add_argument(
        "--scanner-retry-backoff-seconds",
        type=float,
        default=DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS,
        help="Initial retry backoff in seconds for transient scanner failures.",
    )
    parser.add_argument("--skip-axe", action="store_true")
    parser.add_argument("--skip-lighthouse", action="store_true")
    parser.add_argument("--mock-axe-json")
    parser.add_argument("--mock-lighthouse-json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Check runtime tooling availability (npx, axe, lighthouse) and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_axe and args.mock_axe_json:
        raise ValueError('--skip-axe cannot be combined with --mock-axe-json')
    if args.skip_lighthouse and args.mock_lighthouse_json:
        raise ValueError('--skip-lighthouse cannot be combined with --mock-lighthouse-json')
    if args.dry_run and args.execution_mode != 'apply-fixes':
        raise ValueError('--dry-run is only supported when --execution-mode is apply-fixes')
    if args.scanner_retry_attempts < 1:
        raise ValueError('--scanner-retry-attempts must be >= 1')
    if args.scanner_retry_backoff_seconds < 0:
        raise ValueError('--scanner-retry-backoff-seconds must be >= 0')

    if args.preflight_only:
        preflight = run_preflight_checks(args.timeout)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0 if preflight["ok"] else 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = resolve_contract(
        {
            "task_mode": args.task_mode,
            "execution_mode": args.execution_mode,
            "wcag_version": args.wcag_version,
            "conformance_level": args.conformance_level,
            "target": args.target,
            "output_language": args.output_language,
        }
    )
    local_target = target_to_local_path(contract.target)
    scanner_target = _resolve_target_for_scanners(contract.target)

    preflight_required = not (
        (args.skip_axe or args.mock_axe_json) and (args.skip_lighthouse or args.mock_lighthouse_json)
    )
    if preflight_required:
        preflight = run_preflight_checks(args.timeout)
    else:
        preflight = {
            "ok": True,
            "checks": [
                {
                    "tool": "runtime",
                    "status": "skipped",
                    "message": "scanner tooling preflight skipped due to mock or skip flags",
                    "command": "",
                    "resolved_command": "",
                    "version": "",
                }
            ],
            "tools": {
                "runtime": {
                    "status": "skipped",
                    "command": "",
                    "resolved_command": "",
                    "version": "",
                    "message": "scanner tooling preflight skipped due to mock or skip flags",
                }
            },
        }

    axe_data = None
    axe_error = None
    scanner_retry_runs: list[dict[str, Any]] = []
    if args.mock_axe_json:
        axe_data = json.loads(Path(args.mock_axe_json).read_text(encoding='utf-8'))
    elif not args.skip_axe:
        axe_data, axe_error, axe_retry = _run_scanner_with_retry(
            'axe',
            lambda: _try_run_axe(scanner_target, output_dir, args.timeout),
            args.scanner_retry_attempts,
            args.scanner_retry_backoff_seconds,
        )
        scanner_retry_runs.append(axe_retry)

    lighthouse_data = None
    lighthouse_error = None
    if args.mock_lighthouse_json:
        lighthouse_data = json.loads(Path(args.mock_lighthouse_json).read_text(encoding='utf-8'))
    elif not args.skip_lighthouse:
        lighthouse_data, lighthouse_error, lighthouse_retry = _run_scanner_with_retry(
            'lighthouse',
            lambda: _try_run_lighthouse(
                scanner_target,
                output_dir,
                args.timeout,
            ),
            args.scanner_retry_attempts,
            args.scanner_retry_backoff_seconds,
        )
        scanner_retry_runs.append(lighthouse_retry)

    report = normalize_report(
        contract=contract,
        axe_data=axe_data,
        lighthouse_data=lighthouse_data,
        axe_error=axe_error,
        lighthouse_error=lighthouse_error,
        axe_skipped=args.skip_axe,
        lighthouse_skipped=args.skip_lighthouse,
    )
    report['run_meta']['preflight'] = preflight
    report['run_meta']['retry_policy'] = {
        'attempts': args.scanner_retry_attempts,
        'initial_backoff_seconds': args.scanner_retry_backoff_seconds,
        'max_backoff_seconds': MAX_SCANNER_RETRY_BACKOFF_SECONDS,
    }
    if scanner_retry_runs:
        report['run_meta']['scanner_retries'] = scanner_retry_runs
        retried_tools = [item['tool'] for item in scanner_retry_runs if item.get('retry_count', 0) > 0]
        if retried_tools:
            report['run_meta']['notes'].append(
                f"Retried scanner execution for transient errors: {', '.join(sorted(set(retried_tools)))}."
            )
    if not preflight['ok']:
        report['run_meta']['notes'].append(
            'Preflight checks detected tooling issues; scanner results may be incomplete.'
        )

    if contract.execution_mode == 'apply-fixes':
        if args.dry_run:
            diff_path = output_dir / 'wcag-fixes.dry-run.diff'
            snapshot_path = output_dir / 'wcag-fixed-report.dry-run.snapshot.json'
        else:
            diff_path = output_dir / 'wcag-fixes.diff'
            snapshot_path = output_dir / 'wcag-fixed-report.snapshot.json'

        if local_target is None:
            report['run_meta']['notes'].append('apply-fixes skipped: target is not a local file path.')
            _remove_if_exists(diff_path)
            _remove_if_exists(snapshot_path)
        elif not supports_apply_fixes_target(local_target):
            report['run_meta']['notes'].append(
                f'apply-fixes skipped: unsupported local target extension "{local_target.suffix or "<none>"}".'
            )
            _remove_if_exists(diff_path)
            _remove_if_exists(snapshot_path)
        else:
            report, diff_text = apply_report_fixes(local_target, report, dry_run=args.dry_run)
            if diff_text:
                write_diff(diff_text, diff_path)
                diff_type = 'projected-unified-diff' if args.dry_run else 'unified-diff'
                report['run_meta'].setdefault('diff_artifacts', []).append(
                    {'path': str(diff_path), 'type': diff_type}
                )
                if args.dry_run:
                    report['run_meta']['notes'].append(
                        f'Saved projected auto-fix diff (--dry-run): {diff_path}'
                    )
                else:
                    report['run_meta']['notes'].append(f'Saved auto-fix diff: {diff_path}')
                write_snapshot(report, snapshot_path)
            else:
                _remove_if_exists(diff_path)
                _remove_if_exists(snapshot_path)

    output_json = output_dir / "wcag-report.json"
    output_md = output_dir / "wcag-report.md"
    write_report_files(report, str(output_json), str(output_md))

    print(f"Saved JSON report: {output_json}")
    print(f"Saved Markdown table: {output_md}")
    if report["run_meta"]["notes"]:
        print("Notes:")
        for note in report["run_meta"]["notes"]:
            print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
