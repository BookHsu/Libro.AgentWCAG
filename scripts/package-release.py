#!/usr/bin/env python3
"""Build deterministic release bundles, checksums, and release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "skills" / "libro-wcag" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from shared_constants import get_product_provenance

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "libro-wcag"
SUPPORTED_AGENTS = ("codex", "claude", "gemini", "copilot")
PRODUCT_SLUG = "libro-wcag"
FIXED_ZIP_TIMESTAMP = (2024, 1, 1, 0, 0, 0)
BASE_RELEASE_FILES = (
    Path("README.md"),
    Path("CHANGELOG.md"),
    Path("LICENSE"),
    Path("pyproject.toml"),
    Path("scripts/install-agent.py"),
    Path("scripts/install-agent.ps1"),
    Path("scripts/install-agent.sh"),
    Path("scripts/doctor-agent.py"),
    Path("scripts/uninstall-agent.py"),
    Path("docs/release/adoption-smoke-guide.md"),
    Path("docs/release/supported-environments.md"),
)
OPTIONAL_RELEASE_ASSETS = (
    ("bootstrap-installer", Path("scripts/install-latest.ps1"), "{slug}-{version}-install-latest.ps1"),
    ("bootstrap-installer", Path("scripts/install-latest.sh"), "{slug}-{version}-install-latest.sh"),
    ("smoke-runner", Path("scripts/run-release-adoption-smoke.py"), "{slug}-{version}-run-release-adoption-smoke.py"),
)
REQUIRED_ADAPTER_DOCS = ("prompt-template.md", "usage-example.md", "failure-guide.md", "e2e-example.md")
AGENT_MANIFESTS = {
    "codex": "openai.yaml",
    "claude": "claude.yaml",
    "gemini": "gemini.yaml",
    "copilot": "copilot.yaml",
}
TEMP_FILE_SUFFIXES = {".tmp", ".bak"}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package Libro.AgentWCAG release assets.")
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "dist" / "release"),
        help="Directory that will receive versioned release assets.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output directory if it already exists.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_specs() -> list[tuple[str, str | None]]:
    return [(agent, agent) for agent in SUPPORTED_AGENTS] + [("all-in-one", None)]


def _adapter_directory_name(agent: str) -> str:
    return "openai-codex" if agent == "codex" else agent


def _iter_validated_agents(agent: str | None) -> tuple[str, ...]:
    return SUPPORTED_AGENTS if agent is None else (agent,)


def _is_temporary_release_file(path: Path) -> bool:
    return path.suffix.lower() in TEMP_FILE_SUFFIXES or path.name.endswith("~")


def _validate_release_inputs(agent: str | None) -> None:
    missing: list[str] = []

    for relative in BASE_RELEASE_FILES:
        candidate = REPO_ROOT / relative
        if not candidate.is_file():
            missing.append(relative.as_posix())

    for relative in (
        Path("skills/libro-wcag/SKILL.md"),
        Path("skills/libro-wcag/scripts"),
        Path("skills/libro-wcag/schemas"),
        Path("skills/libro-wcag/references"),
        Path("skills/libro-wcag/agents"),
        Path("skills/libro-wcag/adapters"),
    ):
        candidate = REPO_ROOT / relative
        if not candidate.exists():
            missing.append(relative.as_posix())

    for validated_agent in _iter_validated_agents(agent):
        manifest_name = AGENT_MANIFESTS[validated_agent]
        manifest_path = SKILL_ROOT / "agents" / manifest_name
        if not manifest_path.is_file():
            missing.append(manifest_path.relative_to(REPO_ROOT).as_posix())

        adapter_root = SKILL_ROOT / "adapters" / _adapter_directory_name(validated_agent)
        if not adapter_root.is_dir():
            missing.append(adapter_root.relative_to(REPO_ROOT).as_posix())
            continue

        for doc_name in REQUIRED_ADAPTER_DOCS:
            doc_path = adapter_root / doc_name
            if not doc_path.is_file():
                missing.append(doc_path.relative_to(REPO_ROOT).as_posix())

    if missing:
        raise FileNotFoundError(
            "Release packaging input validation failed; missing required files:\n- "
            + "\n- ".join(sorted(set(missing)))
        )


def _iter_release_skill_files(agent: str | None) -> list[Path]:
    files: list[Path] = []
    for path in sorted(SKILL_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT)
        parts = relative.parts
        if "__pycache__" in parts:
            continue
        if _is_temporary_release_file(path):
            continue
        if parts[:4] == ("skills", "libro-wcag", "scripts", "tests"):
            continue
        if parts[:3] == ("skills", "libro-wcag", "adapters") and agent is not None:
            if len(parts) < 4 or parts[3] != _adapter_directory_name(agent):
                continue
        files.append(path)
    return files


def _iter_policy_bundle_files() -> list[Path]:
    return sorted((REPO_ROOT / "docs" / "policy-bundles").glob("*.json"))


def _bundle_input_files(agent: str | None) -> list[Path]:
    input_files = [REPO_ROOT / relative for relative in BASE_RELEASE_FILES]
    input_files.extend(_iter_policy_bundle_files())
    input_files.extend(_iter_release_skill_files(agent))
    return sorted({path.resolve(): path for path in input_files}.values(), key=lambda path: str(path.relative_to(REPO_ROOT)).replace("\\", "/"))


def _write_zip_entry(archive: zipfile.ZipFile, source_path: Path, archive_path: str) -> None:
    info = zipfile.ZipInfo(archive_path, FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, source_path.read_bytes())


def build_bundle(bundle_path: Path, version: str, label: str, agent: str | None) -> dict[str, object]:
    bundle_root = f"{PRODUCT_SLUG}-{version}-{label}"
    _validate_release_inputs(agent)
    input_files = _bundle_input_files(agent)
    with zipfile.ZipFile(bundle_path, "w") as archive:
        for source_path in input_files:
            relative = source_path.relative_to(REPO_ROOT).as_posix()
            _write_zip_entry(archive, source_path, f"{bundle_root}/{relative}")
    return {
        "filename": bundle_path.name,
        "kind": "bundle",
        "bundle": label,
        "agent": agent or "all",
        "bundle_root": bundle_root,
        "sha256": sha256_file(bundle_path),
        "size_bytes": bundle_path.stat().st_size,
    }


def _copy_optional_assets(output_dir: Path, version: str) -> list[dict[str, object]]:
    assets: list[dict[str, object]] = []
    for kind, relative_path, template in OPTIONAL_RELEASE_ASSETS:
        source_path = REPO_ROOT / relative_path
        if not source_path.exists():
            continue
        filename = template.format(slug=PRODUCT_SLUG, version=version)
        destination = output_dir / filename
        shutil.copyfile(source_path, destination)
        assets.append(
            {
                "filename": filename,
                "kind": kind,
                "source_path": relative_path.as_posix(),
                "sha256": sha256_file(destination),
                "size_bytes": destination.stat().st_size,
            }
        )
    return assets


def _checksum_lines(paths: list[Path]) -> str:
    lines = []
    for path in sorted(paths, key=lambda item: item.name):
        lines.append(f"{sha256_file(path)} *{path.name}")
    return "\n".join(lines) + "\n"


def _write_latest_pointer(
    path: Path,
    *,
    provenance: dict[str, str],
    manifest_name: str,
    manifest_sha256: str,
) -> None:
    payload = {
        "product_name": provenance["product_name"],
        "product_version": provenance["product_version"],
        "source_revision": provenance["source_revision"],
        "release_manifest": manifest_name,
        "release_manifest_sha256": manifest_sha256,
    }
    if "build_timestamp" in provenance:
        payload["build_timestamp"] = provenance["build_timestamp"]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_release_manifest(
    path: Path,
    *,
    provenance: dict[str, str],
    assets: list[dict[str, object]],
    checksum_file: str,
    latest_pointer: str,
) -> None:
    payload = {
        "product_name": provenance["product_name"],
        "product_version": provenance["product_version"],
        "source_revision": provenance["source_revision"],
        "asset_naming": {
            "agent_bundle": f"{PRODUCT_SLUG}-<version>-<agent>.zip",
            "all_in_one_bundle": f"{PRODUCT_SLUG}-<version>-all-in-one.zip",
            "checksum_file": f"{PRODUCT_SLUG}-<version>-sha256sums.txt",
            "release_manifest": f"{PRODUCT_SLUG}-<version>-release-manifest.json",
            "latest_pointer": "latest-release.json",
        },
        "bundle_contract": {
            "bundle_root_pattern": f"{PRODUCT_SLUG}-<version>-<bundle>",
            "excludes": [
                "skills/libro-wcag/scripts/tests/**",
                "docs/archive/**",
                "docs/testing/**",
            ],
        },
        "checksum_file": checksum_file,
        "latest_pointer": latest_pointer,
        "assets": assets,
    }
    if "build_timestamp" in provenance:
        payload["build_timestamp"] = provenance["build_timestamp"]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    if output_dir.exists():
        if not args.overwrite:
            raise FileExistsError(f"Output directory already exists: {output_dir}. Use --overwrite to replace it.")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    provenance = get_product_provenance()
    version = provenance["product_version"]
    checksum_name = f"{PRODUCT_SLUG}-{version}-sha256sums.txt"
    manifest_name = f"{PRODUCT_SLUG}-{version}-release-manifest.json"
    latest_name = "latest-release.json"

    assets: list[dict[str, object]] = []
    for label, agent in _bundle_specs():
        bundle_path = output_dir / f"{PRODUCT_SLUG}-{version}-{label}.zip"
        assets.append(build_bundle(bundle_path, version, label, agent))

    assets.extend(_copy_optional_assets(output_dir, version))

    manifest_path = output_dir / manifest_name
    _write_release_manifest(
        manifest_path,
        provenance=provenance,
        assets=assets,
        checksum_file=checksum_name,
        latest_pointer=latest_name,
    )

    latest_path = output_dir / latest_name
    _write_latest_pointer(
        latest_path,
        provenance=provenance,
        manifest_name=manifest_name,
        manifest_sha256=sha256_file(manifest_path),
    )

    checksum_targets = [output_dir / asset["filename"] for asset in assets]
    checksum_targets.extend([manifest_path, latest_path])
    checksum_path = output_dir / checksum_name
    checksum_path.write_text(_checksum_lines(checksum_targets), encoding="utf-8")

    summary = {
        "output_dir": str(output_dir),
        "product_name": provenance["product_name"],
        "product_version": version,
        "source_revision": provenance["source_revision"],
        "asset_count": len(assets),
        "checksum_file": checksum_name,
        "release_manifest": manifest_name,
        "latest_pointer": latest_name,
    }
    if "build_timestamp" in provenance:
        summary["build_timestamp"] = provenance["build_timestamp"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
