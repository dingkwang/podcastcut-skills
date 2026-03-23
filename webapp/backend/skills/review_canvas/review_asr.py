"""ASR helpers local to the review_canvas skill.

Preferred path:
1. DashScope FunASR with speaker diarization
2. OpenRouter Gemini audio transcription fallback
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import time
from pathlib import Path

import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

DASHSCOPE_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
DASHSCOPE_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"
POLL_INTERVAL = 5
MAX_POLL_ATTEMPTS = 300

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


def _mime_type_for(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type or "audio/mp4"


def _upload_to_uguu(file_path: str) -> str:
    with open(file_path, "rb") as handle:
        files = {
            "files[]": (
                os.path.basename(file_path),
                handle,
                _mime_type_for(file_path),
            )
        }
        response = requests.post(
            "https://uguu.se/upload?output=text",
            files=files,
            timeout=120,
        )
        response.raise_for_status()
        url = response.text.strip()

    if not url.startswith("http"):
        raise RuntimeError(f"uguu.se upload failed: {url}")
    return url


def _sentence_text(sentence: dict) -> str:
    if sentence.get("text"):
        return str(sentence["text"]).strip()

    parts = []
    for word in sentence.get("words", []) or []:
        text = str(word.get("text", "") or "")
        punctuation = str(word.get("punctuation", "") or "")
        if text or punctuation:
            parts.append(f"{text}{punctuation}")
    return "".join(parts).strip()


def _parse_funasr_transcript(transcript: dict) -> dict:
    raw_sentences = transcript.get("transcripts", [{}])[0].get("sentences", []) or []
    sentences = []
    speakers = set()

    for idx, sentence in enumerate(raw_sentences):
        speaker_id = int(sentence.get("speaker_id", 0) or 0)
        start = float(sentence.get("begin_time", 0)) / 1000
        end = float(sentence.get("end_time", 0)) / 1000
        text = _sentence_text(sentence)
        if not text and end <= start:
            continue

        sentences.append(
            {
                "text": text,
                "start": round(start, 3),
                "end": round(end, 3),
                "spk": speaker_id,
                "source": "dashscope_funasr",
                "idx": idx,
            }
        )
        speakers.add(speaker_id)

    return {
        "sentences": sentences,
        "speaker_count": len(speakers) if speakers else 0,
        "sentence_count": len(sentences),
        "source": "dashscope_funasr",
    }


def _transcribe_with_dashscope(audio_path: str, speaker_count: int | None) -> dict:
    dashscope_api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_api_key:
        raise RuntimeError("DASHSCOPE_API_KEY not set")

    audio_url = _upload_to_uguu(audio_path)
    headers = {
        "Authorization": f"Bearer {dashscope_api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    parameters = {
        "diarization_enabled": True,
        "channel_id": [0],
    }
    if speaker_count and speaker_count > 0:
        parameters["speaker_count"] = int(speaker_count)

    payload = {
        "model": "fun-asr",
        "input": {"file_urls": [audio_url]},
        "parameters": parameters,
    }

    submit_response = requests.post(
        DASHSCOPE_SUBMIT_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    submit_response.raise_for_status()
    submit_result = submit_response.json()
    task_id = submit_result.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"DashScope FunASR submit failed: {submit_result}")

    poll_headers = {"Authorization": f"Bearer {dashscope_api_key}"}
    for _ in range(MAX_POLL_ATTEMPTS):
        time.sleep(POLL_INTERVAL)
        poll_response = requests.get(
            f"{DASHSCOPE_TASK_URL}/{task_id}",
            headers=poll_headers,
            timeout=30,
        )
        poll_response.raise_for_status()
        poll_result = poll_response.json()
        status = poll_result.get("output", {}).get("task_status")

        if status == "SUCCEEDED":
            transcription_url = (
                poll_result.get("output", {})
                .get("results", [{}])[0]
                .get("transcription_url")
            )
            if not transcription_url:
                raise RuntimeError(f"No transcription_url in FunASR result: {poll_result}")
            transcription_response = requests.get(transcription_url, timeout=60)
            transcription_response.raise_for_status()
            return _parse_funasr_transcript(transcription_response.json())

        if status == "FAILED":
            raise RuntimeError(f"DashScope FunASR task failed: {poll_result}")

    raise RuntimeError(
        f"DashScope FunASR task timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL}s"
    )


def _transcribe_with_openrouter(audio_path: str, speaker_count: int | None = None) -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    audio_bytes = Path(audio_path).read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    prompt = TRANSCRIPT_PROMPT
    if speaker_count and speaker_count > 1:
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
                        "input_audio": {
                            "data": audio_b64,
                            "format": _mime_type_for(audio_path),
                        },
                    },
                ],
            }
        ],
    )

    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    result = json.loads(text)
    sentences = result.get("sentences", [])
    speakers = set(s.get("spk", 0) for s in sentences)
    return {
        "sentences": sentences,
        "speaker_count": len(speakers),
        "sentence_count": len(sentences),
        "source": "openrouter_gemini",
    }


def transcribe(audio_path: str, speaker_count: int | None = None) -> dict:
    dashscope_error = None
    if os.environ.get("DASHSCOPE_API_KEY"):
        try:
            return _transcribe_with_dashscope(audio_path, speaker_count)
        except Exception as exc:
            dashscope_error = exc
            logger.warning("DashScope FunASR failed, falling back to OpenRouter: %s", exc)

    if not os.environ.get("OPENROUTER_API_KEY"):
        if dashscope_error:
            raise RuntimeError(
                f"DashScope FunASR failed and no OPENROUTER_API_KEY fallback is configured: {dashscope_error}"
            )
        raise RuntimeError("Neither DASHSCOPE_API_KEY nor OPENROUTER_API_KEY is configured")

    return _transcribe_with_openrouter(audio_path, speaker_count)
