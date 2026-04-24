import os
from typing import Optional, Union
from fastapi import APIRouter, HTTPException, Depends, Query, Response, UploadFile, File, Form, Body
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import TicketDB
from app.models import (
    Ticket, TicketCreate, TicketUpdate, MessageResponse,
    TicketListResponse, TicketWithAttachments,
    Attachment, AttachmentListResponse
)
from app.models import TicketStatus

from app.services import tickets as tickets_service
from app.services import attachments as attachments_service

ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return tickets_service.list_tickets(db=db, limit=limit, offset=offset)


@router.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: int,
    include_attachments: bool = Query(False, description="Include attachments in response"),
    db: Session = Depends(get_db)
):
    ticket = tickets_service.get_ticket(db=db, ticket_id=ticket_id)
    if include_attachments:
        attachments = attachments_service.list_attachments(db=db, ticket_id=ticket_id)
        return TicketWithAttachments(
            id=ticket.id,
            title=ticket.title,
            status=ticket.status,
            attachments=attachments
        )
    return Ticket(
        id=ticket.id,
        title=ticket.title,
        status=ticket.status
    )


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    return tickets_service.create_ticket(db=db, payload=payload)


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket_status(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    return tickets_service.update_ticket_status(db=db, ticket_id=ticket_id, payload=payload)


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None


@router.post("/tickets/{ticket_id}/attachments", response_model=Attachment, status_code=201)
def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    return attachments_service.upload_attachment(
        db=db,
        ticket_id=ticket_id,
        file=file,
        description=description
    )


@router.get("/tickets/{ticket_id}/attachments", response_model=AttachmentListResponse)
def list_attachments(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    attachments = attachments_service.list_attachments(db=db, ticket_id=ticket_id)
    return {
        "total": len(attachments),
        "items": attachments
    }


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}", response_model=Attachment)
def get_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db)
):
    return attachments_service.get_attachment(db=db, ticket_id=ticket_id, attachment_id=attachment_id)


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}/download")
def download_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db)
):
    attachment = attachments_service.get_attachment(
        db=db,
        ticket_id=ticket_id,
        attachment_id=attachment_id
    )
    
    file_path = attachments_service.get_attachment_file_path(attachment)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=file_path,
        media_type=attachment.content_type,
        filename=attachment.original_name
    )


@router.delete("/tickets/{ticket_id}/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db)
):
    attachments_service.delete_attachment(
        db=db,
        ticket_id=ticket_id,
        attachment_id=attachment_id
    )
    return None


@router.patch("/tickets/{ticket_id}/attachments/{attachment_id}", response_model=Attachment)
def update_attachment_description(
    ticket_id: int,
    attachment_id: int,
    description: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    return attachments_service.update_attachment_description(
        db=db,
        ticket_id=ticket_id,
        attachment_id=attachment_id,
        description=description
    )

