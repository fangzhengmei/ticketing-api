from fastapi import APIRouter, HTTPException, Depends, Query, Response, Body
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Ticket, TicketCreate, TicketUpdate, MessageResponse,
    TicketListResponse, TicketStatus,
    Tag, TagCreate, TagUpdate, TagListResponse, TagUsageResponse,
    TagMergeRequest, TagMergeResponse, TagMergePreviewResponse, TagMergePreviewSource,
    TagMergeHistory, TagMergeHistoryListResponse, TagMergeHistorySource,
    TagMergeStatsResponse
)

from app.services import tickets as tickets_service
from app.services import tags as tags_service


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/tags", response_model=TagListResponse)
def list_tags(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db)
):
    return tags_service.list_tags(
        db=db,
        limit=limit,
        offset=offset,
        search=search,
    )


@router.get("/tags/usage", response_model=List[TagUsageResponse])
def list_tags_with_usage(
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return tags_service.list_tags_with_usage(
        db=db,
        limit=limit,
        offset=offset,
    )


@router.get("/tags/{tag_id}", response_model=Tag)
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    return tags_service.get_tag(db=db, tag_id=tag_id)


@router.post("/tags", response_model=Tag, status_code=201)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)):
    return tags_service.create_tag(db=db, payload=payload)


@router.patch("/tags/{tag_id}", response_model=Tag)
def update_tag(tag_id: int, payload: TagUpdate, db: Session = Depends(get_db)):
    return tags_service.update_tag(db=db, tag_id=tag_id, payload=payload)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tags_service.delete_tag(db=db, tag_id=tag_id)
    return None


@router.post("/tags/merge", response_model=TagMergeResponse)
def merge_tags(payload: TagMergeRequest, db: Session = Depends(get_db)):
    result = tags_service.merge_tags(
        db=db,
        target_tag_id=payload.target_tag_id,
        source_tag_ids=payload.source_tag_ids,
    )
    return TagMergeResponse(
        target_tag=Tag.model_validate(result.target_tag),
        migrated_ticket_count=result.migrated_ticket_count,
        deleted_tag_count=result.deleted_tag_count,
        deleted_tag_names=result.deleted_tag_names,
    )


@router.post("/tags/merge/preview", response_model=TagMergePreviewResponse)
def preview_merge_tags(payload: TagMergeRequest, db: Session = Depends(get_db)):
    result = tags_service.preview_merge_tags(
        db=db,
        target_tag_id=payload.target_tag_id,
        source_tag_ids=payload.source_tag_ids,
    )
    return TagMergePreviewResponse(
        target_tag=Tag.model_validate(result.target_tag),
        target_current_ticket_count=result.target_current_ticket_count,
        target_after_merge_ticket_count=result.target_after_merge_ticket_count,
        sources_to_delete=[
            TagMergePreviewSource(
                id=s.id,
                name=s.name,
                color=s.color,
                current_ticket_count=s.current_ticket_count,
            )
            for s in result.sources_to_delete
        ],
        tickets_to_migrate=result.tickets_to_migrate,
        total_tags_to_delete=result.total_tags_to_delete,
    )


@router.get("/tags/merge/history", response_model=TagMergeHistoryListResponse)
def list_tag_merge_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    target_tag_id: Optional[int] = Query(None, ge=1),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    result = tags_service.list_tag_merge_history(
        db=db,
        limit=limit,
        offset=offset,
        target_tag_id=target_tag_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    items = []
    for history in result["items"]:
        items.append(TagMergeHistory(
            id=history.id,
            target_tag_id=history.target_tag_id,
            target_tag_name=history.target_tag_name,
            target_tag_color=history.target_tag_color,
            source_tags=[
                TagMergeHistorySource(
                    id=s["id"],
                    name=s["name"],
                    color=s["color"],
                    current_ticket_count=s["current_ticket_count"],
                )
                for s in history.source_tags
            ],
            migrated_ticket_count=history.migrated_ticket_count,
            deleted_tag_count=history.deleted_tag_count,
            created_at=history.created_at,
        ))
    
    return TagMergeHistoryListResponse(
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
        items=items,
    )


@router.get("/tags/merge/stats", response_model=TagMergeStatsResponse)
def get_tag_merge_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    result = tags_service.get_tag_merge_stats(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )
    return TagMergeStatsResponse(
        total_merges=result.total_merges,
        total_migrated_tickets=result.total_migrated_tickets,
        total_deleted_tags=result.total_deleted_tags,
    )


@router.get("/tags/merge/history/{history_id}", response_model=TagMergeHistory)
def get_tag_merge_history(history_id: int, db: Session = Depends(get_db)):
    history = tags_service.get_tag_merge_history(db=db, history_id=history_id)
    
    return TagMergeHistory(
        id=history.id,
        target_tag_id=history.target_tag_id,
        target_tag_name=history.target_tag_name,
        target_tag_color=history.target_tag_color,
        source_tags=[
            TagMergeHistorySource(
                id=s["id"],
                name=s["name"],
                color=s["color"],
                current_ticket_count=s["current_ticket_count"],
            )
            for s in history.source_tags
        ],
        migrated_ticket_count=history.migrated_ticket_count,
        deleted_tag_count=history.deleted_tag_count,
        created_at=history.created_at,
    )


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[TicketStatus] = Query(None),
    tag_ids: Optional[List[int]] = Query(None),
    search: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db)
):
    return tickets_service.list_tickets(
        db=db,
        limit=limit,
        offset=offset,
        status=status,
        tag_ids=tag_ids,
        search=search,
    )


@router.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return tickets_service.get_ticket(db=db, ticket_id=ticket_id)


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    return tickets_service.create_ticket(db=db, payload=payload)


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    return tickets_service.update_ticket_status(db=db, ticket_id=ticket_id, payload=payload)


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None


@router.post("/tickets/{ticket_id}/tags", response_model=Ticket)
def add_tags_to_ticket(
    ticket_id: int,
    tag_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    if not tag_ids:
        raise HTTPException(status_code=422, detail="tag_ids cannot be empty")
    return tickets_service.add_tags_to_ticket(db=db, ticket_id=ticket_id, tag_ids=tag_ids)


@router.delete("/tickets/{ticket_id}/tags/{tag_id}", response_model=Ticket)
def remove_tag_from_ticket(
    ticket_id: int,
    tag_id: int,
    db: Session = Depends(get_db)
):
    return tickets_service.remove_tag_from_ticket(db=db, ticket_id=ticket_id, tag_id=tag_id)
