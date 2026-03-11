import re
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "003_evidence_draft_workflow.py"
)
REQUIRED_TABLES = [
    "figure_plans",
    "figure_plan_assets",
    "claims",
    "claim_evidence_links",
    "analysis_runs",
    "outlines",
    "outline_asset_bindings",
    "section_drafts",
    "review_comments",
    "workflow_instances",
    "workflow_events",
    "approval_tasks",
]


REQUIRED_INDEXES = [
    "ix_claim_evidence_links_unique_without_run",
    "ix_claim_evidence_links_unique_with_run",
]


def test_migration_declares_expected_revision_chain() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision: str = "003_evidence_draft_workflow"' in content
    assert 'down_revision: str | None = "002_assets_manifest"' in content


def test_migration_creates_all_required_tables() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    for table_name in REQUIRED_TABLES:
        pattern = re.compile(rf'op\.create_table\(\s*"{re.escape(table_name)}"')
        assert pattern.search(content)
        assert f'op.drop_table("{table_name}")' in content



def test_migration_does_not_set_null_on_claim_evidence_link_analysis_run_fk() -> None:
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert (
        'sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL")'
        not in content
    )
    assert 'sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"])' in content
