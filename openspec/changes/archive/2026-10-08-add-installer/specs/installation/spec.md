# Spec Delta

## Purpose

Installs `huginn` and its dependencies with a single command so that the `huginn` command is available from any directory.

## ADDED Requirements

### Requirement: Platform check
The installer SHALL work only on a Mac with Apple Silicon and SHALL exit with an error on other platforms without installing anything.

#### Scenario: Unsupported platform
- **WHEN** the installer is run on Linux or on a Mac with an Intel processor
- **THEN** it reports that only a Mac with Apple Silicon is supported, exits with a non-zero code and installs nothing

### Requirement: Installing system dependencies
The installer SHALL use Homebrew to install those of the dependencies `uv` and `ffmpeg` that are missing on the machine and SHALL NOT reinstall the ones already present.

#### Scenario: No dependencies
- **WHEN** the machine has neither `uv` nor `ffmpeg`
- **THEN** the installer installs both with Homebrew

#### Scenario: Some dependencies already present
- **WHEN** `uv` is installed and `ffmpeg` is not
- **THEN** the installer installs only `ffmpeg`

#### Scenario: All dependencies already present
- **WHEN** `uv` and `ffmpeg` are installed
- **THEN** the installer does not call Homebrew

#### Scenario: No Homebrew
- **WHEN** dependencies are missing and Homebrew is not installed
- **THEN** the installer reports that Homebrew is needed and where to get it, exits with a non-zero code and does not change the shell config

### Requirement: Installing the command
The installer SHALL install the `huginn` command from the repository directory in which it is located and SHALL verify that the installed command runs.

#### Scenario: Successful install
- **WHEN** the dependencies are in place
- **THEN** the `huginn` command is installed from this repository and the installer exits with a zero code

#### Scenario: Command does not run
- **WHEN** the `huginn` command does not run after installation
- **THEN** the installer reports it and exits with a non-zero code

### Requirement: PATH setup
When the directory of the installed command is not on `PATH`, the installer SHALL append it to the user's shell config without changing the rest of the file, and SHALL NOT change the config when the directory is already on `PATH`.

#### Scenario: Directory not on PATH
- **WHEN** the user's shell is zsh and the command directory is not on `PATH`
- **THEN** a line is appended to `.zshrc` after which `huginn` is found in a new shell session
- **AND** the previous contents of the file are preserved
- **AND** the installer says how to apply the change

#### Scenario: Directory already on PATH
- **WHEN** the command directory is already on `PATH`
- **THEN** the shell config is not changed

#### Scenario: Another shell
- **WHEN** the user's shell is bash
- **THEN** the line is appended to `.bash_profile`

#### Scenario: Colourised tool output
- **WHEN** coloured output is forced in the environment
- **THEN** the line in the shell config contains only the path, without control sequences

### Requirement: Safe re-run
Running the installer again SHALL succeed and SHALL NOT duplicate entries in the shell config.

#### Scenario: Second run
- **WHEN** the installer is run a second time in a row
- **THEN** it exits with a zero code and the shell config still has one `PATH` entry
