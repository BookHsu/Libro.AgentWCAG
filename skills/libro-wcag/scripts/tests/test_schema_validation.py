#!/usr/bin/env python3
"""Validate generated reports against the JSON Schema (V1+V2)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "wcag-report-1.0.0.schema.json"

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from shared_constants import REPORT_SCHEMA_VERSION
from wcag_workflow import normalize_report, resolve_contract


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _add_cli_pipeline_fields(report: dict) -> dict:
    """Add fields that the CLI pipeline normally injects after normalize_report."""
    report["report_schema"] = {
        "name": "libro-wcag-report",
        "version": REPORT_SCHEMA_VERSION,
        "artifact": "wcag-report-1.0.0.schema.json",
        "compatibility": f"^{REPORT_SCHEMA_VERSION.split('.')[0]}.0.0",
    }
    report["run_meta"]["report_schema_version"] = REPORT_SCHEMA_VERSION
    report["run_meta"]["report_schema_artifact"] = "wcag-report-1.0.0.schema.json"
    report["run_meta"].setdefault("product", {
        "product_name": "Libro.AgentWCAG",
        "product_version": "test",
        "source_revision": "test",
        "report_schema_version": REPORT_SCHEMA_VERSION,
    })
    return report


def _make_sample_report(**overrides) -> dict:
    """Generate a minimal but complete report from mock scanner data."""
    contract = resolve_contract(overrides.get("contract_raw", {"target": "https://example.com"}))
    axe_data = overrides.get("axe_data", {
        "violations": [
            {
                "id": "image-alt",
                "impact": "serious",
                "description": "Images must have alternate text",
                "nodes": [{"target": ["img.hero"]}],
            }
        ]
    })
    lighthouse_data = overrides.get("lighthouse_data", {
        "audits": {
            "label": {
                "score": 0,
                "scoreDisplayMode": "binary",
                "title": "Form elements have labels",
                "details": {"items": [{"node": {"selector": "input#email"}}]},
            }
        }
    })
    report = normalize_report(
        contract=contract,
        axe_data=axe_data,
        lighthouse_data=lighthouse_data,
    )
    return _add_cli_pipeline_fields(report)


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed (pip install jsonschema)")
class TestReportSchemaValidation(unittest.TestCase):
    """Validate that generated reports conform to the JSON Schema."""

    def setUp(self) -> None:
        self.schema = _load_schema()

    def test_sample_report_validates_against_schema(self) -> None:
        report = _make_sample_report()
        jsonschema.validate(instance=report, schema=self.schema)

    def test_empty_scanner_report_validates(self) -> None:
        report = _make_sample_report(axe_data=None, lighthouse_data=None)
        jsonschema.validate(instance=report, schema=self.schema)

    def test_axe_only_report_validates(self) -> None:
        report = _make_sample_report(lighthouse_data=None)
        jsonschema.validate(instance=report, schema=self.schema)

    def test_lighthouse_only_report_validates(self) -> None:
        report = _make_sample_report(axe_data=None)
        jsonschema.validate(instance=report, schema=self.schema)

    def test_suggest_only_mode_validates(self) -> None:
        report = _make_sample_report(
            contract_raw={"target": "https://example.com", "execution_mode": "suggest-only"}
        )
        jsonschema.validate(instance=report, schema=self.schema)

    def test_audit_only_mode_validates(self) -> None:
        report = _make_sample_report(
            contract_raw={"target": "https://example.com", "execution_mode": "audit-only"}
        )
        jsonschema.validate(instance=report, schema=self.schema)

    def test_schema_rejects_missing_required_key(self) -> None:
        report = _make_sample_report()
        del report["findings"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=self.schema)

    def test_schema_rejects_wrong_report_schema_version(self) -> None:
        report = _make_sample_report()
        report["report_schema"]["version"] = "99.0.0"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=report, schema=self.schema)


if __name__ == "__main__":
    unittest.main()
