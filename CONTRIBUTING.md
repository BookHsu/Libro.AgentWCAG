# Contributing

Thank you for contributing to Libro.AgentWCAG.

This repository maintains a vendor-neutral WCAG skill contract shared across Codex, Claude, Gemini, and Copilot. Changes should preserve contract stability first, then improve adapters, tooling, and documentation around that contract.

## Ground Rules

- Keep adapters thin. Files under `skills/libro-wcag/adapters/` may change prompt phrasing, but must not change contract field names, field ordering, status vocabulary, or JSON keys.
- Keep the vendor-neutral contract authoritative. Update `skills/libro-wcag/SKILL.md`, `skills/libro-wcag/references/core-spec.md`, and schemas/tests together when the contract changes.
- Prefer safe auto-fixes only. Any new `apply-fixes` behavior must be demonstrably safe, narrowly scoped, and covered by regression tests.
- Use official W3C citations. Material findings and documentation examples should point to official WCAG / Understanding URLs.
- Keep versions in sync. Release-facing version strings in `pyproject.toml` and `package.json` must match.

## Development Setup

Requirements:

- Python 3.12+
- `pyyaml`
- Node.js only when you need scanner/runtime or packaging workflows

Common commands:

```bash
python -m unittest discover -s skills/libro-wcag/scripts/tests -p "test_*.py"
python scripts/validate_skill.py skills/libro-wcag
python scripts/libro.py doctor codex
```

## Change Types

### Contract or Schema Changes

When changing report fields, status vocabularies, defaults, or schema behavior:

1. Update the contract source in `skills/libro-wcag/SKILL.md` and related references.
2. Update the JSON schema in `skills/libro-wcag/schemas/`.
3. Add or adjust regression coverage in `skills/libro-wcag/scripts/tests/`.
4. Update adapter examples if the user-visible output shape changes.
5. Record the change in `CHANGELOG.md`.

### Adapter Changes

When changing adapter docs or prompt templates:

1. Keep the output contract semantically identical across adapters.
2. Update the affected adapter's `prompt-template.md`, `usage-example.md`, `failure-guide.md`, and `e2e-example.md` together when needed.
3. Re-run `python scripts/validate_skill.py skills/libro-wcag`.

### Auto-Fix Changes

When changing `skills/libro-wcag/scripts/auto_fix.py` or related rewrite helpers:

1. Limit changes to patterns that are safe to rewrite automatically.
2. Add targeted fixture or unit coverage for both successful rewrites and guarded non-rewrites.
3. Verify unified diff output remains reviewable.

## Pull Request Expectations

- Keep PRs focused and small enough to review coherently.
- Describe user-visible contract changes explicitly.
- Call out any backward compatibility risk.
- Include the validation commands you ran.
- Update `CHANGELOG.md` for behavior, contract, packaging, or operator-facing documentation changes.

## Documentation Expectations

- Prefer updating the primary source of truth instead of adding duplicate guidance.
- Put operational docs under `docs/release/`, testing docs under `docs/testing/`, and examples under `docs/examples/`.
- Archive superseded material under `docs/archive/` rather than deleting useful history.

## Review Checklist

Before requesting review, confirm:

- Tests or validation relevant to the change have been run.
- Contract, schema, adapters, and examples remain aligned.
- New files are placed in the correct docs section.
- No unrelated generated artifacts are included.
