from enum import StrEnum


class CellType(StrEnum):
    profile = "profile"
    preference = "preference"
    constraint = "constraint"
    fact = "fact"
    episode = "episode"
    task_state = "task_state"
    project_state = "project_state"
    procedure = "procedure"
    tool_memory = "tool_memory"
    reflection = "reflection"
    document_reference = "document_reference"


class CellStatus(StrEnum):
    active = "active"
    superseded = "superseded"
    contradicted = "contradicted"
    quarantined = "quarantined"
    deleted = "deleted"
    expired = "expired"


class Sensitivity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    restricted = "restricted"


class RetrievalMode(StrEnum):
    context = "context"
    constraint = "constraint"
    background = "background"
    suppress = "suppress"
    reverify_before_use = "reverify_before_use"


class RetentionAction(StrEnum):
    keep = "keep"
    decay = "decay"
    compress = "compress"
    merge = "merge"
    promote = "promote"
    quarantine = "quarantine"
    supersede = "supersede"
    delete = "delete"


class EventType(StrEnum):
    write_cell = "write_cell"
    update_cell = "update_cell"
    retrieve_cells = "retrieve_cells"
    decide_cells = "decide_cells"
    feedback_received = "feedback_received"
    forget_cell = "forget_cell"
    supersede_cell = "supersede_cell"
    policy_action = "policy_action"
