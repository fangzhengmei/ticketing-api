from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#3b82f6", pattern=r"^#[0-9a-fA-F]{6}$")
    description: Optional[str] = Field(None, max_length=200)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: Optional[str] = Field(None, max_length=200)


class Tag(BaseModel):
    id: int
    name: str
    color: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Tag]

    model_config = ConfigDict(from_attributes=True)


class TagUsageResponse(BaseModel):
    id: int
    name: str
    color: str
    description: Optional[str]
    ticket_count: int

    model_config = ConfigDict(from_attributes=True)


class TagMergeRequest(BaseModel):
    target_tag_id: int = Field(..., ge=1)
    source_tag_ids: list[int] = Field(..., min_length=1)


class TagMergeResponse(BaseModel):
    target_tag: Tag
    migrated_ticket_count: int
    deleted_tag_count: int
    deleted_tag_names: list[str]

    model_config = ConfigDict(from_attributes=True)


class TagMergePreviewSource(BaseModel):
    id: int
    name: str
    color: str
    current_ticket_count: int

    model_config = ConfigDict(from_attributes=True)


class TagMergePreviewResponse(BaseModel):
    target_tag: Tag
    target_current_ticket_count: int
    target_after_merge_ticket_count: int
    sources_to_delete: list[TagMergePreviewSource]
    tickets_to_migrate: int
    total_tags_to_delete: int

    model_config = ConfigDict(from_attributes=True)


class TagMergeHistorySource(BaseModel):
    id: int
    name: str
    color: str
    current_ticket_count: int

    model_config = ConfigDict(from_attributes=True)


class TagMergeHistory(BaseModel):
    id: int
    target_tag_id: int
    target_tag_name: str
    target_tag_color: str
    source_tags: list[TagMergeHistorySource]
    migrated_ticket_count: int
    deleted_tag_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagMergeHistoryListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TagMergeHistory]

    model_config = ConfigDict(from_attributes=True)


class TagMergeStatsResponse(BaseModel):
    total_merges: int
    total_migrated_tickets: int
    total_deleted_tags: int

    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    title: str
    status: TicketStatus = TicketStatus.open
    tag_ids: Optional[list[int]] = None


class TicketUpdate(BaseModel):
    status: TicketStatus
    title: Optional[str] = None
    tag_ids: Optional[list[int]] = None


class Ticket(BaseModel):
    id: int
    title: str
    status: TicketStatus
    tags: list[Tag] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class TicketListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Ticket]

    model_config = ConfigDict(from_attributes=True)