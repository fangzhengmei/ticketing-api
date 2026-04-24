from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class SlaStatus(str, Enum):
    on_track = "on_track"
    warning = "warning"
    breached = "breached"
    not_set = "not_set"


def validate_deadline_not_in_past(v: Optional[datetime]) -> Optional[datetime]:
    if v is None:
        return None
    
    if v.tzinfo is not None:
        v = v.replace(tzinfo=None)
    
    now = datetime.utcnow()
    if v < now:
        raise ValueError("sla_deadline cannot be in the past")
    
    return v


class TicketCreate(BaseModel):
    title: str
    status: TicketStatus = TicketStatus.open
    sla_deadline: Optional[datetime] = None

    @field_validator("sla_deadline")
    @classmethod
    def validate_sla_deadline(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return None
        if v.tzinfo is not None:
            v = v.replace(tzinfo=None)
        now = datetime.utcnow()
        if v < now:
            raise ValueError("sla_deadline cannot be in the past")
        return v


class TicketUpdate(BaseModel):
    status: TicketStatus
    sla_deadline: Optional[datetime] = None

    @field_validator("sla_deadline")
    @classmethod
    def validate_sla_deadline(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return None
        if v.tzinfo is not None:
            v = v.replace(tzinfo=None)
        now = datetime.utcnow()
        if v < now:
            raise ValueError("sla_deadline cannot be in the past")
        return v


class Ticket(BaseModel):
    id: int
    title: str
    status: TicketStatus
    created_at: datetime
    sla_deadline: Optional[datetime]
    sla_breached: bool
    resolved_at: Optional[datetime]
    sla_status: SlaStatus = SlaStatus.not_set

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

    model_config = ConfigDict(from_attributes=True)
