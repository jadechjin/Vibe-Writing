"""drop obsolete system definition columns from experimental_systems

Revision ID: 005_drop_sysdef_cols
Revises: 004_structure_skeletons
Create Date: 2026-03-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005_drop_sysdef_cols"
down_revision: str | None = "004_structure_skeletons"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLE = "experimental_systems"
_COLUMNS = [
    "research_goal",
    "samples_subjects",
    "variables_controls",
    "output_metrics",
    "methods_summary",
    "system_card_json",
]


def upgrade() -> None:
    for col in _COLUMNS:
        op.drop_column(_TABLE, col)


def downgrade() -> None:
    for col in _COLUMNS[:-1]:
        op.add_column(_TABLE, sa.Column(col, sa.String(), nullable=True))
    op.add_column(
        _TABLE,
        sa.Column("system_card_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.alter_column(_TABLE, "system_card_json", server_default=None)
