# Proposal

## Why

A course or a lecture series is published as a playlist, and screening it today means copying every video link by hand: a playlist link is rejected with "playlists and channels are not supported". The batch machinery (per-source failures, skipping finished transcripts, the summary) already exists, so a playlist only has to be expanded into its videos.

## What Changes

- A link to a playlist is accepted as a source and produces one transcript per video, in playlist order.
- Transcripts of a playlist go into their own subdirectory of the output directory, named after the playlist, and each file name starts with the position of the video in the playlist.
- A repeated run recognises an already transcribed playlist video by its identity, not by its position, so a failed run can be resumed and a reordered playlist is not transcribed again.
- An unavailable video in a playlist is reported as a failed source; the rest of the playlist is still processed.
- A link to a video opened inside a playlist (`watch?v=...&list=...`) keeps producing a single transcript.
- The README note "Playlists and channels are not supported" is replaced with usage documentation.

Out of scope: channels, limiting the number of videos, an index file for the playlist, sharing transcripts between a playlist directory and the top-level output directory.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `media-transcription`: playlist links become an accepted source; new requirements cover playlist expansion, the playlist output layout and repeated runs over a playlist.

## Impact

- Code: `src/huginn/fetch.py` (playlist detection), `src/huginn/pipeline.py` (expansion, per-video processing, done-check), `src/huginn/render.py` (numbered file name), `src/huginn/cli.py` (several results per source).
- Tests: `tests/test_fetch.py`, `tests/test_pipeline.py`, `tests/test_render.py`, `tests/test_cli.py`.
- Docs: `README.md`.
- No new dependencies; `yt-dlp` already returns playlist entries.
