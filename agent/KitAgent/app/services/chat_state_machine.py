"""Chat Agent 状态机"""
from enum import Enum
from typing import Optional, Dict
from app.utils.logger import logger


class ChatState(Enum):
    """聊天状态枚举"""
    INIT = "init"  # 初始状态，等待 API key 校验
    AUTHENTICATED = "authenticated"  # 已认证，等待 device id
    READY = "ready"  # 准备就绪，可以开始聊天
    CHATTING = "chatting"  # 正在聊天中


class ChatStateMachine:
    """聊天状态机"""
    
    def __init__(self):
        """初始化状态机"""
        self.state = ChatState.INIT
        self.api_key: Optional[str] = None
        self.device_id: Optional[str] = None
        self.state_data: Dict = {}
    
    def get_state(self) -> ChatState:
        """获取当前状态"""
        return self.state
    
    def is_authenticated(self) -> bool:
        """是否已认证"""
        return self.state != ChatState.INIT
    
    def is_ready(self) -> bool:
        """是否准备就绪"""
        return self.state == ChatState.READY or self.state == ChatState.CHATTING
    
    def authenticate(self, api_key: str):
        """
        认证 API Key
        
        Args:
            api_key: API Key
        """
        if self.state != ChatState.INIT:
            logger.warning(f"状态机不在 INIT 状态，当前状态: {self.state}")
            return False
        
        self.api_key = api_key
        self.state = ChatState.AUTHENTICATED
        logger.info("状态机: INIT -> AUTHENTICATED")
        return True
    
    def register_device(self, device_id: str):
        """
        注册设备
        
        Args:
            device_id: 设备 ID
        """
        if self.state != ChatState.AUTHENTICATED:
            logger.warning(f"状态机不在 AUTHENTICATED 状态，当前状态: {self.state}")
            return False
        
        self.device_id = device_id
        self.state = ChatState.READY
        logger.info(f"状态机: AUTHENTICATED -> READY (device_id: {device_id})")
        return True
    
    def start_chatting(self):
        """开始聊天"""
        if self.state != ChatState.READY:
            logger.warning(f"状态机不在 READY 状态，当前状态: {self.state}")
            return False
        
        self.state = ChatState.CHATTING
        logger.debug("状态机: READY -> CHATTING")
        return True
    
    def reset(self):
        """重置状态机"""
        logger.info("状态机重置")
        self.state = ChatState.INIT
        self.api_key = None
        self.device_id = None
        self.state_data.clear()
    
    def get_info(self) -> Dict:
        """获取状态信息"""
        return {
            "state": self.state.value,
            "device_id": self.device_id,
            "is_authenticated": self.is_authenticated(),
            "is_ready": self.is_ready()
        }

