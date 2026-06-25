from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class MemoryCellORM(Base):
    __tablename__ = "memory_cells"

    cell_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    sensitivity: Mapped[str] = mapped_column(String, nullable=False, default="low")
    source_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    supersedes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    contradicted_by: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    policy_features: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)


class MemoryEventORM(Base):
    __tablename__ = "memory_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    cell_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    query_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class MemoryTransitionORM(Base):
    __tablename__ = "memory_transitions"

    transition_id: Mapped[str] = mapped_column(String, primary_key=True)
    query_id: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    action: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reward: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    next_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
