# Repo Admin Setup

Use this note to keep release publishing and PR governance aligned for this repository.

## Release Assets

- `.github/workflows/release.yml` now supports three entry paths:
  - tag push for `v*`
  - manual `workflow_dispatch`
  - GitHub Release `published`
- The `published` trigger matters when an operator creates or publishes a release from the GitHub UI. Without that trigger, a manually published release can exist without the packaged zip assets.
- Published release assets should include:
  - `libro-agent-wcag-<version>-codex.zip`
  - `libro-agent-wcag-<version>-claude.zip`
  - `libro-agent-wcag-<version>-gemini.zip`
  - `libro-agent-wcag-<version>-copilot.zip`
  - `libro-agent-wcag-<version>-all-in-one.zip`
  - `libro-agent-wcag-<version>-sha256sums.txt`
  - `libro-agent-wcag-<version>-release-manifest.json`
  - `latest-release.json`

## Quick Install From Published Release

- PowerShell:

```powershell
pwsh -File .\scripts\install-latest.ps1 -ReleaseBase https://github.com/<owner>/<repo>/releases/download/vX.Y.Z -Agent codex
```

- POSIX shell:

```sh
sh ./scripts/install-latest.sh --release-base https://github.com/<owner>/<repo>/releases/download/vX.Y.Z --agent codex
```

- Replace `vX.Y.Z` with the actual tag, for example `v1.0.1`.
- The bootstrap installer resolves `latest-release.json` or the pinned manifest, verifies `sha256`, extracts the selected bundle, runs the packaged installer, then runs doctor integrity verification.

## PR Rule Bypass

- `owner can bypass` is a GitHub repository setting, not something this repo can enforce through files alone.
- Preferred setup is a branch ruleset targeting the default branch with:
  - require pull request before merging
  - require status checks to pass
  - required check `libro-agent-wcag-real-scanner`
  - bypass list containing the repository admin/owner role, or a dedicated maintainers team
- If you want owners to keep an audit trail but still bypass merge blockers, use ruleset bypass permission `For pull requests only` instead of unrestricted bypass.
- If the repository still uses legacy branch protection instead of rulesets, configure the equivalent bypass behavior in repository settings. GitHub notes that bypass actors in classic branch protection are only available for organization-owned repositories.

## References

- GitHub rulesets overview: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- GitHub ruleset creation and bypass list: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository
- GitHub branch protection overview: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
