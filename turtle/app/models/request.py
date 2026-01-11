# app/models/request.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class AgentRequest(BaseModel):
    input: str = Field(..., description="用户输入文本")
    user_id: Optional[str] = Field(None, description="用户唯一标识")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    stream: bool = Field(False, description="是否流式响应")

class HealthCheck(BaseModel):
    status: str = "ok"