"""聊天上下文模型"""
from typing import Any, Optional, List, Dict
from enum import Enum
from pydantic import BaseModel
from pydantic import Field


class RequestType(str, Enum):
    """请求类型枚举"""
    TEXT = "text"
    AUDIO = "audio"


class ChatContext(BaseModel):
    """
    聊天上下文类
    用于存储ChatService处理用户对话请求的上下文信息
    """
    # 允许在运行时动态注入额外属性（Pydantic v2 配置）
    model_config = {"extra": "allow"}

    query: Optional[str] = None
    answer: Optional[str] = None
    device_id: Optional[str] = None
    agent: Optional[object] = None  # 指向 ChatAgent 实例
    conversation_history: List[Dict] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 推荐显式存放动态属性
# ...existing code...