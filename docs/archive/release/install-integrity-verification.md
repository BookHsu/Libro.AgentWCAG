# Post-install Integrity Verification

Use this flow after every install/reinstall to verify the installed bundle was not partially copied or tampered.

## 1. Run integrity-aware doctor checks

Single agent:

```powershell
python .\scripts\doctor-agent.py --agent codex --verify-manifest-integrity
```

All agents under a custom base path:

```powershell
python .\scripts\doctor-agent.py --agent all --dest .\.tmp\agents --verify-manifest-integrity
```

## 2. Expected healthy output

- `ok` is `true`
- `manifest_integrity.verified` is `true`
- `manifest_integrity.hash_mismatches` is empty
- `manifest_integrity.missing_files` is empty

## 3. Failure remediation playbook

### A. Missing companion files (`usage-example`, `failure-guide`, `e2e-example`)

1. Reinstall the same agent bundle with `--force`.
2. Re-run doctor with `--verify-manifest-integrity`.
3. If still missing, compare local bundle contents against `skills/libro-wcag/adapters/<adapter>/` in this repo.

### B. Hash mismatch on adapter prompt or entrypoint files

1. Treat the installation as corrupted or manually modified.
2. Reinstall with `--force` from a known-good checkout.
3. Re-run integrity doctor; archive before/after doctor JSON for release evidence.

### C. Missing integrity metadata in manifest

1. Ensure installer version includes `manifest_integrity.entrypoint_hashes`.
2. Reinstall with the current `scripts/install-agent.py`.
3. If old bundles must be retained, regenerate manifest by reinstalling into the same destination with `--force`.

## 4. Release evidence

Archive these artifacts with release validation evidence:

- doctor JSON output for each shipped agent target
- command transcript showing `--verify-manifest-integrity`
- any remediation actions (reinstall command + rerun output)
