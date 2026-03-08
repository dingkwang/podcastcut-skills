"""Fish Audio voice clone and TTS service."""

import os
from pathlib import Path

import requests


def list_models() -> list[dict]:
    """List existing voice models on Fish Audio."""
    api_key = os.environ["FISH_API_KEY"]
    resp = requests.get(
        "https://api.fish.audio/model",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"self": "true", "page_size": 10},
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def delete_model(model_id: str) -> None:
    api_key = os.environ["FISH_API_KEY"]
    requests.delete(
        f"https://api.fish.audio/model/{model_id}",
        headers={"Authorization": f"Bearer {api_key}"},
    )


def ensure_model_slots(needed: int) -> None:
    """Delete existing models if we need room (free tier limit = 3)."""
    models = list_models()
    to_free = len(models) + needed - 3
    if to_free > 0:
        for m in models[:to_free]:
            delete_model(m["_id"])


def create_voice_model(sample_paths: list[str], name: str) -> str:
    """Upload samples and create a voice model. Returns model_id."""
    api_key = os.environ["FISH_API_KEY"]

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


def tts_generate(text: str, model_id: str, output_path: str) -> None:
    """Generate speech audio for a text segment."""
    api_key = os.environ["FISH_API_KEY"]

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
