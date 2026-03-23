#!/usr/bin/env python3
"""Install libro-agent-wcag for a target AI agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "skills" / "libro-agent-wcag" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from shared_constants import get_product_provenance

SKILL_NAME = "libro-agent-wcag"
SUPPORTED_AGENTS = ("codex", "claude", "gemini", "copilot")
ALL_AGENTS = SUPPORTED_AGENTS + ("all",)


def source_directory() -> Path:
    return Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME


def default_destination(agent: str) -> Path:
    home = Path.home()
    if agent == "codex":
        return home / ".codex" / "skills" / SKILL_NAME
    if agent == "claude":
        return home / ".claude" / "skills" / SKILL_NAME
    if agent == "gemini":
        return home / ".gemini" / "skills" / SKILL_NAME
    if agent == "copilot":
        return home / ".copilot" / "skills" / SKILL_NAME
    raise ValueError(f"Unsupported agent: {agent}")


def adapter_name(agent: str) -> str:
    return "openai-codex" if agent == "codex" else agent


def invoke_example(agent: str) -> str:
    if agent == "codex":
        return "Use $libro-agent-wcag to audit or remediate a web page using a selected WCAG version and level."
    return (
        "Load the adapter prompt from "
        f"adapters/{adapter_name(agent)}/prompt-template.md and inject the shared contract into your agent workflow."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install libro-agent-wcag for a target AI agent.")
    parser.add_argument("--agent", required=True, choices=ALL_AGENTS)
    parser.add_argument("--dest", help="Destination directory. Defaults to the agent-specific path. When --agent all is used, this becomes the base directory.")
    parser.add_argument("--force", action="store_true", help="Replace an existing installation.")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(destination: Path, agent: str) -> None:
    provenance = get_product_provenance()
    entrypoints = {
        "skill_entrypoint": Path("SKILL.md"),
        "adapter_prompt": Path(f"adapters/{adapter_name(agent)}/prompt-template.md"),
        "usage_example": Path(f"adapters/{adapter_name(agent)}/usage-example.md"),
        "failure_guide": Path(f"adapters/{adapter_name(agent)}/failure-guide.md"),
        "e2e_example": Path(f"adapters/{adapter_name(agent)}/e2e-example.md"),
    }
    integrity_hashes = {
        name: sha256_file(destination / relative_path) for name, relative_path in entrypoints.items()
    }

    manifest = {
        "skill_name": SKILL_NAME,
        "product_name": provenance["product_name"],
        "product_version": provenance["product_version"],
        "source_revision": provenance["source_revision"],
        "agent": agent,
        "skill_entrypoint": str(entrypoints["skill_entrypoint"]).replace("\\", "/"),
        "adapter_prompt": str(entrypoints["adapter_prompt"]).replace("\\", "/"),
        "usage_example": str(entrypoints["usage_example"]).replace("\\", "/"),
        "failure_guide": str(entrypoints["failure_guide"]).replace("\\", "/"),
        "e2e_example": str(entrypoints["e2e_example"]).replace("\\", "/"),
        "manifest_integrity": {
            "algorithm": "sha256",
            "entrypoint_hashes": integrity_hashes,
        },
        "notes": "For non-Codex agents, wire the adapter prompt into your agent's prompt or skill system.",
        "invoke_example": invoke_example(agent),
        "doctor_command": f"python scripts/doctor-agent.py --agent {agent}",
    }
    manifest["provenance"] = {
        "version_source": provenance["version_source"],
        "source_revision_source": provenance["source_revision_source"],
    }
    if "build_timestamp" in provenance:
        manifest["build_timestamp"] = provenance["build_timestamp"]
        manifest["provenance"]["build_timestamp_source"] = provenance["build_timestamp_source"]
    (destination / "install-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def install(agent: str, destination: Path, force: bool) -> Path:
    source = source_directory()
    if not source.exists():
        raise FileNotFoundError(f"Missing source skill directory: {source}")

    if destination.exists():
        if not force:
            raise FileExistsError(
                f"Destination already exists: {destination}. Use --force to replace it."
            )
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    write_manifest(destination, agent)
    return destination


def install_all(base_destination: Path | None, force: bool) -> list[Path]:
    installed = []
    for agent in SUPPORTED_AGENTS:
        destination = (base_destination / agent / SKILL_NAME) if base_destination else default_destination(agent)
        installed.append(install(agent, destination, force))
    return installed


def main() -> int:
    args = parse_args()
    provenance = get_product_provenance()
    if args.agent == "all":
        base_destination = Path(args.dest) if args.dest else None
        installed = install_all(base_destination, args.force)
        for path in installed:
            print(
                f"Installed at: {path} "
                f"(version {provenance['product_version']}, source_revision {provenance['source_revision']})"
            )
        return 0

    destination = Path(args.dest) if args.dest else default_destination(args.agent)
    installed = install(args.agent, destination, args.force)
    print(
        f"Installed {SKILL_NAME} for {args.agent} at: {installed} "
        f"(version {provenance['product_version']}, source_revision {provenance['source_revision']})"
    )
    print(f"Installation manifest: {installed / 'install-manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
