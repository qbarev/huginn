"""Tests for install.sh: the script runs in a sandbox with stub brew, uv and uname."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
INSTALLER = REPO / "install.sh"

UNAME = """#!/bin/sh
case "$1" in
    -s) echo "$FAKE_OS" ;;
    -m) echo "$FAKE_ARCH" ;;
esac
"""

# The stub brew "installs" a tool by creating its stub in the same directory.
BREW = """#!/bin/sh
echo "brew $*" >> "$CALLS"
shift
for tool in "$@"; do
    if [ "$tool" = uv ]; then
        cp "$STUBS/uv.template" "$STUBS/uv"
    else
        printf '#!/bin/sh\\n' > "$STUBS/$tool"
    fi
    chmod +x "$STUBS/$tool"
done
"""

UV = """#!/bin/sh
echo "uv $* [UV_PYTHON_PREFERENCE=$UV_PYTHON_PREFERENCE]" >> "$CALLS"
if [ "$1 $2" = "tool dir" ]; then
    # Like real uv under FORCE_COLOR: the path is colourised unless colour is disabled explicitly.
    case "$*" in
        *"--color never"*) echo "$TOOL_BIN" ;;
        *) printf '\\033[36m%s\\033[39m\\n' "$TOOL_BIN" ;;
    esac
elif [ "$1 $2" = "tool install" ]; then
    mkdir -p "$TOOL_BIN"
    printf '#!/bin/sh\\nexit %s\\n' "${HUGINN_EXIT:-0}" > "$TOOL_BIN/huginn"
    chmod +x "$TOOL_BIN/huginn"
fi
"""


@dataclass
class Sandbox:
    root: Path
    env: dict[str, str]

    @property
    def stubs(self) -> Path:
        return self.root / "stubs"

    @property
    def home(self) -> Path:
        return self.root / "home"

    @property
    def tool_bin(self) -> Path:
        return self.home / ".local" / "bin"

    def stub(self, name: str, body: str) -> None:
        path = self.stubs / name
        path.write_text(body)
        path.chmod(0o755)

    def have(self, *tools: str) -> None:
        for tool in tools:
            self.stub(tool, {"brew": BREW, "uv": UV}.get(tool, "#!/bin/sh\n"))

    def run(self, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", str(INSTALLER)], env={**self.env, **env}, capture_output=True, text=True
        )

    def calls(self) -> list[str]:
        log = self.root / "calls.log"
        return log.read_text().splitlines() if log.exists() else []


@pytest.fixture
def sandbox(tmp_path) -> Sandbox:
    box = Sandbox(tmp_path, {})
    box.stubs.mkdir()
    box.home.mkdir()
    box.env = {
        # Real brew, uv and ffmpeg live outside /usr/bin and /bin, so they never leak into the sandbox.
        "PATH": f"{box.stubs}:/usr/bin:/bin",
        "HOME": str(box.home),
        "SHELL": "/bin/zsh",
        "CALLS": str(tmp_path / "calls.log"),
        "STUBS": str(box.stubs),
        "TOOL_BIN": str(box.tool_bin),
        "FAKE_OS": "Darwin",
        "FAKE_ARCH": "arm64",
    }
    box.stub("uname", UNAME)
    (box.stubs / "uv.template").write_text(UV)
    return box


def test_installs_missing_dependencies_with_brew(sandbox):
    sandbox.have("brew")
    result = sandbox.run()
    assert result.returncode == 0, result.stderr
    assert sandbox.calls()[0] == "brew install uv ffmpeg"


def test_installs_only_what_is_missing(sandbox):
    sandbox.have("brew", "uv")
    result = sandbox.run()
    assert result.returncode == 0, result.stderr
    assert sandbox.calls()[0] == "brew install ffmpeg"
    assert "✓ uv уже установлен" in result.stdout


def test_skips_brew_when_dependencies_present(sandbox):
    sandbox.have("uv", "ffmpeg")
    result = sandbox.run()
    assert result.returncode == 0, result.stderr
    assert not any(call.startswith("brew") for call in sandbox.calls())


def test_fails_without_homebrew(sandbox):
    result = sandbox.run()
    assert result.returncode == 1
    assert "не найден Homebrew" in result.stderr and "https://brew.sh" in result.stderr
    assert sandbox.calls() == []
    assert not (sandbox.home / ".zshrc").exists()


@pytest.mark.parametrize("system, arch", [("Linux", "x86_64"), ("Darwin", "x86_64")])
def test_rejects_unsupported_platform(sandbox, system, arch):
    sandbox.have("brew", "uv", "ffmpeg")
    result = sandbox.run(FAKE_OS=system, FAKE_ARCH=arch)
    assert result.returncode == 1
    assert "только на Mac с Apple Silicon" in result.stderr
    assert sandbox.calls() == []


def test_installs_command_from_repository_with_managed_python(sandbox):
    sandbox.have("uv", "ffmpeg")
    sandbox.run()
    assert (
        f"uv tool install --editable {REPO} --python 3.12 --force [UV_PYTHON_PREFERENCE=only-managed]"
        in sandbox.calls()
    )


def test_adds_command_directory_to_zshrc(sandbox):
    sandbox.have("uv", "ffmpeg")
    (sandbox.home / ".zshrc").write_text("alias ll='ls -l'\n")
    result = sandbox.run()
    assert result.returncode == 0, result.stderr
    rc = (sandbox.home / ".zshrc").read_text()
    assert rc.startswith("alias ll='ls -l'\n")
    assert f'export PATH="{sandbox.tool_bin}:$PATH"' in rc
    assert f"source {sandbox.home}/.zshrc" in result.stdout


def test_path_line_makes_command_available_in_new_shell(sandbox):
    sandbox.have("uv", "ffmpeg")
    sandbox.run()
    found = subprocess.run(
        ["/bin/bash", "-c", f"source {sandbox.home}/.zshrc && command -v huginn"],
        env=sandbox.env, capture_output=True, text=True,
    )
    assert found.stdout.strip() == str(sandbox.tool_bin / "huginn")


def test_second_run_does_not_duplicate_path_line(sandbox):
    sandbox.have("uv", "ffmpeg")
    sandbox.run()
    result = sandbox.run()
    assert result.returncode == 0, result.stderr
    assert (sandbox.home / ".zshrc").read_text().count("export PATH=") == 1
    assert "PATH уже прописан" in result.stdout


def test_leaves_shell_config_alone_when_directory_already_in_path(sandbox):
    sandbox.have("uv", "ffmpeg")
    result = sandbox.run(PATH=f"{sandbox.tool_bin}:{sandbox.env['PATH']}")
    assert result.returncode == 0, result.stderr
    assert not (sandbox.home / ".zshrc").exists()
    assert "уже в PATH" in result.stdout


@pytest.mark.parametrize(
    "shell, rc_name", [("/bin/bash", ".bash_profile"), ("/usr/local/bin/fish", ".profile")]
)
def test_shell_config_depends_on_shell(sandbox, shell, rc_name):
    sandbox.have("uv", "ffmpeg")
    sandbox.run(SHELL=shell)
    assert "export PATH=" in (sandbox.home / rc_name).read_text()
    assert not (sandbox.home / ".zshrc").exists()


def test_zsh_respects_zdotdir(sandbox):
    sandbox.have("uv", "ffmpeg")
    zdotdir = sandbox.root / "zsh"
    zdotdir.mkdir()
    sandbox.run(ZDOTDIR=str(zdotdir))
    assert "export PATH=" in (zdotdir / ".zshrc").read_text()


def test_fails_when_installed_command_does_not_run(sandbox):
    sandbox.have("uv", "ffmpeg")
    result = sandbox.run(HUGINN_EXIT="1")
    assert result.returncode == 1
    assert "не запускается после установки" in result.stderr


def test_installer_is_executable():
    assert os.access(INSTALLER, os.X_OK)
