#!/usr/bin/env python3
"""Run release-consumer smoke flow from packaged release assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_AGENTS = ("codex", "claude", "gemini", "copilot")
DEFAULT_SOURCE_REVISION = "0123456789abcdef0123456789abcdef01234567"
DEFAULT_BUILD_TIMESTAMP = "2026-03-23T00:00:00Z"
AXE_FIXTURE = {
    "violations": [
        {
            "id": "image-alt",
            "impact": "serious",
            "description": "Images must have alternate text",
            "nodes": [{"target": ["img.hero"]}],
        },
        {
            "id": "button-name",
            "impact": "serious",
            "description": "Buttons must have discernible text",
            "nodes": [{"target": ["button.icon-only"]}],
        },
    ]
}
LIGHTHOUSE_FIXTURE = {
    "audits": {
        "meta-viewport": {
            "score": 0,
            "scoreDisplayMode": "binary",
            "title": "User-scalable is not disabled",
            "details": {"items": [{"node": {"selector": "meta[name=\"viewport\"]"}}]},
        }
    }
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run release adoption smoke from packaged assets.")
    parser.add_argument("--agent", default="codex", choices=SUPPORTED_AGENTS)
    parser.add_argument("--release-dir", help="Directory containing packaged release assets.")
    parser.add_argument("--version", help="Pinned version to use. Defaults to latest-release.json.")
    parser.add_argument(
        "--summary-path",
        help="Destination for smoke-summary.json. Defaults to .tmp-release-smoke-summary.json in the repo root.",
    )
    parser.add_argument("--keep-temp", action="store_true", help="Keep extracted bundle and logs.")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_checksum_file(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, filename = line.split(" *", 1)
        entries[filename] = digest
    return entries


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_fixture_files(workspace: Path) -> tuple[Path, Path, Path]:
    sample = workspace / "sample-page.html"
    sample.write_text(
        """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Release Smoke</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  </head>
  <body>
    <img class="hero" src="hero.jpg">
    <button class="icon-only"></button>
  </body>
</html>
""",
        encoding="utf-8",
    )
    axe_path = workspace / "axe.mock.json"
    lighthouse_path = workspace / "lighthouse.mock.json"
    _write_json(axe_path, AXE_FIXTURE)
    _write_json(lighthouse_path, LIGHTHOUSE_FIXTURE)
    return sample, axe_path, lighthouse_path


def _run(command: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ {' '.join(command)}\n\nSTDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}\n",
        encoding="utf-8",
    )
    return completed


def _ensure_release_assets(release_dir: Path | None) -> Path:
    if release_dir is not None:
        if not release_dir.exists():
            raise FileNotFoundError(f"Release asset directory does not exist: {release_dir}")
        return release_dir

    output_dir = REPO_ROOT / ".tmp-release-smoke-assets"
    env = os.environ.copy()
    env.setdefault("LIBRO_AGENTWCAG_SOURCE_REVISION", DEFAULT_SOURCE_REVISION)
    env.setdefault("LIBRO_AGENTWCAG_BUILD_TIMESTAMP", DEFAULT_BUILD_TIMESTAMP)
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/package-release.py",
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout + completed.stderr)
    return output_dir


def _resolve_manifest(asset_dir: Path, version: str | None) -> tuple[Path, dict[str, object], Path]:
    if version:
        manifest_path = asset_dir / f"libro-wcag-{version}-release-manifest.json"
        latest_path = asset_dir / "latest-release.json"
    else:
        latest_path = asset_dir / "latest-release.json"
        latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
        manifest_path = asset_dir / str(latest_payload["release_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest_path, manifest, latest_path


def _find_bundle_asset(manifest: dict[str, object], agent: str) -> dict[str, object]:
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError("release manifest is missing assets")
    for asset in assets:
        if asset.get("kind") == "bundle" and asset.get("agent") == agent:
            return asset
    raise RuntimeError(f"release manifest does not contain a bundle for agent: {agent}")


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary_path) if args.summary_path else REPO_ROOT / ".tmp-release-smoke-summary.json"
    cleanup_assets = args.release_dir is None
    release_dir = _ensure_release_assets(Path(args.release_dir) if args.release_dir else None)
    if cleanup_assets:
        release_dir = release_dir.resolve()
    temp_root = release_dir.parent / ".tmp-release-smoke" / uuid.uuid4().hex
    temp_root.mkdir(parents=True, exist_ok=True)

    triage_dir = temp_root / "triage"
    logs_dir = triage_dir / "logs"
    summary: dict[str, object] = {
        "agent": args.agent,
        "release_dir": str(release_dir),
        "steps": [],
        "triage_dir": str(triage_dir),
        "clean_environment_verified": False,
        "checksum_verified": False,
        "artifacts": [],
    }

    try:
        manifest_path, manifest, latest_path = _resolve_manifest(release_dir, args.version)
        checksum_path = release_dir / str(manifest["checksum_file"])
        checksums = _parse_checksum_file(checksum_path)
        bundle_asset = _find_bundle_asset(manifest, args.agent)
        bundle_path = release_dir / str(bundle_asset["filename"])

        expected_manifest_hash = checksums.get(manifest_path.name)
        expected_latest_hash = checksums.get(latest_path.name)
        expected_bundle_hash = checksums.get(bundle_path.name)
        actual_manifest_hash = sha256_file(manifest_path)
        actual_latest_hash = sha256_file(latest_path)
        actual_bundle_hash = sha256_file(bundle_path)

        if expected_manifest_hash != actual_manifest_hash:
            raise RuntimeError("release manifest checksum verification failed")
        if expected_latest_hash != actual_latest_hash:
            raise RuntimeError("latest pointer checksum verification failed")
        if expected_bundle_hash != actual_bundle_hash:
            raise RuntimeError("bundle checksum verification failed")
        if bundle_asset.get("sha256") != actual_bundle_hash:
            raise RuntimeError("bundle sha256 does not match release manifest")

        summary["checksum_verified"] = True
        summary["release_manifest"] = manifest_path.name
        summary["bundle"] = bundle_path.name
        summary["product_version"] = manifest["product_version"]
        summary["source_revision"] = manifest["source_revision"]

        extract_dir = temp_root / "extracted"
        with zipfile.ZipFile(bundle_path) as archive:
            archive.extractall(extract_dir)
        bundle_root = (extract_dir / str(bundle_asset["bundle_root"])).resolve()

        install_dir = (temp_root / "installed").resolve()
        run_dir = (temp_root / "run").resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        sample_path, axe_path, lighthouse_path = _write_fixture_files(run_dir)
        audit_output = run_dir / "audit-output"

        env = os.environ.copy()
        env["LIBRO_AGENTWCAG_SOURCE_REVISION"] = str(manifest["source_revision"])
        if "build_timestamp" in manifest:
            env["LIBRO_AGENTWCAG_BUILD_TIMESTAMP"] = str(manifest["build_timestamp"])

        install_cmd = [
            sys.executable,
            str(bundle_root / "scripts" / "install-agent.py"),
            "--agent",
            args.agent,
            "--dest",
            str(install_dir),
            "--force",
        ]
        install = _run(install_cmd, bundle_root, env, logs_dir / "install.log")
        summary["steps"].append({"name": "install", "exit_code": install.returncode, "log": str(logs_dir / "install.log")})
        if install.returncode != 0:
            raise RuntimeError("install step failed")

        doctor_cmd = [
            sys.executable,
            str(bundle_root / "scripts" / "doctor-agent.py"),
            "--agent",
            args.agent,
            "--dest",
            str(install_dir),
            "--verify-manifest-integrity",
        ]
        doctor = _run(doctor_cmd, bundle_root, env, logs_dir / "doctor.log")
        summary["steps"].append({"name": "doctor", "exit_code": doctor.returncode, "log": str(logs_dir / "doctor.log")})
        if doctor.returncode != 0:
            raise RuntimeError("doctor step failed")
        doctor_payload = json.loads(doctor.stdout)

        audit_cmd = [
            sys.executable,
            str(bundle_root / "skills" / "libro-wcag" / "scripts" / "run_accessibility_audit.py"),
            "--target",
            str(sample_path),
            "--output-dir",
            str(audit_output),
            "--execution-mode",
            "apply-fixes",
            "--wcag-version",
            "2.2",
            "--output-language",
            "en",
            "--mock-axe-json",
            str(axe_path),
            "--mock-lighthouse-json",
            str(lighthouse_path),
        ]
        audit = _run(audit_cmd, bundle_root, env, logs_dir / "audit.log")
        summary["steps"].append({"name": "audit", "exit_code": audit.returncode, "log": str(logs_dir / "audit.log")})
        if audit.returncode != 0:
            raise RuntimeError("audit step failed")
        report_path = audit_output / "wcag-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))

        uninstall_cmd = [
            sys.executable,
            str(bundle_root / "scripts" / "uninstall-agent.py"),
            "--agent",
            args.agent,
            "--dest",
            str(install_dir),
        ]
        uninstall = _run(uninstall_cmd, bundle_root, env, logs_dir / "uninstall.log")
        summary["steps"].append({"name": "uninstall", "exit_code": uninstall.returncode, "log": str(logs_dir / "uninstall.log")})
        if uninstall.returncode != 0:
            raise RuntimeError("uninstall step failed")

        summary["doctor_ok"] = doctor_payload["ok"]
        summary["doctor_version_consistency_verified"] = doctor_payload["version_consistency"]["verified"]
        summary["doctor_manifest_integrity_verified"] = doctor_payload["manifest_integrity"]["verified"]
        summary["installed_product_version"] = doctor_payload["installed_product"]["product_version"]
        summary["report_product_version"] = report["run_meta"]["product"]["product_version"]
        summary["report_source_revision"] = report["run_meta"]["product"]["source_revision"]
        summary["uninstall_removed_destination"] = not install_dir.exists()
        summary["artifacts"] = [
            str(report_path),
            str(audit_output / "wcag-report.md"),
            str(audit_output / "artifact-manifest.json"),
        ]
        summary["clean_environment_verified"] = bool(
            summary["checksum_verified"]
            and summary["doctor_ok"]
            and summary["doctor_version_consistency_verified"]
            and summary["doctor_manifest_integrity_verified"]
            and summary["uninstall_removed_destination"]
        )

        _write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["clean_environment_verified"] else 1
    except Exception as exc:  # pragma: no cover
        summary["error"] = str(exc)
        _write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1
    finally:
        if cleanup_assets and release_dir.exists():
            shutil.rmtree(release_dir, ignore_errors=True)
        if summary.get("clean_environment_verified") and not args.keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
