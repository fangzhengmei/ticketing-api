from fastapi import FastAPI
from app.routes import router
from app.database import Base, engine
from app import db_models

app = FastAPI(
    title="Ticket API",
    description="工单管理系统 API - 支持 SLA 追踪和权限控制",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "tickets",
            "description": "工单管理操作",
        },
        {
            "name": "sla",
            "description": "SLA 相关统计",
        },
    ],
)

Base.metadata.create_all(bind=engine)

app.include_router(router)
