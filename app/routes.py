from fastapi import APIRouter, HTTPException, Depends, Query, Response

from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import TicketDB
from app.models import Ticket, TicketCreate, TicketUpdate, MessageResponse
from app.models import TicketListResponse
from app.models import TicketStatus  # μαζί με τα άλλα imports

from app.services import tickets as tickets_service

ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
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


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    return tickets_service.create_ticket(db=db, payload=payload)


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket_status(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    return tickets_service.update_ticket_status(db=db, ticket_id=ticket_id, payload=payload)


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None

