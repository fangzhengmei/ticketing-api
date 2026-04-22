from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.db_models import TicketDB
from app.models import TicketCreate, TicketUpdate, TicketStatus


ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


def list_tickets(db: Session, limit: int, offset: int, keyword: str | None = None):
    query = db.query(TicketDB)
    
    if keyword:
        query = query.filter(func.lower(TicketDB.title).like(func.lower(f"%{keyword}%")))
    
    total = query.count()

    items = (
        query
        .order_by(TicketDB.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


def get_ticket(db: Session, ticket_id: int) -> TicketDB:
    ticket = db.query(TicketDB).filter(TicketDB.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def create_ticket(db: Session, payload: TicketCreate) -> TicketDB:
    ticket = TicketDB(title=payload.title, status=payload.status.value)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket_status(db: Session, ticket_id: int, payload: TicketUpdate) -> TicketDB:
    ticket = get_ticket(db, ticket_id)

    current = TicketStatus(ticket.status)
    new = payload.status

    if new == current:
        return ticket

    if new not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(status_code=409, detail="Invalid status transition")

    ticket.status = new.value
    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket_id: int) -> None:
    ticket = get_ticket(db, ticket_id)
    db.delete(ticket)
    db.commit()
