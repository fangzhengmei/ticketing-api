from sqlalchemy.orm import Session
from sqlalchemy import func, select, text
from fastapi import HTTPException
from typing import Optional, List

from app.db_models import TagDB, TicketDB, ticket_tags
from app.models import TagCreate, TagUpdate, TagUsageResponse


def list_tags(
    db: Session,
    limit: int,
    offset: int,
    search: Optional[str] = None,
) -> dict:
    query = db.query(TagDB)
    
    if search:
        query = query.filter(TagDB.name.ilike(f"%{search}%"))
    
    total = query.count()
    
    items = (
        query
        .order_by(TagDB.name)
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


def list_tags_with_usage(
    db: Session,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[TagUsageResponse]:
    subquery = (
        select(ticket_tags.c.tag_id, func.count(ticket_tags.c.ticket_id).label("ticket_count"))
        .group_by(ticket_tags.c.tag_id)
        .subquery()
    )
    
    query = (
        db.query(
            TagDB.id,
            TagDB.name,
            TagDB.color,
            TagDB.description,
            func.coalesce(subquery.c.ticket_count, 0).label("ticket_count")
        )
        .outerjoin(subquery, TagDB.id == subquery.c.tag_id)
        .order_by(func.coalesce(subquery.c.ticket_count, 0).desc(), TagDB.name)
    )
    
    if limit:
        query = query.offset(offset).limit(limit)
    
    results = query.all()
    
    return [
        TagUsageResponse(
            id=r.id,
            name=r.name,
            color=r.color,
            description=r.description,
            ticket_count=r.ticket_count
        )
        for r in results
    ]


def get_tag(db: Session, tag_id: int) -> TagDB:
    tag = db.query(TagDB).filter(TagDB.id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


def get_tag_by_name(db: Session, name: str) -> Optional[TagDB]:
    return db.query(TagDB).filter(TagDB.name == name).first()


def create_tag(db: Session, payload: TagCreate) -> TagDB:
    existing = get_tag_by_name(db, payload.name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Tag with name '{payload.name}' already exists"
        )
    
    tag = TagDB(
        name=payload.name,
        color=payload.color,
        description=payload.description,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, payload: TagUpdate) -> TagDB:
    tag = get_tag(db, tag_id)
    
    update_data = payload.model_dump(exclude_unset=True)
    
    if "name" in update_data and update_data["name"] != tag.name:
        existing = get_tag_by_name(db, update_data["name"])
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Tag with name '{update_data['name']}' already exists"
            )
    
    for key, value in update_data.items():
        setattr(tag, key, value)
    
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    tag = get_tag(db, tag_id)
    db.delete(tag)
    db.commit()


def get_or_create_tag_by_name(db: Session, name: str, color: Optional[str] = None) -> TagDB:
    tag = get_tag_by_name(db, name)
    if tag:
        return tag
    
    tag = TagDB(
        name=name,
        color=color or "#3b82f6",
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag
