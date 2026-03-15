from __future__ import annotations

import re
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "009_chat_session_scope.py"
)


def test_chat_session_scope_migration_declares_expected_revision_chain() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "009_chat_session_scope"' in content
    assert 'down_revision: str | None = "008_analysis_run_image_analysis"' in content


def test_chat_session_scope_migration_updates_scope_and_unique_constraint() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert re.search(
        r'add_column\([^)]*"scope"[^)]*sa\.String\(length=50\)[^)]*server_default="planning"',
        content,
        re.DOTALL,
    )
    assert "uq_figure_plan_chat_sessions_plan_provider" in content
    assert "uq_figure_plan_chat_sessions_plan_provider_scope" in content


def test_chat_session_scope_migration_is_reversible() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert re.search(r'drop_constraint\(', content)
    assert re.search(r'drop_column\([^)]*"scope"', content)
