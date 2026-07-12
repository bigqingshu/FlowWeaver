from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "20260712_0025"
down_revision = "20260711_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "node_task_result_output_bindings",
        sa.Column("result_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("node_run_id", sa.Text(), nullable=False),
        sa.Column("output_slot", sa.Text(), nullable=False),
        sa.Column("output_ref_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["node_task_results.result_id"],
        ),
        sa.ForeignKeyConstraint(["task_id"], ["node_tasks.task_id"]),
        sa.ForeignKeyConstraint(["node_run_id"], ["node_runs.node_run_id"]),
        sa.PrimaryKeyConstraint("result_id", "output_slot"),
    )
    op.create_index(
        "idx_node_task_result_bindings_output_ref",
        "node_task_result_output_bindings",
        ["output_ref_id"],
    )
    op.create_index(
        "idx_node_task_result_bindings_node_slot",
        "node_task_result_output_bindings",
        ["node_run_id", "output_slot"],
    )
    _backfill_output_bindings()


def downgrade() -> None:
    op.drop_index(
        "idx_node_task_result_bindings_node_slot",
        table_name="node_task_result_output_bindings",
    )
    op.drop_index(
        "idx_node_task_result_bindings_output_ref",
        table_name="node_task_result_output_bindings",
    )
    op.drop_table("node_task_result_output_bindings")


def _backfill_output_bindings() -> None:
    connection = op.get_bind()
    records = connection.execute(
        sa.text(
            "SELECT result_id, task_id, node_run_id, "
            "output_slot_bindings_json FROM node_task_results"
        )
    ).mappings()
    rows: list[dict[str, str]] = []
    for record in records:
        bindings = _load_bindings(record["output_slot_bindings_json"])
        for output_slot, output_ref_id in bindings.items():
            rows.append(
                {
                    "result_id": str(record["result_id"]),
                    "task_id": str(record["task_id"]),
                    "node_run_id": str(record["node_run_id"]),
                    "output_slot": output_slot,
                    "output_ref_id": output_ref_id,
                }
            )
    if not rows:
        return
    bindings_table = sa.table(
        "node_task_result_output_bindings",
        sa.column("result_id", sa.Text()),
        sa.column("task_id", sa.Text()),
        sa.column("node_run_id", sa.Text()),
        sa.column("output_slot", sa.Text()),
        sa.column("output_ref_id", sa.Text()),
    )
    connection.execute(sa.insert(bindings_table), rows)


def _load_bindings(value: Any) -> dict[str, str]:
    try:
        loaded = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {
        output_slot: output_ref_id
        for output_slot, output_ref_id in loaded.items()
        if isinstance(output_slot, str)
        and output_slot
        and isinstance(output_ref_id, str)
        and output_ref_id
    }
