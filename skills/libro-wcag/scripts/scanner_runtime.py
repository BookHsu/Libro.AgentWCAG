#!/usr/bin/env python3
"""Scanner runtime helpers for accessibility audit orchestration."""

from __future__ import annotations

import functools
import http.server
import json
import os
import socket
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlparse
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


def _run_command(
    command: list[str],
    timeout_seconds: int,
    *,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_seconds,
            env=env,
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


def _normalize_axe_payload(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                return item
        return None
    return None


def _format_cli_output_path(path: Path) -> str:
    absolute = path.resolve()
    try:
        relative = absolute.relative_to(Path.cwd().resolve())
        return str(relative)
    except ValueError:
        try:
            return os.path.relpath(str(absolute), str(Path.cwd().resolve()))
        except ValueError:
            return str(absolute)


def _try_run_axe(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    axe_json = output_dir / "axe.raw.json"
    command = [NPX_EXECUTABLE, "@axe-core/cli", target, "--save", _format_cli_output_path(axe_json)]
    ok, result = _run_command(command, timeout_seconds)
    if not ok:
        return None, result
    if not axe_json.exists():
        return None, "axe did not generate output json"
    with axe_json.open("r", encoding="utf-8") as handle:
        payload = _normalize_axe_payload(json.load(handle))
    if payload is None:
        return None, "axe output json format is unsupported"
    return payload, None


def _find_browser_executable() -> str | None:
    configured = os.environ.get("CHROME_PATH", "").strip()
    if configured and Path(configured).exists():
        return configured

    candidates = [
        "chrome",
        "chrome.exe",
        "google-chrome",
        "chromium",
        "chromium-browser",
        "msedge",
        "msedge.exe",
    ]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    if os.name == "nt":
        windows_candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ]
        for candidate in windows_candidates:
            if candidate.exists():
                return str(candidate)

    return None


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def _wait_for_debug_port(port: int, timeout_seconds: int) -> bool:
    deadline = time.time() + max(1, timeout_seconds)
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _resolve_local_target_path(target: str) -> Path | None:
    local_path = Path(target)
    if local_path.exists():
        return local_path.resolve()

    parsed = urlparse(target)
    if parsed.scheme != "file":
        return None
    if parsed.netloc not in {"", "localhost"}:
        return None
    file_path = Path(url2pathname(parsed.path))
    if file_path.exists():
        return file_path.resolve()
    return None


class _QuietStaticFileHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def _inject_lighthouse_paint_marker(html: str) -> str:
    marker = (
        '<div aria-hidden="true" '
        'style="position:fixed;top:0;left:0;width:2px;height:2px;'
        'background:#000;opacity:1;pointer-events:none;z-index:2147483647"></div>'
    )
    body_close = "</body>"
    if body_close in html:
        return html.replace(body_close, f"{marker}{body_close}", 1)
    return html + marker


class _LighthouseFixtureHandler(_QuietStaticFileHandler):
    target_name: str

    def do_GET(self) -> None:
        request_path = urlparse(self.path).path.lstrip("/")
        if request_path == self.target_name:
            target_path = Path(self.directory) / self.target_name
            if target_path.exists():
                content = _inject_lighthouse_paint_marker(
                    target_path.read_text(encoding="utf-8")
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
        super().do_GET()


def _start_local_file_server(target_path: Path) -> tuple[http.server.ThreadingHTTPServer, threading.Thread, str]:
    handler_class = type(
        "_BoundLighthouseFixtureHandler",
        (_LighthouseFixtureHandler,),
        {"target_name": target_path.name},
    )
    handler = functools.partial(handler_class, directory=str(target_path.parent))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    served_target = f"http://127.0.0.1:{server.server_port}/{quote(target_path.name)}"
    return server, thread, served_target


def _try_run_lighthouse(
    target: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, str | None]:
    lighthouse_json = output_dir / "lighthouse.raw.json"
    browser_executable = _find_browser_executable()
    if not browser_executable:
        return None, "browser executable not found for lighthouse"

    lighthouse_temp_root = output_dir / "lighthouse-tmp"
    chrome_profile_dir = lighthouse_temp_root / "chrome-profile"
    lighthouse_temp_root.mkdir(parents=True, exist_ok=True)
    chrome_profile_dir.mkdir(parents=True, exist_ok=True)
    port = _find_free_port()
    browser_command = [
        browser_executable,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={chrome_profile_dir.resolve()}",
        "about:blank",
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))

    browser_process = subprocess.Popen(
        browser_command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    file_server: http.server.ThreadingHTTPServer | None = None
    file_server_thread: threading.Thread | None = None
    try:
        if not _wait_for_debug_port(port, min(timeout_seconds, 15)):
            return None, "debug browser did not become ready for lighthouse"

        lighthouse_target = target
        local_target_path = _resolve_local_target_path(target)
        if local_target_path is not None:
            file_server, file_server_thread, lighthouse_target = _start_local_file_server(local_target_path)

        command = [
            NPX_EXECUTABLE,
            "lighthouse",
            lighthouse_target,
            f"--port={port}",
            "--only-categories=accessibility",
            "--output=json",
            f"--output-path={lighthouse_json}",
            "--quiet",
        ]
        ok, result = _run_command(command, timeout_seconds)
        if not ok:
            return None, result
    finally:
        if file_server is not None:
            file_server.shutdown()
            file_server.server_close()
        if file_server_thread is not None:
            file_server_thread.join(timeout=5)
        if browser_process.poll() is None:
            browser_process.terminate()
            try:
                browser_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser_process.kill()
                browser_process.wait(timeout=5)
        shutil.rmtree(lighthouse_temp_root, ignore_errors=True)
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


def _collect_scanner_rule_ids(
    axe_data: dict[str, Any] | None,
    lighthouse_data: dict[str, Any] | None,
) -> list[str]:
    rule_ids: set[str] = set()
    normalized_axe = _normalize_axe_payload(axe_data)
    if isinstance(normalized_axe, dict):
        for violation in normalized_axe.get("violations", []):
            if not isinstance(violation, dict):
                continue
            rule_id = str(violation.get("id", "")).strip()
            if rule_id:
                rule_ids.add(rule_id)
    if isinstance(lighthouse_data, dict):
        audits = lighthouse_data.get("audits", {})
        if isinstance(audits, dict):
            for audit_id in audits:
                if isinstance(audit_id, str):
                    value = audit_id.strip()
                    if value:
                        rule_ids.add(value)
    return sorted(rule_ids)


def _build_scanner_capabilities(
    preflight: dict[str, Any],
    report: dict[str, Any],
    args: Any,
    axe_data: dict[str, Any] | None,
    lighthouse_data: dict[str, Any] | None,
) -> dict[str, Any]:
    tools = preflight.get("tools", {})
    run_tools = report.get("run_meta", {}).get("tools", {})
    available_rules = _collect_scanner_rule_ids(axe_data, lighthouse_data)
    scanner_map = {
        "axe": {
            "requested": not args.skip_axe,
            "mocked": bool(args.mock_axe_json),
            "preflight_tool": "@axe-core/cli",
        },
        "lighthouse": {
            "requested": not args.skip_lighthouse,
            "mocked": bool(args.mock_lighthouse_json),
            "preflight_tool": "lighthouse",
        },
    }
    scanners: dict[str, Any] = {}
    for scanner, config in scanner_map.items():
        preflight_tool = config["preflight_tool"]
        preflight_entry = tools.get(preflight_tool, {})
        preflight_status = str(preflight_entry.get("status", "unknown"))
        input_mode = "skipped"
        if config["mocked"]:
            input_mode = "mock"
        elif config["requested"]:
            input_mode = "live"
        scanners[scanner] = {
            "requested": config["requested"],
            "input_mode": input_mode,
            "preflight_status": preflight_status,
            "run_status": run_tools.get(scanner, "unknown"),
            "available": bool(config["mocked"] or preflight_status == "ok"),
        }

    return {
        "scanners": scanners,
        "available_rules": available_rules,
        "available_rule_count": len(available_rules),
    }


__all__ = [
    "ALLOWED_URL_SCHEMES",
    "DEFAULT_SCANNER_RETRY_ATTEMPTS",
    "DEFAULT_SCANNER_RETRY_BACKOFF_SECONDS",
    "MAX_SCANNER_RETRY_BACKOFF_SECONDS",
    "NPX_EXECUTABLE",
    "PREFLIGHT_TOOL_CHECKS",
    "_build_version_provenance",
    "_build_scanner_capabilities",
    "_collect_scanner_rule_ids",
    "_extract_version_line",
    "_find_browser_executable",
    "_find_free_port",
    "_format_cli_output_path",
    "_is_transient_scanner_error",
    "_normalize_axe_payload",
    "_resolve_npx_executable",
    "_resolve_target_for_scanners",
    "_run_command",
    "_run_scanner_with_retry",
    "_tool_available",
    "_try_run_axe",
    "_try_run_lighthouse",
    "_wait_for_debug_port",
    "run_preflight_checks",
]
