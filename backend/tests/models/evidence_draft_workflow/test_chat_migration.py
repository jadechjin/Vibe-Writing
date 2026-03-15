from __future__ import annotations

import re
from pathlib import Path

MIGRATION_007_PATH = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "007_figure_plan_chat.py"
)
MIGRATION_008_PATH = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "008_add_audit_fields_to_chat_tables.py"
)


def test_chat_migration_declares_expected_revision_chain() -> None:
    content = MIGRATION_007_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "007_figure_plan_chat"' in content
    assert 'down_revision: str | None = "006_figure_plan_skeleton_binding"' in content


def test_chat_migration_includes_required_constraints_and_indexes() -> None:
    content = MIGRATION_007_PATH.read_text(encoding="utf-8")

    assert re.search(
        r'op\.create_unique_constraint\(\s*"uq_figure_plan_chat_sessions_plan_provider"',
        content,
    )
    assert re.search(
        r'op\.create_index\(\s*"ix_figure_plan_chat_messages_session_turn"',
        content,
    )


def test_chat_migration_does_not_keep_duplicate_followup_revision() -> None:
    assert not MIGRATION_008_PATH.exists()
