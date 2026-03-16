"""FastAPI app for PodcastCut chat-based agent."""

import hashlib
import json
import logging
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agent import PodcastAgent

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="PodcastCut")

podcast_agent = PodcastAgent()

# Auth state (in-memory)
users: dict[str, str] = {}  # email -> hashed_password
sessions: dict[str, dict] = {}  # session_id -> {email}

# Chat history (in-memory)
chat_sessions: dict[str, list[dict]] = {}  # chat_session_id -> [{role, content}]
pending_uploads: dict[str, list[dict]] = {}  # chat_session_id -> [{file_name, size}]


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and not path.startswith("/api/auth/") and not path.startswith("/api/debug/"):
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
        full_response = []
        async for event in podcast_agent.stream_response(chat_session_id, agent_message):
            event_type = event.get("type", "")

            if event_type == "text":
                yield {"event": "text", "data": json.dumps({"content": event["content"]})}
                full_response.append(event["content"])

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
                        "content": "\n".join(full_response),
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
