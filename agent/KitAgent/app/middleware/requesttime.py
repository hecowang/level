# middleware/request_timing.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()  # 记录请求开始时间
        response = await call_next(request)  # 处理请求
        process_time = time.time() - start_time  # 计算耗时（秒）
        
        # 将耗时添加到响应头（可选）
        response.headers["X-Process-Time"] = str(process_time)
        
        # 记录日志（需结合 logging 配置）
        return response