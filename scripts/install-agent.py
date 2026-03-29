#!/usr/bin/env python3
"""Install libro-wcag for a target AI agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "skills" / "libro-wcag" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from shared_constants import get_product_provenance

SKILL_NAME = "libro-wcag"
SUPPORTED_AGENTS = ("codex", "claude", "gemini", "copilot")
ALL_AGENTS = SUPPORTED_AGENTS + ("all",)
MCP_CLIENTS = ("claude", "copilot", "gemini")
REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_TEMPLATE_ROOT = REPO_ROOT / "packaging" / "templates" / "workspace"
TEMP_FILE_SUFFIXES = {".tmp", ".bak"}


def source_directory() -> Path:
    return REPO_ROOT / "skills" / SKILL_NAME


def workspace_template_root(agent: str) -> Path:
    return WORKSPACE_TEMPLATE_ROOT / agent


def workspace_template_skill_source(agent: str) -> Path:
    return workspace_template_root(agent) / "skills" / SKILL_NAME / "SKILL.md"


def workspace_template_extras(agent: str) -> list[tuple[Path, Path]]:
    extras: list[tuple[Path, Path]] = []
    if agent == "codex":
        extras.append(
            (
                workspace_template_root(agent) / "environments" / "environment.toml",
                Path(".codex/environments/environment.toml"),
            )
        )
    return extras


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


def workspace_destination(agent: str, workspace_root: Path) -> Path:
    return workspace_root / f".{agent}" / "skills" / SKILL_NAME


def adapter_name(agent: str) -> str:
    return "openai-codex" if agent == "codex" else agent


def invoke_example(agent: str) -> str:
    if agent == "codex":
        return "Use $libro-wcag to audit or remediate a web page using a selected WCAG version and level."
    return (
        "Load the adapter prompt from "
        f"adapters/{adapter_name(agent)}/prompt-template.md and inject the shared contract into your agent workflow."
    )


def mcp_server_entrypoint() -> Path:
    return Path(__file__).resolve().parents[1] / "mcp-server" / "server.py"


def mcp_server_config_payload() -> dict[str, object]:
    return {
        "command": "python",
        "args": [mcp_server_entrypoint().as_posix()],
    }


def mcp_config_path(client: str, workspace_root: Path) -> Path:
    if client == "claude":
        return workspace_root / ".mcp.json"
    if client == "copilot":
        return workspace_root / ".vscode" / "mcp.json"
    if client == "gemini":
        return workspace_root / ".gemini" / "settings.json"
    raise ValueError(f"Unsupported MCP client: {client}")


def write_mcp_config(client: str, workspace_root: Path) -> Path:
    path = mcp_config_path(client, workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = mcp_server_config_payload()
    if client == "copilot":
        document = {"servers": {SKILL_NAME: payload}}
    else:
        document = {"mcpServers": {SKILL_NAME: payload}}
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install libro-wcag for a target AI agent.")
    parser.add_argument("--agent", required=True, choices=ALL_AGENTS)
    parser.add_argument("--dest", help="Destination directory. Defaults to the agent-specific path. When --agent all is used, this becomes the base directory.")
    parser.add_argument(
        "--workspace-root",
        help="Install into a project workspace root using .<agent>/skills/libro-wcag. When --agent all is used, installs all supported agent skill directories under that workspace root.",
    )
    parser.add_argument(
        "--emit-mcp-config",
        action="append",
        default=[],
        choices=MCP_CLIENTS,
        help="Write a workspace-local MCP config for claude, copilot, or gemini. Requires --workspace-root.",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing installation.")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copytree_ignore(dirpath: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(dirpath) / name
        if path.name == "__pycache__":
            ignored.add(name)
            continue
        if path.is_file() and (path.suffix.lower() in TEMP_FILE_SUFFIXES or path.name.endswith("~")):
            ignored.add(name)
    return ignored


def _copy_template_skill(agent: str, destination: Path) -> None:
    template_skill = workspace_template_skill_source(agent)
    if not template_skill.exists():
        raise FileNotFoundError(f"Missing workspace template skill: {template_skill}")
    shutil.copyfile(template_skill, destination / "SKILL.md")


def materialize_workspace_extras(agent: str, workspace_root: Path) -> list[Path]:
    written: list[Path] = []
    for source_path, relative_destination in workspace_template_extras(agent):
        if not source_path.exists():
            raise FileNotFoundError(f"Missing workspace template extra: {source_path}")
        destination = workspace_root / relative_destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination)
        written.append(destination)
    return written


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


def _read_installed_version(destination: Path) -> str | None:
    """Read the product_version from an existing install manifest, if present."""
    manifest_path = destination / "install-manifest.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data.get("product_version")
    except (json.JSONDecodeError, OSError):
        return None


def _backup_existing(destination: Path) -> Path | None:
    """Create a timestamped backup of the existing installation.

    Returns the backup path, or None if no backup was needed.
    """
    if not destination.exists():
        return None
    import time

    timestamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = destination.with_name(f"{destination.name}.bak-{timestamp}")
    shutil.copytree(destination, backup_path)
    return backup_path


def _rollback(destination: Path, backup_path: Path | None) -> None:
    """Restore from backup after a failed installation."""
    if destination.exists():
        try:
            shutil.rmtree(destination)
        except OSError:
            pass
    if backup_path and backup_path.exists():
        shutil.copytree(backup_path, destination)


def install(agent: str, destination: Path, force: bool) -> Path:
    source = source_directory()
    if not source.exists():
        raise FileNotFoundError(f"Missing source skill directory: {source}")

    backup_path: Path | None = None
    if destination.exists():
        if not force:
            raise FileExistsError(
                f"Destination already exists: {destination}. Use --force to replace it."
            )
        old_version = _read_installed_version(destination)
        new_version = get_product_provenance().get("product_version", "unknown")
        if old_version and old_version > new_version:
            print(
                f"Warning: downgrading from {old_version} to {new_version} at {destination}",
                file=sys.stderr,
            )
        backup_path = _backup_existing(destination)
        try:
            shutil.rmtree(destination)
        except (PermissionError, OSError) as exc:
            raise OSError(
                f"Cannot remove existing installation at {destination}: {exc}"
            ) from exc

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, ignore=_copytree_ignore)
        _copy_template_skill(agent, destination)
        write_manifest(destination, agent)
    except (PermissionError, OSError) as exc:
        _rollback(destination, backup_path)
        raise OSError(
            f"Installation failed, rolled back to previous state: {exc}"
        ) from exc
    finally:
        if backup_path and backup_path.exists():
            shutil.rmtree(backup_path, ignore_errors=True)

    return destination


def install_all(
    base_destination: Path | None,
    force: bool,
    *,
    workspace_root: Path | None = None,
) -> list[Path]:
    installed = []
    for agent in SUPPORTED_AGENTS:
        if workspace_root:
            destination = workspace_destination(agent, workspace_root)
        else:
            destination = (base_destination / agent / SKILL_NAME) if base_destination else default_destination(agent)
        installed.append(install(agent, destination, force))
        if workspace_root:
            materialize_workspace_extras(agent, workspace_root)
    return installed


def main() -> int:
    args = parse_args()
    if args.dest and args.workspace_root:
        raise ValueError("--dest and --workspace-root cannot be used together")
    if args.emit_mcp_config and not args.workspace_root:
        raise ValueError("--emit-mcp-config requires --workspace-root")
    provenance = get_product_provenance()
    written_mcp_configs: list[Path] = []
    if args.agent == "all":
        base_destination = Path(args.dest) if args.dest else None
        workspace_root = Path(args.workspace_root) if args.workspace_root else None
        installed = install_all(base_destination, args.force, workspace_root=workspace_root)
        if workspace_root:
            written_mcp_configs = [write_mcp_config(client, workspace_root) for client in args.emit_mcp_config]
        for path in installed:
            print(
                f"Installed at: {path} "
                f"(version {provenance['product_version']}, source_revision {provenance['source_revision']})"
            )
        for path in written_mcp_configs:
            print(f"Wrote MCP config: {path}")
        return 0

    workspace_root = Path(args.workspace_root) if args.workspace_root else None
    destination = (
        Path(args.dest)
        if args.dest
        else (workspace_destination(args.agent, workspace_root) if workspace_root else default_destination(args.agent))
    )
    installed = install(args.agent, destination, args.force)
    if workspace_root:
        materialize_workspace_extras(args.agent, workspace_root)
        written_mcp_configs = [write_mcp_config(client, workspace_root) for client in args.emit_mcp_config]
    print(
        f"Installed {SKILL_NAME} for {args.agent} at: {installed} "
        f"(version {provenance['product_version']}, source_revision {provenance['source_revision']})"
    )
    print(f"Installation manifest: {installed / 'install-manifest.json'}")
    for path in written_mcp_configs:
        print(f"Wrote MCP config: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
