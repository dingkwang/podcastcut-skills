"""Generate TTS audio using Fish Audio voice model."""

import argparse
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
    parser = argparse.ArgumentParser(description="Generate TTS audio using Fish Audio")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument("--model-id", required=True, help="Fish Audio voice model ID")
    parser.add_argument("--output", required=True, help="Output file path (MP3)")
    args = parser.parse_args()

    tts_generate(args.text, args.model_id, args.output)
    print(f"TTS audio generated.")
    print(f"Output: {args.output}")
    print(f"Text: {args.text[:80]}{'...' if len(args.text) > 80 else ''}")


if __name__ == "__main__":
    main()
