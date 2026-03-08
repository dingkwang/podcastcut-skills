"""Gemini API for transcript correction."""

import json
import os

from google import genai


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


def correct_transcript(
    transcript: dict,
    speaker_names: dict[str, str],
    user_prompt: str = "",
) -> dict:
    """Use Gemini to correct the ASR transcript.

    Args:
        transcript: ASR result with 'sentences' list.
        speaker_names: Mapping of speaker ID to name.
        user_prompt: Additional user instructions.

    Returns:
        Dict with 'segments' list, each having speaker and text.
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Build the transcript text for review
    lines = []
    for s in transcript["sentences"]:
        name = speaker_names.get(str(s["spk"]), f"说话人{s['spk']}")
        lines.append(f"[{name}] {s['text']}")

    transcript_text = "\n".join(lines)

    user_message = f"请修正以下播客逐字稿：\n\n{transcript_text}"
    if user_prompt:
        user_message = f"用户要求：{user_prompt}\n\n{user_message}"

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[f"{SYSTEM_PROMPT}\n\n{user_message}"],
    )

    # Parse JSON from response
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(text)
