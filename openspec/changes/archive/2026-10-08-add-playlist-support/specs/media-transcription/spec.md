# Spec Delta

## MODIFIED Requirements

### Requirement: Accepting sources
The system SHALL accept one or more sources in a single run, each of which is a link to media, a link to a playlist, a path to a media file or a path to a directory.

#### Scenario: Link
- **WHEN** the user passes an `http(s)://...` link to a video or audio
- **THEN** the system creates one transcript for that media

#### Scenario: Playlist link
- **WHEN** the user passes an `http(s)://...` link to a playlist
- **THEN** the system creates one transcript for each video of the playlist

#### Scenario: Local file
- **WHEN** the user passes a path to an existing video or audio file
- **THEN** the system creates one transcript for that file

#### Scenario: Directory
- **WHEN** the user passes a path to a directory that contains media files and files of other types
- **THEN** the system creates one transcript for each video and audio file directly inside that directory
- **AND** does not process files of other types or the contents of nested directories

#### Scenario: Several sources
- **WHEN** the user passes a link and a file path in one run
- **THEN** the system processes both sources and creates a transcript for each

#### Scenario: Unrecognised source
- **WHEN** the user passes a path that does not exist, or a directory without media files
- **THEN** the system reports that source as failed and states the reason

## ADDED Requirements

### Requirement: Playlist expansion
The system SHALL process the videos of a playlist in playlist order, treating each video as a separate source in the summary, and SHALL expand a link into a playlist only when the link points to the playlist itself.

#### Scenario: Videos processed in order
- **WHEN** the user passes a link to a playlist of three videos
- **THEN** the videos are processed from the first to the third
- **AND** the summary lists each video separately

#### Scenario: Video opened inside a playlist
- **WHEN** the user passes a link to a single video that also carries a playlist identifier (`watch?v=...&list=...`)
- **THEN** the system creates one transcript for that video only

#### Scenario: Unavailable video in a playlist
- **WHEN** the second of three playlist videos is private or deleted
- **THEN** transcripts are created for the first and the third
- **AND** the second is marked as failed with the reason
- **AND** the exit code is non-zero

#### Scenario: Empty playlist
- **WHEN** the playlist behind the link has no videos
- **THEN** the playlist link is marked as failed with the reason "playlist is empty"

#### Scenario: Channel link
- **WHEN** the user passes a link to a channel
- **THEN** the link is marked as failed with a reason that tells the user to pass a link to a playlist
- **AND** none of the channel's videos are processed

#### Scenario: Nested playlist
- **WHEN** an entry of the playlist is itself a playlist
- **THEN** that entry is marked as failed with a reason that tells the user to pass a link to a playlist
- **AND** its videos are not processed

#### Scenario: Progress for a playlist
- **WHEN** processing of a playlist starts
- **THEN** the user sees the playlist title and the number of videos before the first video is processed

### Requirement: Playlist output layout
The system SHALL save the transcripts of a playlist into a subdirectory of the output directory whose name is derived from the playlist title and identifier, and SHALL start each transcript file name with the position of the video in the playlist, zero-padded so that files sort in playlist order.

#### Scenario: Playlist subdirectory
- **WHEN** the user passes a link to a playlist without setting `--out`
- **THEN** the transcripts appear in `./transcripts/<playlist name>/` and not directly in `./transcripts/`

#### Scenario: Numbered files
- **WHEN** the playlist has three videos
- **THEN** the transcript file names start with `01-`, `02-` and `03-` followed by the name the video would get as a single link

#### Scenario: Long playlist
- **WHEN** the playlist has 120 videos
- **THEN** the positions are written with three digits, from `001-` to `120-`

#### Scenario: Two playlists with the same title
- **WHEN** two different playlists have the same title
- **THEN** their transcripts are saved into two different subdirectories

### Requirement: Repeated runs over a playlist
The system SHALL treat a playlist video as already transcribed when the playlist subdirectory contains a transcript of that video at any position, unless the user asked to recreate it.

#### Scenario: Resuming a playlist
- **WHEN** the user runs processing of the same playlist again after some of its videos failed
- **THEN** the videos transcribed earlier are marked as skipped without being downloaded or recognised
- **AND** only the remaining videos are processed

#### Scenario: Video moved within the playlist
- **WHEN** a transcribed video now stands at another position because the playlist was reordered or a video was inserted before it
- **THEN** the existing transcript is kept under its old name, no second transcript of that video is created and the video is marked as skipped

#### Scenario: Forced recreation of a playlist
- **WHEN** the user runs processing of the playlist again with the `--force` flag
- **THEN** every transcript of the playlist is created anew
