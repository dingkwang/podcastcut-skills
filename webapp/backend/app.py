"""FastAPI app for voice-clone podcast service."""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from pipeline import Pipeline

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="PodcastCut Voice Clone")

UPLOAD_DIR = Path("uploads")
JOBS_DIR = Path("jobs")
UPLOAD_DIR.mkdir(exist_ok=True)
JOBS_DIR.mkdir(exist_ok=True)

# In-memory job state
jobs: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
async def index():
    frontend = Path(__file__).parent.parent / "frontend" / "index.html"
    return HTMLResponse(frontend.read_text(encoding="utf-8"))


@app.post("/api/jobs")
async def create_job(
    audio: UploadFile = File(...),
    speaker_names: str = Form('{"0":"说话人A","1":"说话人B"}'),
    speaker_count: int = Form(2),
    prompt: str = Form(""),
):
    """Create a new voice-clone job."""
    job_id = uuid.uuid4().hex[:12]
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True)

    # Save uploaded audio with ASCII-safe filename
    suffix = Path(audio.filename).suffix or ".mp3"
    audio_path = job_dir / f"upload{suffix}"
    content = await audio.read()
    audio_path.write_bytes(content)

    # Parse speaker names
    names = json.loads(speaker_names)

    # Initialize job state
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "stage": "",
        "detail": "",
        "audio_path": str(audio_path),
        "output_path": None,
        "error": None,
    }

    # Run pipeline in background
    asyncio.get_event_loop().run_in_executor(
        None, _run_job, job_id, str(audio_path), names, speaker_count, prompt,
    )

    return {"job_id": job_id}


def _run_job(
    job_id: str,
    audio_path: str,
    speaker_names: dict,
    speaker_count: int,
    prompt: str,
):
    """Run the pipeline (blocking, runs in thread pool)."""
    job = jobs[job_id]
    job["status"] = "running"
    job_dir = str(JOBS_DIR / job_id)

    def on_progress(stage, detail):
        job["stage"] = stage
        job["detail"] = detail

    try:
        pipeline = Pipeline(job_dir, on_progress=on_progress)
        output = pipeline.run(
            audio_path=audio_path,
            speaker_names=speaker_names,
            speaker_count=speaker_count,
            user_prompt=prompt,
        )
        job["status"] = "completed"
        job["output_path"] = output
    except Exception as e:
        logging.exception(f"Job {job_id} failed")
        job["status"] = "failed"
        job["error"] = str(e)
        job["stage"] = "error"
        job["detail"] = str(e)


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status."""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    """SSE stream for job progress."""
    async def event_generator():
        last_detail = ""
        while True:
            job = jobs.get(job_id)
            if not job:
                yield {"event": "error", "data": "Job not found"}
                break

            current = f"{job['stage']}:{job['detail']}"
            if current != last_detail:
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "status": job["status"],
                        "stage": job["stage"],
                        "detail": job["detail"],
                    }),
                }
                last_detail = current

            if job["status"] in ("completed", "failed"):
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "status": job["status"],
                        "output_path": job.get("output_path"),
                        "error": job.get("error"),
                    }),
                }
                break

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@app.get("/api/jobs/{job_id}/download")
async def download_output(job_id: str):
    """Download the final audio."""
    job = jobs.get(job_id)
    if not job or not job.get("output_path"):
        return JSONResponse({"error": "Output not ready"}, status_code=404)
    return FileResponse(job["output_path"], filename="podcast_voiceclone.mp3")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
