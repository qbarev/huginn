# Design

## Context

See `proposal.md`. The command is installed via `uv tool install`; the directory of its executables is reported by `uv tool dir --bin`.

## Goals / Non-Goals

**Goals:**
- The script is fully verified by tests without a real installation.

**Non-Goals:**
- Installing Homebrew: it is interactive and requires administrator rights.

## Decisions

### 1. A Bash script in the repository root

The installer must work before the project's Python environment exists, so it is `install.sh` in bash, compatible with the system bash 3.2 from macOS.

### 2. An editable install on a managed Python

`uv tool install --editable <repository> --python 3.12 --force` with `UV_PYTHON_PREFERENCE=only-managed`: changes to the code are picked up without reinstalling, and `uv` cannot run the system Python 3.9 on the target machine.

### 3. PATH is set up by the script itself

The config is chosen by `$SHELL`: zsh — `${ZDOTDIR:-$HOME}/.zshrc`, bash — `~/.bash_profile`, otherwise `~/.profile`. The line is accompanied by a marker comment, which is used to determine that it has already been appended.

The alternative is `uv tool update-shell`: it does the same, but its behavior cannot be checked deterministically in tests. Rejected.

### 4. Color in `uv` output is disabled explicitly

The path is requested as `uv tool dir --bin --color never`. With `FORCE_COLOR` in the environment, `uv` colors the path even in a command substitution; on the first real run this led to control sequences being written to `~/.zshrc`.

### 5. Tests in a sandbox with stubs

`pytest` runs the script with a `PATH` made of the stub directory and `/usr/bin:/bin`, a temporary `HOME` and fake `brew`, `uv`, `uname` that log their calls. The `uv` stub colors the path the same way the real one does until color is disabled.

## Risks / Trade-offs

- [The stubs diverge from the behavior of the real tools] → the script is additionally run on a real machine; the divergence that was found (color) has been carried over into the stub.
- [The script modifies the user's shell config] → it only appends to the end, only when the directory is not in `PATH`, and reports it.
