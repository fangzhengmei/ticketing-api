from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class TicketDB(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    solution = Column(Text, nullable=True)
    solution_time = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolution_category = Column(String, nullable=True)
