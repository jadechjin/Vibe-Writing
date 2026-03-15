"""Tests for chat provider CLI bridge."""

from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.evidence.chat_provider import (
    ChatProvider,
    _build_chat_command,
    extract_session_id,
    invoke_chat_stream,
)


class TestBuildChatCommand:
    """Test chat command construction."""

    def test_build_claude_command_includes_verbose(self):
        """Test that Claude command includes --verbose flag."""
        cmd = _build_chat_command(ChatProvider.CLAUDE, "test message")
        assert "--verbose" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "-p" in cmd
        assert cmd[-1] == "test message"  # Prompt at the end

    def test_build_claude_command_with_session(self):
        """Test that Claude command with session includes --resume."""
        cmd = _build_chat_command(ChatProvider.CLAUDE, "test", session_id="abc123")
        assert "--resume" in cmd
        assert "abc123" in cmd
        assert "--verbose" in cmd
        assert cmd[-1] == "test"  # Prompt still at the end

    def test_build_claude_command_order(self):
        """Test that Claude command has correct argument order."""
        cmd = _build_chat_command(ChatProvider.CLAUDE, "hello")
        # Options should come before the prompt
        verbose_idx = cmd.index("--verbose")
        prompt_idx = cmd.index("hello")
        assert verbose_idx < prompt_idx

    def test_build_gemini_command_unchanged(self):
        """Test that Gemini command is not affected by Claude changes."""
        cmd = _build_chat_command(ChatProvider.GEMINI, "test")
        assert "gemini" in cmd
        assert "-o" in cmd
        assert "stream-json" in cmd

    def test_build_codex_command_unchanged(self):
        """Test that Codex command is not affected by Claude changes."""
        cmd = _build_chat_command(ChatProvider.CODEX, "test")
        assert "codeagent-wrapper" in cmd
        assert "--backend" in cmd
        assert "codex" in cmd


class TestExtractSessionId:
    """Test session ID extraction from CLI output."""

    def test_extract_session_id_pattern_1(self):
        lines = ["Some output", "SESSION_ID: abc123", "More output"]
        assert extract_session_id(lines) == "abc123"

    def test_extract_session_id_pattern_2(self):
        lines = ['{"session_id": "xyz789"}']
        assert extract_session_id(lines) == "xyz789"

    def test_extract_session_id_pattern_3(self):
        lines = ['{"sessionId": "def456"}']
        assert extract_session_id(lines) == "def456"

    def test_extract_session_id_no_match(self):
        lines = ["No session ID here"]
        assert extract_session_id(lines) is None

    def test_extract_session_id_empty(self):
        assert extract_session_id([]) is None


class TestInvokeChatStream:
    """Test chat provider stream invocation."""

    @pytest.mark.asyncio
    async def test_invoke_claude_success(self):
        """Test successful Claude stream-json invocation."""
        # Mock subprocess that returns stream-json format
        mock_proc = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.stdout.readline = Mock(
            side_effect=[
                b'{"type":"content_block_delta","delta":{"text":"Hello"}}\n',
                b'{"type":"content_block_delta","delta":{"text":" World"}}\n',
                b"SESSION_ID: test-session-123\n",
                b"",  # EOF
            ]
        )
        mock_proc.stderr.readline = Mock(return_value=b"")
        mock_proc.wait = Mock(return_value=0)
        mock_proc.poll = Mock(return_value=0)

        with patch("app.modules.evidence.chat_provider._start_chat_process", return_value=mock_proc):
            chunks = []
            async for chunk in invoke_chat_stream(ChatProvider.CLAUDE, "test message"):
                chunks.append(chunk)

            # Should get text chunks and session ID
            assert "Hello" in chunks
            assert " World" in chunks
            assert any("__SESSION_ID__:test-session-123" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_invoke_gemini_success(self):
        """Test successful Gemini stream-json invocation."""
        mock_proc = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.stdout.readline = Mock(
            side_effect=[
                b'{"text":"Gemini "}\n',
                b'{"text":"response"}\n',
                b"",  # EOF
            ]
        )
        mock_proc.stderr.readline = Mock(return_value=b"")
        mock_proc.wait = Mock(return_value=0)
        mock_proc.poll = Mock(return_value=0)

        with patch("app.modules.evidence.chat_provider._start_chat_process", return_value=mock_proc):
            chunks = []
            async for chunk in invoke_chat_stream(ChatProvider.GEMINI, "test message"):
                chunks.append(chunk)

            assert "Gemini " in chunks
            assert "response" in chunks

    @pytest.mark.asyncio
    async def test_invoke_codex_success(self):
        """Test successful Codex raw text invocation."""
        mock_proc = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.stdout.readline = Mock(
            side_effect=[
                b"Line 1\n",
                b"Line 2\n",
                b"SESSION_ID: codex-session-456\n",
                b"",  # EOF
            ]
        )
        mock_proc.stderr.readline = Mock(return_value=b"")
        mock_proc.wait = Mock(return_value=0)
        mock_proc.poll = Mock(return_value=0)

        with patch("app.modules.evidence.chat_provider._start_chat_process", return_value=mock_proc):
            chunks = []
            async for chunk in invoke_chat_stream(ChatProvider.CODEX, "test message"):
                chunks.append(chunk)

            assert "Line 1" in chunks
            assert "Line 2" in chunks
            assert any("__SESSION_ID__:codex-session-456" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_invoke_cli_not_found(self):
        """Test CLI tool not found error."""
        with patch(
            "app.modules.evidence.chat_provider._start_chat_process",
            side_effect=FileNotFoundError("claude not found"),
        ):
            with pytest.raises(AppException) as exc_info:
                async for _ in invoke_chat_stream(ChatProvider.CLAUDE, "test"):
                    pass

            assert "not found" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_invoke_timeout(self):
        """Test CLI timeout handling."""
        mock_proc = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()

        # Simulate slow readline by blocking forever
        def slow_readline():
            import time
            time.sleep(1000)
            return b""

        mock_proc.stdout.readline = Mock(side_effect=slow_readline)
        mock_proc.stderr.readline = Mock(return_value=b"")
        mock_proc.wait = Mock(return_value=0)
        mock_proc.poll = Mock(return_value=None)

        with patch("app.modules.evidence.chat_provider._start_chat_process", return_value=mock_proc):
            with patch("app.modules.evidence.chat_provider.CHAT_CLI_TIMEOUT_SECONDS", 0.1):
                with pytest.raises(AppException) as exc_info:
                    async for _ in invoke_chat_stream(ChatProvider.CLAUDE, "test"):
                        pass

                assert "timeout" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_invoke_non_zero_exit(self):
        """Test CLI non-zero exit code."""
        mock_proc = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.stdout.readline = Mock(return_value=b"")
        mock_proc.stderr.readline = Mock(
            side_effect=[
                b"Error: something went wrong\n",
                b"",
            ]
        )
        mock_proc.wait = Mock(return_value=1)
        mock_proc.poll = Mock(return_value=1)

        with patch("app.modules.evidence.chat_provider._start_chat_process", return_value=mock_proc):
            with pytest.raises(AppException) as exc_info:
                async for _ in invoke_chat_stream(ChatProvider.CLAUDE, "test"):
                    pass

            assert "exited with code 1" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_invoke_with_context(self):
        """Test invocation with context prepended."""
        mock_proc = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.stdout.readline = Mock(
            side_effect=[
                b'{"type":"content_block_delta","delta":{"text":"OK"}}\n',
                b"",
            ]
        )
        mock_proc.stderr.readline = Mock(return_value=b"")
        mock_proc.wait = Mock(return_value=0)
        mock_proc.poll = Mock(return_value=0)

        with patch("app.modules.evidence.chat_provider._start_chat_process", return_value=mock_proc):
            chunks = []
            async for chunk in invoke_chat_stream(ChatProvider.CLAUDE, "message", context="context info"):
                chunks.append(chunk)

            assert "OK" in chunks

