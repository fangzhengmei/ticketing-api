from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime

from app.db_models import TicketDB
from app.models import TicketCreate, TicketUpdate, TicketStatus


ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


def calculate_is_overdue(ticket: TicketDB) -> bool:
    if ticket.deadline is None:
        return False
    if ticket.status == TicketStatus.resolved.value:
        return False
    return ticket.deadline < datetime.utcnow()


def list_tickets(db: Session, limit: int, offset: int, is_overdue: bool = None):
    query = db.query(TicketDB)
    
    if is_overdue is not None:
        now = datetime.utcnow()
        if is_overdue:
            query = query.filter(
                TicketDB.deadline.isnot(None),
                TicketDB.deadline < now,
                TicketDB.status != TicketStatus.resolved.value
            )
        else:
            query = query.filter(
                (TicketDB.deadline.is_(None)) | 
                (TicketDB.deadline >= now) | 
                (TicketDB.status == TicketStatus.resolved.value)
            )
    
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
    ticket = TicketDB(
        title=payload.title, 
        status=payload.status.value,
        deadline=payload.deadline
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket(db: Session, ticket_id: int, payload: TicketUpdate) -> TicketDB:
    ticket = get_ticket(db, ticket_id)
    
    if 'status' in payload.model_fields_set:
        new = payload.status
        if new is not None:
            current = TicketStatus(ticket.status)

            if new != current:
                if new not in ALLOWED_TRANSITIONS[current]:
                    raise HTTPException(status_code=409, detail="Invalid status transition")

                ticket.status = new.value
    
    if 'deadline' in payload.model_fields_set:
        ticket.deadline = payload.deadline
    
    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket_id: int) -> None:
    ticket = get_ticket(db, ticket_id)
    db.delete(ticket)
    db.commit()
