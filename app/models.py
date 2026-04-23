from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from enum import Enum
from datetime import datetime

class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    merged = "merged"


class TicketCreate(BaseModel):
    title: str
    status: TicketStatus = TicketStatus.open


class TicketUpdate(BaseModel):
    status: TicketStatus


class TicketMerge(BaseModel):
    target_ticket_id: int
    reason: Optional[str] = None


class MergedTicketInfo(BaseModel):
    id: int
    title: str
    status: TicketStatus

    model_config = ConfigDict(from_attributes=True)


class Ticket(BaseModel):
    id: int
    title: str
    status: TicketStatus
    merged_to_id: Optional[int] = None
    merged_at: Optional[datetime] = None
    merge_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TicketWithRelations(Ticket):
    merged_to: Optional[MergedTicketInfo] = None
    merged_tickets: list[MergedTicketInfo] = []


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    author: Optional[str] = Field(None, max_length=100)


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class Comment(BaseModel):
    id: int
    ticket_id: int
    original_ticket_id: Optional[int] = None
    content: str
    author: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Comment]

    model_config = ConfigDict(from_attributes=True)


class CommentWithTicketInfo(Comment):
    original_ticket_title: Optional[str] = None


class CommentListWithTicketInfoResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CommentWithTicketInfo]

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str

class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

    model_config = ConfigDict(from_attributes=True)