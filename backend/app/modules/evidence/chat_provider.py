"""Chat provider adapter for invoking AI CLI tools with streaming output."""

from __future__ import annotations

import asyncio
import enum
import json
import logging
import re
import subprocess
import sys
import threading
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from app.common.errors import ErrorCode
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

CHAT_CLI_TIMEOUT_SECONDS = 300
BRIDGE_QUEUE_MAX_SIZE = 1000  # Prevent unbounded memory growth
_FALLBACK_SENTINEL = "__FALLBACK__"  # Marks assistant/result as fallback-only

# Session ID extraction patterns (used by all parsers)
_SESSION_ID_PATTERNS = [
    re.compile(r"SESSION_ID:\s*(\S+)"),
    re.compile(r'"session_id"\s*:\s*"([^"]+)"'),
    re.compile(r'"sessionId"\s*:\s*"([^"]+)"'),
    re.compile(r"session[_\s]?id[=:]\s*(\S+)", re.IGNORECASE),
]


@dataclass(slots=True)
class _BridgeEvent:
    """Event passed from subprocess thread to async consumer."""

    kind: str  # "stdout" | "stderr" | "exit" | "error"
    text: str | None = None
    returncode: int | None = None
    error: Exception | None = None


class ChatProvider(str, enum.Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"


def _build_chat_command(
    provider: ChatProvider,
    message: str,
    session_id: str | None = None,
) -> list[str]:
    if provider is ChatProvider.CLAUDE:
        # Options first, prompt last (best practice)
        # --verbose is required for --output-format stream-json
        # --include-partial-messages enables streaming of partial content
        # --disallowedTools prevents interactive tools in pipe mode
        # IMPORTANT: --disallowedTools is variadic (<tools...>), it will greedily
        # consume subsequent non-flag arguments. Use -- separator before the prompt.
        cmd = [
            "claude",
            "-p",
            "--verbose",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
            "--dangerously-skip-permissions",
            "--no-session-persistence",
            "--disallowedTools",
            "AskUserQuestion,EnterPlanMode,EnterWorktree,ExitWorktree",
        ]
        # NOTE: --no-session-persistence means --resume is not possible.
        # Multi-turn is handled by including conversation history in the prompt.
        cmd.append("--")  # Separator: everything after is positional (prompt)
        cmd.append(message)  # Prompt as last positional argument
        return cmd

    if provider is ChatProvider.GEMINI:
        cmd = ["gemini", "-p", message, "-o", "stream-json", "-y"]
        if session_id:
            cmd.extend(["--resume", session_id])
        return cmd

    # Codex via codeagent-wrapper
    wrapper = "codeagent-wrapper"
    if session_id:
        return [wrapper, "resume", session_id, message]
    return [wrapper, "--backend", "codex", message]


def _parse_claude_stream_event(line: str) -> tuple[str | None, str | None]:
    """Parse Claude Code CLI stream-json event.

    Returns:
        (text_content, session_id) tuple
    """
    line = line.strip()
    if not line:
        return None, None

    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        # Non-JSON line, might be plain text or session ID
        if any(pattern.search(line) for pattern in _SESSION_ID_PATTERNS):
            match = None
            for pattern in _SESSION_ID_PATTERNS:
                match = pattern.search(line)
                if match:
                    return None, match.group(1).strip().rstrip(",").strip('"')
            return None, None
        return line, None

    event_type = obj.get("type")

    # Extract session ID if present
    session_id = None
    if "session_id" in obj:
        session_id = obj["session_id"]
    elif "sessionId" in obj:
        session_id = obj["sessionId"]

    # PRIMARY: Claude Code CLI stream-json wraps raw API events as:
    # {"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}}
    if event_type == "stream_event":
        event = obj.get("event", {})
        inner_type = event.get("type")
        if inner_type == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                return delta.get("text"), session_id
        # Other stream_event subtypes (message_start, content_block_start/stop,
        # message_delta, message_stop) carry no renderable text — skip them.
        return None, session_id

    # FALLBACK: accumulated assistant message (only used when no stream_event deltas)
    # {"type":"assistant","message":{"content":[{"type":"text","text":"..."}],...}}
    if event_type == "assistant":
        return _FALLBACK_SENTINEL, session_id

    # FALLBACK: final result (only used when no stream_event deltas)
    # {"type":"result","result":"..."}
    if event_type == "result":
        result_text = obj.get("result")
        if isinstance(result_text, str) and result_text.strip():
            return _FALLBACK_SENTINEL, session_id
        return None, session_id

    # Raw API passthrough (non-wrapped): {"type":"content_block_delta","delta":{"text":"..."}}
    if event_type == "content_block_delta":
        delta = obj.get("delta", {})
        return delta.get("text"), session_id

    # Legacy: {"type":"message","role":"assistant","content":"..."}
    if event_type == "message":
        role = obj.get("role")
        if role == "assistant" or role is None:
            content = obj.get("content", "")
            if isinstance(content, str):
                return content, session_id
            if isinstance(content, list) and content:
                text_parts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                return "".join(text_parts) if text_parts else None, session_id

    return None, session_id


def _parse_gemini_stream_event(line: str) -> tuple[str | None, str | None]:
    """Parse Gemini CLI stream-json event.

    Returns:
        (text_content, session_id) tuple
    """
    line = line.strip()
    if not line:
        return None, None

    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        # Non-JSON line
        if any(pattern.search(line) for pattern in _SESSION_ID_PATTERNS):
            match = None
            for pattern in _SESSION_ID_PATTERNS:
                match = pattern.search(line)
                if match:
                    return None, match.group(1).strip().rstrip(",").strip('"')
            return None, None
        return line, None

    event_type = obj.get("type")

    # Extract session ID if present
    session_id = None
    if "session_id" in obj:
        session_id = obj["session_id"]
    elif "sessionId" in obj:
        session_id = obj["sessionId"]

    # Gemini CLI JSONL events
    # {"type":"message","role":"assistant","content":"..."}
    if event_type == "message" and obj.get("role") == "assistant":
        content = obj.get("content", "")
        if isinstance(content, str):
            return content, session_id

    # Legacy format: {"text":"..."}
    if "text" in obj and isinstance(obj["text"], str):
        return obj["text"], session_id

    # Fallback: {"content":"..."}
    if "content" in obj and isinstance(obj["content"], str):
        return obj["content"], session_id

    return None, session_id


def _parse_codex_stream_line(line: str) -> tuple[str | None, str | None]:
    """Parse Codex (via codeagent-wrapper) plain text output.

    Returns:
        (text_content, session_id) tuple
    """
    line = line.strip()
    if not line:
        return None, None

    # Check for session ID
    for pattern in _SESSION_ID_PATTERNS:
        match = pattern.search(line)
        if match:
            return None, match.group(1).strip().rstrip(",").strip('"')

    # Plain text content
    return line, None


def _extract_text_from_stream_json(line: str) -> str | None:
    """Extract text content from a stream-json line (Claude/Gemini format)."""
    line = line.strip()
    if not line:
        return None

    # Filter out session ID lines to prevent leaking to client
    if any(pattern.search(line) for pattern in _SESSION_ID_PATTERNS):
        logger.debug("Filtered session ID line: %s", line[:100])
        return None

    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        logger.debug("Non-JSON line (returning as-is): %s", line[:100])
        return line if line else None

    # Log the parsed JSON structure for debugging
    event_type = obj.get("type", "unknown")
    logger.debug("Parsed JSON event: type=%s keys=%s", event_type, list(obj.keys()))

    # PRIMARY: Claude Code CLI stream-json wrapped events
    if event_type == "stream_event":
        event = obj.get("event", {})
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text")
                if text:
                    logger.debug("Extracted from stream_event delta: %s", text[:50])
                return text
        return None

    # Claude Code CLI stream-json: {"type":"assistant",...} — skip to avoid duplication
    if event_type == "assistant":
        return None

    # Claude stream-json: {"type":"content_block_delta","delta":{"text":"..."}}
    if event_type == "content_block_delta":
        delta = obj.get("delta", {})
        text = delta.get("text")
        if text:
            logger.debug("Extracted from content_block_delta: %s", text[:50])
        return text

    # Claude stream-json: {"type":"result","result":"..."}
    if event_type == "result":
        result = obj.get("result")
        if result:
            logger.debug("Extracted from result: %s", str(result)[:50])
        return result

    # Gemini stream-json: {"text":"..."}
    if "text" in obj and isinstance(obj["text"], str):
        logger.debug("Extracted from text field: %s", obj["text"][:50])
        return obj["text"]

    # Fallback: if there's a content field
    if "content" in obj and isinstance(obj["content"], str):
        logger.debug("Extracted from content field: %s", obj["content"][:50])
        return obj["content"]

    logger.debug("No text extracted from event: type=%s", event_type)
    return None


def extract_session_id(output_lines: list[str]) -> str | None:
    """Try to extract a CLI session ID from collected output lines."""
    for line in reversed(output_lines):
        for pattern in _SESSION_ID_PATTERNS:
            match = pattern.search(line)
            if match:
                return match.group(1).strip().rstrip(",").strip('"')
    return None


def _start_chat_process(cmd: list[str]) -> subprocess.Popen[bytes]:
    """Start subprocess with platform-specific settings."""
    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
    }

    # Windows: hide console window
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore

    return subprocess.Popen(cmd, **kwargs)


def _pump_pipe(pipe, kind: str, loop, queue: asyncio.Queue) -> None:
    """Read pipe line-by-line and push events to async queue."""
    try:
        for line_bytes in iter(pipe.readline, b""):
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace")
            event = _BridgeEvent(kind=kind, text=line)
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:
                # Event loop closed, consumer already gone
                break
    except Exception as exc:
        try:
            event = _BridgeEvent(kind="error", error=exc)
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except RuntimeError:
            # Event loop closed, consumer already gone
            pass
    finally:
        pipe.close()


def _run_process_bridge(cmd: list[str], loop, queue: asyncio.Queue, proc_ref: list) -> None:
    """Run subprocess and bridge stdout/stderr to async queue.

    Args:
        proc_ref: Mutable list to store process reference for external termination.
    """
    proc = None
    try:
        proc = _start_chat_process(cmd)
        proc_ref.append(proc)  # Allow async side to terminate if needed

        # Start reader threads for stdout and stderr
        stdout_thread = threading.Thread(
            target=_pump_pipe,
            args=(proc.stdout, "stdout", loop, queue),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_pump_pipe,
            args=(proc.stderr, "stderr", loop, queue),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        # Wait for process to complete
        returncode = proc.wait()

        # Wait for reader threads to finish
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        # Send exit event (check if loop is still open)
        try:
            event = _BridgeEvent(kind="exit", returncode=returncode)
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except RuntimeError:
            # Event loop closed, consumer already gone
            pass

    except Exception as exc:
        try:
            event = _BridgeEvent(kind="error", error=exc)
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except RuntimeError:
            # Event loop closed, consumer already gone
            pass

        if proc and proc.poll() is None:
            proc.kill()


async def _iter_bridge_events(
    cmd: list[str],
    *,
    timeout_seconds: int,
) -> AsyncGenerator[_BridgeEvent, None]:
    """Iterate bridge events with total timeout control."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[_BridgeEvent] = asyncio.Queue(maxsize=BRIDGE_QUEUE_MAX_SIZE)
    proc_ref: list[subprocess.Popen] = []  # Mutable reference for cleanup

    # Start bridge thread
    bridge_thread = threading.Thread(
        target=_run_process_bridge,
        args=(cmd, loop, queue, proc_ref),
        daemon=True,
    )
    bridge_thread.start()

    deadline = time.monotonic() + timeout_seconds
    exited = False

    try:
        while not exited:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError("CLI execution exceeded timeout")

            try:
                event = await asyncio.wait_for(queue.get(), timeout=remaining)
            except asyncio.TimeoutError as err:
                raise asyncio.TimeoutError(
                    "CLI execution exceeded timeout"
                ) from err

            if event.kind == "exit":
                exited = True

            yield event

    finally:
        # Ensure process cleanup on timeout/cancel
        if proc_ref and proc_ref[0].poll() is None:
            try:
                proc_ref[0].terminate()
                # Give it a moment to terminate gracefully
                try:
                    proc_ref[0].wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc_ref[0].kill()
            except Exception as exc:
                logger.warning("Failed to terminate subprocess: %s", exc)

        # Ensure thread cleanup
        bridge_thread.join(timeout=1)


def _build_provider_exception(
    provider: ChatProvider,
    reason: str,
    *,
    details: dict[str, object] | None = None,
) -> AppException:
    """Build AppException for provider failures.

    Note: Do not include full cmd or user input in details to avoid log leakage.
    """
    safe_details = details.copy() if details else {}
    # Remove sensitive data from details
    safe_details.pop("cmd", None)

    return AppException(
        code=ErrorCode.WORKFLOW_ERROR,
        message=f"Chat provider {provider.value} failed: {reason}",
        details=safe_details,
    )


async def invoke_chat_stream(
    provider: ChatProvider,
    message: str,
    session_id: str | None = None,
    context: str = "",
) -> AsyncGenerator[str, None]:
    """Invoke a CLI agent and yield text chunks as they arrive.

    Raises:
        AppException: If CLI tool is not found, times out, or exits with error.
    """
    full_message = f"{context}\n\n{message}" if context else message
    cmd = _build_chat_command(provider, full_message, session_id)

    logger.info("Chat CLI invoke: provider=%s session=%s", provider.value, session_id)
    logger.debug("Chat CLI command: %s", " ".join(cmd))

    collected_stdout: list[str] = []
    collected_stderr: list[str] = []
    line_count = 0
    extracted_session_id: str | None = None
    has_streamed_deltas = False  # Track if we got real stream_event deltas
    fallback_text: str | None = None  # Last assistant/result full text

    try:
        async for event in _iter_bridge_events(cmd, timeout_seconds=CHAT_CLI_TIMEOUT_SECONDS):
            if event.kind == "stdout":
                if event.text:
                    collected_stdout.append(event.text)
                    line_count += 1

                    # Log first 20 lines of raw output for debugging
                    if line_count <= 20:
                        logger.debug(
                            "[%s] Raw stdout line %d: %s",
                            provider.value,
                            line_count,
                            event.text[:200] if len(event.text) > 200 else event.text,
                        )

                    # Use provider-specific parser
                    text_content = None
                    session_id_from_line = None

                    if provider is ChatProvider.CLAUDE:
                        text_content, session_id_from_line = _parse_claude_stream_event(event.text)
                    elif provider is ChatProvider.GEMINI:
                        text_content, session_id_from_line = _parse_gemini_stream_event(event.text)
                    elif provider is ChatProvider.CODEX:
                        text_content, session_id_from_line = _parse_codex_stream_line(event.text)

                    # Store session ID if found
                    if session_id_from_line and not extracted_session_id:
                        extracted_session_id = session_id_from_line
                        logger.debug("Extracted session_id from stream: %s", extracted_session_id)

                    # Yield text content if present (skip fallback sentinels)
                    if text_content and text_content != _FALLBACK_SENTINEL:
                        has_streamed_deltas = True
                        yield text_content
                    elif text_content == _FALLBACK_SENTINEL:
                        # Store fallback: extract full text from the raw line
                        try:
                            obj = json.loads(event.text.strip())
                            if obj.get("type") == "assistant":
                                msg = obj.get("message", {})
                                content = msg.get("content", [])
                                if isinstance(content, list):
                                    parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                                    fallback_text = "".join(parts) or fallback_text
                                elif isinstance(content, str):
                                    fallback_text = content
                            elif obj.get("type") == "result":
                                r = obj.get("result")
                                if isinstance(r, str):
                                    fallback_text = r
                        except (json.JSONDecodeError, AttributeError):
                            pass

            elif event.kind == "stderr":
                if event.text:
                    collected_stderr.append(event.text)
                    # Only log stderr at debug level to avoid log amplification
                    logger.debug("Chat CLI stderr: %s", event.text.strip())

            elif event.kind == "error":
                if isinstance(event.error, FileNotFoundError):
                    raise _build_provider_exception(
                        provider,
                        "CLI tool not found",
                        details={"provider": provider.value},
                    )
                raise _build_provider_exception(
                    provider,
                    f"Bridge error: {type(event.error).__name__}",
                    details={"error_type": type(event.error).__name__},
                )

            elif event.kind == "exit":
                if event.returncode != 0:
                    # Only include last 5 lines of stderr to avoid log bloat
                    stderr_summary = "".join(collected_stderr[-5:])[:500]  # Max 500 chars
                    # Log stderr for debugging (helps diagnose CLI parameter issues)
                    logger.error(
                        "Chat CLI failed: provider=%s returncode=%d stderr=%s",
                        provider.value,
                        event.returncode,
                        stderr_summary,
                    )
                    raise _build_provider_exception(
                        provider,
                        f"CLI exited with code {event.returncode}",
                        details={
                            "returncode": event.returncode,
                            "stderr_summary": stderr_summary,
                        },
                    )

    except asyncio.TimeoutError as exc:
        raise _build_provider_exception(
            provider,
            f"CLI execution timeout after {CHAT_CLI_TIMEOUT_SECONDS}s",
            details={"timeout_seconds": CHAT_CLI_TIMEOUT_SECONDS},
        ) from exc

    # Log summary statistics
    logger.info(
        "Chat CLI completed: provider=%s total_lines=%d stderr_lines=%d streamed_deltas=%s",
        provider.value,
        len(collected_stdout),
        len(collected_stderr),
        has_streamed_deltas,
    )

    # Fallback: if no streaming deltas were received, yield the accumulated full text
    if not has_streamed_deltas and fallback_text:
        logger.info("No stream_event deltas received, using fallback text (%d chars)", len(fallback_text))
        yield fallback_text

    # Use session ID extracted during streaming, or fallback to legacy extraction
    if not extracted_session_id:
        extracted_session_id = extract_session_id(collected_stdout)

    if extracted_session_id:
        logger.debug("Final session_id: %s", extracted_session_id)
        yield f"\n__SESSION_ID__:{extracted_session_id}"
    else:
        logger.warning("No session_id found in CLI output for provider=%s", provider.value)
