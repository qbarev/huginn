# Design

## Context

See proposal.md for motivation. Today `sources.resolve` turns every link into one `Item("url", ...)`, `Pipeline.process` returns exactly one `Result` per item, and `Fetcher.probe` raises `SourceError` when yt-dlp returns `_type == "playlist"`. All yt-dlp calls share `_QUIET`, which sets `noplaylist: True`. A transcript of a link is named by `render.output_name(title, id)` → `<title>-<id>.md`, and "already done" means that exact path exists.

## Goals / Non-Goals

**Goals:**
- One network request decides whether a link is a single media or a playlist; single links cost what they cost today.
- A playlist video goes through the existing `_url` path unchanged apart from where and under which name it is written.
- Resuming a playlist does not touch the network for videos that are already done.

**Non-Goals:**
- Recursing into nested playlists (channels).
- Detecting that a video was already transcribed outside its playlist directory.
- Renaming existing files when positions change.

## Decisions

### `Fetcher.probe` returns `MediaInfo | Playlist`
`probe` adds `extract_flat: "in_playlist"` to its options. For a single media yt-dlp still returns full metadata; for a playlist it returns the entries (id, url, title) without resolving each one. The result is mapped to a new frozen dataclass `Playlist(id, title, entries)` with `Entry(url, id)`.

Alternative considered: expanding playlists in `sources.resolve`. Rejected — `resolve` is pure and offline today, and a separate expansion call would double the requests for every single-video link.

`noplaylist: True` stays in `_QUIET`, so `watch?v=...&list=...` keeps resolving to the video.

### `Pipeline.process` returns `list[Result]`
A playlist yields one `Result` per video, so `process` returns a list and `cli.run` flattens it. For a playlist `process` logs the title and the number of videos, then calls `_url(entry.url, ...)` for each entry inside the same error isolation that `process` gives a single source today, so one failed video does not stop the rest. `Result.source` is the video URL.

An entry whose probe returns a `Playlist` again is not expanded: it fails with "nested playlists and channels are not supported, pass a link to a playlist". An empty `entries` list fails the playlist link with "playlist is empty".

### Channels are rejected by metadata
A live check showed that yt-dlp resolves a YouTube channel link to a flat list of all its videos (924 for one channel), not to nested playlists, so the nested-playlist rule does not catch it. `probe` therefore rejects a playlist whose `id` equals its `channel_id` with "channels are not supported, pass a link to a playlist". A playlist owned by a channel has a different id and is accepted, as is the channel's uploads playlist when its playlist link is passed explicitly.

Alternative considered: matching channel URL shapes (`/@name`, `/channel/...`). Rejected — platform-specific and incomplete.

### Placement and naming
`_url` gains an optional placement: the directory `out / <playlist name>` and the position. The playlist name reuses the title/id sanitising of `output_name` without the `.md` suffix. The file name is `<NN>-<output_name(title, id)>`, where the width is `max(2, len(str(count)))`.

### Done-check by id
Inside a playlist directory a video is done when any file matching `*-<safe id>.md` exists. When the flat entry carries an id (YouTube always does), the check runs before the video is probed, so a resumed run makes no request for finished videos; otherwise it runs after the probe using `MediaInfo.id`. With `--force` the matching file is overwritten in place when the position is unchanged; a file left at an old position is removed so that one video keeps one transcript.

Alternative considered: exact-path match as for single links. Rejected — inserting a video at the start of a course would re-recognise every later video.

## Risks / Trade-offs

- [The suffix match `*-<id>.md` can match another video whose id ends with `-<id>`] → Ids of one platform have a fixed shape (YouTube: 11 characters), so within one playlist this does not occur in practice; accepted.
- [Positions in file names go stale after a reorder] → Accepted; the transcript header still links to the video, and `--force` renumbers.
- [A flat entry of another platform may lack an id] → The done-check falls back to after the probe; one extra request per video.
- [`process` changing its return type touches every existing pipeline test] → Mechanical update, done in the same task as the signature change.
