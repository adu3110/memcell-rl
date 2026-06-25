"""Cell CRUD routes: write, get, retrieve, forget, supersede."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from memcell_rl.core.cell_store import (
    create_cell,
    get_cell,
    mark_superseded,
    soft_delete_cell,
)
from memcell_rl.core.event_log import log_event
from memcell_rl.core.retrieval import retrieve_cells
from memcell_rl.db import get_db
from memcell_rl.models.enums import CellStatus, EventType
from memcell_rl.models.schemas import (
    ForgetRequest,
    MemoryStateCellSchema,
    RetrieveRequest,
    RetrieveResponse,
    SupersedeRequest,
    SupersedeResponse,
    WriteCellRequest,
)

router = APIRouter(prefix="/v1/cells", tags=["cells"])


@router.post("/write", response_model=MemoryStateCellSchema)
def write_cell(req: WriteCellRequest, db: Session = Depends(get_db)) -> MemoryStateCellSchema:
    cell = create_cell(db, req)
    log_event(
        db,
        EventType.write_cell,
        [cell.cell_id],
        {"type": cell.type, "scope": cell.scope},
    )
    return MemoryStateCellSchema.model_validate(cell)


@router.get("/{cell_id}", response_model=MemoryStateCellSchema)
def get_cell_endpoint(cell_id: str, db: Session = Depends(get_db)) -> MemoryStateCellSchema:
    cell = get_cell(db, cell_id)
    if cell is None or cell.status == CellStatus.deleted.value:
        raise HTTPException(status_code=404, detail="Cell not found")
    return MemoryStateCellSchema.model_validate(cell)


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(req: RetrieveRequest, db: Session = Depends(get_db)) -> RetrieveResponse:
    query_id = str(uuid.uuid4())
    cells, scores = retrieve_cells(db, req.query, req.scope, req.types, req.k)
    log_event(
        db,
        EventType.retrieve_cells,
        [c.cell_id for c in cells],
        {"query": req.query, "scope": req.scope, "k": req.k},
        query_id=query_id,
    )
    return RetrieveResponse(
        query_id=query_id,
        cells=[MemoryStateCellSchema.model_validate(c) for c in cells],
        scores=scores,
    )


@router.post("/forget")
def forget_cell(req: ForgetRequest, db: Session = Depends(get_db)) -> dict:
    cell = get_cell(db, req.cell_id)
    if cell is None:
        raise HTTPException(status_code=404, detail="Cell not found")
    soft_delete_cell(db, cell)
    log_event(
        db,
        EventType.forget_cell,
        [req.cell_id],
        {"reason": req.reason},
    )
    return {"ok": True, "cell_id": req.cell_id}


@router.post("/supersede", response_model=SupersedeResponse)
def supersede_cell(req: SupersedeRequest, db: Session = Depends(get_db)) -> SupersedeResponse:
    old_cell = get_cell(db, req.old_cell_id)
    if old_cell is None or old_cell.status == CellStatus.deleted.value:
        raise HTTPException(status_code=404, detail="Old cell not found")

    new_confidence = req.new_confidence if req.new_confidence is not None else old_cell.confidence

    from memcell_rl.models.enums import CellType, Sensitivity
    from memcell_rl.models.schemas import PolicyFeatures, WriteCellRequest

    new_req = WriteCellRequest(
        type=CellType(old_cell.type),
        scope=old_cell.scope,
        content=req.new_content,
        confidence=new_confidence,
        sensitivity=Sensitivity(old_cell.sensitivity),
        source_refs=req.source_refs,
        supersedes=[req.old_cell_id],
        policy_features=PolicyFeatures(**old_cell.policy_features),
    )
    # Bump version

    new_cell_orm = create_cell(db, new_req)
    new_cell_orm.version = old_cell.version + 1
    db.commit()
    db.refresh(new_cell_orm)

    mark_superseded(db, old_cell)

    log_event(
        db,
        EventType.supersede_cell,
        [old_cell.cell_id, new_cell_orm.cell_id],
        {"old_cell_id": old_cell.cell_id, "new_cell_id": new_cell_orm.cell_id},
    )

    return SupersedeResponse(
        old_cell=MemoryStateCellSchema.model_validate(old_cell),
        new_cell=MemoryStateCellSchema.model_validate(new_cell_orm),
    )
