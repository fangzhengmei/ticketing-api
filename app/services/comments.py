from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from typing import List, Optional, Tuple

from app.db_models import CommentDB, TicketDB
from app.models import CommentCreate, CommentUpdate


def create_comment(db: Session, ticket_id: int, payload: CommentCreate) -> CommentDB:
    from app.services.tickets import get_ticket

    ticket = get_ticket(db, ticket_id)

    comment = CommentDB(
        ticket_id=ticket.id,
        original_ticket_id=ticket.id,
        content=payload.content,
        author=payload.author,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comment(db: Session, comment_id: int) -> CommentDB:
    comment = db.query(CommentDB).filter(CommentDB.id == comment_id).first()
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


def list_comments(
    db: Session,
    ticket_id: int,
    limit: int,
    offset: int,
    include_merged: bool = False,
) -> Tuple[int, List[CommentDB]]:
    from app.services.tickets import get_ticket, get_all_merged_ticket_ids

    ticket = get_ticket(db, ticket_id)

    if include_merged:
        all_child_ids = get_all_merged_ticket_ids(db, ticket.id)
        ticket_ids = [ticket.id] + all_child_ids
        query = db.query(CommentDB).filter(CommentDB.ticket_id.in_(ticket_ids))
    else:
        query = db.query(CommentDB).filter(CommentDB.ticket_id == ticket.id)

    total = query.count()
    comments = query.order_by(CommentDB.created_at.asc()).offset(offset).limit(limit).all()

    return total, comments


def list_comments_with_ticket_info(
    db: Session,
    ticket_id: int,
    limit: int,
    offset: int,
) -> Tuple[int, List[dict]]:
    from app.services.tickets import get_ticket, get_all_merged_ticket_ids

    ticket = get_ticket(db, ticket_id)

    all_child_ids = get_all_merged_ticket_ids(db, ticket.id)
    ticket_ids = [ticket.id] + all_child_ids

    comments = (
        db.query(CommentDB)
        .filter(CommentDB.ticket_id.in_(ticket_ids))
        .order_by(CommentDB.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    total = db.query(CommentDB).filter(CommentDB.ticket_id.in_(ticket_ids)).count()

    ticket_cache = {}

    result = []
    for comment in comments:
        comment_dict = {
            "id": comment.id,
            "ticket_id": comment.ticket_id,
            "original_ticket_id": comment.original_ticket_id,
            "content": comment.content,
            "author": comment.author,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "original_ticket_title": None,
        }

        if comment.original_ticket_id:
            if comment.original_ticket_id in ticket_cache:
                comment_dict["original_ticket_title"] = ticket_cache[comment.original_ticket_id]
            else:
                original_ticket = db.query(TicketDB).filter(TicketDB.id == comment.original_ticket_id).first()
                if original_ticket:
                    ticket_cache[comment.original_ticket_id] = original_ticket.title
                    comment_dict["original_ticket_title"] = original_ticket.title

        result.append(comment_dict)

    return total, result


def update_comment(db: Session, comment_id: int, payload: CommentUpdate) -> CommentDB:
    comment = get_comment(db, comment_id)
    comment.content = payload.content
    comment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment_id: int) -> None:
    comment = get_comment(db, comment_id)
    db.delete(comment)
    db.commit()


def merge_comments_to_target(db: Session, source_ticket_id: int, target_ticket_id: int) -> int:
    comments_updated = (
        db.query(CommentDB)
        .filter(CommentDB.ticket_id == source_ticket_id)
        .update(
            {
                CommentDB.ticket_id: target_ticket_id,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return comments_updated


def unmerge_comments_from_target(db: Session, source_ticket_id: int) -> int:
    comments_updated = (
        db.query(CommentDB)
        .filter(
            CommentDB.original_ticket_id == source_ticket_id,
            CommentDB.ticket_id != source_ticket_id,
        )
        .update(
            {
                CommentDB.ticket_id: source_ticket_id,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return comments_updated
