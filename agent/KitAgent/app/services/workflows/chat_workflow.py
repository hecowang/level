"""聊天工作流"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from app.models.intent import IntentType
from app.services.workflows.base_workflow import BaseWorkflow
from app.config import settings
from app.utils.logger import logger


class ChatWorkflow(BaseWorkflow):
    """聊天工作流"""
    
    @property
    def intent_type(self) -> IntentType:
        return IntentType.CHAT
    
    def __init__(self):
        """初始化聊天工作流"""
        self.llm = None
        self._init_llm()
    
    def _init_llm(self):
        """初始化 LLM"""
        try:
            if settings.OPENAI_API_KEY:
                self.llm = ChatOpenAI(
                    model=settings.MODEL_NAME,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    api_key=settings.OPENAI_API_KEY
                )
            else:
                logger.warning("OPENAI_API_KEY 未配置，聊天工作流将使用模拟模式")
        except Exception as e:
            logger.error(f"初始化聊天 LLM 失败: {e}")
    
    async def execute(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行聊天工作流
        
        Args:
            user_input: 用户输入
            context: 上下文信息
        
        Returns:
            包含回复消息的结果
        """
        context = context or {}
        conversation_history = context.get("conversation_history", [])
        
        try:
            if self.llm:
                # 构建消息列表
                messages = []
                if conversation_history:
                    # 添加历史消息（最多最近5条）
                    for msg in conversation_history[-5:]:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        if role == "user":
                            messages.append(("human", content))
                        elif role == "assistant":
                            messages.append(("ai", content))
                
                # 添加当前用户输入
                messages.append(("human", user_input))
                
                # 调用 LLM
                if hasattr(self.llm, 'ainvoke'):
                    response = await self.llm.ainvoke(messages)
                else:
                    response = self.llm.invoke(messages)
                
                reply = response.content if hasattr(response, 'content') else str(response)
                
                return {
                    "success": True,
                    "reply": reply,
                    "workflow": "chat"
                }
            else:
                # 模拟回复
                return {
                    "success": True,
                    "reply": f"收到您的消息：{user_input}。这是一个聊天回复（LLM 未配置）。",
                    "workflow": "chat"
                }
        
        except Exception as e:
            logger.error(f"聊天工作流执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "reply": "抱歉，处理您的消息时出现了错误。",
                "workflow": "chat"
            }

