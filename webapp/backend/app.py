"""FastAPI app for PodcastCut chat-based agent."""

import base64
import hashlib
import hmac
import json
import logging
import os
import subprocess
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agent import PodcastAgent

BACKEND_DIR = Path(__file__).parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.fly", override=True)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="PodcastCut")

podcast_agent = PodcastAgent()

# Chat history (in-memory)
chat_sessions: dict[str, list[dict]] = {}  # chat_session_id -> [{role, content}]
pending_uploads: dict[str, list[dict]] = {}  # chat_session_id -> [{file_name, size}]

AUTH_SECRET = (
    os.getenv("AUTH_SECRET")
    or os.getenv("ANTHROPIC_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or "podcastcut-dev-secret"
).encode("utf-8")


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _sign_session(email: str) -> str:
    payload = base64.urlsafe_b64encode(email.encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(AUTH_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _verify_session(session_token: str | None) -> str | None:
    if not session_token or "." not in session_token:
        return None

    payload, signature = session_token.rsplit(".", 1)
    expected = hmac.new(AUTH_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None

    padding = "=" * (-len(payload) % 4)
    try:
        return base64.urlsafe_b64decode(f"{payload}{padding}".encode("ascii")).decode("utf-8")
    except Exception:
        return None


def _load_review_data(workspace: Path) -> dict:
    review_path = workspace / "review_data.json"
    if not review_path.exists():
        raise FileNotFoundError("review_data.json not found")
    return json.loads(review_path.read_text(encoding="utf-8"))


def _merge_segments(segments: list[tuple[float, float]]) -> list[dict[str, float]]:
    cleaned = sorted(
        [(max(0.0, float(start)), max(0.0, float(end))) for start, end in segments if float(end) > float(start)],
        key=lambda item: item[0],
    )
    if not cleaned:
        return []

    merged: list[list[float]] = [[cleaned[0][0], cleaned[0][1]]]
    for start, end in cleaned[1:]:
        current = merged[-1]
        if start <= current[1] + 0.01:
            current[1] = max(current[1], end)
        else:
            merged.append([start, end])

    return [{"start": round(start, 3), "end": round(end, 3)} for start, end in merged]


def _build_delete_segments(review_data: dict) -> list[dict[str, float]]:
    sentences = review_data.get("sentences", []) or []
    fine_edits = review_data.get("fineEdits", []) or []

    segments: list[tuple[float, float]] = []

    active_sentence_ranges: list[tuple[float, float]] = []
    current_start: float | None = None
    current_end: float | None = None

    for sentence in sentences:
        if sentence.get("isAiDeleted", False):
            start_time = float(sentence.get("startTime", 0))
            end_time = float(sentence.get("endTime", 0))
            if end_time <= start_time:
                continue

            if current_start is None:
                current_start = start_time
                current_end = end_time
            elif start_time <= (current_end or 0) + 0.01:
                current_end = max(current_end or end_time, end_time)
            else:
                active_sentence_ranges.append((current_start, current_end or current_start))
                current_start = start_time
                current_end = end_time
        elif current_start is not None:
            active_sentence_ranges.append((current_start, current_end or current_start))
            current_start = None
            current_end = None

    if current_start is not None:
        active_sentence_ranges.append((current_start, current_end or current_start))

    segments.extend(active_sentence_ranges)

    for fine_edit in fine_edits:
        if fine_edit.get("enabled", True) is False:
            continue
        start_time = float(fine_edit.get("ds", 0))
        end_time = float(fine_edit.get("de", 0))
        if end_time > start_time:
            segments.append((start_time, end_time))

    return _merge_segments(segments)


def _probe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _merge_assistant_text(current_text: str, incoming_text: str) -> str:
    if not current_text:
        return incoming_text
    if not incoming_text:
        return current_text
    if incoming_text == current_text:
        return current_text
    if incoming_text.startswith(current_text):
        return incoming_text
    if current_text.startswith(incoming_text):
        return current_text
    return current_text + incoming_text


def _run_cut_pipeline(workspace: Path, audio_file: str, delete_segments_file: str, output_file: str) -> subprocess.CompletedProcess[str]:
    python_bin = BACKEND_DIR / ".venv" / "bin" / "python"
    script_path = BACKEND_DIR / "skills" / "cut_audio" / "cut_audio.py"
    return subprocess.run(
        [str(python_bin), str(script_path), output_file, audio_file, delete_segments_file],
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            path.startswith("/api/")
            and not path.startswith("/api/auth/")
            and not path.startswith("/api/debug/")
            and path != "/api/health"
        ):
            session_id = request.cookies.get("session_id")
            if not _verify_session(session_id):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


app.add_middleware(AuthMiddleware)


@app.get("/api/health")
async def health():
    """Lightweight health check for Fly machine readiness."""
    return {"ok": True}


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
    session_id = _sign_session(email)
    resp = JSONResponse({"ok": True, "email": email})
    resp.set_cookie("session_id", session_id, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    if not email or "@" not in email:
        return JSONResponse({"error": "Invalid email"}, status_code=400)
    if len(password) < 6:
        return JSONResponse({"error": "Password must be at least 6 characters"}, status_code=400)

    session_id = _sign_session(email)
    resp = JSONResponse({"ok": True, "email": email})
    resp.set_cookie("session_id", session_id, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.get("/api/auth/me")
async def auth_me(request: Request):
    session_id = request.cookies.get("session_id")
    email = _verify_session(session_id)
    if not email:
        return JSONResponse({"logged_in": False})
    return {"logged_in": True, "email": email}


# --- Debug ---
@app.get("/api/debug/skills")
async def debug_skills():
    """Return discovered skills (no auth required)."""
    from agent import _discover_skills
    return {"skills": _discover_skills()}


@app.post("/api/debug/chat")
async def debug_chat(request: Request):
    """Send a message to the agent and return raw SDK events (no auth required)."""
    body = await request.json()
    message = body.get("message", "/skills")
    session_id = f"debug_{uuid.uuid4().hex[:8]}"

    events = []
    async for event in podcast_agent.stream_response(session_id, message):
        events.append(event)
    return {"events": events}


# --- Chat ---
@app.post("/api/chat")
async def chat(request: Request):
    """SSE stream of agent responses."""
    body = await request.json()
    chat_session_id = body.get("session_id", uuid.uuid4().hex[:12])
    message = body.get("message", "")

    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    if chat_session_id not in chat_sessions:
        chat_sessions[chat_session_id] = []

    # Prepend pending file uploads to the user message sent to the agent
    uploads = pending_uploads.pop(chat_session_id, [])
    agent_message = message
    if uploads:
        file_lines = "\n".join(
            f"- {u['file_name']} ({u['size'] / 1024:.1f}KB)" for u in uploads
        )
        agent_message = f"[用户上传了文件到工作区]\n{file_lines}\n\n{message}"

    chat_sessions[chat_session_id].append({"role": "user", "content": message})

    async def event_generator():
        full_response = ""
        async for event in podcast_agent.stream_response(chat_session_id, agent_message):
            event_type = event.get("type", "")

            if event_type == "text":
                yield {"event": "text", "data": json.dumps({"content": event["content"]})}
                full_response = _merge_assistant_text(full_response, event["content"])

            elif event_type == "tool_start":
                yield {
                    "event": "tool_start",
                    "data": json.dumps({"tool": event["tool"], "description": event["description"]}),
                }

            elif event_type == "skills_loaded":
                yield {"event": "skills_loaded", "data": json.dumps({"skills": event["skills"]})}

            elif event_type == "done":
                if full_response:
                    chat_sessions[chat_session_id].append({
                        "role": "assistant",
                        "content": full_response,
                    })
                yield {"event": "done", "data": json.dumps({"session_id": chat_session_id})}

            elif event_type == "error":
                yield {"event": "error", "data": json.dumps({"message": event["message"]})}

    return EventSourceResponse(event_generator())


@app.post("/api/chat/new")
async def new_chat():
    session_id = uuid.uuid4().hex[:12]
    chat_sessions[session_id] = []
    return {"session_id": session_id}


@app.get("/api/chat/sessions")
async def list_chat_sessions():
    return [
        {
            "session_id": sid,
            "message_count": len(msgs),
            "preview": next((m["content"][:80] for m in msgs if m["role"] == "user"), ""),
        }
        for sid, msgs in chat_sessions.items()
    ]


@app.get("/api/chat/{session_id}/history")
async def chat_history(session_id: str):
    return chat_sessions.get(session_id, [])


# --- File upload ---
@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    params = request.query_params
    chat_session_id = params.get("session_id", uuid.uuid4().hex[:12])

    workspace = podcast_agent._get_workspace(chat_session_id)
    safe_name = Path(file.filename).name if file.filename else "upload"
    file_path = workspace / safe_name

    content = await file.read()
    file_path.write_bytes(content)

    # Track upload so next user message includes file context
    pending_uploads.setdefault(chat_session_id, []).append({
        "file_name": safe_name,
        "size": len(content),
    })

    return {
        "ok": True,
        "session_id": chat_session_id,
        "file_name": safe_name,
        "file_path": str(file_path),
        "size": len(content),
    }


# --- Workspace ---
@app.get("/api/workspace/{session_id}")
async def list_workspace(session_id: str):
    return podcast_agent.list_workspace_files(session_id)


@app.get("/api/workspace/{session_id}/{filename:path}")
async def get_workspace_file(session_id: str, filename: str):
    workspace = podcast_agent._get_workspace(session_id)
    file_path = workspace / filename

    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)

    try:
        file_path.resolve().relative_to(workspace.resolve())
    except ValueError:
        return JSONResponse({"error": "Invalid path"}, status_code=403)

    return FileResponse(str(file_path), filename=Path(filename).name)


@app.post("/api/review/{session_id}/cut")
async def cut_review_audio(session_id: str, request: Request):
    workspace = podcast_agent._get_workspace(session_id)
    review_path = workspace / "review_data.json"

    raw_body = await request.body()
    if raw_body:
        try:
            review_data = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            return JSONResponse({"error": f"Invalid review payload: {exc}"}, status_code=400)
        review_path.write_text(json.dumps(review_data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        try:
            review_data = _load_review_data(workspace)
        except FileNotFoundError:
            return JSONResponse({"error": "review_data.json not found"}, status_code=404)
        except json.JSONDecodeError as exc:
            return JSONResponse({"error": f"Invalid review_data.json: {exc}"}, status_code=400)

    audio_name = str(review_data.get("audio_url") or "").strip()
    if not audio_name:
        return JSONResponse({"error": "review_data.json is missing audio_url"}, status_code=400)

    audio_path = workspace / audio_name
    if not audio_path.exists():
        return JSONResponse({"error": f"Audio file not found: {audio_name}"}, status_code=404)

    delete_segments = _build_delete_segments(review_data)
    if not delete_segments:
        return JSONResponse({"error": "No enabled delete segments found in review_data.json"}, status_code=400)

    delete_segments_path = workspace / "delete_segments.json"
    delete_segments_path.write_text(
        json.dumps(
            {
                "segments": delete_segments,
                "summary": {
                    "segments": len(delete_segments),
                    "source": review_path.name,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_name = "podcast_cut.mp3"
    cut_result = _run_cut_pipeline(workspace, audio_path.name, delete_segments_path.name, output_name)
    if cut_result.returncode != 0:
        return JSONResponse(
            {
                "error": "Cut pipeline failed",
                "stdout": cut_result.stdout[-4000:],
                "stderr": cut_result.stderr[-4000:],
            },
            status_code=500,
        )

    output_path = workspace / output_name
    if not output_path.exists():
        return JSONResponse({"error": "Cut pipeline finished without producing output audio"}, status_code=500)

    original_duration = _probe_duration(audio_path)
    output_duration = _probe_duration(output_path)

    return {
        "ok": True,
        "session_id": session_id,
        "audio_url": output_name,
        "delete_segments_url": "delete_segments.json",
        "segments": delete_segments,
        "segments_count": len(delete_segments),
        "original_duration": round(original_duration, 3),
        "output_duration": round(output_duration, 3),
        "saved_duration": round(max(0.0, original_duration - output_duration), 3),
        "stdout": cut_result.stdout[-4000:],
    }


# --- Serve frontend ---
static_dir = Path(__file__).parent / "static"
if not static_dir.exists():
    static_dir = Path(__file__).parent.parent / "frontend" / "dist"

if static_dir.exists() and (static_dir / "index.html").exists():
    # Mount assets if they exist
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(static_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
