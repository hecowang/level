"""意图分类模型"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class IntentType(str, Enum):
    """意图类型枚举"""
    CHAT = "chat"  # 聊天
    SEARCH = "search"  # 实搜
    REASONING = "reasoning"  # 推理计算
    MUSIC = "music"  # 播放音乐
    FUNCALL = "funcall"  # FunCall


class IntentResult(BaseModel):
    """意图分类结果"""
    intent: IntentType
    confidence: float  # 置信度 0-1
    reasoning: Optional[str] = None  # 分类理由
    entities: Optional[dict] = None  # 提取的实体信息


# 意图描述（用于提示词）
INTENT_DESCRIPTIONS = {
    IntentType.CHAT: "日常聊天对话，包括问答、闲聊、咨询等",
    IntentType.SEARCH: "实时信息搜索，需要查询当前信息、新闻、天气、股票等",
    IntentType.REASONING: "推理计算，包括数学计算、逻辑推理、问题分析等",
    IntentType.MUSIC: "播放音乐，包括搜索歌曲、播放、暂停、切歌等音乐相关操作",
    IntentType.FUNCALL: "函数调用，执行特定的功能调用，如控制设备、设置提醒等"
}

