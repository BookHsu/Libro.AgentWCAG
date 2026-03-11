# Non-Functional and Reliability Checks

This file defines the non-functional checks that apply to this repo.

## Compatibility Test

- Verify Python installer behavior for `codex`, `claude`, `gemini`, `copilot`, and `all`.
- Verify PowerShell and POSIX wrapper scripts point to the Python installer.

## Performance Test

- Run normalization on a synthetic report with many findings.
- Confirm completion stays within an acceptable local threshold.

## Stress Test

- Run normalization with repeated or large finding sets.
- Confirm report generation still succeeds without malformed output.

## Endurance / Soak Test

- Execute repeated normalization loops and repeated install/doctor/uninstall cycles.
- Confirm no progressive failures occur.

## Volume / Capacity Test

- Generate a report with a larger set of findings and citations.
- Confirm JSON and Markdown files are written correctly.

## Scalability Test

- Compare small and larger synthetic inputs.
- Confirm growth remains operationally linear enough for local CLI usage.

## Security Test

- Verify invalid target schemes are rejected.
- Verify nonexistent local files are rejected before scanner execution.
- Verify install destinations are not silently overwritten without `--force`.

## Vulnerability Scan

- Run dependency and script review before release.
- Current minimum command set:
  - `python -m pip check`
  - `python -m unittest discover -s skills/libro-agent-wcag/scripts/tests -p "test_*.py"`
- If additional dependencies are added later, attach a dedicated dependency scanner.

## Recovery Test

- Break an installed bundle by removing the adapter prompt.
- Confirm `doctor-agent.py` reports the installation as unhealthy.
- Reinstall with `--force` and confirm health returns.

## Interrupt Test

- Simulate partial or broken installations by removing expected files.
- Confirm doctor and reinstall flows can detect and recover from the interruption.

## Concurrency Test

- Install to independent destinations in parallel.
- Confirm both installations complete successfully and generate valid manifests.
