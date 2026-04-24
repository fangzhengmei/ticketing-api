from fastapi import APIRouter, HTTPException, Depends, Query, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.db_models import TicketDB
from app.models import Ticket, TicketCreate, TicketUpdate, MessageResponse
from app.models import TicketListResponse
from app.models import TicketStatus, SlaStatus
from app.auth import get_api_key_info, AuthenticatedUser, APIKeyInfo, UserRole

from app.services import tickets as tickets_service

ALLOWED_TRANSITIONS = {
    TicketStatus.open: {TicketStatus.in_progress, TicketStatus.resolved},
    TicketStatus.in_progress: {TicketStatus.resolved},
    TicketStatus.resolved: set(),
}

security = HTTPBearer(
    scheme_name="BearerToken",
    description="API Key authentication using Bearer token. "
                "Format: 'Authorization: Bearer <your-api-key>'"
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    key_info = get_api_key_info(api_key)
    
    if key_info is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return AuthenticatedUser(
        user_id=key_info.user_id,
        role=key_info.role,
    )


router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    return {"ok": True}


@router.get(
    "/tickets",
    response_model=TicketListResponse,
    tags=["tickets"],
    summary="获取工单列表",
    description="获取工单列表，支持按状态和SLA状态过滤。需要Bearer Token认证。",
)
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[TicketStatus] = Query(None, description="按工单状态过滤"),
    sla_status: Optional[SlaStatus] = Query(None, description="按SLA状态过滤"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return tickets_service.list_tickets(
        db=db,
        limit=limit,
        offset=offset,
        status=status,
        sla_status=sla_status,
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=Ticket,
    tags=["tickets"],
    summary="获取单个工单",
    description="根据ID获取工单详情。需要Bearer Token认证。",
)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return tickets_service.get_ticket(db=db, ticket_id=ticket_id)


@router.post(
    "/tickets",
    response_model=Ticket,
    status_code=201,
    tags=["tickets"],
    summary="创建工单",
    description="创建新工单，可选设置SLA截止时间。sla_deadline不能是过去时间。需要Bearer Token认证。",
)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return tickets_service.create_ticket(
        db=db,
        payload=payload,
        created_by=current_user.user_id,
    )


@router.patch(
    "/tickets/{ticket_id}",
    response_model=Ticket,
    tags=["tickets"],
    summary="更新工单",
    description="更新工单状态或SLA截止时间。修改SLA截止时间需要工单创建者或管理员权限。需要Bearer Token认证。",
)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return tickets_service.update_ticket_status(
        db=db,
        ticket_id=ticket_id,
        payload=payload,
        current_user=current_user,
    )


@router.delete(
    "/tickets/{ticket_id}",
    status_code=204,
    tags=["tickets"],
    summary="删除工单",
    description="删除指定工单。需要Bearer Token认证。",
)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    tickets_service.delete_ticket(db=db, ticket_id=ticket_id)
    return None


@router.get(
    "/sla/statistics",
    tags=["sla"],
    summary="获取SLA统计",
    description="获取所有工单的SLA状态统计信息。需要Bearer Token认证。",
)
def get_sla_statistics(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return tickets_service.get_sla_statistics(db=db)
