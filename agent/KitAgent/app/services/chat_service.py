"""Chat Agent 服务层，管理对话历史和设备状态"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
from app.utils.logger import logger
from app.config import settings


class ChatHistory:
    """聊天历史记录"""
    def __init__(self, device_id: str, max_history: int = 100):
        """
        初始化聊天历史
        
        Args:
            device_id: 设备 ID
            max_history: 最大历史记录数
        """
        self.device_id = device_id
        self.max_history = max_history
        self.messages: deque = deque(maxlen=max_history)
        self.created_at = datetime.now()
        self.last_active = datetime.now()
    
    def add_message(self, role: str, content: str, message_type: str = "text"):
        """
        添加消息到历史记录
        
        Args:
            role: 角色 (user/assistant/system)
            content: 消息内容
            message_type: 消息类型 (text/audio)
        """
        message = {
            "role": role,
            "content": content,
            "type": message_type,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)
        self.last_active = datetime.now()
        logger.debug(f"设备 {self.device_id} 添加消息: {role} - {len(content)} 字符")
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        获取聊天历史
        
        Args:
            limit: 限制返回的消息数量
        
        Returns:
            消息历史列表
        """
        messages = list(self.messages)
        if limit:
            messages = messages[-limit:]
        return messages
    
    def clear_history(self):
        """清空聊天历史"""
        self.messages.clear()
        logger.info(f"设备 {self.device_id} 的聊天历史已清空")


class ChatService:
    """Chat Agent 服务类"""
    
    def __init__(self):
        """初始化 Chat 服务"""
        # 设备ID -> 聊天历史的映射
        self.device_histories: Dict[str, ChatHistory] = {}
        # API Key 验证（生产环境应该使用数据库或配置）
        self.valid_api_keys: set = self._load_valid_api_keys()
    
    def _load_valid_api_keys(self) -> set:
        """
        加载有效的 API Key（从配置或环境变量）
        
        Returns:
            有效的 API Key 集合
        """
        keys = set()
        
        # 从配置中加载单个 API Key
        api_key = getattr(settings, 'API_KEY', '')
        if api_key:
            keys.add(api_key)
        
        # 从配置中加载多个 API Key
        # 格式: API_KEYS=key1,key2,key3
        api_keys_str = getattr(settings, 'API_KEYS', '')
        if api_keys_str:
            keys.update([k.strip() for k in api_keys_str.split(',') if k.strip()])
        
        return keys
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        验证 API Key
        
        Args:
            api_key: 要验证的 API Key
        
        Returns:
            是否有效
        """
        is_valid = api_key in self.valid_api_keys
        if is_valid:
            logger.info(f"API Key 验证成功")
        else:
            logger.warning(f"API Key 验证失败: {api_key[:8]}...")
        return is_valid
    
    def register_device(self, device_id: str) -> ChatHistory:
        """
        注册设备并返回或创建聊天历史
        
        Args:
            device_id: 设备 ID
        
        Returns:
            聊天历史对象
        """
        if device_id not in self.device_histories:
            self.device_histories[device_id] = ChatHistory(device_id)
            logger.info(f"新设备注册: {device_id}")
        else:
            logger.debug(f"设备 {device_id} 已存在")
        
        return self.device_histories[device_id]
    
    def get_chat_history(self, device_id: str) -> Optional[ChatHistory]:
        """
        获取设备的聊天历史
        
        Args:
            device_id: 设备 ID
        
        Returns:
            聊天历史对象，如果不存在返回 None
        """
        return self.device_histories.get(device_id)
    
    def save_message(self, device_id: str, role: str, content: str, message_type: str = "text"):
        """
        保存消息到设备历史
        
        Args:
            device_id: 设备 ID
            role: 角色
            content: 消息内容
            message_type: 消息类型
        """
        history = self.get_chat_history(device_id)
        if history:
            history.add_message(role, content, message_type)
        else:
            logger.warning(f"设备 {device_id} 不存在，无法保存消息")
    
    def get_conversation_context(self, device_id: str, limit: int = 10) -> List[Dict]:
        """
        获取对话上下文（用于发送给 AI 模型）
        
        Args:
            device_id: 设备 ID
            limit: 返回最近的消息数量
        
        Returns:
            消息列表，格式适合发送给 AI 模型
        """
        history = self.get_chat_history(device_id)
        if not history:
            return []
        
        messages = history.get_history(limit=limit)
        # 转换为 AI 模型需要的格式
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    def clear_device_history(self, device_id: str):
        """
        清空设备历史
        
        Args:
            device_id: 设备 ID
        """
        history = self.get_chat_history(device_id)
        if history:
            history.clear_history()
            logger.info(f"设备 {device_id} 的聊天历史已清空")
    
    def remove_device(self, device_id: str):
        """
        移除设备（清理资源）
        
        Args:
            device_id: 设备 ID
        """
        if device_id in self.device_histories:
            del self.device_histories[device_id]
            logger.info(f"设备 {device_id} 已移除")


def get_chat_service() -> ChatService:
    """获取全局 chat 服务实例（单例模式）"""
    global chat_service
    if chat_service is None:
        chat_service = ChatService()
    return chat_service


# 创建全局 chat 服务实例
chat_service = ChatService()

