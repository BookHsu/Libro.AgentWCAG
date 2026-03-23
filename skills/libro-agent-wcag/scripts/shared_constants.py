#!/usr/bin/env python3
"""Shared constants for accessibility audit modules."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tomllib

PRODUCT_NAME = "Libro.AgentWCAG"
REPORT_SCHEMA_VERSION = "1.0.0"
SOURCE_REVISION_ENV_VAR = "LIBRO_AGENTWCAG_SOURCE_REVISION"
BUILD_TIMESTAMP_ENV_VAR = "LIBRO_AGENTWCAG_BUILD_TIMESTAMP"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_pyproject(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or _repo_root()
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        raise RuntimeError(f"pyproject.toml is missing: {pyproject_path}")
    return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))


def get_product_version(repo_root: Path | None = None) -> str:
    project = _load_pyproject(repo_root).get("project", {})
    version = project.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("pyproject.toml is missing project.version")
    return version.strip()


def _resolve_git_dir(repo_root: Path) -> Path | None:
    git_root = repo_root / ".git"
    if git_root.is_dir():
        return git_root
    if not git_root.is_file():
        return None
    head = git_root.read_text(encoding="utf-8").strip()
    prefix = "gitdir: "
    if not head.startswith(prefix):
        return None
    git_dir = Path(head[len(prefix) :].strip())
    if not git_dir.is_absolute():
        git_dir = (repo_root / git_dir).resolve()
    return git_dir


def _read_git_head_revision(repo_root: Path | None = None) -> str | None:
    root = repo_root or _repo_root()
    git_dir = _resolve_git_dir(root)
    if git_dir is None:
        return None

    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return None
    head = head_path.read_text(encoding="utf-8").strip()
    if not head:
        return None
    if head.startswith("ref: "):
        ref_path = git_dir / head[5:].strip()
        if not ref_path.exists():
            return None
        revision = ref_path.read_text(encoding="utf-8").strip()
    else:
        revision = head
    if len(revision) == 40 and all(ch in "0123456789abcdefABCDEF" for ch in revision):
        return revision.lower()
    return None


def _normalize_utc_timestamp(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise RuntimeError("build timestamp is empty")
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise RuntimeError(
            f"build timestamp must be ISO-8601 with UTC timezone: {value}"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RuntimeError(f"build timestamp must use UTC timezone: {value}")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_source_revision(
    repo_root: Path | None = None,
    *,
    env: dict[str, str] | None = None,
    require: bool = True,
) -> str:
    environment = env or os.environ
    explicit_revision = environment.get(SOURCE_REVISION_ENV_VAR, "").strip()
    if explicit_revision:
        if len(explicit_revision) == 40 and all(ch in "0123456789abcdefABCDEF" for ch in explicit_revision):
            return explicit_revision.lower()
        raise RuntimeError(
            f"{SOURCE_REVISION_ENV_VAR} must be a 40-character git commit SHA"
        )

    revision = _read_git_head_revision(repo_root)
    if revision:
        return revision
    if require:
        raise RuntimeError(
            f"source revision is unavailable; set {SOURCE_REVISION_ENV_VAR} or run inside a git checkout"
        )
    return ""


def get_build_timestamp(*, env: dict[str, str] | None = None, require: bool = False) -> str | None:
    environment = env or os.environ
    raw_value = environment.get(BUILD_TIMESTAMP_ENV_VAR, "").strip()
    if raw_value:
        return _normalize_utc_timestamp(raw_value)
    if require:
        raise RuntimeError(f"build timestamp is unavailable; set {BUILD_TIMESTAMP_ENV_VAR}")
    return None


def get_product_provenance(
    repo_root: Path | None = None,
    *,
    env: dict[str, str] | None = None,
    require_build_timestamp: bool = False,
) -> dict[str, str]:
    environment = env or os.environ
    provenance = {
        "product_name": PRODUCT_NAME,
        "product_version": get_product_version(repo_root),
        "version_source": "pyproject.toml",
        "source_revision": get_source_revision(repo_root, env=environment, require=True),
        "source_revision_source": (
            SOURCE_REVISION_ENV_VAR if environment.get(SOURCE_REVISION_ENV_VAR, "").strip() else "git-head"
        ),
    }
    build_timestamp = get_build_timestamp(env=environment, require=require_build_timestamp)
    if build_timestamp is not None:
        provenance["build_timestamp"] = build_timestamp
        provenance["build_timestamp_source"] = BUILD_TIMESTAMP_ENV_VAR
    return provenance

__all__ = [
    "BUILD_TIMESTAMP_ENV_VAR",
    "PRODUCT_NAME",
    "REPORT_SCHEMA_VERSION",
    "SOURCE_REVISION_ENV_VAR",
    "get_build_timestamp",
    "get_product_provenance",
    "get_product_version",
    "get_source_revision",
]
