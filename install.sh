#!/usr/bin/env bash
# Installs huginn: system dependencies, the command itself and PATH.
# Safe to re-run: steps that are already done are skipped.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.12"
PATH_MARKER="# huginn: uv tool bin directory"

say() { printf '%s\n' "$*"; }
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }

check_platform() {
    if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
        fail "huginn works only on a Mac with Apple Silicon (detected: $(uname -s) $(uname -m))"
    fi
}

install_dependencies() {
    local missing=()
    local tool
    for tool in uv ffmpeg; do
        if command -v "$tool" >/dev/null 2>&1; then
            say "✓ $tool is already installed"
        else
            missing+=("$tool")
        fi
    done
    if [ "${#missing[@]}" -eq 0 ]; then
        return
    fi
    if ! command -v brew >/dev/null 2>&1; then
        fail "Homebrew not found — it is needed to install: ${missing[*]}. Install it from https://brew.sh and run the installer again"
    fi
    say "→ brew install ${missing[*]}"
    brew install "${missing[@]}"
}

install_command() {
    say "→ installing the huginn command"
    UV_PYTHON_PREFERENCE=only-managed \
        uv tool install --editable "$REPO_DIR" --python "$PYTHON_VERSION" --force
}

shell_rc_file() {
    case "$(basename "${SHELL:-}")" in
        zsh) printf '%s\n' "${ZDOTDIR:-$HOME}/.zshrc" ;;
        bash) printf '%s\n' "$HOME/.bash_profile" ;;
        *) printf '%s\n' "$HOME/.profile" ;;
    esac
}

ensure_path() {
    local bin_dir="$1"
    case ":$PATH:" in
        *":$bin_dir:"*)
            say "✓ $bin_dir is already on PATH"
            return
            ;;
    esac
    local rc
    rc="$(shell_rc_file)"
    if [ -f "$rc" ] && grep -qF "$PATH_MARKER" "$rc"; then
        say "✓ PATH is already set in $rc"
    else
        printf '\n%s\nexport PATH="%s:$PATH"\n' "$PATH_MARKER" "$bin_dir" >>"$rc"
        say "→ PATH added to $rc"
    fi
    say "  Open a new terminal or run: source $rc"
}

main() {
    check_platform
    install_dependencies
    install_command

    local bin_dir
    # Colour is disabled explicitly: with FORCE_COLOR uv colourises the path even in command substitution.
    bin_dir="$(uv tool dir --bin --color never)"
    ensure_path "$bin_dir"

    if ! "$bin_dir/huginn" --help >/dev/null 2>&1; then
        fail "the command $bin_dir/huginn does not run after installation"
    fi
    say "Done. Check: huginn --help"
}

main "$@"
