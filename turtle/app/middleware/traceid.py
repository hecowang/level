import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.ctxvars import trace_id_var

class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 生成 Trace ID（或从请求头获取，如 X-B3-TraceId）
        trace_id = request.headers.get("X-Bce-RequestID", str(uuid.uuid4()))
        request.state.trace_id = trace_id  # 存储在请求状态中

        trace_id_var.set(trace_id)
        
        response = await call_next(request)
        response.headers["X-Bce-RequestID"] = trace_id
        return response