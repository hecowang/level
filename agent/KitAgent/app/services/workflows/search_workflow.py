"""实搜工作流"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from app.models.intent import IntentType
from app.services.workflows.base_workflow import BaseWorkflow
from app.config import settings
from app.utils.logger import logger
from app.models.chat_context import ChatContext
from app.services.tts.volcengine.binary import do_tts


class SearchWorkflow(BaseWorkflow):
    """实时搜索工作流"""
    
    @property
    def intent_type(self) -> IntentType:
        return IntentType.SEARCH
    
    def __init__(self):
        """初始化搜索工作流"""
        self.llm = None
        self._init_llm()
    
    def _init_llm(self):
        """初始化 LLM"""
        try:
            if settings.OPENAI_API_KEY:
                self.llm = ChatOpenAI(
                    model=settings.MODEL_NAME,
                    temperature=0.1,  # 搜索任务使用较低温度
                    max_tokens=settings.LLM_MAX_TOKENS,
                    api_key=settings.OPENAI_API_KEY,
                    streaming=True  # 启用流式
                )
        except Exception as e:
            logger.error(f"初始化搜索 LLM 失败: {e}")
    
    async def execute(self, chat_context: ChatContext) -> Dict[str, Any]:
        """
        执行实搜工作流
        
        Args:
            chat_context: 聊天上下文对象，包含用户输入和上下文信息
        
        Returns:
            搜索结果
        """
        user_input = chat_context.query or ""
        
        try:
            if self.llm:
                # 构建提示词
                prompt = f"""你是一个专业的搜索助手。请根据用户的问题提供准确、简洁的搜索结果。

用户搜索：{user_input}

请按照以下格式提供搜索结果：
1. 首先给出一个简洁的总结
2. 然后列出3-5个最相关的搜索结果
3. 每个结果应该包含关键信息
4. 最后给出搜索建议或下一步操作
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
                    "workflow": "search",
                    "search_query": user_input
                }
            else:
                # 模拟搜索结果
                logger.info(f"实搜工作流：搜索 '{user_input}'")
                
                # 模拟搜索结果
                search_results = [
                    f"关于 '{user_input}' 的搜索结果 1",
                    f"关于 '{user_input}' 的搜索结果 2",
                    f"关于 '{user_input}' 的搜索结果 3"
                ]
                
                reply = f"我找到了关于 '{user_input}' 的信息：\n" + "\n".join(search_results)
                
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
                    "workflow": "search",
                    "search_query": user_input,
                    "results": search_results
                }
        
        except Exception as e:
            logger.error(f"实搜工作流执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "reply": f"抱歉，搜索 '{user_input}' 时出现了错误。",
                "workflow": "search"
            }

