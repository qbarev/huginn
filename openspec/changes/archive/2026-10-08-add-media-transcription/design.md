# Design

## Context

The project is created from scratch: the repository contains only the OpenSpec scaffold. The motivation is in `proposal.md`, the requirements are in `specs/media-transcription/spec.md`.

Constraints that shape the approach:

- The target machine is an Apple M1, 16 GB, macOS. Other platforms are not required.
- The main requirement is speed: the text must appear much faster than the media lasts.
- The material is Russian and English, from short clips to recordings of 1–3 hours.
- The machine has Node 22, Homebrew and the system Python 3.9.6; it has no `uv`, `ffmpeg`, `yt-dlp` or Whisper.

## Goals / Non-Goals

**Goals:**

- For links with subtitles — a result in seconds, without downloading the media.
- For everything else — local recognition several times faster than real time.
- Every module is tested without the network and without the model.
- The recognition engine is replaceable without changes to the rest of the code.

**Non-Goals:**

- Portability to Linux, Windows and Intel Macs.
- Parallel processing of several sources: recognition already occupies the whole GPU.
- A configuration file: all settings are command-line flags.

## Decisions

### 1. Two stages: platform subtitles, then Whisper

For a link, metadata and subtitles are requested first; recognition is started only if there are no subtitles or `--whisper` is set.

Why: no local engine can outrun ready-made text. This is the only way to screen an hour-long video in seconds.

The alternative is to always recognize: stable quality, but minutes of waiting for every video. Rejected as contradicting the goal; kept as an explicit choice via `--whisper`.

### 2. Recognition engine — `mlx-whisper`, model `large-v3-turbo`

Why: it computes on the Apple Silicon GPU via MLX, is called as a Python function and returns segments with timecodes. `large-v3-turbo` gives acceptable Russian at a speed noticeably higher than `large-v3`.

Alternatives:

- `openai/whisper` (PyTorch) — the reference, but on an M1 it computes on the CPU, at a speed of about real time. Rejected.
- `whisper.cpp` — comparable speed via Metal, but it is an external binary: a separate installation, separate model downloads, parsing its output. Rejected for the sake of simplicity.
- `faster-whisper` — CPU only on a Mac. Rejected.

The `--model` flag accepts the short names `turbo` (the default), `large-v3`, `small` and maps them to `mlx-community` repositories on Hugging Face; any other value is passed through unchanged as a repository name.

### 3. The transcriber behind a narrow interface

The rest of the code knows only the protocol: "path to audio, language or `None` → language and a list of segments (`start`, `end`, `text`)". The `mlx-whisper` implementation is the only one and is imported lazily.

Why: tests substitute a stub and do not need the model; if the hardware changes, a second backend is added with a single file. Subtitles are converted to the same list of segments, so there is one renderer for both stages.

### 4. Subtitles — the VTT format with custom cleanup

Subtitles are requested via `yt-dlp` in the VTT format and parsed by a custom parser: timing and style tags are stripped, and the "scrolling" line repeats typical of YouTube automatic subtitles are removed.

The alternative is YouTube's `json3` format: cleaner, but specific to one platform. Rejected: VTT is served by all the platforms that `yt-dlp` supports.

Track selection: the language is taken from `--lang`, otherwise from the language field in the metadata; among the tracks in that language, an authored one is preferred over an automatic one. If the language is unknown and there is exactly one authored track, that one is taken. Otherwise the link goes to the second stage.

### 5. `yt-dlp` as a library, `ffmpeg` as a system dependency

`yt-dlp` is included as a Python dependency and called via its API: metadata, subtitles and the audio track without processing (`bestaudio`, no re-encoding).

`ffmpeg` is needed only by `mlx-whisper` itself to decode audio, so there is no separate conversion step: a local file and a downloaded track are passed to the transcriber as is. The presence of `ffmpeg` is checked immediately before the first task that requires recognition — the subtitle path works without it too.

Downloaded audio is placed in a temporary directory and deleted after the source is processed.

### 6. Paragraphs and timecodes

Segments are joined into a paragraph until one of the conditions is met: the pause before the next segment is at least 2 seconds, or the paragraph has already lasted 60 seconds. The numbers are constants of the render module.

Why two conditions: automatic subtitles have almost no pauses, and without a duration limit there would be one paragraph for the whole video.

The timecode is `[MM:SS]`, and `[H:MM:SS]` for media of an hour or longer. It is made clickable only for YouTube (`&t=<seconds>s`): for other platforms there is no single way to link to a moment.

### 7. File names and skipping finished ones

- Local file: `<file name without extension>.md`.
- Link: `<title converted to a safe form>-<media identifier>.md`. The identifier rules out collisions between identical titles.

The "already done" check for a link requires a metadata request (a few seconds), but is performed before downloading and recognition.

### 8. Stack and layout

Python 3.12 managed by `uv`, the `src/huginn/` layout, the `huginn` entry point, argument parsing with `argparse` from the standard library, tests with `pytest`.

| Module | Responsibility | Depends on |
|---|---|---|
| `sources` | Arguments → a list of items (link or file) | the file system |
| `subtitles` | Track selection, VTT parsing and cleanup → segments | — (the network is in `fetch`) |
| `fetch` | A wrapper around `yt-dlp`: metadata, subtitles, audio | `yt-dlp` |
| `transcriber` | The protocol and the `mlx-whisper` implementation | `mlx-whisper` |
| `render` | Segments → paragraphs → Markdown | — |
| `pipeline` | Processing a single item: stage selection, skipping, writing | everything above |
| `cli` | Arguments, progress to stderr, summary, exit code | `pipeline` |

Compared with the design agreed in chat, the `audio` module is replaced by `fetch`: audio conversion turned out not to be needed (decision 5), and all work with the network is gathered in one place, which is replaced in tests.

### 9. Speed measurement — as the first step

Before the pipeline is written, `mlx-whisper` with `large-v3-turbo` is measured on a real hour-long recording on this machine. The expectation is 5–10 minutes per hour, but that is an estimate, not a measurement.

Measurement result (Apple M1, 16 GB, a 58-minute recording in Russian, model `mlx-community/whisper-large-v3-turbo`): 6 minutes 34 seconds via `huginn --whisper` including the audio track download, that is, roughly 9 times faster than real time. The threshold is passed, the default model is `turbo`. The repository names `mlx-community/whisper-large-v3-mlx` and `mlx-community/whisper-small-mlx` were confirmed by downloading them and recognizing a one-minute fragment.

Threshold: if recognizing an hour takes more than 12 minutes (slower than 5× real time), work stops and the decision on the default model is made together with the user (`small` is faster but worse on Russian).

## Risks / Trade-offs

- [Automatic subtitles in Russian have no punctuation or capital letters] → paragraphs by duration make the text readable; the header states the origin of the text; `--whisper` gives tidy text.
- [Whisper speed on the M1 has not been measured] → a measurement as the first step with a stop threshold (decision 9).
- [Platforms change their protection, `yt-dlp` stops working] → a source error does not bring down the batch; the update is `uv lock --upgrade-package yt-dlp`, described in the README.
- [The media language is not specified in the metadata and no subtitles are selected] → the link goes to recognition; the user can set `--lang`.
- [The `mlx-community` model repository names may differ from the expected ones] → they are checked during the speed measurement before they get into the code.
- [The first recognition run downloads a model of about 1.5 GB] → a download message in the progress output; described in the README.
- [The tool works only on Apple Silicon] → accepted deliberately; the transcriber interface leaves a path to another backend.

## Open Questions

None.
