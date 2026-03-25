# Manual Testing Checklists

This file covers the applicable manual test types that cannot be fully automated in-repo.

## Acceptance Test / UAT

- Install `libro-wcag` for the target agent.
- Invoke the skill on one existing page in `audit-only`, `suggest-only`, and `apply-fixes` intent.
- Confirm the result includes Markdown and JSON outputs with aligned issue IDs.
- Confirm the result explains whether files were modified.
- Confirm citations point to `w3.org`.

## Alpha Test

- Run the skill internally on at least one local HTML file and one remote URL.
- Record any missing contract fields, broken prompts, or malformed reports.
- Verify the doctor command reports the installation as healthy before testing.

## Beta Test

- Ask one external user to install via the documented installer path.
- Have them verify install, invocation, and uninstall without local repo knowledge.
- Record friction in installation, prompt loading, or report interpretation.

## Usability Test

- Validate the README gives enough guidance for first install without oral handoff.
- Validate each agent's first-use guidance is sufficient to invoke the skill correctly.
- Confirm the testing plan and runtime requirements are discoverable.

## Exploratory Testing

- Run the skill on pages with mixed issues: missing alt text, labels, link names, and language attributes.
- Try unusual targets: local files, invalid schemes, and partially broken installs.
- Record any confusing output wording or duplicated findings.
