#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import run_accessibility_audit as runner
import advanced_gates
import baseline_governance
import report_artifacts
import scanner_runtime

from run_accessibility_audit import (
    DEFAULT_SCANNER_RETRY_ATTEMPTS,
    DEFAULT_TIMEOUT_SECONDS,
    _find_rule_policy_overlaps,
    _policy_config_keys_payload,
    parse_args,
)


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.test_workspace_root = cls.repo_root / '.tmp-test' / 'runner'

    def _workspace(self, name: str) -> Path:
        workspace = self.test_workspace_root / name
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def test_existing_local_path_is_converted_to_file_uri(self) -> None:
        workspace = self._workspace("scanner-runtime-local-file-uri")
        html_path = workspace / "index.html"
        html_path.write_text("<!doctype html><title>x</title>", encoding="utf-8")
        resolved = scanner_runtime._resolve_target_for_scanners(str(html_path))
        self.assertTrue(resolved.startswith("file:///"))

    def test_http_target_is_preserved(self) -> None:
        target = "https://example.com/page"
        self.assertEqual(scanner_runtime._resolve_target_for_scanners(target), target)

    def test_existing_file_uri_is_preserved(self) -> None:
        workspace = self._workspace("scanner-runtime-existing-file-uri")
        html_path = workspace / "index.html"
        html_path.write_text("<!doctype html><title>x</title>", encoding="utf-8")
        target = html_path.resolve().as_uri()
        self.assertEqual(scanner_runtime._resolve_target_for_scanners(target), target)

    def test_invalid_scheme_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            scanner_runtime._resolve_target_for_scanners("ftp://example.com/file.html")

    def test_missing_local_file_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            scanner_runtime._resolve_target_for_scanners("missing-file.html")

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
            "--debt-trend-window",
            "7",
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
        self.assertEqual(args.debt_trend_window, 7)

    def test_cli_accepts_baseline_evidence_mode_flag(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--baseline-evidence-mode",
            "hash-chain",
            "--waiver-expiry-mode",
            "fail",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.baseline_evidence_mode, "hash-chain")
        self.assertEqual(args.waiver_expiry_mode, "fail")

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
            waiver_expiry_mode='warn',
            risk_calibration_mode='warn',
            risk_calibration_source='calibration.json',
            stability_mode='warn',
            stability_baseline='stability.json',
            overlapping_rules=['meta-viewport'],
        )
        self.assertEqual(policy['bundle'], 'legacy-content')
        self.assertEqual(policy['preset'], 'legacy')
        self.assertTrue(policy['fail_on_new_only'])
        self.assertEqual(policy['baseline_signature']['selector_canonicalization'], 'basic')
        self.assertEqual(policy['baseline_evidence_mode'], 'hash-chain')
        self.assertEqual(policy['waiver_expiry_mode'], 'warn')
        self.assertEqual(policy['risk_calibration_mode'], 'warn')
        self.assertEqual(policy['risk_calibration_source'], 'calibration.json')
        self.assertEqual(policy['stability_mode'], 'warn')
        self.assertEqual(policy['stability_baseline'], 'stability.json')
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

        capabilities = scanner_runtime._build_scanner_capabilities(preflight, report, args, axe_data, lighthouse_data)
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
        first_hash, first_material = baseline_governance._compute_report_evidence_hash(report, signature_config)
        second_hash, second_material = baseline_governance._compute_report_evidence_hash(report, signature_config)
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
        baseline_hash, _ = baseline_governance._compute_report_evidence_hash(baseline_report, signature_config)
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
        evidence = baseline_governance._build_run_baseline_evidence(
            report=report,
            baseline_report=baseline_report,
            signature_config=signature_config,
            evidence_mode='hash-chain',
        )
        self.assertEqual(evidence['mode'], 'hash-chain')
        self.assertTrue(evidence['baseline_verification']['verified'])
        self.assertTrue(bool(evidence['chain_hash']))

    def test_build_artifact_manifest_includes_sha256_and_size(self) -> None:
        workspace = self._workspace('m31-runner-manifest-test')
        output_dir = workspace / 'out'
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / 'wcag-report.json'
        report_path.write_text('{"ok":true}', encoding='utf-8')
        manifest, manifest_path = report_artifacts._build_artifact_manifest(
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
    @patch("scanner_runtime.subprocess.run")
    def test_run_command_returns_stdout_on_success(self, mock_run) -> None:
        mock_run.return_value = type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        ok, result = scanner_runtime._run_command(["npx", "tool"], timeout_seconds=30)
        self.assertTrue(ok)
        self.assertEqual(result, "ok")

    @patch("scanner_runtime.subprocess.run")
    def test_run_command_returns_stderr_on_failure(self, mock_run) -> None:
        mock_run.return_value = type("Result", (), {"returncode": 1, "stdout": "out", "stderr": "boom"})()
        ok, result = scanner_runtime._run_command(["npx", "tool"], timeout_seconds=30)
        self.assertFalse(ok)
        self.assertEqual(result, "boom")

    @patch("scanner_runtime.subprocess.run")
    def test_run_command_returns_timeout_message(self, mock_run) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["npx", "tool"], timeout=7)
        ok, result = scanner_runtime._run_command(["npx", "tool"], timeout_seconds=7)
        self.assertFalse(ok)
        self.assertEqual(result, "command timed out after 7 seconds: npx tool")

    @patch("scanner_runtime.subprocess.run")
    def test_run_command_returns_oserror_message(self, mock_run) -> None:
        mock_run.side_effect = OSError("Access is denied")
        ok, result = scanner_runtime._run_command(["npx", "tool"], timeout_seconds=30)
        self.assertFalse(ok)
        self.assertEqual(result, "failed to execute command npx: Access is denied")

    @patch("scanner_runtime.subprocess.run")
    def test_run_command_returns_permission_denied_message(self, mock_run) -> None:
        mock_run.side_effect = PermissionError("Permission denied")
        ok, result = scanner_runtime._run_command(["npx", "tool"], timeout_seconds=30)
        self.assertFalse(ok)
        self.assertEqual(result, "permission denied while executing command npx: Permission denied")

    @patch("scanner_runtime.subprocess.run")
    def test_run_command_returns_temporary_oserror_message(self, mock_run) -> None:
        mock_run.side_effect = OSError(scanner_runtime.errno.EAGAIN, "Resource temporarily unavailable")
        ok, result = scanner_runtime._run_command(["npx", "tool"], timeout_seconds=30)
        self.assertFalse(ok)
        self.assertIn("temporary failure while executing command npx", result)

    @patch("scanner_runtime.time.sleep")
    @patch("scanner_runtime.socket.create_connection")
    @patch("scanner_runtime.time.monotonic")
    def test_wait_for_debug_port_uses_remaining_timeout(self, mock_monotonic, mock_create_connection, mock_sleep) -> None:
        mock_monotonic.side_effect = [100.0, 100.0, 100.25]
        mock_create_connection.side_effect = OSError("not ready")

        ready = scanner_runtime._wait_for_debug_port(9222, timeout_seconds=0.2)

        self.assertFalse(ready)
        self.assertEqual(mock_create_connection.call_count, 1)
        self.assertAlmostEqual(mock_create_connection.call_args.kwargs["timeout"], 0.2)
        mock_sleep.assert_called_once_with(0.1)

    @patch("scanner_runtime.shutil.which")
    @patch("scanner_runtime.os.name", "nt")
    def test_resolve_npx_executable_prefers_cmd_on_windows(self, mock_which) -> None:
        mock_which.side_effect = lambda tool: "C:/Program Files/nodejs/npx.cmd" if tool == "npx.cmd" else None
        self.assertEqual(scanner_runtime._resolve_npx_executable(), "npx.cmd")

    def test_try_run_axe_uses_resolved_npx_executable(self) -> None:
        output_dir = Path(__file__).parent / "fixtures" / "_tmp-npx-command"
        output_dir.mkdir(parents=True, exist_ok=True)
        axe_json = output_dir / "axe.raw.json"
        axe_json.write_text('{"violations": []}', encoding="utf-8")
        try:
            with patch("scanner_runtime.NPX_EXECUTABLE", "npx.cmd"), patch("scanner_runtime._run_command", return_value=(True, "")) as mock_run:
                payload, err = scanner_runtime._try_run_axe("https://example.com", output_dir, timeout_seconds=15)
            self.assertIsNone(err)
            self.assertEqual(payload, {"violations": []})
            self.assertEqual(mock_run.call_args[0][0][0], "npx.cmd")
        finally:
            if axe_json.exists():
                axe_json.unlink()
            if output_dir.exists():
                output_dir.rmdir()

    def test_try_run_axe_supports_list_wrapped_cli_payload(self) -> None:
        output_dir = Path(__file__).parent / "fixtures" / "_tmp-axe-list-payload"
        output_dir.mkdir(parents=True, exist_ok=True)
        axe_json = output_dir / "axe.raw.json"
        axe_json.write_text('[{"violations": [{"id": "image-alt"}]}]', encoding="utf-8")
        try:
            with patch("scanner_runtime._run_command", return_value=(True, "")):
                payload, err = scanner_runtime._try_run_axe("https://example.com", output_dir, timeout_seconds=15)
            self.assertIsNone(err)
            self.assertEqual(payload, {"violations": [{"id": "image-alt"}]})
        finally:
            if axe_json.exists():
                axe_json.unlink()
            if output_dir.exists():
                output_dir.rmdir()

    def test_try_run_axe_returns_error_for_malformed_json(self) -> None:
        output_dir = Path(__file__).parent / "fixtures" / "_tmp-axe-malformed-json"
        output_dir.mkdir(parents=True, exist_ok=True)
        axe_json = output_dir / "axe.raw.json"
        axe_json.write_text('{"violations": }', encoding="utf-8")
        try:
            with patch("scanner_runtime._run_command", return_value=(True, "")):
                payload, err = scanner_runtime._try_run_axe("https://example.com", output_dir, timeout_seconds=15)
            self.assertIsNone(payload)
            self.assertRegex(err or "", r"axe output json is malformed: .*axe\.raw\.json")
        finally:
            if axe_json.exists():
                axe_json.unlink()
            if output_dir.exists():
                output_dir.rmdir()

    def test_format_cli_output_path_prefers_repo_relative_path(self) -> None:
        output_path = self.repo_root / ".tmp-test" / "runner" / "axe.raw.json"
        formatted = scanner_runtime._format_cli_output_path(output_path)
        self.assertEqual(Path(formatted), Path(".tmp-test") / "runner" / "axe.raw.json")

    def test_try_run_axe_returns_error_when_output_missing(self) -> None:
        output_dir = Path(__file__).parent / "fixtures"
        with patch("scanner_runtime._run_command", return_value=(True, "")):
            payload, err = scanner_runtime._try_run_axe("https://example.com", output_dir, timeout_seconds=15)
        self.assertIsNone(payload)
        self.assertEqual(err, "axe did not generate output json")

    def test_try_run_lighthouse_returns_error_when_output_missing(self) -> None:
        output_dir = Path(__file__).parent / "fixtures"
        with (
            patch("scanner_runtime._find_browser_executable", return_value="chrome.exe"),
            patch("scanner_runtime._find_free_port", return_value=9222),
            patch("scanner_runtime._wait_for_debug_port", return_value=True),
            patch("scanner_runtime.subprocess.Popen") as mock_popen,
            patch("scanner_runtime._run_command", return_value=(True, "")),
        ):
            process = Mock()
            process.poll.return_value = None
            mock_popen.return_value = process
            payload, err = scanner_runtime._try_run_lighthouse("https://example.com", output_dir, timeout_seconds=15)
        self.assertIsNone(payload)
        self.assertEqual(err, "lighthouse did not generate output json")

    def test_try_run_lighthouse_launches_browser_and_connects_over_debug_port(self) -> None:
        output_dir = Path(__file__).parent / "fixtures" / "_tmp-lighthouse-command"
        output_dir.mkdir(parents=True, exist_ok=True)
        lighthouse_json = output_dir / "lighthouse.raw.json"
        lighthouse_json.write_text('{"audits": {}}', encoding="utf-8")
        try:
            process = Mock()
            process.poll.return_value = None
            with (
                patch("scanner_runtime._find_browser_executable", return_value="chrome.exe"),
                patch("scanner_runtime._find_free_port", return_value=9222),
                patch("scanner_runtime._wait_for_debug_port", return_value=True),
                patch("scanner_runtime.subprocess.Popen", return_value=process) as mock_popen,
                patch("scanner_runtime._run_command", return_value=(True, "")) as mock_run,
            ):
                payload, err = scanner_runtime._try_run_lighthouse("https://example.com", output_dir, timeout_seconds=15)
            self.assertIsNone(err)
            self.assertEqual(payload, {"audits": {}})
            browser_command = mock_popen.call_args.args[0]
            self.assertIn("--remote-debugging-port=9222", browser_command)
            self.assertIn("--user-data-dir=", " ".join(browser_command))
            lighthouse_command = mock_run.call_args.args[0]
            self.assertIn("--port=9222", lighthouse_command)
            self.assertNotIn("--chrome-flags=", " ".join(lighthouse_command))
            process.terminate.assert_called_once()
        finally:
            if lighthouse_json.exists():
                lighthouse_json.unlink()
            temp_root = output_dir / "lighthouse-tmp"
            if temp_root.exists():
                import shutil
                shutil.rmtree(temp_root, ignore_errors=True)
            if output_dir.exists():
                output_dir.rmdir()

    def test_try_run_lighthouse_returns_error_for_malformed_json(self) -> None:
        output_dir = Path(__file__).parent / "fixtures" / "_tmp-lighthouse-malformed-json"
        output_dir.mkdir(parents=True, exist_ok=True)
        lighthouse_json = output_dir / "lighthouse.raw.json"
        lighthouse_json.write_text('{"audits": }', encoding="utf-8")
        try:
            process = Mock()
            process.poll.return_value = None
            with (
                patch("scanner_runtime._find_browser_executable", return_value="chrome.exe"),
                patch("scanner_runtime._find_free_port", return_value=9222),
                patch("scanner_runtime._wait_for_debug_port", return_value=True),
                patch("scanner_runtime.subprocess.Popen", return_value=process),
                patch("scanner_runtime._run_command", return_value=(True, "")),
            ):
                payload, err = scanner_runtime._try_run_lighthouse("https://example.com", output_dir, timeout_seconds=15)
            self.assertIsNone(payload)
            self.assertRegex(err or "", r"lighthouse output json is malformed: .*lighthouse\.raw\.json")
        finally:
            if lighthouse_json.exists():
                lighthouse_json.unlink()
            temp_root = output_dir / "lighthouse-tmp"
            if temp_root.exists():
                import shutil

                shutil.rmtree(temp_root, ignore_errors=True)
            if output_dir.exists():
                output_dir.rmdir()

    def test_try_run_lighthouse_serves_local_files_over_http(self) -> None:
        output_dir = Path(__file__).parent / "fixtures" / "_tmp-lighthouse-local"
        output_dir.mkdir(parents=True, exist_ok=True)
        fixture_path = output_dir / "index.html"
        fixture_path.write_text("<!doctype html><img>", encoding="utf-8")
        lighthouse_json = output_dir / "lighthouse.raw.json"
        lighthouse_json.write_text('{"audits": {}}', encoding="utf-8")
        fake_server = Mock()
        fake_thread = Mock()
        try:
            process = Mock()
            process.poll.return_value = None
            with (
                patch("scanner_runtime._find_browser_executable", return_value="chrome.exe"),
                patch("scanner_runtime._find_free_port", return_value=9222),
                patch("scanner_runtime._wait_for_debug_port", return_value=True),
                patch("scanner_runtime._start_local_file_server", return_value=(fake_server, fake_thread, "http://127.0.0.1:8123/index.html")),
                patch("scanner_runtime.subprocess.Popen", return_value=process),
                patch("scanner_runtime._run_command", return_value=(True, "")) as mock_run,
            ):
                payload, err = scanner_runtime._try_run_lighthouse(str(fixture_path), output_dir, timeout_seconds=15)
            self.assertIsNone(err)
            self.assertEqual(payload, {"audits": {}})
            lighthouse_command = mock_run.call_args.args[0]
            self.assertIn("http://127.0.0.1:8123/index.html", lighthouse_command)
            fake_server.shutdown.assert_called_once()
            fake_server.server_close.assert_called_once()
            fake_thread.join.assert_called_once()
        finally:
            for artifact in (lighthouse_json, fixture_path):
                if artifact.exists():
                    artifact.unlink()
            temp_root = output_dir / "lighthouse-tmp"
            if temp_root.exists():
                import shutil
                shutil.rmtree(temp_root, ignore_errors=True)
            if output_dir.exists():
                output_dir.rmdir()

    @patch("scanner_runtime._tool_available", return_value=True)
    @patch("scanner_runtime._run_command")
    def test_preflight_returns_ok_when_all_checks_pass(self, mock_run_command, _mock_tool_available) -> None:
        mock_run_command.return_value = (True, "v")
        result = scanner_runtime.run_preflight_checks(timeout_seconds=5)
        self.assertTrue(result["ok"])
        self.assertTrue(all(item["status"] == "ok" for item in result["checks"]))

    @patch("scanner_runtime._tool_available")
    def test_preflight_reports_missing_binary(self, mock_tool_available) -> None:
        mock_tool_available.side_effect = [False, True, True]
        with patch("scanner_runtime._run_command", return_value=(True, "v")):
            result = scanner_runtime.run_preflight_checks(timeout_seconds=5)
        self.assertFalse(result["ok"])
        self.assertEqual(result["checks"][0]["status"], "error")
        self.assertIn("PATH", result["checks"][0]["message"])
        self.assertEqual(result["checks"][0]["version_provenance"]["source"], "binary-missing")
        self.assertEqual(result["tools"]["npx"]["version_provenance"]["source"], "binary-missing")

    def test_extract_version_line_returns_first_non_empty_line(self) -> None:
        output = "\n\n10.9.0\nsecondary"
        self.assertEqual(scanner_runtime._extract_version_line(output), "10.9.0")

    @patch("scanner_runtime.shutil.which")
    @patch("scanner_runtime._tool_available", return_value=True)
    @patch("scanner_runtime._run_command")
    def test_preflight_includes_diagnostics_fields(
        self,
        mock_run_command,
        _mock_tool_available,
        mock_which,
    ) -> None:
        mock_which.return_value = '/usr/bin/npx'
        mock_run_command.return_value = (True, '10.9.0\n')
        result = scanner_runtime.run_preflight_checks(timeout_seconds=5)
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
        self.assertTrue(scanner_runtime._is_transient_scanner_error("command timed out after 5 seconds"))
        self.assertTrue(scanner_runtime._is_transient_scanner_error("network failure: ECONNRESET"))
        self.assertFalse(scanner_runtime._is_transient_scanner_error("command not found: npx"))

    @patch("scanner_runtime.time.sleep")
    def test_run_scanner_with_retry_retries_transient_error_then_succeeds(self, mock_sleep: Mock) -> None:
        runner = Mock(side_effect=[(None, "command timed out after 2 seconds"), ({"violations": []}, None)])

        payload, error, telemetry = scanner_runtime._run_scanner_with_retry(
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

    @patch("scanner_runtime.time.sleep")
    def test_run_scanner_with_retry_does_not_retry_non_transient_errors(self, mock_sleep: Mock) -> None:
        runner = Mock(return_value=(None, "command not found: npx"))

        payload, error, telemetry = scanner_runtime._run_scanner_with_retry(
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
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[4]
        cls.test_workspace_root = cls.repo_root / '.tmp-test' / 'runner-policy'

    def _workspace(self, name: str) -> Path:
        workspace = self.test_workspace_root / name
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

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

        product_metadata = {
            'name': 'Libro.AgentWCAG',
            'product_version': '0.1.0',
            'source_revision': 'a' * 40,
            'report_schema_version': '1.0.0',
        }
        sarif = runner._report_to_sarif(report, 'https://example.com', None, product_metadata)
        result = sarif['runs'][0]['results'][0]
        driver = sarif['runs'][0]['tool']['driver']
        self.assertEqual(result['ruleId'], 'image-alt')
        self.assertIn('selector: img.hero', result['message']['text'])
        self.assertEqual(result['locations'][0]['physicalLocation']['region']['startLine'], 17)
        self.assertEqual(result['locations'][0]['physicalLocation']['region']['startColumn'], 5)
        self.assertEqual(driver['version'], '0.1.0')
        self.assertEqual(driver['properties']['source_revision'], 'a' * 40)

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

        diff = baseline_governance._build_baseline_diff(current, baseline)
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

        diff = baseline_governance._build_baseline_diff(report, baseline, signature_config)
        baseline_governance._tag_findings_with_debt_state(report, diff, signature_config)
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

        diff = baseline_governance._build_baseline_diff(current, baseline, signature_config)
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

        diff = baseline_governance._build_baseline_diff(current, baseline, signature_config)
        self.assertEqual(diff['introduced_count'], 0)
        self.assertEqual(diff['persistent_count'], 1)

    def test_validate_debt_waivers_rejects_missing_required_fields(self) -> None:
        with self.assertRaises(ValueError):
            baseline_governance._validate_debt_waivers(
                [
                    {
                        'signature': 'image-alt|img.hero',
                        'owner': 'team-a',
                        'approved_at': '2026-01-10T09:00:00Z',
                        'expires_at': '2026-06-01T00:00:00Z',
                    }
                ]
            )

    def test_evaluate_debt_waiver_review_counts_expired_missing_and_valid(self) -> None:
        baseline_diff = {
            'persistent_signatures': ['button-name|button.icon', 'image-alt|img.hero', 'label|input#email'],
        }
        baseline_report = {
            'debt_waivers': [
                {
                    'signature': 'image-alt|img.hero',
                    'owner': 'team-a',
                    'approved_at': '2026-01-10T09:00:00Z',
                    'expires_at': '2026-06-01T00:00:00Z',
                    'reason': 'legacy sprint scope',
                },
                {
                    'signature': 'button-name|button.icon',
                    'owner': 'team-b',
                    'approved_at': '2026-01-10T09:00:00Z',
                    'expires_at': '2026-01-15T00:00:00Z',
                    'reason': 'pending design update',
                },
            ]
        }
        review = baseline_governance._evaluate_debt_waiver_review(
            baseline_diff,
            baseline_report,
            now_utc=datetime.fromisoformat('2026-03-01T00:00:00+00:00'),
        )
        self.assertEqual(review['accepted_count'], 3)
        self.assertEqual(review['valid_count'], 1)
        self.assertEqual(review['expired_count'], 1)
        self.assertEqual(review['missing_count'], 1)
        self.assertEqual(review['expired_waivers'][0]['signature'], 'button-name|button.icon')

    def test_build_debt_trend_payload_handles_missing_history(self) -> None:
        trend = baseline_governance._build_debt_trend_payload(
            now_utc=datetime.fromisoformat('2026-03-13T00:00:00+00:00'),
            window=3,
            baseline_report={},
            baseline_report_path=None,
            debt_transitions=None,
            waiver_review=None,
        )
        self.assertEqual(trend['summary']['total_points'], 1)
        self.assertEqual(trend['summary']['latest_counts']['new'], 0)
        self.assertEqual(trend['summary']['latest_counts']['regressed'], 0)

    def test_build_debt_trend_payload_resets_history_on_schema_mismatch(self) -> None:
        baseline_report = {
            'report_schema': {'version': '0.9.0'},
            'run_meta': {
                'debt_trend': {
                    'schema_version': '1.0.0',
                    'points': [
                        {
                            'recorded_at': '2026-03-10T00:00:00Z',
                            'source_report': 'baseline.json',
                            'counts': {'new': 1, 'accepted': 2, 'retired': 0, 'regressed': 0},
                        }
                    ],
                }
            },
        }
        transitions = {
            'new': {'count': 2},
            'accepted': {'count': 3},
            'retired': {'count': 1},
        }
        trend = baseline_governance._build_debt_trend_payload(
            now_utc=datetime.fromisoformat('2026-03-13T00:00:00+00:00'),
            window=5,
            baseline_report=baseline_report,
            baseline_report_path='baseline.json',
            debt_transitions=transitions,
            waiver_review={'expired_count': 1},
        )
        self.assertEqual(trend['summary']['total_points'], 1)
        self.assertEqual(trend['summary']['latest_counts']['new'], 2)
        self.assertEqual(trend['summary']['latest_counts']['regressed'], 1)
        self.assertEqual(trend['history_meta']['history_reset_reason'], 'schema-version-mismatch')

    def test_build_debt_trend_payload_inherits_and_rolls_waiver_expiry_regression(self) -> None:
        baseline_report = {
            'report_schema': {'version': '1.0.0'},
            'run_meta': {
                'debt_trend': {
                    'schema_version': '1.0.0',
                    'points': [
                        {
                            'recorded_at': '2026-03-11T00:00:00Z',
                            'source_report': 'baseline-a.json',
                            'counts': {'new': 1, 'accepted': 2, 'retired': 0, 'regressed': 0},
                        },
                        {
                            'recorded_at': '2026-03-12T00:00:00Z',
                            'source_report': 'baseline-b.json',
                            'counts': {'new': 0, 'accepted': 2, 'retired': 1, 'regressed': 0},
                        },
                    ],
                }
            },
        }
        transitions = {
            'new': {'count': 0},
            'accepted': {'count': 2},
            'retired': {'count': 1},
        }
        trend = baseline_governance._build_debt_trend_payload(
            now_utc=datetime.fromisoformat('2026-03-13T00:00:00+00:00'),
            window=3,
            baseline_report=baseline_report,
            baseline_report_path='baseline-c.json',
            debt_transitions=transitions,
            waiver_review={'expired_count': 2},
        )
        self.assertEqual(trend['summary']['total_points'], 3)
        self.assertEqual(trend['summary']['latest_counts']['regressed'], 2)
        self.assertEqual(trend['summary']['delta_from_previous']['regressed'], 2)

    def test_cli_accepts_risk_calibration_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--risk-calibration-source",
            "calibration.json",
            "--risk-calibration-mode",
            "strict",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.risk_calibration_source, "calibration.json")
        self.assertEqual(args.risk_calibration_mode, "strict")


    def test_cli_accepts_replay_verify_from_flag(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--replay-verify-from",
            "./out-prev",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.replay_verify_from, "./out-prev")

    def test_evaluate_risk_calibration_downgrades_when_source_missing(self) -> None:
        report = {
            'findings': [
                {'rule_id': 'image-alt', 'severity': 'serious', 'status': 'open'},
            ]
        }
        calibration = advanced_gates._evaluate_risk_calibration(
            report=report,
            source_path='missing-calibration-source.json',
            mode='warn',
        )
        self.assertFalse(calibration['applied'])
        self.assertEqual(calibration['downgrade_reason'], 'missing-evidence')

    def test_evaluate_risk_calibration_downgrades_on_conflicting_rule_ids(self) -> None:
        workspace = self._workspace('m36-risk-calibration-conflict-test')
        source = workspace / 'risk-calibration.json'
        source.write_text(
            json.dumps(
                {
                    'schema_version': '1.0.0',
                    'rules': [
                        {'rule_id': 'image-alt', 'observations': 4, 'actionable_count': 3},
                        {'rule_id': 'image-alt', 'observations': 2, 'actionable_count': 1},
                    ],
                }
            ),
            encoding='utf-8',
        )
        report = {
            'findings': [
                {'rule_id': 'image-alt', 'severity': 'serious', 'status': 'open'},
            ]
        }
        calibration = advanced_gates._evaluate_risk_calibration(
            report=report,
            source_path=str(source),
            mode='warn',
        )
        self.assertFalse(calibration['applied'])
        self.assertEqual(calibration['downgrade_reason'], 'conflicting-rule-ids')

    def test_evaluate_risk_calibration_marks_unstable_high_severity_rule(self) -> None:
        workspace = self._workspace('m36-risk-calibration-unstable-test')
        source = workspace / 'risk-calibration.json'
        source.write_text(
            json.dumps(
                {
                    'schema_version': '1.0.0',
                    'rules': [
                        {
                            'rule_id': 'image-alt',
                            'observations': 8,
                            'actionable_count': 6,
                            'high_severity_observations': 6,
                            'high_severity_actionable_count': 2,
                        }
                    ],
                }
            ),
            encoding='utf-8',
        )
        report = {
            'findings': [
                {'rule_id': 'image-alt', 'severity': 'serious', 'status': 'open'},
            ]
        }
        calibration = advanced_gates._evaluate_risk_calibration(
            report=report,
            source_path=str(source),
            mode='strict',
        )
        self.assertTrue(calibration['applied'])
        self.assertIn('image-alt', calibration['unstable_high_severity_rules'])


    def test_build_replay_verification_summary_detects_high_severity_regression(self) -> None:
        source_report = {
            'target': {'value': 'https://example.com'},
            'run_meta': {
                'scanner_capabilities': {
                    'scanners': {
                        'axe': {'available': True},
                        'lighthouse': {'available': False},
                    }
                }
            },
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'severity': 'serious', 'status': 'open'},
            ],
        }
        current_report = {
            'target': {'value': 'https://example.com'},
            'run_meta': {
                'scanner_capabilities': {
                    'scanners': {
                        'axe': {'available': True},
                        'lighthouse': {'available': False},
                    }
                }
            },
            'findings': [
                {'rule_id': 'image-alt', 'changed_target': 'img.hero', 'severity': 'serious', 'status': 'open'},
                {'rule_id': 'button-name', 'changed_target': 'button.icon', 'severity': 'serious', 'status': 'open'},
            ],
        }
        replay = advanced_gates._build_replay_verification_summary(
            current_report=current_report,
            replay_source_report=source_report,
            replay_source_path=Path('source/wcag-report.json'),
            replay_source_dir=Path('source'),
        )
        self.assertEqual(replay['status_counts']['regressed'], 1)
        self.assertTrue(replay['gate']['failed'])
        self.assertEqual(replay['gate']['exit_code'], 47)



    def test_cli_accepts_stability_flags(self) -> None:
        original = sys.argv
        sys.argv = [
            "run_accessibility_audit.py",
            "--target",
            "https://example.com",
            "--stability-baseline",
            "./baseline-out",
            "--stability-mode",
            "fail",
        ]
        try:
            args = parse_args()
        finally:
            sys.argv = original
        self.assertEqual(args.stability_baseline, "./baseline-out")
        self.assertEqual(args.stability_mode, "fail")

    def test_build_scanner_stability_payload_downgrades_when_history_missing(self) -> None:
        report = {
            'target': {'value': 'https://example.com'},
            'run_meta': {
                'scanner_capabilities': {
                    'scanners': {
                        'axe': {'available': True},
                        'lighthouse': {'available': False},
                    }
                }
            },
            'findings': [
                {
                    'rule_id': 'image-alt',
                    'changed_target': 'img.hero',
                    'status': 'open',
                    'sources': ['axe'],
                }
            ],
        }
        stability = advanced_gates._build_scanner_stability_payload(
            now_utc=datetime.fromisoformat('2026-03-13T00:00:00+00:00'),
            mode='warn',
            current_report=report,
            baseline_path=None,
        )
        self.assertEqual(stability['window'], 5)
        self.assertEqual(stability['comparison']['breach_count'], 1)
        self.assertEqual(stability['gate']['downgrade_reason'], 'missing-history')
        self.assertFalse(stability['gate']['failed'])

    def test_build_scanner_stability_payload_respects_history_window_from_baseline_artifact(self) -> None:
        workspace = self._workspace('m38-stability-window-test')
        baseline = workspace / 'scanner-stability.json'
        baseline.write_text(
            json.dumps(
                {
                    'schema_version': '1.0.0',
                    'window': 2,
                    'approved_bounds': {'default_max_variance': 0, 'per_signature': {}},
                    'points': [
                        {
                            'recorded_at': '2026-03-10T00:00:00Z',
                            'target': 'https://example.com',
                            'available_scanners': ['axe'],
                            'rows': [
                                {
                                    'scanner': 'axe',
                                    'rule_id': 'image-alt',
                                    'target': 'img.hero',
                                    'finding_count': 1,
                                }
                            ],
                        },
                        {
                            'recorded_at': '2026-03-11T00:00:00Z',
                            'target': 'https://example.com',
                            'available_scanners': ['axe'],
                            'rows': [
                                {
                                    'scanner': 'axe',
                                    'rule_id': 'image-alt',
                                    'target': 'img.hero',
                                    'finding_count': 1,
                                }
                            ],
                        },
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )
        report = {
            'target': {'value': 'https://example.com'},
            'run_meta': {
                'scanner_capabilities': {
                    'scanners': {
                        'axe': {'available': True},
                        'lighthouse': {'available': False},
                    }
                }
            },
            'findings': [
                {
                    'rule_id': 'image-alt',
                    'changed_target': 'img.hero',
                    'status': 'open',
                    'sources': ['axe'],
                }
            ],
        }
        stability = advanced_gates._build_scanner_stability_payload(
            now_utc=datetime.fromisoformat('2026-03-12T00:00:00+00:00'),
            mode='warn',
            current_report=report,
            baseline_path=str(baseline),
        )
        self.assertEqual(stability['window'], 2)
        self.assertEqual(len(stability['points']), 2)
        self.assertEqual(stability['history_meta']['loaded_point_count'], 2)

    def test_build_scanner_stability_payload_downgrades_on_scanner_capability_change(self) -> None:
        workspace = self._workspace('m38-stability-capability-drift-test')
        baseline = workspace / 'scanner-stability.json'
        baseline.write_text(
            json.dumps(
                {
                    'schema_version': '1.0.0',
                    'window': 3,
                    'approved_bounds': {'default_max_variance': 0, 'per_signature': {}},
                    'points': [
                        {
                            'recorded_at': '2026-03-10T00:00:00Z',
                            'target': 'https://example.com',
                            'available_scanners': ['axe', 'lighthouse'],
                            'rows': [
                                {
                                    'scanner': 'axe',
                                    'rule_id': 'image-alt',
                                    'target': 'img.hero',
                                    'finding_count': 1,
                                }
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )
        report = {
            'target': {'value': 'https://example.com'},
            'run_meta': {
                'scanner_capabilities': {
                    'scanners': {
                        'axe': {'available': True},
                        'lighthouse': {'available': False},
                    }
                }
            },
            'findings': [
                {
                    'rule_id': 'image-alt',
                    'changed_target': 'img.hero',
                    'status': 'open',
                    'sources': ['axe'],
                },
                {
                    'rule_id': 'button-name',
                    'changed_target': 'button.icon',
                    'status': 'open',
                    'sources': ['axe'],
                },
            ],
        }
        stability = advanced_gates._build_scanner_stability_payload(
            now_utc=datetime.fromisoformat('2026-03-12T00:00:00+00:00'),
            mode='fail',
            current_report=report,
            baseline_path=str(baseline),
        )
        self.assertTrue(stability['comparison']['scanner_capability_changed'])
        self.assertEqual(stability['gate']['downgrade_reason'], 'scanner-capability-changed')
        self.assertFalse(stability['gate']['failed'])

    def test_resolve_advanced_gate_exit_code_prefers_risk_calibration_then_replay_then_stability(self) -> None:
        should_fail, exit_code, notes = advanced_gates._resolve_advanced_gate_exit_code(
            risk_calibration={
                'gate': {'failed': True},
                'unstable_high_severity_rules': ['image-alt'],
            },
            replay_verification={
                'gate': {'failed': True},
            },
            scanner_stability={
                'gate': {'failed': True},
            },
        )
        self.assertTrue(should_fail)
        self.assertEqual(exit_code, 46)
        self.assertEqual(len(notes), 3)


if __name__ == "__main__":
    unittest.main()
