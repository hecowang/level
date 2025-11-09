"""聊天工作流"""
from typing import Dict, Any, AsyncGenerator
from langchain_openai import ChatOpenAI
from app.models.intent import IntentType
from app.services.workflows.base_workflow import BaseWorkflow
from app.config import settings
from app.utils.logger import logger
from app.models.chat_context import ChatContext
from app.services.tts.volcengine.binary import do_tts


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
                    api_key=settings.OPENAI_API_KEY,
                    streaming=True  # 启用流式
                )
            else:
                logger.warning("OPENAI_API_KEY 未配置，聊天工作流将使用模拟模式")
        except Exception as e:
            logger.error(f"初始化聊天 LLM 失败: {e}")
    
    async def execute(self, chat_context: ChatContext) -> Dict[str, Any]:
        """
        执行聊天工作流
        
        Args:
            chat_context: 聊天上下文对象，包含用户输入和上下文信息
        
        Returns:
            包含回复消息的结果
        """
        user_input = chat_context.query or ""
        conversation_history = chat_context.conversation_history
        
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
                
                # 流式调用 LLM
                full_reply = ""
                async for chunk in self.llm.astream(messages):
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
                    
                    if chat_context.agent and hasattr(chat_context.agent, 'send_text'):
                        await chat_context.agent.send_text(reply_chunk)
                
                return {
                    "success": True,
                    "reply": full_reply,
                    "workflow": "chat"
                }
            else:
                # 模拟回复
                reply = f"收到您的消息：{user_input}。这是一个聊天回复（LLM 未配置）。"
                
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

