"""Voice clone pipeline orchestration."""

import json
import logging
from pathlib import Path

from services import asr, audio, llm, voice_clone

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
        logger.info(f"[{stage}] {detail}")
        self.on_progress(stage, detail)

    def run(
        self,
        audio_path: str,
        speaker_names: dict[str, str],
        speaker_count: int = 2,
        user_prompt: str = "",
    ) -> str:
        """Run the full pipeline. Returns path to final audio."""

        # Stage 1: ASR
        self._progress("transcribing", "Uploading to Gemini 3 Flash...")
        transcript = asr.transcribe(audio_path, speaker_count)
        transcript_path = self.job_dir / "transcript.json"
        transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2))
        self._progress(
            "transcribing",
            f"Done: {transcript['sentence_count']} sentences, "
            f"{transcript['speaker_count']} speakers",
        )

        # Stage 2: LLM correction
        self._progress("correcting", "Gemini is reviewing the transcript...")
        corrected = llm.correct_transcript(transcript, speaker_names, user_prompt)
        corrected_path = self.job_dir / "corrected.json"
        corrected_path.write_text(json.dumps(corrected, ensure_ascii=False, indent=2))
        self._progress("correcting", f"Done: {len(corrected['segments'])} segments")

        # Stage 3: Extract speaker samples
        self._progress("extracting_samples", "Extracting speaker audio samples...")
        samples_dir = str(self.job_dir / "samples")
        samples = audio.extract_speaker_samples(transcript, audio_path, samples_dir)
        self._progress(
            "extracting_samples",
            f"Done: {sum(len(v) for v in samples.values())} samples",
        )

        # Stage 4: Create voice models
        self._progress("creating_models", "Creating voice models on Fish Audio...")
        unique_speakers = set(s["speaker"] for s in corrected["segments"])
        # Build spk_id -> name mapping
        name_to_spk = {v: k for k, v in speaker_names.items()}

        voice_clone.ensure_model_slots(len(unique_speakers))

        voice_models = {}
        for name in unique_speakers:
            spk_id = int(name_to_spk.get(name, 0))
            sample_paths = samples.get(spk_id, [])
            if not sample_paths:
                # Fallback: use first available speaker's samples
                sample_paths = next(iter(samples.values()))
            model_id = voice_clone.create_voice_model(sample_paths, name)
            voice_models[name] = model_id
            self._progress("creating_models", f"  {name} → {model_id}")

        models_path = self.job_dir / "voice_models.json"
        models_path.write_text(json.dumps(voice_models, ensure_ascii=False, indent=2))

        # Stage 5: TTS generation
        self._progress("generating_tts", "Generating audio segments...")
        tts_dir = self.job_dir / "tts_output"
        tts_dir.mkdir(exist_ok=True)

        segments = corrected["segments"]
        for i, seg in enumerate(segments):
            model_id = voice_models.get(seg["speaker"])
            if not model_id:
                model_id = next(iter(voice_models.values()))
            out_path = str(tts_dir / f"segment_{i + 1:03d}.mp3")
            voice_clone.tts_generate(seg["text"], model_id, out_path)
            self._progress(
                "generating_tts",
                f"  [{i + 1}/{len(segments)}] {seg['speaker']}: {seg['text'][:30]}...",
            )

        # Stage 6: Merge
        self._progress("merging", "Merging all segments...")
        output_path = str(self.job_dir / "output.mp3")
        audio.merge_segments(str(tts_dir), output_path)
        self._progress("done", output_path)

        return output_path
