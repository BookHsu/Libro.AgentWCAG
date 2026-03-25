#!/usr/bin/env sh
set -eu

python - "$@" <<'PY'
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_REPO = "BookHsu/Libro.AgentWCAG.clean"
DEFAULT_REF = "master"
SUPPORTED_AGENTS = ["codex", "claude", "gemini", "copilot", "all"]
SOURCE_REVISION_ENV_VAR = "LIBRO_AGENTWCAG_SOURCE_REVISION"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Libro.AgentWCAG from GitHub and run the local installer."
    )
    parser.add_argument("--agent", required=True, choices=SUPPORTED_AGENTS)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--archive-path")
    parser.add_argument("--dest")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-downloaded", action="store_true")
    return parser.parse_args()


def _archive_url(repo: str, ref: str) -> str:
    return f"https://github.com/{repo}/archive/{ref}.zip"


def _download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        handle.write(response.read())
    return destination


def _resolve_source_revision(repo: str, ref: str) -> str:
    explicit_revision = os.environ.get(SOURCE_REVISION_ENV_VAR, "").strip()
    if explicit_revision:
        return explicit_revision
    if re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        return ref.lower()
    api_url = f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(ref, safe='')}"
    with urllib.request.urlopen(api_url) as response:
        payload = json.loads(response.read().decode("utf-8"))
    sha = str(payload.get("sha", "")).strip()
    if re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        return sha.lower()
    raise RuntimeError("unable to resolve source revision for repository archive")


def _run_checked(command: list[str], cwd: Path, env: dict[str, str], *, step: str) -> None:
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{step} exited with code {completed.returncode}")


def _require_python_312() -> None:
    if not sys.executable:
        raise RuntimeError("python runtime is unavailable; install Python 3.12+ and ensure it is in PATH")
    if sys.version_info < (3, 12):
        raise RuntimeError(
            f"python 3.12+ is required; detected {sys.version_info.major}.{sys.version_info.minor}"
        )


def _find_repo_root(extract_dir: Path) -> Path:
    children = [item for item in extract_dir.iterdir() if item.is_dir()]
    if len(children) != 1:
        raise RuntimeError("downloaded archive did not contain a single repository root")
    return children[0]


def main() -> int:
    args = parse_args()
    _require_python_312()

    stage_dir = Path(tempfile.mkdtemp(prefix="libro-agentwcag-bootstrap-"))
    try:
        archive_path = stage_dir / "repo.zip"
        if args.archive_path:
            shutil.copyfile(args.archive_path, archive_path)
        else:
            _download(_archive_url(args.repo, args.ref), archive_path)

        extract_dir = stage_dir / "extract"
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_dir)
        repo_root = _find_repo_root(extract_dir)

        env = os.environ.copy()
        env[SOURCE_REVISION_ENV_VAR] = _resolve_source_revision(args.repo, args.ref)
        command = [
            sys.executable,
            str(repo_root / "scripts" / "install-agent.py"),
            "--agent",
            args.agent,
        ]
        if args.dest:
            command.extend(["--dest", args.dest])
        if args.force:
            command.append("--force")
        _run_checked(command, repo_root, env, step="install-agent.py")

        doctor_command = [
            sys.executable,
            str(repo_root / "scripts" / "doctor-agent.py"),
            "--agent",
            args.agent,
            "--verify-manifest-integrity",
        ]
        if args.dest:
            doctor_command.extend(["--dest", args.dest])
        _run_checked(doctor_command, repo_root, env, step="doctor-agent.py")
        print("Bootstrap install completed and doctor verification passed.")
        return 0
    except urllib.error.URLError as exc:
        raise RuntimeError("network failure while downloading repository archive") from exc
    except PermissionError as exc:
        raise RuntimeError("insufficient filesystem permissions while staging or installing repository archive") from exc
    finally:
        if not args.keep_downloaded:
            shutil.rmtree(stage_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
PY
