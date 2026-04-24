from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base
from datetime import datetime


class TicketDB(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sla_deadline = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime, nullable=True)
