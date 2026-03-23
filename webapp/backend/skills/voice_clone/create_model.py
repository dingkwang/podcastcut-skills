"""Create a voice clone model on Fish Audio from speaker samples."""

import argparse
import os
import sys
from pathlib import Path

import requests


def list_models(api_key: str) -> list[dict]:
    resp = requests.get(
        "https://api.fish.audio/model",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"self": "true", "page_size": 10},
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def delete_model(model_id: str) -> None:
    api_key = os.environ["FISH_API_KEY"]
    resp = requests.delete(
        f"https://api.fish.audio/model/{model_id}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    resp.raise_for_status()


def ensure_model_slots(api_key: str, needed: int) -> None:
    """Delete existing models if we need room (free tier limit = 3)."""
    models = list_models(api_key)

    to_free = len(models) + needed - 3
    if to_free > 0:
        for m in models[:to_free]:
            delete_model(m["_id"])
            print(f"Deleted old model {m['_id']} ({m.get('title', '')}) to free slot")


def create_voice_model(sample_paths: list[str], name: str) -> str:
    api_key = os.environ["FISH_API_KEY"]

    ensure_model_slots(api_key, 1)

    files = []
    opened = []
    for p in sample_paths:
        f = open(p, "rb")
        opened.append(f)
        files.append(("voices", (Path(p).name, f, "audio/wav")))

    try:
        resp = requests.post(
            "https://api.fish.audio/model",
            headers={"Authorization": f"Bearer {api_key}"},
            data={
                "type": "tts",
                "title": name,
                "train_mode": "fast",
                "visibility": "private",
            },
            files=files,
        )
        resp.raise_for_status()
        return resp.json()["_id"]
    finally:
        for f in opened:
            f.close()


def main():
    parser = argparse.ArgumentParser(description="Create voice model on Fish Audio")
    parser.add_argument("--name", required=True, help="Name for the voice model")
    parser.add_argument("--samples", required=True, help="Comma-separated paths to sample WAV files")
    args = parser.parse_args()

    sample_paths = [p.strip() for p in args.samples.split(",") if p.strip()]
    for p in sample_paths:
        if not Path(p).exists():
            print(f"Error: Sample file not found: {p}", file=sys.stderr)
            sys.exit(1)

    model_id = create_voice_model(sample_paths, args.name)
    print(f"Voice model created successfully.")
    print(f"Speaker: {args.name}")
    print(f"Model ID: {model_id}")
    print(f"Samples used: {len(sample_paths)}")


if __name__ == "__main__":
    main()
