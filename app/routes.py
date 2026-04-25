from fastapi import APIRouter, HTTPException, Depends, Query, Response

from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import TicketDB
from app.models import Ticket, TicketCreate, TicketUpdate, MessageResponse
from app.models import TicketListResponse
from app.models import TicketStatus

from app.services import tickets as tickets_service


router = APIRouter()


def convert_to_ticket_model(ticket_db: TicketDB) -> Ticket:
    is_overdue = tickets_service.calculate_is_overdue(ticket_db)
    return Ticket(
        id=ticket_db.id,
        title=ticket_db.title,
        status=TicketStatus(ticket_db.status),
        deadline=ticket_db.deadline,
        is_overdue=is_overdue
    )


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_overdue: bool = Query(None, description="Filter by overdue status"),
    db: Session = Depends(get_db)
):
    result = tickets_service.list_tickets(
        db=db, 
        limit=limit, 
        offset=offset,
        is_overdue=is_overdue
    )
    result["items"] = [convert_to_ticket_model(t) for t in result["items"]]
    return result


@router.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = tickets_service.get_ticket(db=db, ticket_id=ticket_id)
    return convert_to_ticket_model(ticket)


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    ticket = tickets_service.create_ticket(db=db, payload=payload)
    return convert_to_ticket_model(ticket)


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    ticket = tickets_service.update_ticket(db=db, ticket_id=ticket_id, payload=payload)
    return convert_to_ticket_model(ticket)


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None
