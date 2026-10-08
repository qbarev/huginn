# Spec Delta

## Purpose

Turns links to video and audio and local media files into text transcripts that are comfortable for a person to read, fast enough to decide from the text whether the original is worth watching.

## ADDED Requirements

### Requirement: Accepting sources
The system SHALL accept one or more sources in a single run, each of which is a link to media, a path to a media file or a path to a directory.

#### Scenario: Link
- **WHEN** the user passes an `http(s)://...` link to a video or audio
- **THEN** the system creates one transcript for that media

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

### Requirement: Existing subtitles for links
For a link the system SHALL first use subtitles published on the platform in the original language of the media, preferring authored subtitles over automatically generated ones, and SHALL NOT download the media or run speech recognition when such subtitles are obtained.

#### Scenario: Authored subtitles exist
- **WHEN** the video behind the link has both authored and automatic subtitles in the original language
- **THEN** the transcript is built from the authored subtitles without speech recognition

#### Scenario: Only automatic subtitles exist
- **WHEN** the video behind the link has only automatic subtitles in the original language
- **THEN** the transcript is built from the automatic subtitles without speech recognition

#### Scenario: Repeats in automatic subtitles
- **WHEN** the subtitle track contains lines repeated from cue to cue and service markup
- **THEN** every phrase appears once in the transcript and there is no markup

### Requirement: Local speech recognition
The system SHALL obtain the text by local speech recognition for local files, for links without suitable subtitles and for any source when the user explicitly demands recognition.

#### Scenario: Local file
- **WHEN** the source is a local video or audio file
- **THEN** the transcript is built by recognising its audio track

#### Scenario: Link has no subtitles
- **WHEN** the media behind the link has no subtitles in the original language
- **THEN** the system downloads the audio track and builds the transcript by recognition

#### Scenario: Forced recognition
- **WHEN** the user passes a link with the `--whisper` flag and the video has subtitles
- **THEN** the transcript is built by recognition and the subtitles are not used

#### Scenario: Choosing model and language
- **WHEN** the user sets `--model` and `--lang`
- **THEN** recognition runs with the given model, assuming the given language

#### Scenario: Language not set
- **WHEN** the user does not set `--lang`
- **THEN** the language of the speech is detected automatically

### Requirement: Transcript format
The system SHALL save each transcript as a separate Markdown file containing a heading with the media title, information about the source, duration, language and how the text was obtained, and the text split into paragraphs.

#### Scenario: Header of a transcript from subtitles
- **WHEN** the transcript is built from the platform's automatic subtitles
- **THEN** the file starts with the media title and contains the link to the source, the duration, the language and a note that the text comes from automatic subtitles

#### Scenario: Header of a transcript from recognition
- **WHEN** the transcript is built by speech recognition
- **THEN** the header states that the text was obtained by recognition and names the model used

#### Scenario: Text in paragraphs
- **WHEN** the original cues are short lines
- **THEN** in the transcript they are joined into paragraphs of several sentences, and long continuous speech is split into several paragraphs

### Requirement: Timecodes
Every paragraph of the transcript SHALL start with the timecode of the moment at which it is spoken in the media.

#### Scenario: Timecode format
- **WHEN** a paragraph starts at 2 minutes 35 seconds of media shorter than an hour
- **THEN** the paragraph starts with `[02:35]`

#### Scenario: Media longer than an hour
- **WHEN** a paragraph starts at 1 hour 2 minutes 14 seconds
- **THEN** the paragraph starts with `[1:02:14]`

#### Scenario: Clickable timecode
- **WHEN** the source is a YouTube link
- **THEN** the timecode is a link that opens the video at that moment

#### Scenario: Source without a link to a moment
- **WHEN** the source is a local file
- **THEN** the timecode is plain text

### Requirement: Output location
The system SHALL save transcripts into the `transcripts` directory of the current directory, or into the directory given by `--out`, under a name derived from the media title or the name of the source file.

#### Scenario: Default directory
- **WHEN** the user does not set `--out`
- **THEN** transcripts appear in `./transcripts/`, and the directory is created if missing

#### Scenario: Given directory
- **WHEN** the user sets `--out notes`
- **THEN** transcripts appear in `notes/`

#### Scenario: Different media with the same title
- **WHEN** two different media behind links have the same title
- **THEN** two different files are created and neither overwrites the other

### Requirement: Repeated runs
The system SHALL skip a source whose transcript already exists in the target directory unless the user asked to recreate it.

#### Scenario: Transcript already exists
- **WHEN** the user runs processing of the same source again
- **THEN** the existing file is not changed, recognition does not run and the source is marked as skipped in the summary

#### Scenario: Forced recreation
- **WHEN** the user runs processing again with the `--force` flag
- **THEN** the transcript is created anew and replaces the existing one

### Requirement: Batch resilience
A failure while processing one source SHALL NOT interrupt processing of the others; on completion the system SHALL print a summary of all sources and exit with a non-zero code if at least one source was not processed.

#### Scenario: One of several sources is unavailable
- **WHEN** a run has three sources and the second is unavailable
- **THEN** transcripts are created for the first and the third
- **AND** the summary names the created files and the failed source with the reason
- **AND** the exit code is non-zero

#### Scenario: All sources processed
- **WHEN** all sources are processed or skipped as already done
- **THEN** the exit code is zero

#### Scenario: No speech in the media
- **WHEN** recognition returned no text
- **THEN** no transcript file is created and the source is marked as failed with the reason "no speech found"

### Requirement: Clear messages about environment problems
When processing is impossible because a system dependency is missing, the system SHALL say what is missing and how to install it, without printing a stack trace.

#### Scenario: No ffmpeg
- **WHEN** a source needs speech recognition and `ffmpeg` is not installed
- **THEN** the system prints a message naming the missing program and the install command, and starts neither the download nor recognition

#### Scenario: ffmpeg not needed
- **WHEN** `ffmpeg` is not installed and the transcript of a link is built from subtitles
- **THEN** the transcript is created successfully

### Requirement: Showing progress
The system SHALL tell the user which source is being processed and by which method, without mixing these messages with the contents of transcripts.

#### Scenario: Long recognition
- **WHEN** recognition of a long media is started
- **THEN** before it starts the user sees which source is being processed, that the recognition path was chosen and which model is used
