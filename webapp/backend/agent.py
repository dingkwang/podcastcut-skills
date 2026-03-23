"""PodcastCut agent orchestrator using claude-agent-sdk."""

import logging
import os
import time
from pathlib import Path
from typing import Any, AsyncGenerator

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
)
from claude_agent_sdk._errors import ProcessError

logger = logging.getLogger(__name__)

WORKSPACES_ROOT = Path(os.environ.get("WORKSPACES_ROOT", "workspaces"))

# Path to the directory containing .claude/skills/
PLUGIN_DIR = Path(__file__).parent

SKILLS_DIR = PLUGIN_DIR / "skills"


def _discover_skills() -> list[str]:
    """Read skill names from SKILL.md frontmatter in the skills directory."""
    skills = []
    if not SKILLS_DIR.is_dir():
        return skills
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.startswith("name:"):
                    skills.append(line.split(":", 1)[1].strip())
                    break
            else:
                # Fallback to directory name
                skills.append(skill_dir.name)
        except Exception:
            skills.append(skill_dir.name)
    return skills


SYSTEM_PROMPT = """你是一个播客后期制作助手。你可以帮助用户处理音频文件。

你已经加载了播客后期制作相关的 skills，请根据用户需求灵活使用。
不要假设用户需要走完所有步骤，根据对话灵活使用工具。
每次使用工具后，告诉用户进展和结果。
工作区中的文件会自动显示在右侧面板中。

重要：所有文件操作都在当前工作目录（用户的工作区）中进行。
重要：执行 backend 的 Python 脚本时，不要使用系统 `python`、`python3`、`pip` 或 `pip3`。
请统一使用项目虚拟环境里的解释器：
`/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python`

如果需要运行某个 backend 脚本，命令应该像这样：
`/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/.../script.py ...`

不要尝试临时安装依赖；这个虚拟环境里已经包含 backend 所需的 Python 包。

当用户要你分析播客、准备审查稿、做审查画布、找出该删的内容、或者生成 review data 时：
1. 优先使用 review-canvas skill
2. 必须优先使用 review-canvas skill 自己目录中的 DashScope FunASR 转录能力；只有 DashScope 明确失败时，才允许回退到 OpenRouter Gemini
3. 真实转录入口在：
`/Users/lincolnwang/podcastcut-skills/webapp/backend/skills/review_canvas/review_asr.py`
4. 对审查稿任务，优先直接执行 review-canvas skill 自带脚本：
`/Users/lincolnwang/podcastcut-skills/webapp/backend/skills/review_canvas/generate_review_data.py`
5. 这个脚本负责真实转录并落盘 `transcript.json` 和 `review_data.json`
6. 文本清理、删除建议、块和精剪判断由 Claude 自己完成，不要再调用独立的 transcript-correction LLM 脚本
7. `review_data.json` 必须严格符合 `review_data.schema.json`
8. 输出的数据模型要与 PodcastCut 审查画布一致：顶层包含 `audio_url`、`audio_duration`、`sentences`、`blocks`、`fineEdits`
9. 如果用户已经明确说出说话人数，就把这个人数传给生成脚本；如果用户没有明确说，就不要硬编码 `--speakers 2`，优先让 DashScope 自行分离说话人
10. 只要 DashScope FunASR 或 OpenRouter Gemini 中至少一个可用，就不要生成空壳 `review_data.json`
11. 文件必须是合法 JSON；如果第一次写坏了，必须继续修到能通过 `/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/review_canvas/validate_review_data.py review_data.json`

只有在你已经明确尝试过 DashScope FunASR，必要时也尝试过 OpenRouter Gemini，并且拿到了可说明的失败原因时，才允许退回最小可用版本。此时必须在回复中明确说出失败原因，不要假装已经完成了真实审查。"""


class PodcastAgent:
    """Agent for podcast post-production using Claude Agent SDK.

    Each chat session gets an isolated workspace directory.
    The SDK handles the agentic loop internally — we just send messages
    and stream back the responses.
    """

    def __init__(self):
        WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, str] = {}  # chat_session_id -> sdk_session_id
        logger.info(
            "PodcastAgent initialized",
            extra={"workspaces_root": str(WORKSPACES_ROOT), "plugin_dir": str(PLUGIN_DIR)},
        )

    def _get_workspace(self, session_id: str) -> Path:
        """Get or create workspace directory for a session."""
        workspace = WORKSPACES_ROOT / session_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _create_client_options(
        self,
        session_id: str,
        resume_session_id: str | None = None,
    ) -> ClaudeAgentOptions:
        """Create ClaudeAgentOptions for a query."""
        workspace = self._get_workspace(session_id)

        options = ClaudeAgentOptions(
            cwd=str(workspace),
            model=os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
            system_prompt=SYSTEM_PROMPT,
            # Load skills from the plugin directory
            plugins=[{"type": "local", "path": str(PLUGIN_DIR)}],
            # Allow Skill invocation + built-in tools (Bash, Read, Write, Glob, Grep)
            allowed_tools=["Skill", "Bash", "Read", "Write", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            resume=resume_session_id,
        )
        return options

    def _format_tool_use(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Format tool usage for display in the chat UI."""
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if "transcribe" in command:
                return "Transcribing audio..."
            elif "correct" in command:
                return "Correcting transcript..."
            elif "extract" in command:
                return "Extracting voice samples..."
            elif "create_model" in command:
                return "Creating voice model..."
            elif "tts" in command:
                return "Generating speech..."
            elif "merge" in command:
                return "Merging audio segments..."
            elif len(command) > 60:
                return f"Running: {command[:57]}..."
            return f"Running: {command}"
        elif tool_name == "Skill":
            skill_name = tool_input.get("skill", "unknown")
            return f"Using skill: {skill_name}"
        elif tool_name == "Read":
            return f"Reading: {tool_input.get('file_path', '')}"
        elif tool_name == "Write":
            return f"Writing: {tool_input.get('file_path', '')}"
        elif tool_name == "Glob":
            return f"Finding files: {tool_input.get('pattern', '')}"
        elif tool_name == "Grep":
            return f"Searching: {tool_input.get('pattern', '')}"
        return f"Using: {tool_name}"

    async def stream_response(
        self,
        session_id: str,
        user_message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream agent responses as events.

        Yields dicts with event types:
        - {"type": "text", "content": "..."}
        - {"type": "tool_start", "tool": "...", "description": "..."}
        - {"type": "done", "session_id": "..."}
        - {"type": "error", "message": "..."}
        """
        resume_session_id = self._sessions.get(session_id)
        options = self._create_client_options(session_id, resume_session_id)
        client = ClaudeSDKClient(options=options)

        try:
            # Connect with resume fallback
            try:
                await client.connect()
            except (ProcessError, Exception) as e:
                if resume_session_id:
                    logger.warning(
                        "Resume failed, starting fresh",
                        extra={"session_id": session_id, "error": str(e)},
                    )
                    self._sessions.pop(session_id, None)
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                    options = self._create_client_options(session_id, None)
                    client = ClaudeSDKClient(options=options)
                    await client.connect()
                else:
                    raise

            # Send the user message
            await client.query(user_message)

            # Stream responses
            async for message in client.receive_response():
                logger.info("SDK message received: type=%s data=%s",
                    type(message).__name__, repr(message)[:500])

                if isinstance(message, SystemMessage):
                    if message.subtype == "init":
                        skills = _discover_skills()
                        logger.info("Skills loaded", extra={"skills": skills})
                        yield {"type": "skills_loaded", "skills": skills}
                    else:
                        logger.info("SDK system message", extra={"subtype": message.subtype})
                    continue

                if isinstance(message, ResultMessage):
                    if hasattr(message, "session_id") and message.session_id:
                        self._sessions[session_id] = message.session_id
                    # Forward result text if present (e.g. /skills response)
                    result_text = getattr(message, "result", None)
                    if result_text:
                        yield {"type": "text", "content": result_text}
                    logger.info(
                        "Query completed",
                        extra={
                            "session_id": session_id,
                            "cost_usd": getattr(message, "total_cost_usd", 0),
                            "result_preview": (result_text or "")[:200],
                        },
                    )
                    continue

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield {"type": "text", "content": block.text}
                        elif isinstance(block, ToolUseBlock):
                            description = self._format_tool_use(block.name, block.input or {})
                            yield {
                                "type": "tool_start",
                                "tool": block.name,
                                "description": description,
                            }

            yield {"type": "done", "session_id": session_id}

        except Exception as e:
            logger.error("Agent stream error", extra={"error": str(e)}, exc_info=True)
            yield {"type": "error", "message": str(e)}

        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    def list_workspace_files(self, session_id: str) -> list[dict[str, Any]]:
        """List files in a session's workspace."""
        workspace = self._get_workspace(session_id)
        files = []
        for root, dirs, filenames in os.walk(workspace):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in sorted(filenames):
                if fname.startswith("."):
                    continue
                fpath = Path(root) / fname
                rel = fpath.relative_to(workspace)
                stat = fpath.stat()
                files.append({
                    "name": str(rel),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "type": fpath.suffix.lstrip("."),
                })
        return files
