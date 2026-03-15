"""Transcribe audio using Gemini 3 Flash via OpenRouter."""

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path

from openai import OpenAI

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


def transcribe(audio_path: str, speaker_count: int = 2) -> dict:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )

    audio_bytes = Path(audio_path).read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/mp4"

    prompt = TRANSCRIPT_PROMPT
    if speaker_count > 1:
        prompt += f"\n说话人数量大约为 {speaker_count} 人。"

    response = client.chat.completions.create(
        model="google/gemini-3-flash-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": mime_type},
                    },
                ],
            },
        ],
    )

    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(text)


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio using Gemini 3 Flash")
    parser.add_argument("audio_path", help="Path to the audio file")
    parser.add_argument("--speakers", type=int, default=2, help="Expected number of speakers")
    args = parser.parse_args()

    audio_file = Path(args.audio_path)
    if not audio_file.exists():
        print(f"Error: File not found: {args.audio_path}", file=sys.stderr)
        sys.exit(1)

    result = transcribe(args.audio_path, args.speakers)
    sentences = result.get("sentences", [])
    speakers = set(s.get("spk", 0) for s in sentences)

    output_path = audio_file.parent / "transcript.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Transcription complete.")
    print(f"Sentences: {len(sentences)}")
    print(f"Speakers detected: {len(speakers)}")
    print(f"Transcript saved to: {output_path}")


if __name__ == "__main__":
    main()
