---
name: create-voice-model
description: Create a voice clone model on Fish Audio from speaker voice samples. Returns a model ID for TTS.
triggers:
  - "create voice model"
  - "创建声音模型"
  - "voice clone"
  - "clone voice"
---

# Create Voice Model

Upload speaker voice samples to Fish Audio and create a voice clone model. The model can then be used with generate_tts to synthesize speech.

## Prerequisites

- `FISH_API_KEY` environment variable set
- Voice sample WAV files from extract_samples skill
- Note: Fish Audio free tier allows max 3 models. Old models are auto-deleted if needed.

## Usage

```bash
python .claude/skills/create_voice_model/create_model.py --name "SpeakerName" --samples path1.wav,path2.wav
```

### Arguments

- `--name` (required): Name for this voice model
- `--samples` (required): Comma-separated paths to voice sample WAV files

### Output

- Prints the created model ID
- The model ID is used with the generate_tts skill

### Example

```bash
python .claude/skills/create_voice_model/create_model.py \
  --name "张三" \
  --samples "workspaces/abc123/samples/speaker_0_sample_0.wav,workspaces/abc123/samples/speaker_0_sample_1.wav"
```
