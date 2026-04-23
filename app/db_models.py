from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
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
    
    comments = relationship("CommentDB", back_populates="ticket", foreign_keys="CommentDB.ticket_id")


class CommentDB(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    original_ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    ticket = relationship("TicketDB", back_populates="comments", foreign_keys=[ticket_id])
