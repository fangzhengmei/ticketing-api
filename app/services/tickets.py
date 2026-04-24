from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_
from fastapi import HTTPException
from typing import Optional, List

from app.db_models import TicketDB, TagDB, ticket_tags
from app.models import TicketCreate, TicketUpdate, TicketStatus
from app.services import tags as tags_service


ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


def _validate_tags(db: Session, tag_ids: Optional[List[int]]) -> List[TagDB]:
    if not tag_ids:
        return []
    
    unique_ids = list(set(tag_ids))
    tags = db.query(TagDB).filter(TagDB.id.in_(unique_ids)).all()
    
    if len(tags) != len(unique_ids):
        found_ids = {tag.id for tag in tags}
        missing_ids = [tid for tid in unique_ids if tid not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Tags not found: {missing_ids}"
        )
    
    return tags


def list_tickets(
    db: Session,
    limit: int,
    offset: int,
    status: Optional[TicketStatus] = None,
    tag_ids: Optional[List[int]] = None,
    search: Optional[str] = None,
) -> dict:
    query = db.query(TicketDB).options(joinedload(TicketDB.tags))
    
    if status:
        query = query.filter(TicketDB.status == status.value)
    
    if search:
        query = query.filter(TicketDB.title.ilike(f"%{search}%"))
    
    if tag_ids and len(tag_ids) > 0:
        for tag_id in tag_ids:
            query = query.filter(TicketDB.tags.any(id=tag_id))
    
    total = query.distinct().count()
    
    items = (
        query
        .order_by(TicketDB.id)
        .offset(offset)
        .limit(limit)
        .unique()
        .all()
    )
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


def get_ticket(db: Session, ticket_id: int) -> TicketDB:
    ticket = (
        db.query(TicketDB)
        .options(joinedload(TicketDB.tags))
        .filter(TicketDB.id == ticket_id)
        .first()
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def create_ticket(db: Session, payload: TicketCreate) -> TicketDB:
    tags = _validate_tags(db, payload.tag_ids) if payload.tag_ids else []
    
    ticket = TicketDB(
        title=payload.title,
        status=payload.status.value,
    )
    
    if tags:
        ticket.tags = tags
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket_status(db: Session, ticket_id: int, payload: TicketUpdate) -> TicketDB:
    ticket = get_ticket(db, ticket_id)
    
    if payload.title:
        ticket.title = payload.title
    
    if payload.status != TicketStatus(ticket.status):
        current = TicketStatus(ticket.status)
        new = payload.status
        
        if new not in ALLOWED_TRANSITIONS[current]:
            raise HTTPException(status_code=409, detail="Invalid status transition")
        
        ticket.status = new.value
    
    if payload.tag_ids is not None:
        tags = _validate_tags(db, payload.tag_ids)
        ticket.tags = tags
    
    db.commit()
    db.refresh(ticket)
    return ticket


def delete_ticket(db: Session, ticket_id: int) -> None:
    ticket = get_ticket(db, ticket_id)
    db.delete(ticket)
    db.commit()


def add_tags_to_ticket(db: Session, ticket_id: int, tag_ids: List[int]) -> TicketDB:
    ticket = get_ticket(db, ticket_id)
    tags = _validate_tags(db, tag_ids)
    
    existing_ids = {tag.id for tag in ticket.tags}
    for tag in tags:
        if tag.id not in existing_ids:
            ticket.tags.append(tag)
    
    db.commit()
    db.refresh(ticket)
    return ticket


def remove_tag_from_ticket(db: Session, ticket_id: int, tag_id: int) -> TicketDB:
    ticket = get_ticket(db, ticket_id)
    tags_service.get_tag(db, tag_id)
    
    tag_to_remove = None
    for tag in ticket.tags:
        if tag.id == tag_id:
            tag_to_remove = tag
            break
    
    if tag_to_remove:
        ticket.tags.remove(tag_to_remove)
        db.commit()
        db.refresh(ticket)
    
    return ticket
