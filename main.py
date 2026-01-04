from fastapi import FastAPI
from app.routes import router
from app.database import Base, engine
from app import db_models  # IMPORTANT: αυτό κάνει register το TicketDB

app = FastAPI()
Base.metadata.create_all(bind=engine)

app.include_router(router)
