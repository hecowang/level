import asyncio
import uuid
from typing import Dict

# 内存存储任务状态（生产环境可以换成 Redis）
TASKS: Dict[str, dict] = {}

async def run_agent_task(prompt: str):
    """模拟调用大模型的耗时任务"""
    await asyncio.sleep(2)  # 模拟网络请求
    return f"大模型输出: {prompt[::-1]}"  # 反转字符串作为假输出

async def start_task(prompt: str) -> str:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "running", "result": None}

    async def task_wrapper():
        try:
            result = await run_agent_task(prompt)
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["result"] = result
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["result"] = str(e)

    asyncio.create_task(task_wrapper())  # 异步后台执行
    return task_id

def get_task_result(task_id: str):
    return TASKS.get(task_id)
