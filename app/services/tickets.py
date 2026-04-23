from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime

from app.db_models import TicketDB
from app.models import TicketCreate, TicketUpdate, TicketStatus, TicketMerge


ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved, TicketStatus.merged},
    TicketStatus.in_progress: {TicketStatus.resolved, TicketStatus.merged},
    TicketStatus.resolved: {TicketStatus.merged},
    TicketStatus.merged: set(),
}


def list_tickets(db: Session, limit: int, offset: int):
    total = db.query(TicketDB).count()

    items = (
        db.query(TicketDB)
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


def merge_ticket(db: Session, source_ticket_id: int, payload: TicketMerge) -> TicketDB:
    if source_ticket_id == payload.target_ticket_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot merge a ticket into itself"
        )

    source_ticket = get_ticket(db, source_ticket_id)
    target_ticket = get_ticket(db, payload.target_ticket_id)

    if TicketStatus(source_ticket.status) == TicketStatus.merged:
        raise HTTPException(
            status_code=400,
            detail="Source ticket is already merged"
        )

    if TicketStatus(target_ticket.status) == TicketStatus.merged:
        raise HTTPException(
            status_code=400,
            detail="Target ticket is merged, cannot merge into it"
        )

    if target_ticket.merged_to_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Target ticket is merged into another ticket"
        )

    source_current = TicketStatus(source_ticket.status)
    if TicketStatus.merged not in ALLOWED_TRANSITIONS[source_current]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot merge ticket with status: {source_current.value}"
        )

    source_ticket.status = TicketStatus.merged.value
    source_ticket.merged_to_id = target_ticket.id
    source_ticket.merged_at = datetime.utcnow()
    source_ticket.merge_reason = payload.reason

    db.commit()
    db.refresh(source_ticket)
    return source_ticket


def unmerge_ticket(db: Session, ticket_id: int) -> TicketDB:
    ticket = get_ticket(db, ticket_id)

    if TicketStatus(ticket.status) != TicketStatus.merged:
        raise HTTPException(
            status_code=400,
            detail="Ticket is not merged"
        )

    ticket.status = TicketStatus.open.value
    ticket.merged_to_id = None
    ticket.merged_at = None
    ticket.merge_reason = None

    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_with_relations(db: Session, ticket_id: int) -> TicketDB:
    from sqlalchemy.orm import joinedload

    ticket = (
        db.query(TicketDB)
        .options(
            joinedload(TicketDB.merged_to),
            joinedload(TicketDB.merged_tickets)
        )
        .filter(TicketDB.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def get_all_merged_ticket_ids(db: Session, ticket_id: int) -> list[int]:
    from sqlalchemy.orm import joinedload

    def _get_children(tid: int, visited: set[int]) -> list[int]:
        if tid in visited:
            return []
        visited.add(tid)

        ticket = (
            db.query(TicketDB)
            .options(joinedload(TicketDB.merged_tickets))
            .filter(TicketDB.id == tid)
            .first()
        )

        if not ticket:
            return []

        children = []
        for child in ticket.merged_tickets:
            children.append(child.id)
            children.extend(_get_children(child.id, visited))

        return children

    visited = set()
    return _get_children(ticket_id, visited)


def get_root_ticket_id(db: Session, ticket_id: int) -> int:
    ticket = get_ticket(db, ticket_id)

    while ticket.merged_to_id is not None:
        ticket = get_ticket(db, ticket.merged_to_id)

    return ticket.id
