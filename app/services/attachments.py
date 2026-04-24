import os
import uuid
from typing import Optional, List, BinaryIO
from datetime import datetime
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db_models import AttachmentDB, TicketDB
from app.models import Attachment


UPLOAD_DIR = "./uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "application/x-gzip",
    "application/x-rar-compressed",
}


def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_safe_filename(original_name: str) -> str:
    ext = os.path.splitext(original_name)[1] or ""
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return safe_name


def validate_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )


def get_file_size(file: BinaryIO) -> int:
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size


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
    ticket = get_ticket(db, ticket_id)
    
    validate_file(file)
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    
    ensure_upload_dir()
    
    safe_filename = get_safe_filename(file.filename or "unknown")
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
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
    return os.path.join(UPLOAD_DIR, attachment.filename)


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