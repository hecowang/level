"""工作流模块"""
from app.services.workflows.chat_workflow import ChatWorkflow
from app.services.workflows.search_workflow import SearchWorkflow
from app.services.workflows.reasoning_workflow import ReasoningWorkflow
from app.services.workflows.music_workflow import MusicWorkflow
from app.services.workflows.funcall_workflow import FuncallWorkflow

__all__ = [
    "ChatWorkflow",
    "SearchWorkflow",
    "ReasoningWorkflow",
    "MusicWorkflow",
    "FuncallWorkflow",
]

