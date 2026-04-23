from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class TicketDB(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    
    merged_to_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    merged_at = Column(DateTime, nullable=True)
    merge_reason = Column(String, nullable=True)
    
    merged_to = relationship(
        "TicketDB",
        remote_side=[id],
        backref="merged_tickets"
    )
