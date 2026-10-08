#!/usr/bin/env bash
# Installs huginn: system dependencies, the command itself and PATH.
# Safe to re-run: steps that are already done are skipped.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.12"
PATH_MARKER="# huginn: uv tool bin directory"

say() { printf '%s\n' "$*"; }
fail() { printf 'Ошибка: %s\n' "$*" >&2; exit 1; }

check_platform() {
    if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
        fail "huginn работает только на Mac с Apple Silicon (обнаружено: $(uname -s) $(uname -m))"
    fi
}

install_dependencies() {
    local missing=()
    local tool
    for tool in uv ffmpeg; do
        if command -v "$tool" >/dev/null 2>&1; then
            say "✓ $tool уже установлен"
        else
            missing+=("$tool")
        fi
    done
    if [ "${#missing[@]}" -eq 0 ]; then
        return
    fi
    if ! command -v brew >/dev/null 2>&1; then
        fail "не найден Homebrew — он нужен для установки: ${missing[*]}. Установите его с https://brew.sh и запустите установщик снова"
    fi
    say "→ brew install ${missing[*]}"
    brew install "${missing[@]}"
}

install_command() {
    say "→ установка команды huginn"
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
            say "✓ $bin_dir уже в PATH"
            return
            ;;
    esac
    local rc
    rc="$(shell_rc_file)"
    if [ -f "$rc" ] && grep -qF "$PATH_MARKER" "$rc"; then
        say "✓ PATH уже прописан в $rc"
    else
        printf '\n%s\nexport PATH="%s:$PATH"\n' "$PATH_MARKER" "$bin_dir" >>"$rc"
        say "→ PATH прописан в $rc"
    fi
    say "  Откройте новый терминал или выполните: source $rc"
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
        fail "команда $bin_dir/huginn не запускается после установки"
    fi
    say "Готово. Проверка: huginn --help"
}

main "$@"
