from fastapi import APIRouter
from pydantic import BaseModel
from app.services.agent_service import start_task, get_task_result

router = APIRouter()

class AgentRequest(BaseModel):
    prompt: str

@router.post("/agent/run")
async def run_agent(request: AgentRequest):
    task_id = await start_task(request.prompt)
    return {"task_id": task_id, "status": "running"}

@router.get("/agent/result/{task_id}")
async def get_agent_result(task_id: str):
    result = get_task_result(task_id)
    if not result:
        return {"error": "Task not found"}
    return result
