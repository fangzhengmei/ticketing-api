from fastapi import APIRouter, HTTPException, Depends, Query, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.db_models import TicketDB
from app.models import Ticket, TicketCreate, TicketUpdate, MessageResponse
from app.models import TicketListResponse
from app.models import TicketStatus, SlaStatus
from app.services.tickets import CurrentUser

from app.services import tickets as tickets_service

ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_is_admin: Optional[str] = Header(None, alias="X-Is-Admin"),
) -> CurrentUser:
    is_admin = False
    if x_is_admin and x_is_admin.lower() in ("true", "1", "yes"):
        is_admin = True
    return CurrentUser(user_id=x_user_id, is_admin=is_admin)


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[TicketStatus] = Query(None, description="按工单状态过滤"),
    sla_status: Optional[SlaStatus] = Query(None, description="按SLA状态过滤"),
    db: Session = Depends(get_db)
):
    return tickets_service.list_tickets(
        db=db,
        limit=limit,
        offset=offset,
        status=status,
        sla_status=sla_status,
    )


@router.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return tickets_service.get_ticket(db=db, ticket_id=ticket_id)


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return tickets_service.create_ticket(
        db=db,
        payload=payload,
        created_by=current_user.user_id,
    )


@router.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return tickets_service.update_ticket_status(
        db=db,
        ticket_id=ticket_id,
        payload=payload,
        current_user=current_user,
    )


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None


@router.get("/sla/statistics")
def get_sla_statistics(db: Session = Depends(get_db)):
    return tickets_service.get_sla_statistics(db=db)
