from pydantic import BaseModel, ConfigDict
from typing import Optional
from enum import Enum
from datetime import datetime

class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class ResolutionCategory(str, Enum):
    code_fix = "code_fix"
    configuration = "configuration"
    documentation = "documentation"
    training = "training"
    environment = "environment"
    other = "other"


class TicketCreate(BaseModel):
    title: str
    status: TicketStatus = TicketStatus.open


class TicketUpdate(BaseModel):
    status: TicketStatus
    solution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_category: Optional[ResolutionCategory] = None


class Ticket(BaseModel):
    id: int
    title: str
    status: TicketStatus
    solution: Optional[str] = None
    solution_time: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_category: Optional[ResolutionCategory] = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str

class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

model_config = ConfigDict(from_attributes=True)