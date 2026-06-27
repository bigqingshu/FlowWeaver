from __future__ import annotations

from alembic import op

revision = "20260627_0005"
down_revision = "20260627_0004"
branch_labels = None
depends_on = None

_NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    with op.batch_alter_table(
        "workflow_runs",
        recreate="always",
        naming_convention=_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_workflow_runs_workflow_id_workflow_definitions",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_workflow_runs_workflow_id_workflows",
            "workflows",
            ["workflow_id"],
            ["workflow_id"],
        )
        batch_op.create_foreign_key(
            "fk_workflow_runs_revision_id_workflow_revisions",
            "workflow_revisions",
            ["revision_id"],
            ["revision_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "workflow_runs",
        recreate="always",
        naming_convention=_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_workflow_runs_revision_id_workflow_revisions",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_workflow_runs_workflow_id_workflows",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_workflow_runs_workflow_id_workflow_definitions",
            "workflow_definitions",
            ["workflow_id"],
            ["workflow_id"],
        )
