from __future__ import annotations

import re
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "008_analysis_run_image_analysis.py"
)


def test_analysis_run_image_analysis_migration_declares_expected_revision_chain() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "008_analysis_run_image_analysis"' in content
    assert 'down_revision: str | None = "007_figure_plan_chat"' in content


def test_analysis_run_image_analysis_migration_adds_columns_and_index() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert re.search(
        r'op\.add_column\([^)]*"figure_plan_id"[^)]*sa\.String\(length=36\)[^)]*nullable=True',
        content,
        re.DOTALL,
    )
    assert re.search(
        r'op\.add_column\([^)]*"analysis_type"[^)]*sa\.String\(length=50\)[^)]*server_default="comprehensive"',
        content,
        re.DOTALL,
    )
    assert re.search(
        r'op\.create_foreign_key\(\s*(?:_FK_NAME|"fk_analysis_runs_figure_plan_id_figure_plans")',
        content,
    )
    assert re.search(
        r'op\.create_index\(\s*(?:_INDEX_NAME|"ix_analysis_runs_figure_plan_id")',
        content,
    )


def test_analysis_run_image_analysis_migration_is_reversible() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert re.search(
        r'op\.drop_index\(\s*_?INDEX_NAME|"ix_analysis_runs_figure_plan_id"',
        content,
    )
    assert re.search(
        r'op\.drop_constraint\(\s*_?FK_NAME|"fk_analysis_runs_figure_plan_id_figure_plans"',
        content,
    )
    assert re.search(r'op\.drop_column\([^)]*"analysis_type"', content)
    assert re.search(r'op\.drop_column\([^)]*"figure_plan_id"', content)
