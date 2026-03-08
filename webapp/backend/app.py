"""FastAPI app for voice-clone podcast service."""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.base import BaseHTTPMiddleware

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

# Auth state
# email -> hashed_password
users: dict[str, str] = {}
# session_id -> {email, created_at}
sessions: dict[str, dict] = {}


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# --- Auth middleware ---
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/jobs"):
            session_id = request.cookies.get("session_id")
            if not session_id or session_id not in sessions:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

app.add_middleware(AuthMiddleware)


# --- Auth routes ---
@app.post("/api/auth/register")
async def register(request: Request):
    body = await request.json()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    if not email or "@" not in email:
        return JSONResponse({"error": "Invalid email"}, status_code=400)
    if len(password) < 6:
        return JSONResponse({"error": "Password must be at least 6 characters"}, status_code=400)
    if email in users:
        return JSONResponse({"error": "Email already registered"}, status_code=400)

    users[email] = _hash_pw(password)
    logging.info(f"New user registered: {email}")

    session_id = uuid.uuid4().hex
    sessions[session_id] = {"email": email}
    resp = JSONResponse({"ok": True, "email": email})
    resp.set_cookie("session_id", session_id, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if email not in users:
        return JSONResponse({"error": "Email not registered"}, status_code=400)
    if users[email] != _hash_pw(password):
        return JSONResponse({"error": "Wrong password"}, status_code=400)

    logging.info(f"User logged in: {email}")
    session_id = uuid.uuid4().hex
    sessions[session_id] = {"email": email}
    resp = JSONResponse({"ok": True, "email": email})
    resp.set_cookie("session_id", session_id, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.get("/api/auth/me")
async def auth_me(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return JSONResponse({"logged_in": False})
    return {"logged_in": True, "email": sessions[session_id]["email"]}


@app.get("/", response_class=HTMLResponse)
async def index():
    # Try sibling "frontend" dir (Docker), then parent's "frontend" dir (local dev)
    frontend = Path(__file__).parent / "frontend" / "index.html"
    if not frontend.exists():
        frontend = Path(__file__).parent.parent / "frontend" / "index.html"
    return HTMLResponse(frontend.read_text(encoding="utf-8"))


@app.post("/api/jobs")
async def create_job(
    request: Request,
    audio: UploadFile = File(...),
    speaker_names: str = Form('{"0":"说话人A","1":"说话人B"}'),
    speaker_count: int = Form(2),
    prompt: str = Form(""),
):
    """Create a new voice-clone job."""
    session_id = request.cookies.get("session_id")
    email = sessions.get(session_id, {}).get("email", "unknown")

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
        "email": email,
    }
    logging.info(f"Job {job_id} created by {email}")

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
        logging.info(f"Job {job_id} completed for {job.get('email', 'unknown')}")
    except Exception as e:
        logging.exception(f"Job {job_id} failed for {job.get('email', 'unknown')}")
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
