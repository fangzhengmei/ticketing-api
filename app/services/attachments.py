import os
import uuid
from typing import Optional, List
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db_models import AttachmentDB, TicketDB
from app.config import get_settings


def get_safe_filename(original_name: str) -> str:
    ext = os.path.splitext(original_name)[1] or ""
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return safe_name


def validate_file(file: UploadFile) -> None:
    settings = get_settings()
    allowed_types = settings.effective_allowed_content_types
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed types: {', '.join(sorted(allowed_types))}"
        )


def get_ticket(db: Session, ticket_id: int) -> TicketDB:
    ticket = db.query(TicketDB).filter(TicketDB.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def get_attachment(db: Session, ticket_id: int, attachment_id: int) -> AttachmentDB:
    attachment = db.query(AttachmentDB).filter(
        AttachmentDB.id == attachment_id,
        AttachmentDB.ticket_id == ticket_id
    ).first()
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment


def upload_attachment(
    db: Session,
    ticket_id: int,
    file: UploadFile,
    description: Optional[str] = None
) -> AttachmentDB:
    settings = get_settings()
    upload_dir = settings.upload_dir
    max_file_size = settings.max_file_size
    
    ticket = get_ticket(db, ticket_id)
    
    validate_file(file)
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {max_file_size // 1024 // 1024}MB"
        )
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    
    safe_filename = get_safe_filename(file.filename or "unknown")
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        content = file.file.read()
        f.write(content)
    
    attachment = AttachmentDB(
        ticket_id=ticket_id,
        filename=safe_filename,
        original_name=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        description=description
    )
    
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    
    return attachment


def list_attachments(db: Session, ticket_id: int) -> List[AttachmentDB]:
    get_ticket(db, ticket_id)
    
    attachments = db.query(AttachmentDB).filter(
        AttachmentDB.ticket_id == ticket_id
    ).order_by(AttachmentDB.created_at.desc()).all()
    
    return attachments


def get_attachment_file_path(attachment: AttachmentDB) -> str:
    settings = get_settings()
    return os.path.join(settings.upload_dir, attachment.filename)


def delete_attachment(db: Session, ticket_id: int, attachment_id: int) -> None:
    attachment = get_attachment(db, ticket_id, attachment_id)
    
    file_path = get_attachment_file_path(attachment)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.delete(attachment)
    db.commit()


def update_attachment_description(
    db: Session,
    ticket_id: int,
    attachment_id: int,
    description: Optional[str]
) -> AttachmentDB:
    attachment = get_attachment(db, ticket_id, attachment_id)
    
    attachment.description = description
    db.commit()
    db.refresh(attachment)
    
    return attachment