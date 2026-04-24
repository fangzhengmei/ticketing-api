from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta
from typing import Optional, Protocol
from dataclasses import dataclass

from app.db_models import TicketDB
from app.models import TicketCreate, TicketUpdate, TicketStatus, SlaStatus, Ticket
from app.config import get_sla_warning_threshold_hours


class UserWithPermission(Protocol):
    @property
    def user_id(self) -> Optional[str]: ...
    
    @property
    def is_admin(self) -> bool: ...


@dataclass
class UnauthenticatedUser:
    user_id: Optional[str] = None
    is_admin: bool = False


ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


def can_modify_sla(ticket: TicketDB, current_user: UserWithPermission) -> bool:
    if current_user.is_admin:
        return True
    
    if ticket.created_by is None:
        return True
    
    if current_user.user_id and ticket.created_by == current_user.user_id:
        return True
    
    return False


def calculate_sla_status(ticket: TicketDB) -> SlaStatus:
    warning_threshold_hours = get_sla_warning_threshold_hours()
    
    if ticket.sla_deadline is None:
        return SlaStatus.not_set
    
    if ticket.status == TicketStatus.resolved.value:
        if ticket.resolved_at and ticket.resolved_at > ticket.sla_deadline:
            return SlaStatus.breached
        return SlaStatus.on_track
    
    now = datetime.utcnow()
    
    if now > ticket.sla_deadline:
        return SlaStatus.breached
    
    warning_threshold = ticket.sla_deadline - timedelta(hours=warning_threshold_hours)
    if now >= warning_threshold:
        return SlaStatus.warning
    
    return SlaStatus.on_track


def check_and_update_sla_breach(db: Session, ticket: TicketDB) -> TicketDB:
    if ticket.status == TicketStatus.resolved.value:
        return ticket
    
    if ticket.sla_deadline is None:
        return ticket
    
    now = datetime.utcnow()
    if now > ticket.sla_deadline and not ticket.sla_breached:
        ticket.sla_breached = True
        db.commit()
        db.refresh(ticket)
    
    return ticket


def ticket_db_to_model(ticket: TicketDB) -> Ticket:
    sla_status = calculate_sla_status(ticket)
    return Ticket(
        id=ticket.id,
        title=ticket.title,
        status=TicketStatus(ticket.status),
        created_at=ticket.created_at,
        sla_deadline=ticket.sla_deadline,
        sla_breached=ticket.sla_breached,
        resolved_at=ticket.resolved_at,
        created_by=ticket.created_by,
        sla_status=sla_status,
    )


def list_tickets(
    db: Session,
    limit: int,
    offset: int,
    status: Optional[TicketStatus] = None,
    sla_status: Optional[SlaStatus] = None,
):
    query = db.query(TicketDB)
    
    if status:
        query = query.filter(TicketDB.status == status.value)
    
    all_tickets = query.order_by(TicketDB.id).all()
    
    for ticket in all_tickets:
        check_and_update_sla_breach(db, ticket)
    
    filtered_tickets = all_tickets
    if sla_status:
        filtered_tickets = [
            t for t in all_tickets
            if calculate_sla_status(t) == sla_status
        ]
    
    total = len(filtered_tickets)
    items = filtered_tickets[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [ticket_db_to_model(t) for t in items],
    }


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.query(TicketDB).filter(TicketDB.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    check_and_update_sla_breach(db, ticket)
    return ticket_db_to_model(ticket)


def get_ticket_db(db: Session, ticket_id: int) -> TicketDB:
    ticket = db.query(TicketDB).filter(TicketDB.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def create_ticket(
    db: Session,
    payload: TicketCreate,
    created_by: Optional[str] = None,
) -> Ticket:
    ticket = TicketDB(
        title=payload.title,
        status=payload.status.value,
        sla_deadline=payload.sla_deadline,
        created_by=created_by,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket_db_to_model(ticket)


def update_ticket_status(
    db: Session,
    ticket_id: int,
    payload: TicketUpdate,
    current_user: Optional[UserWithPermission] = None,
) -> Ticket:
    if current_user is None:
        current_user = UnauthenticatedUser()
    
    ticket = get_ticket_db(db, ticket_id)

    current = TicketStatus(ticket.status)
    new = payload.status

    sla_modified = payload.sla_deadline is not None and payload.sla_deadline != ticket.sla_deadline
    
    if sla_modified and not can_modify_sla(ticket, current_user):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to modify SLA deadline. Only the creator or admin can modify SLA.",
        )

    if new == current:
        if payload.sla_deadline is not None:
            ticket.sla_deadline = payload.sla_deadline
            db.commit()
            db.refresh(ticket)
        check_and_update_sla_breach(db, ticket)
        return ticket_db_to_model(ticket)

    if new not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(status_code=409, detail="Invalid status transition")

    ticket.status = new.value
    
    if new == TicketStatus.resolved:
        ticket.resolved_at = datetime.utcnow()
        if ticket.sla_deadline and ticket.resolved_at > ticket.sla_deadline:
            ticket.sla_breached = True
    
    if payload.sla_deadline is not None:
        ticket.sla_deadline = payload.sla_deadline
    
    db.commit()
    db.refresh(ticket)
    check_and_update_sla_breach(db, ticket)
    return ticket_db_to_model(ticket)


def delete_ticket(db: Session, ticket_id: int) -> None:
    ticket = get_ticket_db(db, ticket_id)
    db.delete(ticket)
    db.commit()


def get_sla_statistics(db: Session) -> dict:
    all_tickets = db.query(TicketDB).all()
    
    for ticket in all_tickets:
        check_and_update_sla_breach(db, ticket)
    
    stats = {
        "total": len(all_tickets),
        "on_track": 0,
        "warning": 0,
        "breached": 0,
        "not_set": 0,
        "warning_threshold_hours": get_sla_warning_threshold_hours(),
    }
    
    for ticket in all_tickets:
        status = calculate_sla_status(ticket)
        stats[status.value] += 1
    
    return stats
