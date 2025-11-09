"""播放音乐工作流"""
from typing import Dict, Any
from app.models.intent import IntentType
from app.services.workflows.base_workflow import BaseWorkflow
from app.utils.logger import logger
from app.models.chat_context import ChatContext
from app.services.tts.volcengine.binary import do_tts


class MusicWorkflow(BaseWorkflow):
    """播放音乐工作流"""
    
    @property
    def intent_type(self) -> IntentType:
        return IntentType.MUSIC
    
    async def execute(self, chat_context: ChatContext) -> Dict[str, Any]:
        """
        执行播放音乐工作流
        
        Args:
            chat_context: 聊天上下文对象，包含用户输入和上下文信息
        
        Returns:
            音乐操作结果
        """
        user_input = chat_context.query or ""
        
        try:
            # TODO: 集成音乐服务 API（如 Spotify, QQ Music, NetEase Cloud Music 等）
            logger.info(f"音乐工作流：处理请求 '{user_input}'")
            
            user_input_lower = user_input.lower()
            
            # 简单的命令识别
            if "播放" in user_input or "听" in user_input:
                # 提取歌曲名
                song_name = user_input.replace("播放", "").replace("听", "").strip()
                reply = f"正在播放：{song_name}"
                action = "play"
            elif "暂停" in user_input:
                reply = "已暂停播放"
                action = "pause"
            elif "下一首" in user_input or "切歌" in user_input:
                reply = "已切换到下一首"
                action = "next"
            elif "上一首" in user_input:
                reply = "已切换到上一首"
                action = "previous"
            else:
                reply = f"收到音乐相关请求：{user_input}"
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
                "workflow": "music",
                "action": action,
                "query": user_input
            }
        
        except Exception as e:
            logger.error(f"音乐工作流执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "reply": f"抱歉，处理音乐请求时出现了错误。",
                "workflow": "music"
            }

