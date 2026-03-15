---
name: extract-samples
description: Extract voice samples for each speaker from audio using transcript timestamps. Uses FFmpeg.
triggers:
  - "extract samples"
  - "提取样本"
  - "voice samples"
  - "extract speaker"
---

# Extract Speaker Samples

Extract ~15 seconds of voice samples per speaker from the source audio, using transcript timestamps to find the best segments.

## Prerequisites

- `ffmpeg` installed
- Source audio file and `transcript.json` from transcribe_audio skill

## Usage

```bash
python .claude/skills/extract_samples/extract.py <audio_path> <transcript_path> <output_dir> [--duration 15]
```

### Arguments

- `audio_path` (required): Path to the source audio file
- `transcript_path` (required): Path to the transcript JSON file
- `output_dir` (required): Directory to save sample WAV files
- `--duration` (optional): Target duration per speaker in seconds (default: 15)

### Output

- Saves WAV files: `speaker_0_sample_0.wav`, `speaker_0_sample_1.wav`, etc.
- Saves `samples_manifest.json` mapping speaker IDs to file paths
- Prints summary of extracted samples

### Example

```bash
python .claude/skills/extract_samples/extract.py \
  workspaces/abc123/upload.mp3 \
  workspaces/abc123/transcript.json \
  workspaces/abc123/samples/
```
