from pydantic import BaseModel, ConfigDict
from typing import Optional
from enum import Enum

class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class TicketCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: TicketStatus = TicketStatus.open


class TicketUpdate(BaseModel):
    status: TicketStatus


class Ticket(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: TicketStatus

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str

class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

model_config = ConfigDict(from_attributes=True)