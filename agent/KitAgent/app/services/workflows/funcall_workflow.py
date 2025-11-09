"""FunCall 工作流"""
from typing import Dict, Any
from app.models.intent import IntentType
from app.services.workflows.base_workflow import BaseWorkflow
from app.utils.logger import logger
from app.models.chat_context import ChatContext
from app.services.tts.volcengine.binary import do_tts


class FuncallWorkflow(BaseWorkflow):
    """FunCall 工作流（函数调用）"""
    
    @property
    def intent_type(self) -> IntentType:
        return IntentType.FUNCALL
    
    async def execute(self, chat_context: ChatContext) -> Dict[str, Any]:
        """
        执行 FunCall 工作流
        
        Args:
            chat_context: 聊天上下文对象，包含用户输入和上下文信息
        
        Returns:
            函数调用结果
        """
        user_input = chat_context.query or ""
        device_id = chat_context.device_id
        
        try:
            logger.info(f"FunCall 工作流：设备 {device_id}，请求 '{user_input}'")
            
            user_input_lower = user_input.lower()
            
            # 简单的命令识别
            if "打开" in user_input:
                target = user_input.replace("打开", "").strip()
                reply = f"已打开：{target}"
                action = "open"
            elif "关闭" in user_input:
                target = user_input.replace("关闭", "").strip()
                reply = f"已关闭：{target}"
                action = "close"
            elif "设置" in user_input:
                reply = f"正在设置：{user_input}"
                action = "set"
            elif "执行" in user_input or "运行" in user_input:
                target = user_input.replace("执行", "").replace("运行", "").strip()
                reply = f"正在执行：{target}"
                action = "execute"
            else:
                reply = f"收到功能调用请求：{user_input}"
                action = "unknown"
            
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
                "workflow": "funcall",
                "action": action,
                "device_id": device_id,
                "query": user_input
            }
        
        except Exception as e:
            logger.error(f"FunCall 工作流执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "reply": f"抱歉，执行功能调用时出现了错误。",
                "workflow": "funcall"
            }

