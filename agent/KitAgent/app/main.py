# 注意：config.py 中已经加载了 .env 文件，这里不需要重复加载
from app.config import settings
from app.utils.logger import logger
from app.routers import health, agent
from app.middleware.requesttime import RequestTimingMiddleware
from app.middleware.traceid import TraceIDMiddleware 
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

def create_app():
    """创建并配置FastAPI应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="1.0.0"
    )
    
    # 包含路由
    app.include_router(health.router)
    app.include_router(agent.router, prefix=settings.API_V1_STR)
    
    # # 生命周期事件
    # @app.on_event("startup")
    # async def startup_event():
    #     logger.info("Starting AI Agent Server...")
    #     # 可以在这里初始化模型连接等
    
    # @app.on_event("shutdown")
    # async def shutdown_event():
    #     logger.info("Shutting down AI Agent Server...")
    #     # 清理资源
    
    return app

app = create_app()
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(TraceIDMiddleware)

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)  # 暴露 /metrics 端点


@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "Welcome to AI Agent Server",
        "documentation": f"{settings.API_V1_STR}/docs",
        "redoc": f"{settings.API_V1_STR}/redoc"
    }