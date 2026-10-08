# Tasks

## 1. Playlist detection

- [x] 1.1 Add `Entry` and `Playlist` to `fetch.py` and make `Fetcher.probe` return `Playlist` for `_type == "playlist"` using `extract_flat: "in_playlist"`; replace `test_probe_rejects_playlists` with tests that a playlist maps to id, title and ordered entries and that the probe options keep `noplaylist` — verify with `uv run pytest tests/test_fetch.py`

## 2. Naming

- [x] 2.1 Add the playlist directory name and the position-prefixed file name to `render.py` (width `max(2, digits of count)`), with tests for 3 and 120 videos and for two playlists with the same title — verify with `uv run pytest tests/test_render.py`

## 3. Pipeline

- [x] 3.1 Change `Pipeline.process` to return `list[Result]` and flatten in `cli.run`; update existing tests mechanically — verify with `uv run pytest` (all green, no behaviour change)
- [x] 3.2 Expand a playlist in `Pipeline`: log title and count, process entries in order into the playlist subdirectory with numbered names, isolate per-video failures; tests for order, layout, an unavailable middle video, an empty playlist and a nested playlist — verify with `uv run pytest tests/test_pipeline.py`
- [x] 3.3 Done-check by id inside the playlist directory: skip before probing when the entry has an id, keep the old file when the position changed, and with `--force` recreate and drop the file at the old position; tests for resume without probe, moved video and forced recreation — verify with `uv run pytest tests/test_pipeline.py`
- [x] 3.4 Add a CLI test that a playlist source yields one summary line per video and exit code 1 when one of them fails — verify with `uv run pytest tests/test_cli.py`

## 4. Documentation

- [x] 4.1 Update `README.md`: a playlist usage example, the output layout, the rule for `watch?v=...&list=...`, and replace the "Playlists and channels are not supported" note with "Channels are not supported" — verify the documented command against the behaviour in 5.1

## 5. Integration check

- [x] 5.1 Run `huginn` on a small real YouTube playlist into a temporary directory, then run it again: verify the subdirectory, numbered files, a second run that skips everything, and that a `watch?v=...&list=...` link gives one file in the top-level directory
