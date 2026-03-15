"""Tests for provider-specific stream parsers."""

import pytest

from app.modules.evidence.chat_provider import (
    _parse_claude_stream_event,
    _parse_codex_stream_line,
    _parse_gemini_stream_event,
)


class TestClaudeParser:
    """Test Claude Code CLI stream-json parser."""

    def test_content_block_delta(self):
        """Test parsing content_block_delta event."""
        line = '{"type":"content_block_delta","delta":{"text":"Hello"}}'
        text, session_id = _parse_claude_stream_event(line)
        assert text == "Hello"
        assert session_id is None

    def test_message_event(self):
        """Test parsing message event with assistant role."""
        line = '{"type":"message","role":"assistant","content":"World"}'
        text, session_id = _parse_claude_stream_event(line)
        assert text == "World"
        assert session_id is None

    def test_result_event(self):
        """Test parsing result event."""
        line = '{"type":"result","result":"Done"}'
        text, session_id = _parse_claude_stream_event(line)
        assert text == "Done"
        assert session_id is None

    def test_session_id_extraction(self):
        """Test extracting session ID from JSON."""
        line = '{"type":"message","session_id":"abc123","content":"Hi"}'
        text, session_id = _parse_claude_stream_event(line)
        assert text == "Hi"
        assert session_id == "abc123"

    def test_plain_text_session_id(self):
        """Test extracting session ID from plain text line."""
        line = "SESSION_ID: xyz789"
        text, session_id = _parse_claude_stream_event(line)
        assert text is None
        assert session_id == "xyz789"

    def test_empty_line(self):
        """Test handling empty line."""
        text, session_id = _parse_claude_stream_event("")
        assert text is None
        assert session_id is None


class TestGeminiParser:
    """Test Gemini CLI stream-json parser."""

    def test_message_event(self):
        """Test parsing message event with assistant role."""
        line = '{"type":"message","role":"assistant","content":"Hello Gemini"}'
        text, session_id = _parse_gemini_stream_event(line)
        assert text == "Hello Gemini"
        assert session_id is None

    def test_legacy_text_field(self):
        """Test parsing legacy text field."""
        line = '{"text":"Legacy format"}'
        text, session_id = _parse_gemini_stream_event(line)
        assert text == "Legacy format"
        assert session_id is None

    def test_content_field_fallback(self):
        """Test fallback to content field."""
        line = '{"content":"Fallback content"}'
        text, session_id = _parse_gemini_stream_event(line)
        assert text == "Fallback content"
        assert session_id is None

    def test_session_id_extraction(self):
        """Test extracting session ID."""
        line = '{"type":"message","sessionId":"gem456","content":"Hi"}'
        text, session_id = _parse_gemini_stream_event(line)
        assert text == "Hi"
        assert session_id == "gem456"


class TestCodexParser:
    """Test Codex (codeagent-wrapper) plain text parser."""

    def test_plain_text(self):
        """Test parsing plain text line."""
        line = "This is plain text output"
        text, session_id = _parse_codex_stream_line(line)
        assert text == "This is plain text output"
        assert session_id is None

    def test_session_id_extraction(self):
        """Test extracting session ID from text."""
        line = "SESSION_ID: codex999"
        text, session_id = _parse_codex_stream_line(line)
        assert text is None
        assert session_id == "codex999"

    def test_empty_line(self):
        """Test handling empty line."""
        text, session_id = _parse_codex_stream_line("")
        assert text is None
        assert session_id is None
