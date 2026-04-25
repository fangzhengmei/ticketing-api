from pydantic import BaseModel, ConfigDict, field_validator
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
    deadline: Optional[datetime] = None


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    deadline: Optional[datetime] = None


class Ticket(BaseModel):
    id: int
    title: str
    status: TicketStatus
    deadline: Optional[datetime] = None
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str

class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

model_config = ConfigDict(from_attributes=True)