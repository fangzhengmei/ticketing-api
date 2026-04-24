from pydantic import BaseModel, ConfigDict
from typing import Optional
from enum import Enum
from datetime import datetime

class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class TicketCreate(BaseModel):
    title: str
    status: TicketStatus = TicketStatus.open


class TicketUpdate(BaseModel):
    status: TicketStatus


class Attachment(BaseModel):
    id: int
    ticket_id: int
    original_name: str
    content_type: str
    file_size: int
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentListResponse(BaseModel):
    total: int
    items: list[Attachment]


class Ticket(BaseModel):
    id: int
    title: str
    status: TicketStatus

    model_config = ConfigDict(from_attributes=True)


class TicketWithAttachments(Ticket):
    attachments: list[Attachment] = []


class MessageResponse(BaseModel):
    message: str


class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

    model_config = ConfigDict(from_attributes=True)