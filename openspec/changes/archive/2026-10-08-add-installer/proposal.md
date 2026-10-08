# Proposal

## Why

To start using `huginn`, you currently have to install `uv` and `ffmpeg` by hand, know the `uv tool install` command with the right flags, and check `PATH`. A single step is needed after which the `huginn` command works from any directory.

## What Changes

- An `install.sh` script appears in the repository root: it checks the platform, installs the missing `uv` and `ffmpeg` via Homebrew, installs the `huginn` command, adds the command's directory to `PATH` if necessary, and checks that the command runs.
- The README describes installation via this script and running without `uv run`.

Out of scope: installing Homebrew itself, uninstalling `huginn`, support for platforms other than a Mac with Apple Silicon.

## Capabilities

### New Capabilities
- `installation`: installing `huginn` and its dependencies on the user's machine with a single command — platform check, dependencies, the command, `PATH`, verification of the result.

### Modified Capabilities

None.

## Impact

- New files `install.sh` and `tests/test_install.py`; edits to the README.
- The script calls `brew` and `uv` and may append a line to the user's shell config (`~/.zshrc`, `~/.bash_profile` or `~/.profile`).
