from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from memcell_rl.models.enums import (
    CellStatus,
    CellType,
    EventType,
    RetrievalMode,
    Sensitivity,
)

# ── Sub-models ──────────────────────────────────────────────────────────────


class PolicyFeatures(BaseModel):
    criticality: float = 0.0
    compressibility: float = 0.5
    staleness: float = 0.0
    future_utility_estimate: float = 0.0


# ── Core domain objects ──────────────────────────────────────────────────────


class MemoryStateCellSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cell_id: str
    type: CellType
    scope: dict[str, Any]
    content: str
    status: CellStatus
    confidence: float
    sensitivity: Sensitivity
    source_refs: list[str]
    valid_from: datetime | None
    valid_until: datetime | None
    supersedes: list[str]
    contradicted_by: list[str]
    access_count: int
    last_retrieved_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    policy_features: dict[str, float]


class MemoryEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    timestamp: datetime
    event_type: EventType
    cell_ids: list[str]
    query_id: str | None
    payload: dict[str, Any]


class MemoryTransitionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transition_id: str
    query_id: str
    state: dict[str, Any]
    action: dict[str, Any]
    reward: dict[str, Any] | None
    next_state: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None


# ── Request / response models ────────────────────────────────────────────────


class WriteCellRequest(BaseModel):
    type: CellType
    scope: dict[str, Any]
    content: str
    status: CellStatus = CellStatus.active
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sensitivity: Sensitivity = Sensitivity.low
    source_refs: list[str] = Field(default_factory=list)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    supersedes: list[str] = Field(default_factory=list)
    contradicted_by: list[str] = Field(default_factory=list)
    policy_features: PolicyFeatures | None = None


class RetrieveRequest(BaseModel):
    query: str
    scope: dict[str, Any]
    types: list[CellType] | None = None
    k: int = Field(default=5, ge=1)


class RetrieveResponse(BaseModel):
    query_id: str
    cells: list[MemoryStateCellSchema]
    scores: list[float]


class SelectedCell(BaseModel):
    cell_id: str
    mode: RetrievalMode
    score: float
    reason: str


class SuppressedCell(BaseModel):
    cell_id: str
    reason: str


class PolicyInfo(BaseModel):
    policy_id: str
    policy_type: str
    confidence: float


class DecideRequest(BaseModel):
    query: str
    scope: dict[str, Any]
    task_type: str = ""
    budget_tokens: int = Field(default=2000, ge=1)
    k: int = Field(default=10, ge=1)


class DecideResponse(BaseModel):
    query_id: str
    selected_cells: list[SelectedCell]
    suppressed_cells: list[SuppressedCell]
    policy: PolicyInfo
    transition_id: str


class FeedbackRequest(BaseModel):
    query_id: str
    transition_id: str
    task_success: bool
    user_correction: str | None = None
    unsafe_action: bool = False
    stale_memory_error: bool = False
    tokens_used: int = 0
    latency_ms: int = 0


class FeedbackResponse(BaseModel):
    transition_id: str
    reward_value: float
    completed_at: datetime


class ForgetRequest(BaseModel):
    cell_id: str
    reason: str = "user_request"


class SupersedeRequest(BaseModel):
    old_cell_id: str
    new_content: str
    new_confidence: float | None = None
    source_refs: list[str] = Field(default_factory=list)


class SupersedeResponse(BaseModel):
    old_cell: MemoryStateCellSchema
    new_cell: MemoryStateCellSchema


class RLDatasetEntry(BaseModel):
    transition_id: str
    state: dict[str, Any]
    action: dict[str, Any]
    reward: dict[str, Any]
    next_state: dict[str, Any]
