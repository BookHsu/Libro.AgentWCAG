#!/usr/bin/env node

const { existsSync } = require("node:fs");
const { join, resolve } = require("node:path");
const { spawnSync } = require("node:child_process");

const packageRoot = resolve(__dirname, "..");
const pythonScript = join(packageRoot, "scripts", "libro.py");

function resolvePythonCommand() {
  const candidates = process.platform === "win32"
    ? [
        { command: "python", args: [] },
        { command: "py", args: ["-3"] },
        { command: "py", args: ["-3.12"] }
      ]
    : [
        { command: "python3", args: [] },
        { command: "python", args: [] }
      ];

  for (const candidate of candidates) {
    const probe = spawnSync(candidate.command, [...candidate.args, "--version"], {
      encoding: "utf-8",
      shell: false
    });
    if (probe.status === 0) {
      return candidate;
    }
  }
  return null;
}

function main() {
  if (!existsSync(pythonScript)) {
    console.error(`Missing bundled CLI entrypoint: ${pythonScript}`);
    process.exit(1);
  }

  const python = resolvePythonCommand();
  if (!python) {
    console.error("Python 3.12+ is required. Install Python and ensure `python` or `py` is in PATH.");
    process.exit(1);
  }

  const result = spawnSync(
    python.command,
    [...python.args, pythonScript, ...process.argv.slice(2)],
    {
      stdio: "inherit",
      shell: false,
      cwd: process.cwd(),
      env: process.env
    }
  );

  if (typeof result.status === "number") {
    process.exit(result.status);
  }
  console.error(`Failed to launch ${python.command}.`);
  process.exit(1);
}

main();
