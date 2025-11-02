"""基础工作流类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.intent import IntentType


class BaseWorkflow(ABC):
    """工作流基类"""
    
    @property
    @abstractmethod
    def intent_type(self) -> IntentType:
        """返回该工作流处理的意图类型"""
        pass
    
    @abstractmethod
    async def execute(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            user_input: 用户输入
            context: 上下文信息（可能包含对话历史、设备信息等）
        
        Returns:
            执行结果字典
        """
        pass
    
    def get_system_prompt(self) -> str:
        """获取系统提示词（可选）"""
        return ""

