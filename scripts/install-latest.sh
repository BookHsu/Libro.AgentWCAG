#!/usr/bin/env sh
set -eu

python - "$@" <<'PY'
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and install the latest Libro.AgentWCAG release bundle.")
    parser.add_argument("--release-base", required=True)
    parser.add_argument("--agent", default="codex", choices=["codex", "claude", "gemini", "copilot"])
    parser.add_argument("--version")
    parser.add_argument("--dest")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-downloaded", action="store_true")
    return parser.parse_args()


def _is_url(value: str) -> bool:
    return urllib.parse.urlparse(value).scheme in {"http", "https", "file"}


def _read_text(base: str, name: str) -> str:
    if _is_url(base):
        base_url = base.rstrip("/") + "/"
        with urllib.request.urlopen(base_url + name) as response:
            return response.read().decode("utf-8")
    return (Path(base) / name).read_text(encoding="utf-8")


def _copy_asset(base: str, name: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if _is_url(base):
        base_url = base.rstrip("/") + "/"
        with urllib.request.urlopen(base_url + name) as response, destination.open("wb") as handle:
            handle.write(response.read())
    else:
        shutil.copyfile(Path(base) / name, destination)
    return destination


def _parse_checksums(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, filename = line.split(" *", 1)
        entries[filename] = digest
    return entries


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_checked(command: list[str], cwd: Path, env: dict[str, str], *, step: str) -> None:
    try:
        completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    except PermissionError as exc:
        raise RuntimeError(f"{step} failed due to insufficient filesystem permissions") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"{step} exited with code {completed.returncode}")


def _require_python() -> None:
    if not sys.executable:
        raise RuntimeError("python runtime is unavailable; install Python 3.12+ and ensure it is in PATH")


def main() -> int:
    _require_python()
    args = parse_args()
    stage_dir = Path(tempfile.mkdtemp(prefix="libro-agentwcag-install-"))
    try:
        if args.version:
            manifest_name = f"libro-agent-wcag-{args.version}-release-manifest.json"
        else:
            latest = json.loads(_read_text(args.release_base, "latest-release.json"))
            manifest_name = str(latest["release_manifest"])
        manifest = json.loads(_read_text(args.release_base, manifest_name))
        checksum_name = str(manifest["checksum_file"])
        checksums = _parse_checksums(_read_text(args.release_base, checksum_name))
        bundle_asset = next(
            asset for asset in manifest["assets"]
            if asset.get("kind") == "bundle" and asset.get("agent") == args.agent
        )

        bundle_path = _copy_asset(args.release_base, str(bundle_asset["filename"]), stage_dir / str(bundle_asset["filename"]))
        actual_hash = _sha256(bundle_path)
        if checksums.get(bundle_path.name) != actual_hash:
            raise RuntimeError("bundle checksum verification failed")
        if bundle_asset.get("sha256") != actual_hash:
            raise RuntimeError("bundle hash does not match release manifest")

        extract_dir = stage_dir / "extract"
        with zipfile.ZipFile(bundle_path) as archive:
            archive.extractall(extract_dir)
        bundle_root = extract_dir / str(bundle_asset["bundle_root"])

        env = os.environ.copy()
        env["LIBRO_AGENTWCAG_SOURCE_REVISION"] = str(manifest["source_revision"])
        if "build_timestamp" in manifest:
            env["LIBRO_AGENTWCAG_BUILD_TIMESTAMP"] = str(manifest["build_timestamp"])

        command = [
            sys.executable,
            str(bundle_root / "scripts" / "install-agent.py"),
            "--agent",
            args.agent,
        ]
        if args.dest:
            command.extend(["--dest", args.dest])
        if args.force:
            command.append("--force")

        _run_checked(command, bundle_root, env, step="install-agent.py")

        doctor_command = [
            sys.executable,
            str(bundle_root / "scripts" / "doctor-agent.py"),
            "--agent",
            args.agent,
            "--verify-manifest-integrity",
        ]
        if args.dest:
            doctor_command.extend(["--dest", args.dest])
        _run_checked(doctor_command, bundle_root, env, step="doctor-agent.py")
        print("Bootstrap install completed and doctor verification passed.")
        return 0
    except urllib.error.URLError as exc:
        raise RuntimeError("network failure while downloading release assets") from exc
    except PermissionError as exc:
        raise RuntimeError("insufficient filesystem permissions while staging release assets") from exc
    finally:
        if not args.keep_downloaded:
            shutil.rmtree(stage_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
PY
