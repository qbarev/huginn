# Tasks

All groups with code are done through TDD: first a failing test, then a minimal implementation. Tests do not access the network and do not load the model.

## 1. Environment and scaffold

- [x] 1.1 Install `uv` and `ffmpeg` via Homebrew; verify: `uv --version` and `ffmpeg -version` run without errors
- [x] 1.2 Create a `uv` project on Python 3.12 with the `src/huginn/` layout, the `huginn` entry point, the dependencies `mlx-whisper`, `yt-dlp` and the dev dependency `pytest`; verify: `uv run huginn --help` prints the help, `uv run pytest` finishes without build errors
- [x] 1.3 Add `.gitignore` (`.venv/`, `transcripts/`, Python caches); verify: `git status` does not show these paths

## 2. Whisper speed measurement

- [x] 2.1 Run `mlx-whisper` with `large-v3-turbo` on a real recording about an hour long in Russian; verify: the exact model repository name, the recording duration and the recognition time are recorded
- [x] 2.2 Compare the result with the threshold from design.md (decision 9): an hour of recording takes no longer than 12 minutes; verify: if the threshold is exceeded, work is stopped and the question about the default model is put to the user, otherwise the measurement result is entered into design.md
- [x] 2.3 Clarify the repository names for `large-v3` and `small`; verify: each of the models loads and recognizes a short fragment

## 3. Source parsing (`sources`)

- [x] 3.1 Implement classification of an argument as a link, a file or a directory, and expansion of a directory into a list of media files by extension without nested folders; verify: the tests for a link, a file, a directory with mixed contents and a nested folder pass
- [x] 3.2 Implement errors for a nonexistent path and a directory without media files; verify: the tests confirm that the source is returned as failed with a reason, and the other sources are parsed

## 4. Render (`render`)

- [x] 4.1 Implement joining segments into paragraphs by a pause of 2 seconds or more and a limit of 60 seconds; verify: the tests for a pause, for continuous speech without pauses and for an empty list of segments pass
- [x] 4.2 Implement the timecode formats `[MM:SS]` and `[H:MM:SS]` and a clickable timecode for YouTube links; verify: the tests for both formats, a YouTube link, a link from another platform and a local file pass
- [x] 4.3 Implement Markdown assembly: the title, the header (source, duration, language, method of obtaining), the paragraphs; verify: the tests compare the final text with a reference for subtitles and for recognition
- [x] 4.4 Implement the output file name for a local file and for a link (the title in a safe form plus the identifier); verify: the tests for Cyrillic, special characters and two media with the same title pass

## 5. Subtitles (`subtitles`)

- [x] 5.1 Implement parsing VTT into segments with timing and style tags stripped; verify: the tests on saved samples of authored subtitles pass
- [x] 5.2 Implement removal of the scrolling repeats of automatic subtitles; verify: the test on a saved sample of YouTube automatic subtitles confirms that each phrase occurs once
- [x] 5.3 Implement track selection by the rules of design.md (decision 4); verify: the tests for authored and automatic tracks, `--lang`, an unknown language with one authored track and the absence of suitable tracks pass

## 6. Network and recognition (`fetch`, `transcriber`)

- [x] 6.1 Implement a wrapper around `yt-dlp`: metadata (title, identifier, duration, language, list of tracks), downloading the selected subtitle track, downloading the audio track into a temporary directory; verify: the tests with a substituted `yt-dlp` confirm the call parameters and the conversion of the response, `yt-dlp` errors turn into a source error with a reason
- [x] 6.2 Describe the transcriber protocol and the `mlx-whisper` implementation with a lazy import and mapping of short model names; verify: the name mapping test passes, `uv run huginn --help` does not load `mlx`
- [x] 6.3 Implement the check for the presence of `ffmpeg` with a message about installing it; verify: the test with a substituted program lookup confirms the message text

## 7. Pipeline and CLI (`pipeline`, `cli`)

- [x] 7.1 Implement processing of a single item: subtitles for a link, otherwise recognition; `--whisper` forces recognition; verify: the tests with stubs for `fetch` and the transcriber cover all the scenarios of the requirements "Existing subtitles for links" and "Local speech recognition"
- [x] 7.2 Implement skipping of finished transcripts and `--force`, writing to `./transcripts` or `--out`, deletion of the temporary audio; verify: the tests confirm that on a skip the transcriber is not called, and that the temporary files are deleted on an error too
- [x] 7.3 Implement handling of an empty recognition result as the error "no speech found"; verify: the test confirms that the file is not created
- [x] 7.4 Implement the CLI: the arguments `--out`, `--whisper`, `--model`, `--lang`, `--force`, progress to stderr, the final summary and the exit code; verify: the tests confirm that the failure of one source does not interrupt the others, the summary lists the created, skipped and failed ones, the exit code is 1 on a failure and 0 otherwise
- [x] 7.5 Write the README: installation (`brew`, `uv`), usage examples, flags, the model download on the first run, updating `yt-dlp`; verify: the commands from the README run as written

## 8. End-to-end verification

- [x] 8.1 Run `huginn` on a YouTube link with Russian automatic subtitles; verify: the transcript is created in seconds, the header and the clickable timecodes are correct, there are no repeats
- [x] 8.2 Run `huginn --whisper` on the same link and on a directory with local video and audio; verify: the transcripts are created by recognition, the running time matches the measurement from group 2
- [x] 8.3 Run a batch of a working link, an unavailable link and an already processed file; verify: the summary and the exit code match the requirements "Batch resilience" and "Repeated runs"
- [x] 8.4 Run `openspec validate add-media-transcription --strict`; verify: the validation passes without errors
