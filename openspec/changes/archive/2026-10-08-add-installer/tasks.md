# Tasks

## 1. Installer

- [x] 1.1 Write `install.sh`: platform check, dependencies via Homebrew, installing the command, PATH, checking that it runs; verify: the `tests/test_install.py` tests for every scenario of the specification pass
- [x] 1.2 Disable color in `uv` output when requesting the command directory; verify: the test with a coloring `uv` stub passes, and fails without the fix
- [x] 1.3 Update the README: installation via `./install.sh`, running without `uv run`; verify: the commands from the README run as written

## 2. End-to-end verification

- [x] 2.1 Run `./install.sh` on a real machine twice; verify: both runs finish with exit code 0, `huginn --help` works from another directory, the shell config is not modified
- [x] 2.2 Run `openspec validate add-installer --strict`; verify: the validation passes
