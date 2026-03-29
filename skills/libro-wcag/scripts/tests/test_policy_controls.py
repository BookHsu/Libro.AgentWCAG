#!/usr/bin/env python3
"""Unit tests for policy_controls.py — covers functions with zero prior direct coverage."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from policy_controls import (
    _build_rule_sources,
    _merge_rule_list,
    _normalize_rule_list,
    _policy_value_source,
    _resolve_effective_policy_path,
    _load_policy_config,
    _resolve_policy_preset,
    _resolve_policy_bundle,
)


class NormalizeRuleListTests(unittest.TestCase):
    """Tests for _normalize_rule_list()."""

    def test_none_returns_empty(self) -> None:
        self.assertEqual(_normalize_rule_list(None, "include_rules"), [])

    def test_valid_list_strips_whitespace(self) -> None:
        self.assertEqual(
            _normalize_rule_list(["  image-alt ", "button-name"], "include_rules"),
            ["image-alt", "button-name"],
        )

    def test_empty_strings_are_filtered(self) -> None:
        self.assertEqual(
            _normalize_rule_list(["image-alt", "", "  "], "include_rules"),
            ["image-alt"],
        )

    def test_non_list_raises_value_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _normalize_rule_list("image-alt", "include_rules")
        self.assertIn("include_rules", str(ctx.exception))

    def test_list_with_non_string_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            _normalize_rule_list(["image-alt", 42], "ignore_rules")


class PolicyValueSourceTests(unittest.TestCase):
    """Tests for _policy_value_source() — 4-layer priority."""

    def test_cli_wins_over_all(self) -> None:
        self.assertEqual(
            _policy_value_source("serious", "moderate", "critical", "moderate", "default"),
            "cli",
        )

    def test_config_wins_when_cli_is_none(self) -> None:
        self.assertEqual(
            _policy_value_source(None, "moderate", "critical", "moderate", "default"),
            "policy-config",
        )

    def test_preset_wins_when_cli_and_config_none(self) -> None:
        self.assertEqual(
            _policy_value_source(None, None, "critical", "moderate", "default"),
            "policy-preset",
        )

    def test_bundle_wins_when_higher_layers_none(self) -> None:
        self.assertEqual(
            _policy_value_source(None, None, None, "moderate", "default"),
            "policy-bundle",
        )

    def test_default_label_when_all_none(self) -> None:
        self.assertEqual(
            _policy_value_source(None, None, None, None, "built-in"),
            "built-in",
        )


class BuildRuleSourcesTests(unittest.TestCase):
    """Tests for _build_rule_sources() — first-write-wins merge."""

    def test_empty_all(self) -> None:
        self.assertEqual(_build_rule_sources([], [], [], []), {})

    def test_bundle_is_first_source(self) -> None:
        result = _build_rule_sources(["image-alt"], ["image-alt"], [], [])
        self.assertEqual(result["image-alt"], "policy-bundle")

    def test_cli_overrides_nothing_already_set(self) -> None:
        result = _build_rule_sources([], [], [], ["link-name"])
        self.assertEqual(result["link-name"], "cli")

    def test_multiple_sources_preserved(self) -> None:
        result = _build_rule_sources(
            ["image-alt"],
            ["button-name"],
            ["link-name"],
            ["heading-order"],
        )
        self.assertEqual(result["image-alt"], "policy-bundle")
        self.assertEqual(result["button-name"], "policy-preset")
        self.assertEqual(result["link-name"], "policy-config")
        self.assertEqual(result["heading-order"], "cli")

    def test_first_write_wins_across_layers(self) -> None:
        result = _build_rule_sources(
            ["image-alt"],
            ["image-alt"],
            ["image-alt"],
            ["image-alt"],
        )
        self.assertEqual(result["image-alt"], "policy-bundle")


class MergeRuleListTests(unittest.TestCase):
    """Tests for _merge_rule_list() — ordered dedup."""

    def test_empty_groups(self) -> None:
        self.assertEqual(_merge_rule_list([], [], []), [])

    def test_preserves_order_and_deduplicates(self) -> None:
        self.assertEqual(
            _merge_rule_list(["a", "b"], ["b", "c"], ["a", "d"]),
            ["a", "b", "c", "d"],
        )

    def test_strips_whitespace_and_skips_empty(self) -> None:
        self.assertEqual(
            _merge_rule_list(["  a  ", ""], ["b"]),
            ["a", "b"],
        )


class ResolveEffectivePolicyPathTests(unittest.TestCase):
    """Tests for _resolve_effective_policy_path()."""

    def test_none_returns_none(self) -> None:
        self.assertIsNone(_resolve_effective_policy_path(None, Path("/out")))

    def test_auto_returns_default_filename(self) -> None:
        result = _resolve_effective_policy_path("AUTO", Path("/out"))
        self.assertEqual(result, Path("/out/wcag-effective-policy.json"))

    def test_explicit_path_returned_as_is(self) -> None:
        result = _resolve_effective_policy_path("/tmp/my-policy.json", Path("/out"))
        self.assertEqual(result, Path("/tmp/my-policy.json"))


class LoadPolicyConfigTests(unittest.TestCase):
    """Tests for _load_policy_config()."""

    def test_none_returns_empty(self) -> None:
        self.assertEqual(_load_policy_config(None), {})

    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(_load_policy_config(""), {})

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _load_policy_config("/nonexistent/policy.json")
        self.assertIn("does not exist", str(ctx.exception))

    def test_valid_config_loaded(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"fail_on": "serious"}, f)
            f.flush()
            result = _load_policy_config(f.name)
        self.assertEqual(result, {"fail_on": "serious"})

    def test_unknown_keys_rejected(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"fail_on": "serious", "bogus_key": True}, f)
            f.flush()
            with self.assertRaises(ValueError) as ctx:
                _load_policy_config(f.name)
        self.assertIn("bogus_key", str(ctx.exception))

    def test_non_object_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([1, 2, 3], f)
            f.flush()
            with self.assertRaises(ValueError) as ctx:
                _load_policy_config(f.name)
        self.assertIn("JSON object", str(ctx.exception))


class ResolvePresetBundleEdgeCases(unittest.TestCase):
    """Edge cases for _resolve_policy_preset / _resolve_policy_bundle."""

    def test_unknown_preset_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _resolve_policy_preset("nonexistent")
        self.assertIn("unknown policy preset", str(ctx.exception))

    def test_unknown_bundle_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _resolve_policy_bundle("nonexistent")
        self.assertIn("unknown policy bundle", str(ctx.exception))

    def test_none_preset_returns_empty(self) -> None:
        self.assertEqual(_resolve_policy_preset(None), {})

    def test_none_bundle_returns_empty(self) -> None:
        self.assertEqual(_resolve_policy_bundle(None), {})


if __name__ == "__main__":
    unittest.main()
