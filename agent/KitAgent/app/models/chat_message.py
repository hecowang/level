"""WebSocket 消息模型"""
from typing import Optional, Literal
from pydantic import BaseModel


class WebSocketMessage(BaseModel):
    """WebSocket 消息基类"""
    type: str
    data: Optional[dict] = None


class AuthMessage(BaseModel):
    """认证消息"""
    api_key: str


class RegisterDeviceMessage(BaseModel):
    """注册设备消息"""
    device_id: str


class ChatMessage(BaseModel):
    """聊天消息"""
    content: str
    message_type: Literal["text", "audio"] = "text"
    # 如果是音频，可以包含音频数据的 base64 编码或文件路径
    audio_data: Optional[str] = None


class ServerResponse(BaseModel):
    """服务器响应消息"""
    type: str
    status: Literal["success", "error"]
    message: str
    data: Optional[dict] = None

