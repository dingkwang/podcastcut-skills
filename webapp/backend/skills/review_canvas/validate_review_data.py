#!/usr/bin/env python3
"""Validate review_data.json against the PodcastCut review canvas contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"INVALID: {message}", file=sys.stderr)
    return 1


def expect_type(value, expected_type, path: str) -> None:
    if not isinstance(value, expected_type):
        raise ValueError(f"{path} must be {expected_type.__name__}")


def expect_number(value, path: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{path} must be a number")


def expect_string(value, path: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{path} must be a string")


def expect_bool(value, path: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{path} must be a boolean")


def validate_word(word: dict, path: str) -> None:
    expect_type(word, dict, path)
    for key in ("t", "s", "e"):
        if key not in word:
            raise ValueError(f"{path}.{key} is required")
    expect_string(word["t"], f"{path}.t")
    expect_number(word["s"], f"{path}.s")
    expect_number(word["e"], f"{path}.e")


def validate_sentence_fine_edit(edit: dict, path: str) -> None:
    expect_type(edit, dict, path)
    required = ("type", "deleteText", "keepText", "reason", "ds", "de", "enabled")
    for key in required:
        if key not in edit:
            raise ValueError(f"{path}.{key} is required")
    expect_string(edit["type"], f"{path}.type")
    expect_string(edit["deleteText"], f"{path}.deleteText")
    expect_string(edit["keepText"], f"{path}.keepText")
    expect_string(edit["reason"], f"{path}.reason")
    expect_number(edit["ds"], f"{path}.ds")
    expect_number(edit["de"], f"{path}.de")
    expect_bool(edit["enabled"], f"{path}.enabled")
    if "count" in edit and (not isinstance(edit["count"], int) or edit["count"] < 1):
        raise ValueError(f"{path}.count must be a positive integer when present")


def validate_sentence(sentence: dict, path: str) -> None:
    expect_type(sentence, dict, path)
    required = ("idx", "speaker", "text", "startTime", "endTime", "timeStr", "words", "isAiDeleted")
    for key in required:
        if key not in sentence:
            raise ValueError(f"{path}.{key} is required")
    if not isinstance(sentence["idx"], int) or sentence["idx"] < 0:
        raise ValueError(f"{path}.idx must be a non-negative integer")
    expect_string(sentence["speaker"], f"{path}.speaker")
    expect_string(sentence["text"], f"{path}.text")
    expect_number(sentence["startTime"], f"{path}.startTime")
    expect_number(sentence["endTime"], f"{path}.endTime")
    expect_string(sentence["timeStr"], f"{path}.timeStr")
    expect_bool(sentence["isAiDeleted"], f"{path}.isAiDeleted")
    expect_type(sentence["words"], list, f"{path}.words")
    for idx, word in enumerate(sentence["words"]):
        validate_word(word, f"{path}.words[{idx}]")
    if "deleteType" in sentence:
        expect_string(sentence["deleteType"], f"{path}.deleteType")
    if "blockId" in sentence and (not isinstance(sentence["blockId"], int) or sentence["blockId"] < 1):
        raise ValueError(f"{path}.blockId must be a positive integer when present")
    if "fineEdit" in sentence:
        validate_sentence_fine_edit(sentence["fineEdit"], f"{path}.fineEdit")


def validate_block(block: dict, path: str) -> None:
    expect_type(block, dict, path)
    required = ("id", "range", "type", "topic", "reason", "duration", "durationSeconds", "startTime", "enabled")
    for key in required:
        if key not in block:
            raise ValueError(f"{path}.{key} is required")
    if not isinstance(block["id"], int) or block["id"] < 1:
        raise ValueError(f"{path}.id must be a positive integer")
    expect_type(block["range"], list, f"{path}.range")
    if len(block["range"]) != 2:
        raise ValueError(f"{path}.range must have exactly 2 items")
    for idx, item in enumerate(block["range"]):
        if not isinstance(item, int) or item < 0:
            raise ValueError(f"{path}.range[{idx}] must be a non-negative integer")
    expect_string(block["type"], f"{path}.type")
    expect_string(block["topic"], f"{path}.topic")
    expect_string(block["reason"], f"{path}.reason")
    expect_string(block["duration"], f"{path}.duration")
    expect_number(block["durationSeconds"], f"{path}.durationSeconds")
    expect_number(block["startTime"], f"{path}.startTime")
    expect_bool(block["enabled"], f"{path}.enabled")


def validate_fine_edit(edit: dict, path: str) -> None:
    expect_type(edit, dict, path)
    required = ("sentenceIdx", "type", "deleteText", "keepText", "reason", "ds", "de", "enabled")
    for key in required:
        if key not in edit:
            raise ValueError(f"{path}.{key} is required")
    if not isinstance(edit["sentenceIdx"], int) or edit["sentenceIdx"] < 0:
        raise ValueError(f"{path}.sentenceIdx must be a non-negative integer")
    expect_string(edit["type"], f"{path}.type")
    expect_string(edit["deleteText"], f"{path}.deleteText")
    expect_string(edit["keepText"], f"{path}.keepText")
    expect_string(edit["reason"], f"{path}.reason")
    expect_number(edit["ds"], f"{path}.ds")
    expect_number(edit["de"], f"{path}.de")
    expect_bool(edit["enabled"], f"{path}.enabled")


def validate_payload(data: dict) -> None:
    expect_type(data, dict, "root")
    for key in ("audio_url", "audio_duration", "sentences", "blocks", "fineEdits"):
        if key not in data:
            raise ValueError(f"root.{key} is required")

    expect_string(data["audio_url"], "root.audio_url")
    expect_number(data["audio_duration"], "root.audio_duration")
    expect_type(data["sentences"], list, "root.sentences")
    expect_type(data["blocks"], list, "root.blocks")
    expect_type(data["fineEdits"], list, "root.fineEdits")

    for idx, sentence in enumerate(data["sentences"]):
        validate_sentence(sentence, f"root.sentences[{idx}]")
    for idx, block in enumerate(data["blocks"]):
        validate_block(block, f"root.blocks[{idx}]")
    for idx, edit in enumerate(data["fineEdits"]):
        validate_fine_edit(edit, f"root.fineEdits[{idx}]")


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "review_data.json")
    if not path.exists():
        return fail(f"{path} does not exist")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail(f"{path} is not valid JSON: {exc}")

    try:
        validate_payload(data)
    except ValueError as exc:
        return fail(str(exc))

    print(f"VALID: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
