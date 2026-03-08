"""Gemini 3 Flash ASR transcription service."""

import json
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path

from google import genai


TRANSCRIPT_PROMPT = """
请转录这段音频中的所有语音内容。

要求：
1. 识别不同的说话人，标记为 Speaker 0, Speaker 1, Speaker 2 等
2. 每句话标注开始时间（秒），格式为小数
3. 保持原始语言（中文为主，英文术语保留原文）
4. 输出严格的 JSON 格式，不要其他文字

输出格式：
{"sentences": [{"text": "说话内容", "start": 0.0, "end": 3.5, "spk": 0}, ...]}
"""


def _safe_copy(audio_path: str) -> str:
    """Copy file to a temp path with ASCII-safe name (Gemini SDK requirement)."""
    suffix = Path(audio_path).suffix
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, prefix="audio_", delete=False)
    tmp.close()
    shutil.copy2(audio_path, tmp.name)
    return tmp.name


def transcribe(audio_path: str, speaker_count: int = 2) -> dict:
    """Transcribe audio using Gemini 3 Flash.

    Args:
        audio_path: Local path to the audio file.
        speaker_count: Expected number of speakers (used in prompt).

    Returns:
        Dict with 'sentences' list, each having text/start/end/spk.
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Copy to ASCII-safe filename to avoid httpx encoding errors
    safe_path = _safe_copy(audio_path)
    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/mp4"  # sensible default for .m4a etc.
    try:
        audio_file = client.files.upload(file=safe_path, config={"mime_type": mime_type})
    finally:
        os.unlink(safe_path)

    prompt = TRANSCRIPT_PROMPT
    if speaker_count > 1:
        prompt += f"\n说话人数量大约为 {speaker_count} 人。"

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[prompt, audio_file],
    )

    # Parse JSON from response
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    result = json.loads(text)

    # Ensure consistent format
    sentences = result.get("sentences", [])
    speakers = set(s.get("spk", 0) for s in sentences)

    return {
        "sentences": sentences,
        "speaker_count": len(speakers),
        "sentence_count": len(sentences),
    }
