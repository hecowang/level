from app.config import settings
from app.utils.logger import logger
from app.routers import health, agent, stock
from app.middleware.requesttime import RequestTimingMiddleware
from app.middleware.traceid import TraceIDMiddleware 
from dotenv import load_dotenv
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


load_dotenv(dotenv_path=settings.Config.env_file, encoding=settings.Config.env_file_encoding)

def create_app():
    """创建并配置FastAPI应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="1.0.0",
        lifespan=stock.lifespan,
    )
    
    # 包含路由
    app.include_router(health.router)
    app.include_router(stock.router)
    app.include_router(agent.router, prefix=settings.API_V1_STR)

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