"""Correct ASR transcript using Gemini LLM via OpenRouter."""

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

SYSTEM_PROMPT = """你是一个专业的播客编辑。你的任务是审阅ASR转录的逐字稿，修正为干净、流畅的文字。

修正规则：
1. 删除语气词和填充词（呃、嗯、啊、哎、那个、就是说）
2. 修正口误和重复（"我我我觉得" → "我觉得"）
3. 修正ASR识别错误（根据上下文判断正确的词）
4. 阿拉伯数字转汉字（"70岁" → "七十岁"）
5. 删除无意义的寒暄和废话
6. 保持说话人的语言风格和口吻
7. 不要改变原意，不要添加原文没有的内容

输出格式：严格的 JSON，包含 segments 数组，每个 segment 有 speaker 和 text 字段。
只输出 JSON，不要其他文字。"""


def correct(transcript: dict, speaker_names: dict[str, str], user_prompt: str = "") -> dict:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )

    lines = []
    for s in transcript.get("sentences", []):
        name = speaker_names.get(str(s["spk"]), f"说话人{s['spk']}")
        lines.append(f"[{name}] {s['text']}")

    transcript_text = "\n".join(lines)
    user_message = f"请修正以下播客逐字稿：\n\n{transcript_text}"
    if user_prompt:
        user_message = f"用户要求：{user_prompt}\n\n{user_message}"

    response = client.chat.completions.create(
        model="google/gemini-3-flash-preview",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(text)


def main():
    parser = argparse.ArgumentParser(description="Correct ASR transcript using LLM")
    parser.add_argument("transcript_path", help="Path to transcript JSON file")
    parser.add_argument("--speakers", required=True, help='JSON mapping: \'{"0":"Alice","1":"Bob"}\'')
    parser.add_argument("--prompt", default="", help="Additional correction instructions")
    args = parser.parse_args()

    path = Path(args.transcript_path)
    if not path.exists():
        print(f"Error: File not found: {args.transcript_path}", file=sys.stderr)
        sys.exit(1)

    transcript = json.loads(path.read_text(encoding="utf-8"))
    speaker_names = json.loads(args.speakers)

    corrected = correct(transcript, speaker_names, args.prompt)

    output_path = path.parent / "corrected.json"
    output_path.write_text(json.dumps(corrected, ensure_ascii=False, indent=2), encoding="utf-8")

    segment_count = len(corrected.get("segments", []))
    print(f"Transcript correction complete.")
    print(f"Segments: {segment_count}")
    print(f"Corrected transcript saved to: {output_path}")


if __name__ == "__main__":
    main()
