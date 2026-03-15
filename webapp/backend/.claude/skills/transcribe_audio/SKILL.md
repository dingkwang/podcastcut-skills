---
name: transcribe-audio
description: Transcribe an audio file using Gemini 3 Flash via OpenRouter. Returns speaker-diarized transcript with timestamps.
triggers:
  - "transcribe"
  - "转录"
  - "transcribe audio"
  - "speech to text"
---

# Transcribe Audio

Transcribe an audio file using Gemini 3 Flash, producing a JSON transcript with speaker diarization and timestamps.

## Prerequisites

- `OPENROUTER_API_KEY` environment variable set
- Audio file exists in the workspace (mp3, wav, m4a, etc.)

## Usage

```bash
python .claude/skills/transcribe_audio/transcribe.py <audio_file_path> [--speakers N]
```

### Arguments

- `audio_file_path` (required): Path to the audio file
- `--speakers N` (optional): Expected number of speakers (default: 2)

### Output

- Saves `transcript.json` in the same directory as the audio file
- Prints a summary with sentence count and speaker count

### Example

```bash
python .claude/skills/transcribe_audio/transcribe.py workspaces/abc123/upload.mp3 --speakers 2
```

## Output Format

The `transcript.json` file contains:
```json
{
  "sentences": [
    {"text": "说话内容", "start": 0.0, "end": 3.5, "spk": 0},
    {"text": "another sentence", "start": 3.5, "end": 7.2, "spk": 1}
  ]
}
```
