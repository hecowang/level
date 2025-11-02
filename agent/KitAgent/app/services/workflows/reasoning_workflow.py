"""推理计算工作流"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from app.models.intent import IntentType
from app.services.workflows.base_workflow import BaseWorkflow
from app.config import settings
from app.utils.logger import logger


class ReasoningWorkflow(BaseWorkflow):
    """推理计算工作流"""
    
    @property
    def intent_type(self) -> IntentType:
        return IntentType.REASONING
    
    def __init__(self):
        """初始化推理计算工作流"""
        self.llm = None
        self._init_llm()
    
    def _init_llm(self):
        """初始化 LLM"""
        try:
            if settings.OPENAI_API_KEY:
                self.llm = ChatOpenAI(
                    model=settings.MODEL_NAME,
                    temperature=0.3,  # 推理任务使用较低温度
                    max_tokens=settings.LLM_MAX_TOKENS,
                    api_key=settings.OPENAI_API_KEY
                )
        except Exception as e:
            logger.error(f"初始化推理 LLM 失败: {e}")
    
    async def execute(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行推理计算工作流
        
        Args:
            user_input: 用户输入
            context: 上下文信息
        
        Returns:
            推理结果
        """
        try:
            if self.llm:
                # 构建提示词
                prompt = f"""你是一个专业的推理和计算助手。请仔细分析用户的问题，进行推理或计算，然后给出详细的过程和答案。

用户问题：{user_input}

请按照以下步骤回答：
1. 理解问题
2. 分析思路
3. 进行计算或推理
4. 给出最终答案
"""
                
                # 调用 LLM
                if hasattr(self.llm, 'ainvoke'):
                    response = await self.llm.ainvoke([("human", prompt)])
                else:
                    response = self.llm.invoke([("human", prompt)])
                
                reply = response.content if hasattr(response, 'content') else str(response)
                
                return {
                    "success": True,
                    "reply": reply,
                    "workflow": "reasoning"
                }
            else:
                # 简单计算模拟
                reply = f"正在进行推理计算：{user_input}。推理功能需要配置 LLM。"
                return {
                    "success": True,
                    "reply": reply,
                    "workflow": "reasoning"
                }
        
        except Exception as e:
            logger.error(f"推理计算工作流执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "reply": f"抱歉，推理计算时出现了错误。",
                "workflow": "reasoning"
            }

