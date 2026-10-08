# Proposal

## Why

To find out whether an hour-long video is worth watching, you currently have to watch it. A quick screening is needed: get the video's text in seconds or minutes, read it, and decide whether to spend time watching. The tool is useless if preparing the text takes about as long as the video itself.

## What Changes

- A `huginn` CLI appears that accepts one or more sources: a link to a video or audio, a path to a media file, a path to a directory with media files.
- For links, ready-made platform subtitles are taken first (seconds). If there are none or the `--whisper` flag is set, the audio track is downloaded and recognized locally by the Whisper model.
- Local files are always recognized locally by the Whisper model.
- One Markdown file for human reading is created per media file: a header (title, source, duration, language, method of obtaining) and the text in paragraphs with timecodes.
- Batch processing survives the failure of an individual item, skips transcripts that are already done, and finishes with a summary.

Out of scope: whole playlists and channels, speaker separation, summaries and a "watch or not" verdict, translation, cloud recognition APIs, machine-readable output (JSON, SRT).

## Capabilities

### New Capabilities
- `media-transcription`: turning links and local media files into human-readable text transcripts — input parsing, choosing how the text is obtained, the result format, behavior on errors and on repeated runs.

### Modified Capabilities

None — the project is created from scratch.

## Impact

- A new Python package `huginn` (Python 3.12, managed by `uv`) with a `huginn` console command.
- Package dependencies: `mlx-whisper` (works only on Apple Silicon), `yt-dlp`.
- System dependencies that are currently missing on the machine: `uv`, `ffmpeg` (installed via Homebrew).
- On the first Whisper run the model is downloaded (about 1.5 GB for `large-v3-turbo`) into the Hugging Face cache.
- Network requests to video platforms via `yt-dlp`; when platforms change on their side, `yt-dlp` will need to be updated.
