---
name: generate-tts
description: Generate speech audio using a Fish Audio voice model. Takes text and model ID, produces MP3.
triggers:
  - "generate tts"
  - "生成语音"
  - "text to speech"
  - "synthesize"
---

# Generate TTS

Generate speech audio from text using a Fish Audio voice clone model.

## Prerequisites

- `FISH_API_KEY` environment variable set
- A voice model ID from create_voice_model skill

## Usage

```bash
python .claude/skills/generate_tts/tts.py --text "要合成的文字" --model-id MODEL_ID --output path/to/output.mp3
```

### Arguments

- `--text` (required): Text to synthesize into speech
- `--model-id` (required): Fish Audio voice model ID
- `--output` (required): Output file path (MP3)

### Output

- Saves the generated MP3 audio file
- Prints confirmation with file path

### Example

For batch generation of multiple segments, run this script once per segment:

```bash
python .claude/skills/generate_tts/tts.py \
  --text "大家好，欢迎收听本期播客" \
  --model-id "abc123def456" \
  --output "workspaces/abc123/tts_output/segment_001.mp3"
```

### Batch Example

To generate TTS for all segments in a corrected transcript:

```bash
# Read corrected.json and generate each segment
python .claude/skills/generate_tts/tts_batch.py \
  workspaces/abc123/corrected.json \
  workspaces/abc123/voice_models.json \
  workspaces/abc123/tts_output/
```
