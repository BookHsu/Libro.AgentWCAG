#!/usr/bin/env python3
"""Scanner runtime helpers for accessibility audit orchestration."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import url2pathname

DEFAULT_SCANNER_RETRY_ATTEMPTS = 1
DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS = 0.5
MAX_SCANNER_RETRY_BACKOFF_SECONDS = 5.0
ALLOWED_URL_SCHEMES = {"http", "https", "file"}


def _resolve_npx_executable() -> str:
    candidates = ["npx"]
    if os.name == "nt":
        # subprocess on Windows should prefer cmd shim to avoid shell resolution mismatches.
        candidates = ["npx.cmd", "npx.exe", "npx"]
    for candidate in candidates:
        if shutil.which(candidate):
            return candidate
    return "npx"


NPX_EXECUTABLE = _resolve_npx_executable()
PREFLIGHT_TOOL_CHECKS = (
    ("npx", [NPX_EXECUTABLE, "--version"]),
    ("@axe-core/cli", [NPX_EXECUTABLE, "--no-install", "@axe-core/cli", "--version"]),
    ("lighthouse", [NPX_EXECUTABLE, "--no-install", "lighthouse", "--version"]),
)


def _extract_version_line(output: str) -> str | None:
    for line in output.splitlines():
        value = line.strip()
        if value:
            return value
    return None


def _build_version_provenance(
    *,
    source: str,
    command: str,
    resolved_command: str,
    version: str,
) -> dict[str, str]:
    return {
        "source": source,
        "command": command,
        "resolved_command": resolved_command,
        "version": version,
    }


def _run_command(command: list[str], timeout_seconds: int) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"command timed out after {timeout_seconds} seconds"
    except FileNotFoundError as err:
        return False, f"command not found: {err.filename or command[0]}"
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode == 0:
        return True, stdout
    error = stderr.strip() or stdout.strip() or "unknown error"
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
    command = [NPX_EXECUTABLE, "@axe-core/cli", target, "--save", str(axe_json)]
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
        NPX_EXECUTABLE,
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
    results: list[dict[str, Any]] = []
    tools: dict[str, dict[str, Any]] = {}
    ok = True
    for name, command in PREFLIGHT_TOOL_CHECKS:
        command_text = " ".join(command)
        resolved_command = shutil.which(command[0]) or ""
        if not _tool_available(command[0]):
            message = f'{command[0]} is not available in PATH'
            version_provenance = _build_version_provenance(
                source="binary-missing",
                command=command_text,
                resolved_command=resolved_command,
                version="",
            )
            entry = {
                "tool": name,
                "status": "error",
                "message": message,
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
                "version_provenance": version_provenance,
            }
            results.append(entry)
            tools[name] = {
                "status": "error",
                "command": command_text,
                "resolved_command": resolved_command,
                "version": "",
                "message": message,
                "version_provenance": version_provenance,
            }
            ok = False
            continue
        command_ok, output = _run_command(command, timeout_seconds)
        status = "ok" if command_ok else "error"
        message = (output or "").strip() or ("available" if command_ok else "check failed")
        version = _extract_version_line(output) if command_ok else ""
        version_provenance = _build_version_provenance(
            source="command-output-first-line" if command_ok else "command-error",
            command=command_text,
            resolved_command=resolved_command,
            version=version or "",
        )
        entry = {
            "tool": name,
            "status": status,
            "message": message,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
            "version_provenance": version_provenance,
        }
        results.append(entry)
        tools[name] = {
            "status": status,
            "command": command_text,
            "resolved_command": resolved_command,
            "version": version or "",
            "message": message,
            "version_provenance": version_provenance,
        }
        ok = ok and command_ok
    return {"ok": ok, "checks": results, "tools": tools}


__all__ = [
    "ALLOWED_URL_SCHEMES",
    "DEFAULT_SCANNER_RETRY_ATTEMPTS",
    "DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS",
    "MAX_SCANNER_RETRY_BACKOFF_SECONDS",
    "NPX_EXECUTABLE",
    "PREFLIGHT_TOOL_CHECKS",
    "_build_version_provenance",
    "_extract_version_line",
    "_is_transient_scanner_error",
    "_resolve_npx_executable",
    "_resolve_target_for_scanners",
    "_run_command",
    "_run_scanner_with_retry",
    "_tool_available",
    "_try_run_axe",
    "_try_run_lighthouse",
    "run_preflight_checks",
]
