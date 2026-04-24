from sqlalchemy.orm import Session
from sqlalchemy import func, select, text
from fastapi import HTTPException
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.db_models import TagDB, TicketDB, ticket_tags
from app.models import TagCreate, TagUpdate, TagUsageResponse, Tag


@dataclass
class TagMergeResult:
    target_tag: TagDB
    migrated_ticket_count: int
    deleted_tag_count: int
    deleted_tag_names: List[str]


@dataclass
class TagMergePreviewSource:
    id: int
    name: str
    color: str
    current_ticket_count: int


@dataclass
class TagMergePreviewResult:
    target_tag: TagDB
    target_current_ticket_count: int
    target_after_merge_ticket_count: int
    sources_to_delete: List[TagMergePreviewSource]
    tickets_to_migrate: int
    total_tags_to_delete: int


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


def merge_tags(
    db: Session,
    target_tag_id: int,
    source_tag_ids: List[int],
) -> TagMergeResult:
    if not source_tag_ids:
        raise HTTPException(
            status_code=422,
            detail="source_tag_ids cannot be empty"
        )
    
    unique_source_ids = list(set(source_tag_ids))
    
    if target_tag_id in unique_source_ids:
        raise HTTPException(
            status_code=400,
            detail="target_tag_id cannot be in source_tag_ids"
        )
    
    target_tag = get_tag(db, target_tag_id)
    
    source_tags = db.query(TagDB).filter(TagDB.id.in_(unique_source_ids)).all()
    
    if len(source_tags) != len(unique_source_ids):
        found_ids = {tag.id for tag in source_tags}
        missing_ids = [tid for tid in unique_source_ids if tid not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Source tags not found: {missing_ids}"
        )
    
    total_migrated = 0
    deleted_names = []
    
    for source_tag in source_tags:
        ticket_ids_with_source = db.query(ticket_tags.c.ticket_id).filter(
            ticket_tags.c.tag_id == source_tag.id
        ).all()
        ticket_ids_with_source = {row[0] for row in ticket_ids_with_source}
        
        if not ticket_ids_with_source:
            deleted_names.append(source_tag.name)
            continue
        
        ticket_ids_with_target = db.query(ticket_tags.c.ticket_id).filter(
            ticket_tags.c.tag_id == target_tag_id
        ).all()
        ticket_ids_with_target = {row[0] for row in ticket_ids_with_target}
        
        ticket_ids_to_migrate = ticket_ids_with_source - ticket_ids_with_target
        
        if ticket_ids_to_migrate:
            from sqlalchemy import insert
            new_relations = [
                {"ticket_id": tid, "tag_id": target_tag_id}
                for tid in ticket_ids_to_migrate
            ]
            db.execute(insert(ticket_tags).values(new_relations))
            
            total_migrated += len(ticket_ids_to_migrate)
        
        db.query(ticket_tags).filter(
            ticket_tags.c.tag_id == source_tag.id
        ).delete(synchronize_session=False)
        
        deleted_names.append(source_tag.name)
    
    for source_tag in source_tags:
        db.delete(source_tag)
    
    db.commit()
    db.refresh(target_tag)
    
    return TagMergeResult(
        target_tag=target_tag,
        migrated_ticket_count=total_migrated,
        deleted_tag_count=len(source_tags),
        deleted_tag_names=deleted_names,
    )


def preview_merge_tags(
    db: Session,
    target_tag_id: int,
    source_tag_ids: List[int],
) -> TagMergePreviewResult:
    if not source_tag_ids:
        raise HTTPException(
            status_code=422,
            detail="source_tag_ids cannot be empty"
        )
    
    unique_source_ids = list(set(source_tag_ids))
    
    if target_tag_id in unique_source_ids:
        raise HTTPException(
            status_code=400,
            detail="target_tag_id cannot be in source_tag_ids"
        )
    
    target_tag = get_tag(db, target_tag_id)
    
    source_tags = db.query(TagDB).filter(TagDB.id.in_(unique_source_ids)).all()
    
    if len(source_tags) != len(unique_source_ids):
        found_ids = {tag.id for tag in source_tags}
        missing_ids = [tid for tid in unique_source_ids if tid not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Source tags not found: {missing_ids}"
        )
    
    ticket_ids_with_target = db.query(ticket_tags.c.ticket_id).filter(
        ticket_tags.c.tag_id == target_tag_id
    ).all()
    ticket_ids_with_target = {row[0] for row in ticket_ids_with_target}
    
    all_source_ticket_ids = set()
    sources_to_delete = []
    total_tickets_to_migrate = 0
    
    for source_tag in source_tags:
        ticket_ids_with_source = db.query(ticket_tags.c.ticket_id).filter(
            ticket_tags.c.tag_id == source_tag.id
        ).all()
        ticket_ids_with_source = {row[0] for row in ticket_ids_with_source}
        
        all_source_ticket_ids.update(ticket_ids_with_source)
        
        tickets_to_migrate_for_source = ticket_ids_with_source - ticket_ids_with_target
        total_tickets_to_migrate += len(tickets_to_migrate_for_source)
        
        sources_to_delete.append(
            TagMergePreviewSource(
                id=source_tag.id,
                name=source_tag.name,
                color=source_tag.color,
                current_ticket_count=len(ticket_ids_with_source),
            )
        )
    
    target_after_merge_count = len(ticket_ids_with_target | all_source_ticket_ids)
    
    return TagMergePreviewResult(
        target_tag=target_tag,
        target_current_ticket_count=len(ticket_ids_with_target),
        target_after_merge_ticket_count=target_after_merge_count,
        sources_to_delete=sources_to_delete,
        tickets_to_migrate=total_tickets_to_migrate,
        total_tags_to_delete=len(source_tags),
    )
