from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base


class RuntimeEventRecord(Base):
    __tablename__ = "runtime_events"
    __table_args__ = {"sqlite_autoincrement": True}

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    event_version: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_run_id: Mapped[str | None] = mapped_column(Text, index=True)
    node_run_id: Mapped[str | None] = mapped_column(Text, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
