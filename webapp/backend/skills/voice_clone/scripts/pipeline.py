"""Voice clone pipeline orchestration owned by the voice_clone skill."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from correct import correct
from create_model import create_model, delete_model, ensure_model_slots
from extract import extract_samples
from merge import merge_segments
from transcribe import transcribe
from tts import tts_generate

logger = logging.getLogger(__name__)


class Pipeline:
    """Runs the full voice-clone pipeline, reporting progress via callback."""

    STAGES = [
        "transcribing",
        "correcting",
        "extracting_samples",
        "creating_models",
        "generating_tts",
        "merging",
        "done",
    ]

    def __init__(self, job_dir: str, on_progress=None):
        self.job_dir = Path(job_dir)
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.on_progress = on_progress or (lambda stage, detail: None)

    def _progress(self, stage: str, detail: str = ""):
        logger.info("[%s] %s", stage, detail)
        self.on_progress(stage, detail)

    def run(
        self,
        audio_path: str,
        speaker_names: dict[str, str],
        speaker_count: int = 2,
        user_prompt: str = "",
    ) -> str:
        """Run the full pipeline. Returns path to final audio."""

        self._progress("transcribing", "Uploading to Gemini 3 Flash...")
        transcript = transcribe(audio_path, speaker_count)
        transcript_path = self.job_dir / "transcript.json"
        transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2))
        self._progress(
            "transcribing",
            f"Done: {len(transcript.get('sentences', []))} sentences, "
            f"{transcript.get('speaker_count', 0)} speakers",
        )

        self._progress("correcting", "Gemini is reviewing the transcript...")
        corrected = correct(transcript, speaker_names, user_prompt)
        corrected_path = self.job_dir / "corrected.json"
        corrected_path.write_text(json.dumps(corrected, ensure_ascii=False, indent=2))
        self._progress("correcting", f"Done: {len(corrected['segments'])} segments")

        self._progress("extracting_samples", "Extracting speaker audio samples...")
        samples_dir = str(self.job_dir / "samples")
        samples = extract_samples(audio_path, transcript, samples_dir)
        self._progress(
            "extracting_samples",
            f"Done: {sum(len(v) for v in samples.values())} samples",
        )

        self._progress("creating_models", "Creating voice models on Fish Audio...")
        unique_speakers = set(segment["speaker"] for segment in corrected["segments"])
        name_to_spk = {v: k for k, v in speaker_names.items()}

        ensure_model_slots(os.environ["FISH_API_KEY"], len(unique_speakers))

        voice_models = {}
        for name in unique_speakers:
            spk_id = int(name_to_spk.get(name, 0))
            sample_paths = samples.get(spk_id, [])
            if not sample_paths:
                sample_paths = next(iter(samples.values()))
            model_id = create_model(sample_paths, name)
            voice_models[name] = model_id
            self._progress("creating_models", f"  {name} → {model_id}")

        models_path = self.job_dir / "voice_models.json"
        models_path.write_text(json.dumps(voice_models, ensure_ascii=False, indent=2))

        self._progress("generating_tts", "Generating audio segments...")
        tts_dir = self.job_dir / "tts_output"
        tts_dir.mkdir(exist_ok=True)

        try:
            segments = corrected["segments"]
            for idx, segment in enumerate(segments):
                model_id = voice_models.get(segment["speaker"])
                if not model_id:
                    model_id = next(iter(voice_models.values()))
                out_path = str(tts_dir / f"segment_{idx + 1:03d}.mp3")
                tts_generate(segment["text"], model_id, out_path)
                self._progress(
                    "generating_tts",
                    f"  [{idx + 1}/{len(segments)}] {segment['speaker']}: {segment['text'][:30]}...",
                )
        finally:
            self._progress("generating_tts", "Cleaning up voice models...")
            for name, model_id in voice_models.items():
                try:
                    delete_model(model_id)
                except Exception:
                    logger.warning("Failed to delete voice model %s for %s", model_id, name)

        self._progress("merging", "Merging all segments...")
        output_path = str(self.job_dir / "output.mp3")
        merge_segments(str(tts_dir), output_path)
        self._progress("done", output_path)

        return output_path
