from fastapi import APIRouter, HTTPException, Depends, Query, Response

from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import TicketDB
from app.models import (
    Ticket, TicketCreate, TicketUpdate, MessageResponse,
    TicketListResponse, TicketMerge, TicketWithRelations, TicketStatus,
    Comment, CommentCreate, CommentUpdate,
    CommentListResponse, CommentListWithTicketInfoResponse
)

from app.services import tickets as tickets_service
from app.services import comments as comments_service

ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved, TicketStatus.merged},
    TicketStatus.in_progress: {TicketStatus.resolved, TicketStatus.merged},
    TicketStatus.resolved: {TicketStatus.merged},
    TicketStatus.merged: set(),
}


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return tickets_service.list_tickets(db=db, limit=limit, offset=offset)


@router.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return tickets_service.get_ticket(db=db, ticket_id=ticket_id)


@router.get("/tickets/{ticket_id}/with-relations", response_model=TicketWithRelations)
def get_ticket_with_relations(ticket_id: int, db: Session = Depends(get_db)):
    return tickets_service.get_ticket_with_relations(db=db, ticket_id=ticket_id)


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    return tickets_service.create_ticket(db=db, payload=payload)


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket_status(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    return tickets_service.update_ticket_status(db=db, ticket_id=ticket_id, payload=payload)


@router.post("/tickets/{ticket_id}/merge", response_model=Ticket)
def merge_ticket(ticket_id: int, payload: TicketMerge, db: Session = Depends(get_db)):
    return tickets_service.merge_ticket(db=db, source_ticket_id=ticket_id, payload=payload)


@router.post("/tickets/{ticket_id}/unmerge", response_model=Ticket)
def unmerge_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return tickets_service.unmerge_ticket(db=db, ticket_id=ticket_id)


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None


@router.post("/tickets/{ticket_id}/comments", response_model=Comment, status_code=201)
def create_comment(ticket_id: int, payload: CommentCreate, db: Session = Depends(get_db)):
    return comments_service.create_comment(db=db, ticket_id=ticket_id, payload=payload)


@router.get("/tickets/{ticket_id}/comments", response_model=CommentListResponse)
def list_comments(
    ticket_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_merged: bool = Query(False, description="Include comments from merged child tickets"),
    db: Session = Depends(get_db)
):
    total, items = comments_service.list_comments(
        db=db,
        ticket_id=ticket_id,
        limit=limit,
        offset=offset,
        include_merged=include_merged,
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/tickets/{ticket_id}/comments/with-ticket-info", response_model=CommentListWithTicketInfoResponse)
def list_comments_with_ticket_info(
    ticket_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    total, items = comments_service.list_comments_with_ticket_info(
        db=db,
        ticket_id=ticket_id,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/comments/{comment_id}", response_model=Comment)
def get_comment(comment_id: int, db: Session = Depends(get_db)):
    return comments_service.get_comment(db=db, comment_id=comment_id)


@router.patch("/comments/{comment_id}", response_model=Comment)
def update_comment(comment_id: int, payload: CommentUpdate, db: Session = Depends(get_db)):
    return comments_service.update_comment(db=db, comment_id=comment_id, payload=payload)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    comments_service.delete_comment(db=db, comment_id=comment_id)
    return None

