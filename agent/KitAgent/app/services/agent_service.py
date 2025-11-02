"""Agent 服务 - 基于 LangChain 实现"""
import asyncio
import uuid
from typing import Dict, List, Any, Optional
from app.services.intent_classifier import intent_classifier
from app.services.workflows.chat_workflow import ChatWorkflow
from app.services.workflows.search_workflow import SearchWorkflow
from app.services.workflows.reasoning_workflow import ReasoningWorkflow
from app.services.workflows.music_workflow import MusicWorkflow
from app.services.workflows.funcall_workflow import FuncallWorkflow
from app.models.intent import IntentType
from app.utils.logger import logger


# 内存存储任务状态（生产环境可以换成 Redis）
TASKS: Dict[str, dict] = {}

# 工作流映射
WORKFLOW_MAP = {
    IntentType.CHAT: ChatWorkflow(),
    IntentType.SEARCH: SearchWorkflow(),
    IntentType.REASONING: ReasoningWorkflow(),
    IntentType.MUSIC: MusicWorkflow(),
    IntentType.FUNCALL: FuncallWorkflow(),
}


class AgentService:
    """Agent 服务类"""
    
    def __init__(self):
        """初始化 Agent 服务"""
        self.workflows = WORKFLOW_MAP
    
    async def process(self, user_input: str, device_id: str = None, conversation_history: List[dict] = None) -> Dict[str, Any]:
        """
        处理用户输入的主流程
        
        工作流程：
        1. 意图分类
        2. 根据意图选择对应工作流
        3. 执行工作流
        4. 返回结果
        
        Args:
            user_input: 用户输入
            device_id: 设备 ID（可选）
            conversation_history: 对话历史（可选）
        
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"Agent 开始处理用户输入: {user_input[:50]}...")
            
            # 步骤 1: 意图分类
            intent_result = await intent_classifier.classify(user_input, conversation_history)
            logger.info(f"意图分类结果: {intent_result.intent.value} (置信度: {intent_result.confidence:.2f})")
            
            # 步骤 2: 选择工作流
            workflow = self.workflows.get(intent_result.intent)
            if not workflow:
                logger.warning(f"未找到对应意图 {intent_result.intent.value} 的工作流，使用默认聊天工作流")
                workflow = self.workflows[IntentType.CHAT]
            
            # 步骤 3: 执行工作流
            context = {
                "device_id": device_id,
                "conversation_history": conversation_history or [],
                "intent": intent_result.intent.value,
                "intent_confidence": intent_result.confidence,
                "intent_reasoning": intent_result.reasoning,
                "entities": intent_result.entities
            }
            
            result = await workflow.execute(user_input, context)
            
            # 步骤 4: 添加意图信息到结果
            result["intent"] = intent_result.intent.value
            result["intent_confidence"] = intent_result.confidence
            
            logger.info(f"Agent 处理完成，工作流: {result.get('workflow')}, 成功: {result.get('success')}")
            
            return result
        
        except Exception as e:
            logger.error(f"Agent 处理失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "reply": "抱歉，处理您的请求时出现了错误。",
                "workflow": "unknown"
            }


# 创建全局 Agent 服务实例
agent_service = AgentService()


# 保留原有的异步任务接口（向后兼容）
async def run_agent_task(prompt: str):
    """模拟调用大模型的耗时任务（已废弃，使用 AgentService）"""
    logger.warning("run_agent_task 已废弃，请使用 AgentService.process")
    result = await agent_service.process(prompt)
    return result.get("reply", "处理完成")


async def start_task(prompt: str) -> str:
    """启动异步任务（向后兼容）"""
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "running", "result": None}

    async def task_wrapper():
        try:
            result = await agent_service.process(prompt)
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["result"] = result
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["result"] = {"error": str(e)}

    asyncio.create_task(task_wrapper())  # 异步后台执行
    return task_id


def get_task_result(task_id: str):
    """获取任务结果"""
    return TASKS.get(task_id)
