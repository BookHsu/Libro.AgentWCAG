# Reusable Prompt And Invocation Templates

Use these templates when you need consistent, low-friction WCAG runs across adapters.

## 1. Common audit prompt template

```text
Use libro-agent-wcag with the following contract:
- task_mode: {create|modify}
- execution_mode: {audit-only|suggest-only|apply-fixes}
- wcag_version: {2.0|2.1|2.2}
- conformance_level: {A|AA|AAA}
- target: {local_path_or_url}
- output_language: {bcp47}

Requirements:
1) Run axe + Lighthouse checks.
2) Output Markdown table and JSON report using the shared contract fields.
3) Include W3C citations for every major finding.
4) If execution_mode=apply-fixes, only apply supported safe rewrites and report diff artifacts.
```

## 2. Modify + suggest-only template

```text
task_mode=modify
execution_mode=suggest-only
wcag_version=2.2
conformance_level=AA
output_language=zh-TW
target={your_file_or_url}

Please prioritize P0/P1 findings and provide concrete remediation snippets for each.
```

## 3. Modify + apply-fixes template

```text
task_mode=modify
execution_mode=apply-fixes
wcag_version=2.2
conformance_level=AA
output_language=zh-TW
target={local_supported_file}

Apply only safe deterministic rewrites. Keep unsupported or high-risk findings as manual-review.
Return before/after evidence and diff artifact locations.
```

## 4. Create-mode pre-release template

```text
task_mode=create
execution_mode=suggest-only
wcag_version=2.2
conformance_level=AA
output_language=zh-TW
target={draft_or_template_path}

Review as a pre-release draft and list release-blocking accessibility risks first.
```

## 5. Adapter invocation quick templates

### Codex

```powershell
python .\skills\libro-agent-wcag\scripts\run_accessibility_audit.py `
  --target ".\docs\testing\realistic-sample\mixed-findings.html" `
  --task-mode modify `
  --execution-mode suggest-only `
  --wcag-version 2.2 `
  --conformance-level AA `
  --output-language zh-TW
```

### Claude / Gemini / Copilot

1. Load the adapter `prompt-template.md` from the installed skill bundle.
2. Paste one of the contract templates above.
3. Keep output contract keys unchanged (`run_meta`, `findings`, `fixes`, `summary`, etc.).

## 6. Reuse policy

- Reuse these templates as a starting point and only override required fields.
- Keep `wcag_version` + `conformance_level` explicit for reproducibility.
- Link `docs/release/apply-fixes-scope.md` when using `apply-fixes`.
