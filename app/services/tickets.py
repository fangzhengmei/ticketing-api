from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
from sqlalchemy import or_

from app.db_models import TicketDB
from app.models import TicketCreate, TicketUpdate, TicketStatus, ResolutionCategory


ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


def list_tickets(
    db: Session,
    limit: int,
    offset: int,
    status: TicketStatus = None,
    resolution_category: ResolutionCategory = None,
    keyword: str = None
):
    query = db.query(TicketDB)

    if status:
        query = query.filter(TicketDB.status == status.value)

    if resolution_category:
        query = query.filter(TicketDB.resolution_category == resolution_category.value)

    if keyword:
        keyword_lower = keyword.lower()
        query = query.filter(
            or_(
                TicketDB.title.ilike(f"%{keyword}%"),
                TicketDB.solution.ilike(f"%{keyword}%")
            )
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

    if new == TicketStatus.resolved:
        if not payload.solution:
            raise HTTPException(
                status_code=400,
                detail="Solution is required when resolving a ticket"
            )
        ticket.solution = payload.solution
        ticket.solution_time = datetime.now(timezone.utc)
        if payload.resolved_by:
            ticket.resolved_by = payload.resolved_by
        if payload.resolution_category:
            ticket.resolution_category = payload.resolution_category.value

    ticket.status = new.value
    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket_id: int) -> None:
    ticket = get_ticket(db, ticket_id)
    db.delete(ticket)
    db.commit()
