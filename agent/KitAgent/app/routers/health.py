# app/routers/health.py
from fastapi import APIRouter
from app.models.request import HealthCheck
from app.utils.logger import logger

router = APIRouter(
    prefix="/health",
    tags=["health"]
)

@router.get("/", response_model=HealthCheck)
async def health_check():
    """健康检查端点"""
    return HealthCheck()