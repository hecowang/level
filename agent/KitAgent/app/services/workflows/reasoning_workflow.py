"""推理计算工作流"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from app.models.intent import IntentType
from app.services.workflows.base_workflow import BaseWorkflow
from app.config import settings
from app.utils.logger import logger
from app.models.chat_context import ChatContext
from app.services.tts.volcengine.binary import do_tts


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
                    api_key=settings.OPENAI_API_KEY,
                    streaming=True  # 启用流式
                )
        except Exception as e:
            logger.error(f"初始化推理 LLM 失败: {e}")
    
    async def execute(self, chat_context: ChatContext) -> Dict[str, Any]:
        """
        执行推理计算工作流
        
        Args:
            chat_context: 聊天上下文对象，包含用户输入和上下文信息
        
        Returns:
            推理结果
        """
        user_input = chat_context.query or ""
        
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
                
                # 流式调用 LLM
                full_reply = ""
                async for chunk in self.llm.astream([("human", prompt)]):
                    if hasattr(chunk, 'content'):
                        reply_chunk = chunk.content
                    else:
                        reply_chunk = str(chunk)
                    
                    full_reply += reply_chunk
                    
                    # 立即将每个chunk发送给TTS
                    if chat_context.agent and hasattr(chat_context.agent, 'send_audio'):
                        try:
                            async for audio_chunk in do_tts(reply_chunk):
                                await chat_context.agent.send_audio(audio_chunk)
                        except Exception as e:
                            logger.error(f"TTS转换失败: {e}", exc_info=True)
                
                return {
                    "success": True,
                    "reply": full_reply,
                    "workflow": "reasoning"
                }
            else:
                # 简单计算模拟
                reply = f"正在进行推理计算：{user_input}。推理功能需要配置 LLM。"
                
                # 流式返回文本并转换为语音
                if chat_context.agent and hasattr(chat_context.agent, 'send_audio'):
                    try:
                        async for audio_chunk in do_tts(reply):
                            await chat_context.agent.send_audio(audio_chunk)
                    except Exception as e:
                        logger.error(f"TTS转换失败: {e}", exc_info=True)
                
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

