"""Batch TTS generation for all segments in a corrected transcript."""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


def tts_generate(text: str, model_id: str, output_path: str) -> None:
    api_key = os.environ["FISH_API_KEY"]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    resp = requests.post(
        "https://api.fish.audio/v1/tts",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"text": text, "reference_id": model_id},
    )
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)


def main():
    parser = argparse.ArgumentParser(description="Batch TTS from corrected transcript")
    parser.add_argument("corrected_path", help="Path to corrected.json")
    parser.add_argument("voice_models_path", help="Path to voice_models.json (speaker->model_id)")
    parser.add_argument("output_dir", help="Directory for output MP3 segments")
    args = parser.parse_args()

    corrected = json.loads(Path(args.corrected_path).read_text(encoding="utf-8"))
    voice_models = json.loads(Path(args.voice_models_path).read_text(encoding="utf-8"))

    segments = corrected.get("segments", [])
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    for i, seg in enumerate(segments):
        speaker = seg["speaker"]
        text = seg["text"]
        model_id = voice_models.get(speaker)
        if not model_id:
            model_id = next(iter(voice_models.values()))
            print(f"Warning: No model for '{speaker}', using fallback")

        output_path = str(Path(args.output_dir) / f"segment_{i + 1:03d}.mp3")
        tts_generate(text, model_id, output_path)
        print(f"[{i + 1}/{len(segments)}] {speaker}: {text[:40]}... -> {output_path}")

    print(f"\nBatch TTS complete. Generated {len(segments)} segments in {args.output_dir}")


if __name__ == "__main__":
    main()
