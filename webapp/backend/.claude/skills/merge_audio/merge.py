"""Merge audio segments into one file using FFmpeg."""

import argparse
import subprocess
import sys
from pathlib import Path


def merge_segments(segment_dir: str, output_path: str, pattern: str = "segment_*.mp3") -> int:
    seg_dir = Path(segment_dir)
    files = sorted(seg_dir.glob(pattern))

    if not files:
        raise FileNotFoundError(f"No files matching '{pattern}' in {segment_dir}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

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

    return len(files)


def main():
    parser = argparse.ArgumentParser(description="Merge audio segments using FFmpeg")
    parser.add_argument("segment_dir", help="Directory containing segment files")
    parser.add_argument("output_path", help="Output file path")
    parser.add_argument("--pattern", default="segment_*.mp3", help="Glob pattern for segments")
    args = parser.parse_args()

    if not Path(args.segment_dir).exists():
        print(f"Error: Directory not found: {args.segment_dir}", file=sys.stderr)
        sys.exit(1)

    count = merge_segments(args.segment_dir, args.output_path, args.pattern)
    print(f"Audio merge complete.")
    print(f"Segments merged: {count}")
    print(f"Output: {args.output_path}")


if __name__ == "__main__":
    main()
