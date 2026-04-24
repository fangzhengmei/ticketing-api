from fastapi import APIRouter, HTTPException, Depends, Query, Response, Body
from typing import Optional, List

from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Ticket, TicketCreate, TicketUpdate, MessageResponse,
    TicketListResponse, TicketStatus,
    Tag, TagCreate, TagUpdate, TagListResponse, TagUsageResponse,
    TagMergeRequest, TagMergeResponse
)

from app.services import tickets as tickets_service
from app.services import tags as tags_service


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/tags", response_model=TagListResponse)
def list_tags(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db)
):
    return tags_service.list_tags(
        db=db,
        limit=limit,
        offset=offset,
        search=search,
    )


@router.get("/tags/usage", response_model=List[TagUsageResponse])
def list_tags_with_usage(
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return tags_service.list_tags_with_usage(
        db=db,
        limit=limit,
        offset=offset,
    )


@router.get("/tags/{tag_id}", response_model=Tag)
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    return tags_service.get_tag(db=db, tag_id=tag_id)


@router.post("/tags", response_model=Tag, status_code=201)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)):
    return tags_service.create_tag(db=db, payload=payload)


@router.patch("/tags/{tag_id}", response_model=Tag)
def update_tag(tag_id: int, payload: TagUpdate, db: Session = Depends(get_db)):
    return tags_service.update_tag(db=db, tag_id=tag_id, payload=payload)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tags_service.delete_tag(db=db, tag_id=tag_id)
    return None


@router.post("/tags/merge", response_model=TagMergeResponse)
def merge_tags(payload: TagMergeRequest, db: Session = Depends(get_db)):
    result = tags_service.merge_tags(
        db=db,
        target_tag_id=payload.target_tag_id,
        source_tag_ids=payload.source_tag_ids,
    )
    return TagMergeResponse(
        target_tag=Tag.model_validate(result.target_tag),
        migrated_ticket_count=result.migrated_ticket_count,
        deleted_tag_count=result.deleted_tag_count,
        deleted_tag_names=result.deleted_tag_names,
    )


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[TicketStatus] = Query(None),
    tag_ids: Optional[List[int]] = Query(None),
    search: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db)
):
    return tickets_service.list_tickets(
        db=db,
        limit=limit,
        offset=offset,
        status=status,
        tag_ids=tag_ids,
        search=search,
    )


@router.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return tickets_service.get_ticket(db=db, ticket_id=ticket_id)


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    return tickets_service.create_ticket(db=db, payload=payload)


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    return tickets_service.update_ticket_status(db=db, ticket_id=ticket_id, payload=payload)


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None


@router.post("/tickets/{ticket_id}/tags", response_model=Ticket)
def add_tags_to_ticket(
    ticket_id: int,
    tag_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    if not tag_ids:
        raise HTTPException(status_code=422, detail="tag_ids cannot be empty")
    return tickets_service.add_tags_to_ticket(db=db, ticket_id=ticket_id, tag_ids=tag_ids)


@router.delete("/tickets/{ticket_id}/tags/{tag_id}", response_model=Ticket)
def remove_tag_from_ticket(
    ticket_id: int,
    tag_id: int,
    db: Session = Depends(get_db)
):
    return tickets_service.remove_tag_from_ticket(db=db, ticket_id=ticket_id, tag_id=tag_id)
