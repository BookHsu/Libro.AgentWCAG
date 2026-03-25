#!/usr/bin/env python3
"""Generate npm package provenance for installs outside a git checkout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "skills" / "libro-wcag" / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from shared_constants import get_product_provenance

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "package-provenance.json"


def main() -> int:
    provenance = get_product_provenance()
    payload = {
        "product_name": provenance["product_name"],
        "product_version": provenance["product_version"],
        "source_revision": provenance["source_revision"],
    }
    if "build_timestamp" in provenance:
        payload["build_timestamp"] = provenance["build_timestamp"]
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
