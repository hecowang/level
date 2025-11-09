"""基础工作流类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.intent import IntentType
from app.models.chat_context import ChatContext


class BaseWorkflow(ABC):
    """工作流基类"""
    
    @property
    @abstractmethod
    def intent_type(self) -> IntentType:
        """返回该工作流处理的意图类型"""
        pass
    
    @abstractmethod
    async def execute(self, chat_context: ChatContext) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            chat_context: 聊天上下文对象，包含用户输入和上下文信息
        
        Returns:
            执行结果字典
        """
        pass
    
    def get_system_prompt(self) -> str:
        """获取系统提示词（可选）"""
        return ""

