from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base


class WorkflowRunRuntimeOptionsRecord(Base):
    __tablename__ = "workflow_run_runtime_options"
    __table_args__ = (
        CheckConstraint(
            "requested_version >= 0",
            name="ck_workflow_run_runtime_options_requested_version",
        ),
        CheckConstraint(
            "applied_version >= 0 AND applied_version <= requested_version",
            name="ck_workflow_run_runtime_options_applied_version",
        ),
    )

    workflow_run_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("workflow_runs.workflow_run_id", ondelete="CASCADE"),
        primary_key=True,
    )
    requested_version: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_version: Mapped[int] = mapped_column(Integer, nullable=False)
    overlay_json: Mapped[str] = mapped_column(Text, nullable=False)
    requested_at: Mapped[str] = mapped_column(Text, nullable=False)
    applied_at: Mapped[str | None] = mapped_column(Text)
