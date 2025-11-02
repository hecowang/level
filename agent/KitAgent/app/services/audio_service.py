"""音频服务层，处理语音数据的保存和管理"""
import os
from datetime import datetime
from pathlib import Path
from fastapi import WebSocket
from app.utils.logger import logger
from app.config import settings


class AudioService:
    """音频服务类"""
    
    def __init__(self, upload_dir: str = None):
        """
        初始化音频服务
        
        Args:
            upload_dir: 上传目录，如果为 None 则使用默认配置
        """
        self.upload_dir = upload_dir or getattr(settings, 'UPLOAD_DIR', 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)
        logger.info(f"音频服务初始化，上传目录: {self.upload_dir}")
    
    async def save_audio(self, audio_data: bytes, websocket: WebSocket = None) -> dict:
        """
        保存音频数据到文件
        
        Args:
            audio_data: 音频二进制数据
            websocket: WebSocket 连接对象（可选，用于发送响应）
        
        Returns:
            包含保存结果的字典
        """
        try:
            # 生成文件名（使用时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"audio_{timestamp}.wav"
            filepath = os.path.join(self.upload_dir, filename)
            
            # 保存文件
            with open(filepath, "wb") as f:
                f.write(audio_data)
            
            file_size = len(audio_data)
            logger.info(f"语音文件已保存: {filepath} (大小: {file_size} 字节)")
            
            result = {
                "success": True,
                "filename": filename,
                "filepath": filepath,
                "file_size": file_size,
                "message": f"语音文件已接收并保存: {filename}"
            }
            
            # 如果提供了 WebSocket，发送确认消息
            if websocket:
                await websocket.send_text(result["message"])
            
            return result
            
        except Exception as e:
            error_msg = f"保存语音文件时出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            result = {
                "success": False,
                "error": error_msg
            }
            
            if websocket:
                await websocket.send_text(error_msg)
            
            return result
    
    def list_audio_files(self) -> list:
        """
        列出所有保存的音频文件
        
        Returns:
            音频文件列表
        """
        try:
            files = []
            for filepath in Path(self.upload_dir).glob("audio_*.wav"):
                stat = filepath.stat()
                files.append({
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
            return sorted(files, key=lambda x: x["created_at"], reverse=True)
        except Exception as e:
            logger.error(f"列出音频文件时出错: {e}", exc_info=True)
            return []


# 创建全局音频服务实例
audio_service = AudioService()

