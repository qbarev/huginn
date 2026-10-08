# huginn

Fast text transcripts of video and audio: read one in a couple of minutes and decide whether the whole thing is worth watching.

- For links, the platform's existing subtitles are used first — that takes seconds.
- When there are no subtitles, or you want clean text, speech is recognised locally with a Whisper model.
- The result is one Markdown file per media: a header and the text in paragraphs with timecodes.

Works only on a Mac with Apple Silicon.

## Installation

```sh
./install.sh
```

The installer uses Homebrew to install `uv` and `ffmpeg` if they are missing, installs the `huginn` command and, when its directory is not on `PATH`, adds it to your shell config (`~/.zshrc`, `~/.bash_profile` or `~/.profile`). It does not install Homebrew itself. Running it again is safe.

After that the `huginn` command is available from any directory. The install is editable: changes to the project code take effect without reinstalling.

`ffmpeg` is needed only for speech recognition; transcripts built from subtitles work without it.

## Usage

```sh
huginn "https://www.youtube.com/watch?v=..."      # subtitles if available, otherwise Whisper
huginn --whisper "https://www.youtube.com/watch?v=..."   # always Whisper
huginn lecture.mp4 ~/Recordings                   # a file and every media file in a directory
```

You can pass several sources at once. From a directory only top-level media files are taken.

| Flag | What it does |
|---|---|
| `--out DIR` | Where to save transcripts. Defaults to `./transcripts`. |
| `--whisper` | Recognise speech even when the link has subtitles. |
| `--model NAME` | Whisper model: `turbo` (default), `large-v3`, `small` or a Hugging Face repository name. |
| `--lang CODE` | Language of the media (`ru`, `en`). Detected automatically by default. |
| `--force` | Recreate a transcript that already exists. |

Progress is printed to stderr, the final summary to stdout. If at least one source fails the exit code is 1; the other sources are still processed.

## Good to know

- **Automatic subtitles** on YouTube in Russian come without punctuation or capital letters. They are enough to understand the content; use `--whisper` for clean text.
- **Speed**: on an M1 with 16 GB, a 58-minute recording takes about 3 seconds through subtitles and about 6.5 minutes through Whisper `turbo`.
- **The first recognition run** downloads the model (about 1.5 GB for `turbo`) into the Hugging Face cache.
- **Subtitles are skipped** when the platform does not report the media language and there are several authored tracks; pass `--lang` to pick one.
- **Clickable timecodes** are produced only for YouTube.
- **Playlists and channels** are not supported — pass links to individual videos.
- **If links stop working**, update `yt-dlp`: `uv lock --upgrade-package yt-dlp && ./install.sh`.

## Development

```sh
uv run pytest
```

Specifications and the history of changes live in `openspec/`.
