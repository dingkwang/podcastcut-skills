---
name: merge-audio
description: Merge multiple audio segment files into a single output file using FFmpeg.
triggers:
  - "merge audio"
  - "合并音频"
  - "concat audio"
  - "combine segments"
---

# Merge Audio

Merge multiple audio segment files into a single output file using FFmpeg concat.

## Prerequisites

- `ffmpeg` installed
- Audio segment files (MP3) from generate_tts skill

## Usage

```bash
python .claude/skills/merge_audio/merge.py <segment_dir> <output_path> [--pattern "segment_*.mp3"]
```

### Arguments

- `segment_dir` (required): Directory containing audio segment files
- `output_path` (required): Path for the merged output file
- `--pattern` (optional): Glob pattern for segment files (default: `segment_*.mp3`)

### Output

- Creates the merged audio file at the output path
- Prints segment count and output path

### Example

```bash
python .claude/skills/merge_audio/merge.py \
  workspaces/abc123/tts_output/ \
  workspaces/abc123/output.mp3
```
