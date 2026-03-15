---
name: correct-transcript
description: Clean up and correct an ASR transcript using LLM. Removes filler words, fixes recognition errors, produces clean text.
triggers:
  - "correct transcript"
  - "修正文稿"
  - "clean transcript"
  - "fix transcript"
---

# Correct Transcript

Use Gemini LLM to clean up an ASR transcript: remove filler words, fix recognition errors, and produce publication-ready text.

## Prerequisites

- `OPENROUTER_API_KEY` environment variable set
- `transcript.json` file from the transcribe_audio skill

## Usage

```bash
python .claude/skills/correct_transcript/correct.py <transcript_path> --speakers '{"0":"Alice","1":"Bob"}'
```

### Arguments

- `transcript_path` (required): Path to the transcript JSON file
- `--speakers` (required): JSON string mapping speaker ID to name
- `--prompt` (optional): Additional user instructions for correction

### Output

- Saves `corrected.json` in the same directory as the transcript
- Prints segment count

### Example

```bash
python .claude/skills/correct_transcript/correct.py workspaces/abc123/transcript.json \
  --speakers '{"0":"张三","1":"李四"}' \
  --prompt "保留所有技术术语的英文原文"
```

## Output Format

The `corrected.json` file contains:
```json
{
  "segments": [
    {"speaker": "张三", "text": "清理后的文字内容"},
    {"speaker": "李四", "text": "另一段清理后的内容"}
  ]
}
```
