"""Extract speaker voice samples from audio using transcript timestamps."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def extract_samples(
    audio_path: str,
    transcript: dict,
    output_dir: str,
    target_duration: float = 15.0,
) -> dict[int, list[str]]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Group consecutive sentences by speaker
    segments_by_spk: dict[int, list[dict]] = {}
    current_spk = None
    current_start = 0.0
    current_end = 0.0

    for sent in transcript.get("sentences", []):
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

    # Pick longest segments up to target_duration per speaker
    result = {}
    for spk, segments in segments_by_spk.items():
        segments.sort(key=lambda s: s["duration"], reverse=True)
        picked = []
        total = 0.0
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


def main():
    parser = argparse.ArgumentParser(description="Extract speaker voice samples")
    parser.add_argument("audio_path", help="Path to source audio file")
    parser.add_argument("transcript_path", help="Path to transcript JSON file")
    parser.add_argument("output_dir", help="Directory to save sample files")
    parser.add_argument("--duration", type=float, default=15.0, help="Target duration per speaker (seconds)")
    args = parser.parse_args()

    if not Path(args.audio_path).exists():
        print(f"Error: Audio file not found: {args.audio_path}", file=sys.stderr)
        sys.exit(1)
    if not Path(args.transcript_path).exists():
        print(f"Error: Transcript not found: {args.transcript_path}", file=sys.stderr)
        sys.exit(1)

    transcript = json.loads(Path(args.transcript_path).read_text(encoding="utf-8"))
    result = extract_samples(args.audio_path, transcript, args.output_dir, args.duration)

    # Save manifest
    manifest = {str(k): v for k, v in result.items()}
    manifest_path = Path(args.output_dir) / "samples_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_samples = sum(len(v) for v in result.values())
    print(f"Extraction complete.")
    print(f"Speakers: {len(result)}")
    print(f"Total samples: {total_samples}")
    for spk, paths in result.items():
        print(f"  Speaker {spk}: {len(paths)} sample(s)")
        for p in paths:
            print(f"    - {p}")
    print(f"Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
