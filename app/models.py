from pydantic import BaseModel, ConfigDict
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


class MessageResponse(BaseModel):
    message: str

class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

    model_config = ConfigDict(from_attributes=True)