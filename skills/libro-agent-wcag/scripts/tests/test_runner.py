#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import run_accessibility_audit as runner

from run_accessibility_audit import (
    DEFAULT_SCANNER_RETRY_ATTEMPTS,
    DEFAULT_TIMEOUT_SECONDS,
    _build_artifact_manifest,
    _build_run_baseline_evidence,
    _compute_report_evidence_hash,
    _extract_version_line,
    _find_rule_policy_overlaps,
    _is_transient_scanner_error,
    _policy_config_keys_payload,
    _resolve_npx_executable,
    _resolve_target_for_scanners,
    _run_command,
    _run_scanner_with_retry,
    _try_run_axe,
    _try_run_lighthouse,
    parse_args,
    run_preflight_checks,
)


class RunnerTests(unittest.TestCase):
    def test_existing_local_path_is_converted_to_file_uri(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "index.html"
            html_path.write_text("<!doctype html><title>x</title>", encoding="utf-8")
            resolved = _resolve_target_for_scanners(str(html_path))
            self.assertTrue(resolved.startswith("file:///"))

    def test_http_target_is_preserved(self) -> None:
        target = "https://example.com/page"
        self.assertEqual(_resolve_target_for_scanners(target), target)

    def test_existing_file_uri_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "index.html"
            html_path.write_text("<!doctype html><title>x</title>", encoding="utf-8")
            target = html_path.resolve().as_uri()
            self.assertEqual(_resolve_target_for_scanners(target), target)

    def test_invalid_scheme_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _resolve_target_for_scanners("ftp://example.com/file.html")

    def test_missing_local_file_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _resolve_target_for_scanners("missing-file.html")

    def test_cli_has_timeout_default(self) -> None:
        original = sys.argv
        sys.argv = ["run_accessibility_audit.py", "--target", "https://example.com"]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.timeout, DEFAULT_TIMEOUT_SECONDS)

    def test_cli_accepts_mock_scanner_json_arguments(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--mock-axe-json",
            "axe.json",
            "--mock-lighthouse-json",
            "lighthouse.json",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.mock_axe_json, "axe.json")
        self.assertEqual(args.mock_lighthouse_json, "lighthouse.json")

    def test_cli_accepts_dry_run_and_preflight_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--execution-mode",
            "apply-fixes",
            "--dry-run",
            "--preflight-only",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertTrue(args.dry_run)
        self.assertTrue(args.preflight_only)

    def test_cli_accepts_baseline_diff_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--fail-on",
            "serious",
            "--baseline-report",
            "baseline.json",
            "--baseline-include-target",
            "--baseline-target-normalization",
            "host-path",
            "--baseline-selector-canonicalization",
            "basic",
            "--fail-on-new-only",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.baseline_report, "baseline.json")
        self.assertTrue(args.baseline_include_target)
        self.assertEqual(args.baseline_target_normalization, "host-path")
        self.assertEqual(args.baseline_selector_canonicalization, "basic")
        self.assertTrue(args.fail_on_new_only)

    def test_cli_accepts_baseline_evidence_mode_flag(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--baseline-evidence-mode",
            "hash-chain",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.baseline_evidence_mode, "hash-chain")

    def test_cli_accepts_findings_controls_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--max-findings",
            "25",
            "--sort-findings",
            "rule",
            "--summary-only",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.max_findings, 25)
        self.assertEqual(args.sort_findings, "rule")
        self.assertTrue(args.summary_only)


    def test_cli_accepts_policy_preset_flag(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--policy-preset",
            "legacy",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.policy_preset, "legacy")

    def test_cli_accepts_policy_bundle_flag(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--policy-bundle",
            "marketing-site",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.policy_bundle, "marketing-site")

    def test_cli_accepts_policy_discovery_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--list-policy-presets",
            "--explain-policy",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertTrue(args.list_policy_presets)
        self.assertTrue(args.explain_policy)

    def test_cli_accepts_policy_config_key_listing_and_strict_overlap_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--list-policy-config-keys",
            "--strict-rule-overlap",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertTrue(args.list_policy_config_keys)
        self.assertTrue(args.strict_rule_overlap)

    def test_policy_config_keys_payload_contains_fail_on(self) -> None:
        payload = _policy_config_keys_payload()
        names = [item['name'] for item in payload['keys']]
        self.assertIn('fail_on', names)

    def test_find_rule_policy_overlaps_returns_sorted_unique_values(self) -> None:
        overlaps = _find_rule_policy_overlaps(
            ['image-alt', 'button-name', 'image-alt'],
            ['button-name', 'meta-viewport', 'button-name'],
        )
        self.assertEqual(overlaps, ['button-name'])

    def test_resolve_policy_preset_returns_expected_fail_on_and_ignore_rules(self) -> None:
        preset = runner._resolve_policy_preset('legacy')
        self.assertEqual(preset['fail_on'], 'serious')
        self.assertIn('meta-viewport', preset['ignore_rules'])

    def test_resolve_policy_bundle_returns_expected_fail_on_and_ignore_rules(self) -> None:
        bundle = runner._resolve_policy_bundle('legacy-content')
        self.assertEqual(bundle['fail_on'], 'serious')
        self.assertIn('color-contrast', bundle['ignore_rules'])

    def test_policy_presets_payload_contains_balanced_profile(self) -> None:
        payload = runner._policy_presets_payload()
        names = [item['name'] for item in payload['presets']]
        self.assertIn('balanced', names)

    def test_build_effective_policy_includes_baseline_signature_controls(self) -> None:
        policy = runner._build_effective_policy(
            report_format='json',
            fail_on='serious',
            include_rules=['image-alt'],
            ignore_rules=['meta-viewport'],
            policy_bundle={'name': 'legacy-content'},
            policy_preset={'name': 'legacy'},
            policy_config_path='policy.json',
            policy_sources={},
            fail_on_new_only=True,
            baseline_report_path='baseline.json',
            baseline_signature_config={
                'include_target_in_signature': True,
                'target_normalization': 'host-path',
                'selector_canonicalization': 'basic',
            },
            baseline_evidence_mode='hash-chain',
            overlapping_rules=['meta-viewport'],
        )
        self.assertEqual(policy['bundle'], 'legacy-content')
        self.assertEqual(policy['preset'], 'legacy')
        self.assertTrue(policy['fail_on_new_only'])
        self.assertEqual(policy['baseline_signature']['selector_canonicalization'], 'basic')
        self.assertEqual(policy['baseline_evidence_mode'], 'hash-chain')
        self.assertEqual(policy['overlapping_rules'], ['meta-viewport'])

    def test_build_scanner_capabilities_reports_mocked_rule_catalog(self) -> None:
        preflight = {
            'tools': {
                '@axe-core/cli': {'status': 'error'},
                'lighthouse': {'status': 'error'},
            }
        }
        report = {'run_meta': {'tools': {'axe': 'ok', 'lighthouse': 'skipped'}}}
        args = type(
            'Args',
            (),
            {
                'skip_axe': False,
                'skip_lighthouse': True,
                'mock_axe_json': 'axe.json',
                'mock_lighthouse_json': None,
            },
        )()
        axe_data = {'violations': [{'id': 'image-alt'}, {'id': 'button-name'}]}
        lighthouse_data = None

        capabilities = runner._build_scanner_capabilities(preflight, report, args, axe_data, lighthouse_data)
        self.assertTrue(capabilities['scanners']['axe']['available'])
        self.assertEqual(capabilities['scanners']['axe']['input_mode'], 'mock')
        self.assertFalse(capabilities['scanners']['lighthouse']['available'])
        self.assertEqual(capabilities['available_rule_count'], 2)
        self.assertEqual(capabilities['available_rules'], ['button-name', 'image-alt'])

    def test_compute_report_evidence_hash_is_deterministic(self) -> None:
        report = {
            'target': {'value': 'https://example.com'},
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                {'rule_id': 'button-name', 'changed_target': 'button.icon', 'status': 'open'},
            ],
        }
        signature_config = {
            'include_target_in_signature': False,
            'target_normalization': 'none',
            'selector_canonicalization': 'none',
        }
        first_hash, first_material = _compute_report_evidence_hash(report, signature_config)
        second_hash, second_material = _compute_report_evidence_hash(report, signature_config)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_material['unresolved_signatures'], second_material['unresolved_signatures'])

    def test_build_run_baseline_evidence_in_hash_chain_mode(self) -> None:
        signature_config = {
            'include_target_in_signature': False,
            'target_normalization': 'none',
            'selector_canonicalization': 'none',
        }
        baseline_report = {
            'target': {'value': 'https://example.com'},
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
            ],
        }
        baseline_hash, _ = _compute_report_evidence_hash(baseline_report, signature_config)
        baseline_report['run_meta'] = {
            'baseline_evidence': {
                'mode': 'hash',
                'report_hash': baseline_hash,
            }
        }
        report = {
            'target': {'value': 'https://example.com'},
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                {'rule_id': 'button-name', 'changed_target': 'button.icon', 'status': 'open'},
            ],
        }
        evidence = _build_run_baseline_evidence(
            report=report,
            baseline_report=baseline_report,
            signature_config=signature_config,
            evidence_mode='hash-chain',
        )
        self.assertEqual(evidence['mode'], 'hash-chain')
        self.assertTrue(evidence['baseline_verification']['verified'])
        self.assertTrue(bool(evidence['chain_hash']))

    def test_build_artifact_manifest_includes_sha256_and_size(self) -> None:
        workspace = Path(__file__).resolve().parents[4] / 'automation-work' / 'm31-runner-manifest-test'
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)
        output_dir = workspace / 'out'
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / 'wcag-report.json'
        report_path.write_text('{"ok":true}', encoding='utf-8')
        manifest, manifest_path = _build_artifact_manifest(
            output_dir=output_dir,
            report_format='json',
            target='https://example.com',
            artifact_paths={'machine-report-json': report_path},
            baseline_evidence=None,
        )
        self.assertTrue(manifest_path.exists())
        self.assertEqual(manifest['artifact_count'], 1)
        artifact = manifest['artifacts'][0]
        self.assertEqual(artifact['kind'], 'machine-report-json')
        self.assertGreater(artifact['size_bytes'], 0)
        self.assertEqual(len(artifact['sha256']), 64)
    @patch("run_accessibility_audit.subprocess.run")
    def test_run_command_returns_stdout_on_success(self, mock_run) -> None:
        mock_run.return_value = type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        ok, result = _run_command(["npx", "tool"], timeout_seconds=30)
        self.assertTrue(ok)
        self.assertEqual(result, "ok")

    @patch("run_accessibility_audit.subprocess.run")
    def test_run_command_returns_stderr_on_failure(self, mock_run) -> None:
        mock_run.return_value = type("Result", (), {"returncode": 1, "stdout": "out", "stderr": "boom"})()
        ok, result = _run_command(["npx", "tool"], timeout_seconds=30)
        self.assertFalse(ok)
        self.assertEqual(result, "boom")

    @patch("run_accessibility_audit.subprocess.run")
    def test_run_command_returns_timeout_message(self, mock_run) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["npx", "tool"], timeout=7)
        ok, result = _run_command(["npx", "tool"], timeout_seconds=7)
        self.assertFalse(ok)
        self.assertEqual(result, "command timed out after 7 seconds")

    @patch("run_accessibility_audit.shutil.which")
    @patch("run_accessibility_audit.os.name", "nt")
    def test_resolve_npx_executable_prefers_cmd_on_windows(self, mock_which) -> None:
        mock_which.side_effect = lambda tool: "C:/Program Files/nodejs/npx.cmd" if tool == "npx.cmd" else None
        self.assertEqual(_resolve_npx_executable(), "npx.cmd")

    def test_try_run_axe_uses_resolved_npx_executable(self) -> None:
        output_dir = Path(__file__).parent / "fixtures" / "_tmp-npx-command"
        output_dir.mkdir(parents=True, exist_ok=True)
        axe_json = output_dir / "axe.raw.json"
        axe_json.write_text('{"violations": []}', encoding="utf-8")
        try:
            with patch("run_accessibility_audit.NPX_EXECUTABLE", "npx.cmd"), patch("run_accessibility_audit._run_command", return_value=(True, "")) as mock_run:
                payload, err = _try_run_axe("https://example.com", output_dir, timeout_seconds=15)
            self.assertIsNone(err)
            self.assertEqual(payload, {"violations": []})
            self.assertEqual(mock_run.call_args[0][0][0], "npx.cmd")
        finally:
            if axe_json.exists():
                axe_json.unlink()
            if output_dir.exists():
                output_dir.rmdir()

    def test_try_run_axe_returns_error_when_output_missing(self) -> None:
        output_dir = Path(__file__).parent / "fixtures"
        with patch("run_accessibility_audit._run_command", return_value=(True, "")):
            payload, err = _try_run_axe("https://example.com", output_dir, timeout_seconds=15)
        self.assertIsNone(payload)
        self.assertEqual(err, "axe did not generate output json")

    def test_try_run_lighthouse_returns_error_when_output_missing(self) -> None:
        output_dir = Path(__file__).parent / "fixtures"
        with patch("run_accessibility_audit._run_command", return_value=(True, "")):
            payload, err = _try_run_lighthouse("https://example.com", output_dir, timeout_seconds=15)
        self.assertIsNone(payload)
        self.assertEqual(err, "lighthouse did not generate output json")

    @patch("run_accessibility_audit._tool_available", return_value=True)
    @patch("run_accessibility_audit._run_command")
    def test_preflight_returns_ok_when_all_checks_pass(self, mock_run_command, _mock_tool_available) -> None:
        mock_run_command.return_value = (True, "v")
        result = run_preflight_checks(timeout_seconds=5)
        self.assertTrue(result["ok"])
        self.assertTrue(all(item["status"] == "ok" for item in result["checks"]))

    @patch("run_accessibility_audit._tool_available")
    def test_preflight_reports_missing_binary(self, mock_tool_available) -> None:
        mock_tool_available.side_effect = [False, True, True]
        with patch("run_accessibility_audit._run_command", return_value=(True, "v")):
            result = run_preflight_checks(timeout_seconds=5)
        self.assertFalse(result["ok"])
        self.assertEqual(result["checks"][0]["status"], "error")
        self.assertIn("PATH", result["checks"][0]["message"])
        self.assertEqual(result["checks"][0]["version_provenance"]["source"], "binary-missing")
        self.assertEqual(result["tools"]["npx"]["version_provenance"]["source"], "binary-missing")

    def test_extract_version_line_returns_first_non_empty_line(self) -> None:
        output = "\n\n10.9.0\nsecondary"
        self.assertEqual(_extract_version_line(output), "10.9.0")

    @patch("run_accessibility_audit.shutil.which")
    @patch("run_accessibility_audit._tool_available", return_value=True)
    @patch("run_accessibility_audit._run_command")
    def test_preflight_includes_diagnostics_fields(
        self,
        mock_run_command,
        _mock_tool_available,
        mock_which,
    ) -> None:
        mock_which.return_value = '/usr/bin/npx'
        mock_run_command.return_value = (True, '10.9.0\n')
        result = run_preflight_checks(timeout_seconds=5)
        self.assertIn('tools', result)
        self.assertIn('npx', result['tools'])
        npx = result['tools']['npx']
        self.assertEqual(npx['resolved_command'], '/usr/bin/npx')
        self.assertEqual(npx['version'], '10.9.0')
        self.assertIn('--version', npx['command'])


class RunnerRetryTests(unittest.TestCase):
    def test_cli_has_scanner_retry_defaults(self) -> None:
        original = sys.argv
        sys.argv = ["run_accessibility_audit.py", "--target", "https://example.com"]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.scanner_retry_attempts, DEFAULT_SCANNER_RETRY_ATTEMPTS)
        self.assertGreaterEqual(args.scanner_retry_backoff_seconds, 0)

    def test_is_transient_scanner_error_detects_timeout_and_network_signals(self) -> None:
        self.assertTrue(_is_transient_scanner_error("command timed out after 5 seconds"))
        self.assertTrue(_is_transient_scanner_error("network failure: ECONNRESET"))
        self.assertFalse(_is_transient_scanner_error("command not found: npx"))

    @patch("run_accessibility_audit.time.sleep")
    def test_run_scanner_with_retry_retries_transient_error_then_succeeds(self, mock_sleep: Mock) -> None:
        runner = Mock(side_effect=[(None, "command timed out after 2 seconds"), ({"violations": []}, None)])

        payload, error, telemetry = _run_scanner_with_retry(
            "axe",
            runner,
            retry_attempts=3,
            retry_backoff_seconds=0.01,
        )

        self.assertEqual(payload, {"violations": []})
        self.assertIsNone(error)
        self.assertEqual(telemetry["retry_count"], 1)
        self.assertEqual(runner.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("run_accessibility_audit.time.sleep")
    def test_run_scanner_with_retry_does_not_retry_non_transient_errors(self, mock_sleep: Mock) -> None:
        runner = Mock(return_value=(None, "command not found: npx"))

        payload, error, telemetry = _run_scanner_with_retry(
            "lighthouse",
            runner,
            retry_attempts=4,
            retry_backoff_seconds=0.01,
        )

        self.assertIsNone(payload)
        self.assertEqual(error, "command not found: npx")
        self.assertEqual(telemetry["retry_count"], 0)
        self.assertEqual(runner.call_count, 1)
        mock_sleep.assert_not_called()

class RunnerPolicyTests(unittest.TestCase):
    def test_apply_rule_policy_filters_findings_and_summary(self) -> None:
        report = {
            'findings': [
                {'id': 'ISSUE-001', 'rule_id': 'image-alt', 'status': 'open', 'manual_review_required': False, 'severity': 'serious'},
                {'id': 'ISSUE-002', 'rule_id': 'button-name', 'status': 'open', 'manual_review_required': False, 'severity': 'moderate'},
            ],
            'fixes': [
                {'finding_id': 'ISSUE-001', 'status': 'planned', 'manual_review_required': False},
                {'finding_id': 'ISSUE-002', 'status': 'planned', 'manual_review_required': False},
            ],
            'citations': [
                {'finding_id': 'ISSUE-001', 'sc': '1.1.1', 'url': 'https://example.com'},
                {'finding_id': 'ISSUE-002', 'sc': '4.1.2', 'url': 'https://example.com'},
            ],
            'summary': {
                'change_summary': [
                    {'finding_id': 'ISSUE-001', 'rule_id': 'image-alt'},
                    {'finding_id': 'ISSUE-002', 'rule_id': 'button-name'},
                ],
                'fix_blockers': [],
            },
        }

        before_count, after_count = runner._apply_rule_policy(
            report,
            include_rules=['image-alt'],
            ignore_rules=[],
        )

        self.assertEqual(before_count, 2)
        self.assertEqual(after_count, 1)
        self.assertEqual(report['findings'][0]['rule_id'], 'image-alt')
        self.assertEqual(report['summary']['total_findings'], 1)

    def test_sort_and_cap_report_findings_are_deterministic(self) -> None:
        report = {
            'findings': [
                {'id': 'ISSUE-003', 'rule_id': 'zeta-rule', 'changed_target': 'main', 'severity': 'serious'},
                {'id': 'ISSUE-001', 'rule_id': 'alpha-rule', 'changed_target': 'main', 'severity': 'serious'},
                {'id': 'ISSUE-002', 'rule_id': 'beta-rule', 'changed_target': 'main', 'severity': 'moderate'},
            ],
            'fixes': [
                {'finding_id': 'ISSUE-003', 'status': 'planned', 'manual_review_required': False},
                {'finding_id': 'ISSUE-001', 'status': 'planned', 'manual_review_required': False},
                {'finding_id': 'ISSUE-002', 'status': 'planned', 'manual_review_required': False},
            ],
            'citations': [
                {'finding_id': 'ISSUE-001'},
                {'finding_id': 'ISSUE-002'},
                {'finding_id': 'ISSUE-003'},
            ],
            'summary': {
                'change_summary': [
                    {'finding_id': 'ISSUE-001'},
                    {'finding_id': 'ISSUE-002'},
                    {'finding_id': 'ISSUE-003'},
                ],
                'fix_blockers': [],
            },
        }

        runner._sort_report_findings(report, 'rule')
        cap = runner._cap_report_findings(report, 2)

        self.assertEqual([item['id'] for item in report['findings']], ['ISSUE-001', 'ISSUE-002'])
        self.assertEqual(cap['truncated'], 1)
        self.assertEqual(report['summary']['total_findings'], 2)
    def test_resolve_fail_threshold_returns_exit_code(self) -> None:
        report = {
            'findings': [
                {'severity': 'serious', 'status': 'open'},
            ]
        }
        should_fail, exit_code = runner._resolve_fail_threshold(report, 'serious')
        self.assertTrue(should_fail)
        self.assertEqual(exit_code, 43)

    def test_report_to_sarif_includes_rule_and_selector(self) -> None:
        report = {
            'findings': [
                {
                    'id': 'ISSUE-001',
                    'rule_id': 'image-alt',
                    'severity': 'serious',
                    'current': 'Image needs alt',
                    'changed_target': 'img.hero',
                    'status': 'open',
                    'sc': ['1.1.1'],
                    'source_line': 17,
                    'source_column': 5,
                }
            ]
        }

        sarif = runner._report_to_sarif(report, 'https://example.com', None)
        result = sarif['runs'][0]['results'][0]
        self.assertEqual(result['ruleId'], 'image-alt')
        self.assertIn('selector: img.hero', result['message']['text'])
        self.assertEqual(result['locations'][0]['physicalLocation']['region']['startLine'], 17)
        self.assertEqual(result['locations'][0]['physicalLocation']['region']['startColumn'], 5)

    def test_build_baseline_diff_returns_introduced_and_resolved(self) -> None:
        current = {
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                {'rule_id': 'button-name', 'changed_target': 'button.icon', 'status': 'open'},
            ]
        }
        baseline = {
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                {'rule_id': 'label', 'changed_target': 'input#email', 'status': 'open'},
            ]
        }

        diff = runner._build_baseline_diff(current, baseline)
        self.assertEqual(diff['introduced_count'], 1)
        self.assertEqual(diff['resolved_count'], 1)
        self.assertEqual(diff['persistent_count'], 1)
        self.assertEqual(diff['introduced_signatures'], ['button-name|button.icon'])

    def test_tag_findings_with_debt_state_marks_new_accepted_and_retired(self) -> None:
        signature_config = {
            'include_target_in_signature': False,
            'target_normalization': 'none',
            'selector_canonicalization': 'none',
        }
        report = {
            'target': {'value': 'https://example.com'},
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                {'rule_id': 'button-name', 'changed_target': 'button.icon', 'status': 'open'},
                {'rule_id': 'label', 'changed_target': 'input#email', 'status': 'fixed'},
            ],
        }
        baseline = {
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
                {'rule_id': 'label', 'changed_target': 'input#email', 'status': 'open'},
            ]
        }

        diff = runner._build_baseline_diff(report, baseline, signature_config)
        runner._tag_findings_with_debt_state(report, diff, signature_config)
        findings = {f['rule_id']: f for f in report['findings']}
        self.assertEqual(findings['button-name']['debt_state'], 'new')
        self.assertEqual(findings['image-alt']['debt_state'], 'accepted')
        self.assertEqual(findings['label']['debt_state'], 'retired')


    def test_build_baseline_diff_selector_canonicalization_reduces_noise(self) -> None:
        signature_config = {
            'include_target_in_signature': False,
            'target_normalization': 'none',
            'selector_canonicalization': 'basic',
        }
        current = {
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'div.main > img.hero', 'status': 'open'},
            ]
        }
        baseline = {
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'div.main>img.hero', 'status': 'open'},
            ]
        }

        diff = runner._build_baseline_diff(current, baseline, signature_config)
        self.assertEqual(diff['introduced_count'], 0)
        self.assertEqual(diff['persistent_count'], 1)

    def test_build_baseline_diff_target_normalization_matches_file_and_uri(self) -> None:
        signature_config = {
            'include_target_in_signature': True,
            'target_normalization': 'path-only',
            'selector_canonicalization': 'none',
        }
        current = {
            'target': {'value': 'file:///C:/repo/app/index.html'},
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
            ],
        }
        baseline = {
            'target': {'value': 'C:\\repo\\app\\index.html'},
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'status': 'open'},
            ],
        }

        diff = runner._build_baseline_diff(current, baseline, signature_config)
        self.assertEqual(diff['introduced_count'], 0)
        self.assertEqual(diff['persistent_count'], 1)

if __name__ == "__main__":
    unittest.main()








