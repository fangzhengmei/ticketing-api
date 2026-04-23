from fastapi import APIRouter, HTTPException, Depends, Query, Response

from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import TicketDB
from app.models import Ticket, TicketCreate, TicketUpdate, MessageResponse
from app.models import TicketListResponse, TicketMerge, TicketWithRelations
from app.models import TicketStatus

from app.services import tickets as tickets_service

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

