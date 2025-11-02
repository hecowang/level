"""意图分类器服务"""
import json
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.models.intent import IntentType, IntentResult, INTENT_DESCRIPTIONS
from app.config import settings
from app.utils.logger import logger


class IntentClassifier:
    """意图分类器"""
    
    def __init__(self):
        """初始化意图分类器"""
        self.llm = None
        self._init_llm()
        self._init_prompt()
    
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
                logger.info("Intent Classifier LLM 初始化成功")
            else:
                logger.warning("OPENAI_API_KEY 未配置，意图分类器将使用模拟模式")
                self.llm = None
        except Exception as e:
            logger.error(f"初始化 LLM 失败: {e}", exc_info=True)
            self.llm = None
    
    def _init_prompt(self):
        """初始化提示词模板"""
        intent_list = "\n".join([
            f"- {intent.value}: {desc}"
            for intent, desc in INTENT_DESCRIPTIONS.items()
        ])
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """你是一个意图分类专家。根据用户的输入，判断用户的意图类型。

可用的意图类型：
{intent_list}

请仔细分析用户输入，返回 JSON 格式的结果：
{{
    "intent": "意图类型（必须是以下之一：chat, search, reasoning, music, funcall）",
    "confidence": 0.0-1.0的置信度分数,
    "reasoning": "分类理由的简要说明",
    "entities": {{"key": "value"}} // 可选，提取的关键实体信息
}}

只返回 JSON，不要有其他解释。"""),
            ("human", "{user_input}")
        ])
        
        self.prompt_template = self.prompt_template.partial(intent_list=intent_list)
    
    async def classify(self, user_input: str, conversation_history: List[dict] = None) -> IntentResult:
        """
        对用户输入进行意图分类
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史（可选，用于上下文理解）
        
        Returns:
            IntentResult 对象
        """
        try:
            # 如果有 LLM，使用 LLM 进行分类
            if self.llm:
                # 构建包含上下文的输入
                context = ""
                if conversation_history:
                    recent_messages = conversation_history[-3:]  # 取最近3条消息作为上下文
                    context = "\n".join([
                        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                        for msg in recent_messages
                    ])
                    full_input = f"对话上下文：\n{context}\n\n当前用户输入：{user_input}"
                else:
                    full_input = user_input
                
                # 调用 LLM
                chain = self.prompt_template | self.llm
                response = await chain.ainvoke({"user_input": full_input})

                logger.info(f"{full_input}")
                logger.info(f"{response}")
                
                # 解析响应
                content = response.content if hasattr(response, 'content') else str(response)
                
                # 尝试提取 JSON
                json_str = self._extract_json(content)
                result_data = json.loads(json_str)
                
                # 验证意图类型
                intent_str = result_data.get("intent", "").lower()
                try:
                    intent = IntentType(intent_str)
                except ValueError:
                    logger.warning(f"未知意图类型: {intent_str}，默认使用 CHAT")
                    intent = IntentType.CHAT
                
                return IntentResult(
                    intent=intent,
                    confidence=float(result_data.get("confidence", 0.5)),
                    reasoning=result_data.get("reasoning"),
                    entities=result_data.get("entities")
                )
            
            # 如果没有 LLM，使用规则分类
            else:
                return await self._rule_based_classify(user_input)
        
        except Exception as e:
            logger.error(f"意图分类失败: {e}", exc_info=True)
            # 失败时返回默认意图
            return IntentResult(
                intent=IntentType.CHAT,
                confidence=0.5,
                reasoning=f"分类失败，使用默认意图: {str(e)}"
            )
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except:
            pass
        
        # 尝试提取 JSON 代码块
        import re
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # 如果都失败，返回空 JSON
        return '{"intent": "chat", "confidence": 0.5, "reasoning": "无法解析JSON"}'
    
    async def _rule_based_classify(self, user_input: str) -> IntentResult:
        """
        基于规则的意图分类（备用方案）
        
        Args:
            user_input: 用户输入
        
        Returns:
            IntentResult 对象
        """
        user_input_lower = user_input.lower()
        
        # 搜索关键词
        search_keywords = ["搜索", "查询", "查找", "找", "搜索一下", "查一下", "天气", "新闻", "股票"]
        # 推理计算关键词
        reasoning_keywords = ["计算", "算", "求解", "推理", "分析", "为什么", "如何", "怎么"]
        # 音乐关键词
        music_keywords = ["播放", "音乐", "歌曲", "听歌", "暂停", "下一首", "切歌"]
        # 函数调用关键词
        funcall_keywords = ["打开", "关闭", "设置", "执行", "运行", "启动", "停止"]
        
        # 匹配意图
        if any(keyword in user_input_lower for keyword in search_keywords):
            return IntentResult(
                intent=IntentType.SEARCH,
                confidence=0.8,
                reasoning="包含搜索相关关键词"
            )
        elif any(keyword in user_input_lower for keyword in reasoning_keywords):
            return IntentResult(
                intent=IntentType.REASONING,
                confidence=0.8,
                reasoning="包含推理计算相关关键词"
            )
        elif any(keyword in user_input_lower for keyword in music_keywords):
            return IntentResult(
                intent=IntentType.MUSIC,
                confidence=0.8,
                reasoning="包含音乐相关关键词"
            )
        elif any(keyword in user_input_lower for keyword in funcall_keywords):
            return IntentResult(
                intent=IntentType.FUNCALL,
                confidence=0.8,
                reasoning="包含函数调用相关关键词"
            )
        else:
            return IntentResult(
                intent=IntentType.CHAT,
                confidence=0.7,
                reasoning="未匹配到特定意图，默认为聊天"
            )


# 创建全局意图分类器实例
intent_classifier = IntentClassifier()

