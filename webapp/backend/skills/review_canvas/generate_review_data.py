#!/usr/bin/env python3
"""Generate review_data.json for the review canvas from ASR only."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

BACKEND_DIR = SCRIPT_DIR.parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.fly", override=True)

from review_asr import transcribe
from validate_review_data import fail


def _probe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _time_str(seconds: float) -> str:
    total = max(int(seconds), 0)
    return f"{total // 60}:{total % 60:02d}"


def _speaker_label(spk: int) -> str:
    return f"说话人{spk + 1}"


def _resolve_audio_file(audio_path_arg: str) -> Path:
    requested = Path(audio_path_arg)
    candidates = []

    if requested.is_absolute():
        candidates.append(requested)
        candidates.append(Path.cwd() / requested.name)
    else:
        candidates.append(Path.cwd() / requested)
        candidates.append(Path.cwd() / requested.name)

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except FileNotFoundError:
            resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(f"Audio file not found: {audio_path_arg}")


def _build_review_data(audio_file: Path, transcript: dict) -> dict:
    raw_sentences = transcript.get("sentences", []) or []
    audio_duration = round(_probe_duration(audio_file), 2)

    sentences = []
    for idx, sentence in enumerate(raw_sentences):
        start = float(sentence.get("start", 0))
        end = float(sentence.get("end", start))
        spk = int(sentence.get("spk", 0) or 0)
        original_text = str(sentence.get("text", "") or "").strip()

        sentence_entry = {
            "idx": idx,
            "speaker": _speaker_label(spk),
            "text": original_text,
            "startTime": round(start, 3),
            "endTime": round(end, 3),
            "timeStr": _time_str(start),
            "words": [
                {
                    "t": original_text,
                    "s": round(start, 3),
                    "e": round(end, 3),
                }
            ],
            "isAiDeleted": False,
        }
        sentences.append(sentence_entry)

    return {
        "audio_url": audio_file.name,
        "audio_duration": audio_duration,
        "sentences": sentences,
        "blocks": [],
        "fineEdits": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate review_data.json for PodcastCut review canvas")
    parser.add_argument("audio_path", help="Path to the local audio file in the current workspace")
    parser.add_argument("--speakers", type=int, default=0, help="Expected speaker count; omit or use 0 to infer automatically")
    args = parser.parse_args()

    try:
        audio_file = _resolve_audio_file(args.audio_path)
    except FileNotFoundError as exc:
        return fail(str(exc))

    workspace = audio_file.parent

    speaker_count = args.speakers if args.speakers and args.speakers > 0 else None
    transcript = transcribe(str(audio_file), speaker_count=speaker_count)
    transcript_path = workspace / "transcript.json"
    transcript_path.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    review_data = _build_review_data(audio_file, transcript)
    review_path = workspace / "review_data.json"
    review_path.write_text(
        json.dumps(review_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "audio": audio_file.name,
                "source": transcript.get("source"),
                "sentences": len(review_data.get("sentences", [])),
                "transcript_path": str(transcript_path),
                "review_path": str(review_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
