"""FFmpeg audio operations: extract speaker samples, merge segments."""

import json
import subprocess
from pathlib import Path


def extract_speaker_samples(
    transcript: dict,
    audio_path: str,
    output_dir: str,
    target_duration: float = 15.0,
) -> dict[int, list[str]]:
    """Extract ~15s of solo speech for each speaker.

    Returns dict mapping speaker_id -> list of sample file paths.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Group consecutive sentences by speaker
    segments_by_spk: dict[int, list[dict]] = {}
    current_spk = None
    current_start = 0
    current_end = 0

    for sent in transcript["sentences"]:
        spk = sent["spk"]
        if spk == current_spk:
            current_end = sent["end"]
        else:
            if current_spk is not None:
                segments_by_spk.setdefault(current_spk, []).append({
                    "start": current_start,
                    "end": current_end,
                    "duration": current_end - current_start,
                })
            current_spk = spk
            current_start = sent["start"]
            current_end = sent["end"]

    if current_spk is not None:
        segments_by_spk.setdefault(current_spk, []).append({
            "start": current_start,
            "end": current_end,
            "duration": current_end - current_start,
        })

    # For each speaker, pick the longest segment(s) up to target_duration
    result = {}
    for spk, segments in segments_by_spk.items():
        segments.sort(key=lambda s: s["duration"], reverse=True)
        picked = []
        total = 0
        for seg in segments:
            if total >= target_duration:
                break
            picked.append(seg)
            total += seg["duration"]

        paths = []
        for i, seg in enumerate(picked):
            out = str(Path(output_dir) / f"speaker_{spk}_sample_{i}.wav")
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", audio_path,
                    "-af", f"atrim=start={seg['start']}:end={seg['end']},asetpts=PTS-STARTPTS",
                    "-ar", "44100", "-ac", "1", out,
                ],
                capture_output=True,
                check=True,
            )
            paths.append(out)
        result[spk] = paths

    return result


def merge_segments(segment_dir: str, output_path: str) -> None:
    """Merge numbered segment MP3 files into a single file."""
    seg_dir = Path(segment_dir)
    files = sorted(seg_dir.glob("segment_*.mp3"))
    if not files:
        raise FileNotFoundError(f"No segments found in {segment_dir}")

    # Create concat list
    list_file = seg_dir / "concat_list.txt"
    with open(list_file, "w") as f:
        for p in files:
            f.write(f"file '{p.resolve()}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", output_path,
        ],
        capture_output=True,
        check=True,
    )
    list_file.unlink()
