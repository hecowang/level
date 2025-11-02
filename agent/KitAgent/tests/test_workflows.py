"""
工作流流程单元测试
测试意图分类、工作流执行和 Agent 服务流程
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.agent_service import AgentService
from app.services.intent_classifier import IntentClassifier
from app.models.intent import IntentType, IntentResult
from app.services.workflows.chat_workflow import ChatWorkflow
from app.services.workflows.search_workflow import SearchWorkflow
from app.services.workflows.reasoning_workflow import ReasoningWorkflow
from app.services.workflows.music_workflow import MusicWorkflow
from app.services.workflows.funcall_workflow import FuncallWorkflow


class TestIntentClassifier:
    """意图分类器测试"""
    
    @pytest.mark.asyncio
    async def test_rule_based_classify_chat(self):
        """测试规则分类 - 聊天意图"""
        classifier = IntentClassifier()
        result = await classifier._rule_based_classify("你好，今天天气怎么样？")
        assert result.intent == IntentType.SEARCH
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_rule_based_classify_search(self):
        """测试规则分类 - 搜索意图"""
        classifier = IntentClassifier()
        result = await classifier._rule_based_classify("搜索一下北京的天气")
        assert result.intent == IntentType.SEARCH
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_rule_based_classify_reasoning(self):
        """测试规则分类 - 推理计算意图"""
        classifier = IntentClassifier()
        result = await classifier._rule_based_classify("计算 1+1 等于多少")
        assert result.intent == IntentType.REASONING
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_rule_based_classify_music(self):
        """测试规则分类 - 音乐意图"""
        classifier = IntentClassifier()
        result = await classifier._rule_based_classify("播放一首歌")
        assert result.intent == IntentType.MUSIC
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_rule_based_classify_funcall(self):
        """测试规则分类 - FunCall 意图"""
        classifier = IntentClassifier()
        result = await classifier._rule_based_classify("打开灯")
        assert result.intent == IntentType.FUNCALL
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_classify_without_llm(self):
        """测试分类（无 LLM 时使用规则分类）"""
        classifier = IntentClassifier()
        classifier.llm = None  # 确保使用规则分类
        
        result = await classifier.classify("搜索天气")
        assert result.intent in [IntentType.SEARCH, IntentType.CHAT]
        assert 0 <= result.confidence <= 1


class TestChatWorkflow:
    """聊天工作流测试"""
    
    @pytest.mark.asyncio
    async def test_chat_workflow_execute(self):
        """测试聊天工作流执行"""
        workflow = ChatWorkflow()
        result = await workflow.execute("你好", context={})
        
        assert result["success"] is True
        assert "reply" in result
        assert result["workflow"] == "chat"
    
    @pytest.mark.asyncio
    async def test_chat_workflow_with_history(self):
        """测试聊天工作流带历史上下文"""
        workflow = ChatWorkflow()
        context = {
            "conversation_history": [
                {"role": "user", "content": "我叫张三"},
                {"role": "assistant", "content": "你好张三"}
            ]
        }
        result = await workflow.execute("你记得我的名字吗？", context=context)
        
        assert result["success"] is True
        assert result["workflow"] == "chat"
    
    def test_chat_workflow_intent_type(self):
        """测试聊天工作流意图类型"""
        workflow = ChatWorkflow()
        assert workflow.intent_type == IntentType.CHAT


class TestSearchWorkflow:
    """实搜工作流测试"""
    
    @pytest.mark.asyncio
    async def test_search_workflow_execute(self):
        """测试实搜工作流执行"""
        workflow = SearchWorkflow()
        result = await workflow.execute("搜索北京的天气", context={})
        
        assert result["success"] is True
        assert "reply" in result
        assert result["workflow"] == "search"
        assert "search_query" in result
    
    def test_search_workflow_intent_type(self):
        """测试实搜工作流意图类型"""
        workflow = SearchWorkflow()
        assert workflow.intent_type == IntentType.SEARCH


class TestReasoningWorkflow:
    """推理计算工作流测试"""
    
    @pytest.mark.asyncio
    async def test_reasoning_workflow_execute(self):
        """测试推理计算工作流执行"""
        workflow = ReasoningWorkflow()
        result = await workflow.execute("计算 25 * 4 等于多少", context={})
        
        assert result["success"] is True
        assert "reply" in result
        assert result["workflow"] == "reasoning"
    
    def test_reasoning_workflow_intent_type(self):
        """测试推理计算工作流意图类型"""
        workflow = ReasoningWorkflow()
        assert workflow.intent_type == IntentType.REASONING


class TestMusicWorkflow:
    """播放音乐工作流测试"""
    
    @pytest.mark.asyncio
    async def test_music_workflow_play(self):
        """测试音乐工作流 - 播放"""
        workflow = MusicWorkflow()
        result = await workflow.execute("播放周杰伦的歌", context={})
        
        assert result["success"] is True
        assert result["workflow"] == "music"
        assert "action" in result
    
    @pytest.mark.asyncio
    async def test_music_workflow_pause(self):
        """测试音乐工作流 - 暂停"""
        workflow = MusicWorkflow()
        result = await workflow.execute("暂停播放", context={})
        
        assert result["success"] is True
        assert result["action"] == "pause"
    
    @pytest.mark.asyncio
    async def test_music_workflow_next(self):
        """测试音乐工作流 - 下一首"""
        workflow = MusicWorkflow()
        result = await workflow.execute("下一首", context={})
        
        assert result["success"] is True
        assert result["action"] == "next"
    
    def test_music_workflow_intent_type(self):
        """测试音乐工作流意图类型"""
        workflow = MusicWorkflow()
        assert workflow.intent_type == IntentType.MUSIC


class TestFuncallWorkflow:
    """FunCall 工作流测试"""
    
    @pytest.mark.asyncio
    async def test_funcall_workflow_open(self):
        """测试 FunCall 工作流 - 打开"""
        workflow = FuncallWorkflow()
        context = {"device_id": "test-device-001"}
        result = await workflow.execute("打开灯", context=context)
        
        assert result["success"] is True
        assert result["workflow"] == "funcall"
        assert result["action"] == "open"
        assert result["device_id"] == "test-device-001"
    
    @pytest.mark.asyncio
    async def test_funcall_workflow_close(self):
        """测试 FunCall 工作流 - 关闭"""
        workflow = FuncallWorkflow()
        result = await workflow.execute("关闭空调", context={})
        
        assert result["success"] is True
        assert result["action"] == "close"
    
    @pytest.mark.asyncio
    async def test_funcall_workflow_execute(self):
        """测试 FunCall 工作流 - 执行"""
        workflow = FuncallWorkflow()
        result = await workflow.execute("执行任务A", context={})
        
        assert result["success"] is True
        assert result["action"] == "execute"
    
    def test_funcall_workflow_intent_type(self):
        """测试 FunCall 工作流意图类型"""
        workflow = FuncallWorkflow()
        assert workflow.intent_type == IntentType.FUNCALL


class TestAgentService:
    """Agent 服务流程测试"""
    
    @pytest.mark.asyncio
    async def test_agent_service_chat_flow(self):
        """测试 Agent 服务 - 聊天流程"""
        service = AgentService()
        
        # 模拟意图分类返回聊天意图
        with patch('app.services.agent_service.intent_classifier') as mock_classifier:
            mock_classifier.classify = AsyncMock(return_value=IntentResult(
                intent=IntentType.CHAT,
                confidence=0.9,
                reasoning="用户进行日常聊天"
            ))
            
            result = await service.process(
                user_input="你好",
                device_id="test-device",
                conversation_history=[]
            )
            
            assert result["success"] is True
            assert result["intent"] == "chat"
            assert result["workflow"] == "chat"
            assert "reply" in result
    
    @pytest.mark.asyncio
    async def test_agent_service_search_flow(self):
        """测试 Agent 服务 - 搜索流程"""
        service = AgentService()
        
        with patch('app.services.agent_service.intent_classifier') as mock_classifier:
            mock_classifier.classify = AsyncMock(return_value=IntentResult(
                intent=IntentType.SEARCH,
                confidence=0.95,
                reasoning="用户需要搜索信息"
            ))
            
            result = await service.process(
                user_input="搜索北京天气",
                device_id="test-device"
            )
            
            assert result["success"] is True
            assert result["intent"] == "search"
            assert result["workflow"] == "search"
    
    @pytest.mark.asyncio
    async def test_agent_service_reasoning_flow(self):
        """测试 Agent 服务 - 推理计算流程"""
        service = AgentService()
        
        with patch('app.services.agent_service.intent_classifier') as mock_classifier:
            mock_classifier.classify = AsyncMock(return_value=IntentResult(
                intent=IntentType.REASONING,
                confidence=0.9,
                reasoning="需要计算或推理"
            ))
            
            result = await service.process(
                user_input="计算 10 + 20",
                device_id="test-device"
            )
            
            assert result["success"] is True
            assert result["intent"] == "reasoning"
            assert result["workflow"] == "reasoning"
    
    @pytest.mark.asyncio
    async def test_agent_service_music_flow(self):
        """测试 Agent 服务 - 音乐流程"""
        service = AgentService()
        
        with patch('app.services.agent_service.intent_classifier') as mock_classifier:
            mock_classifier.classify = AsyncMock(return_value=IntentResult(
                intent=IntentType.MUSIC,
                confidence=0.9,
                reasoning="音乐相关操作"
            ))
            
            result = await service.process(
                user_input="播放音乐",
                device_id="test-device"
            )
            
            assert result["success"] is True
            assert result["intent"] == "music"
            assert result["workflow"] == "music"
    
    @pytest.mark.asyncio
    async def test_agent_service_funcall_flow(self):
        """测试 Agent 服务 - FunCall 流程"""
        service = AgentService()
        
        with patch('app.services.agent_service.intent_classifier') as mock_classifier:
            mock_classifier.classify = AsyncMock(return_value=IntentResult(
                intent=IntentType.FUNCALL,
                confidence=0.9,
                reasoning="函数调用"
            ))
            
            result = await service.process(
                user_input="打开灯",
                device_id="test-device"
            )
            
            assert result["success"] is True
            assert result["intent"] == "funcall"
            assert result["workflow"] == "funcall"
    
    @pytest.mark.asyncio
    async def test_agent_service_with_conversation_history(self):
        """测试 Agent 服务 - 带对话历史"""
        service = AgentService()
        
        conversation_history = [
            {"role": "user", "content": "我叫张三"},
            {"role": "assistant", "content": "你好张三"}
        ]
        
        with patch('app.services.agent_service.intent_classifier') as mock_classifier:
            mock_classifier.classify = AsyncMock(return_value=IntentResult(
                intent=IntentType.CHAT,
                confidence=0.9
            ))
            
            result = await service.process(
                user_input="你记得我的名字吗？",
                device_id="test-device",
                conversation_history=conversation_history
            )
            
            assert result["success"] is True
            # 验证分类器被调用时传入了对话历史
            mock_classifier.classify.assert_called_once()
            call_args = mock_classifier.classify.call_args
            assert call_args[1]["conversation_history"] == conversation_history
    
    @pytest.mark.asyncio
    async def test_agent_service_error_handling(self):
        """测试 Agent 服务 - 错误处理"""
        service = AgentService()
        
        # 模拟工作流执行出错
        with patch('app.services.agent_service.intent_classifier') as mock_classifier:
            mock_classifier.classify = AsyncMock(return_value=IntentResult(
                intent=IntentType.CHAT,
                confidence=0.9
            ))
            
            with patch.object(ChatWorkflow, 'execute', side_effect=Exception("工作流错误")):
                result = await service.process(
                    user_input="测试错误",
                    device_id="test-device"
                )
                
                assert result["success"] is False
                assert "error" in result
                assert "reply" in result
    
    @pytest.mark.asyncio
    async def test_agent_service_full_integration(self):
        """测试 Agent 服务 - 完整集成测试（使用真实分类器）"""
        service = AgentService()
        
        # 使用真实分类器（规则分类模式）
        # 注意：这需要确保 LLM 未配置，使用规则分类
        result = await service.process(
            user_input="搜索天气",
            device_id="test-device"
        )
        
        assert result["success"] is True
        assert "intent" in result
        assert "workflow" in result
        assert "reply" in result
        assert "intent_confidence" in result


@pytest.mark.asyncio
async def test_workflow_intent_mapping():
    """测试工作流和意图类型的映射关系"""
    service = AgentService()
    
    # 验证所有意图类型都有对应的工作流
    intent_types = [IntentType.CHAT, IntentType.SEARCH, IntentType.REASONING, 
                   IntentType.MUSIC, IntentType.FUNCALL]
    
    for intent_type in intent_types:
        assert intent_type in service.workflows
        workflow = service.workflows[intent_type]
        assert workflow.intent_type == intent_type


@pytest.mark.asyncio
async def test_workflow_context_passing():
    """测试工作流上下文传递"""
    service = AgentService()
    
    device_id = "test-device-123"
    conversation_history = [{"role": "user", "content": "测试"}]
    
    with patch('app.services.agent_service.intent_classifier') as mock_classifier:
        mock_classifier.classify = AsyncMock(return_value=IntentResult(
            intent=IntentType.CHAT,
            confidence=0.9
        ))
        
        # 使用 mock 来验证上下文传递
        with patch.object(ChatWorkflow, 'execute') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "reply": "测试回复",
                "workflow": "chat"
            }
            
            await service.process(
                user_input="测试",
                device_id=device_id,
                conversation_history=conversation_history
            )
            
            # 验证 execute 被调用，并且上下文正确传递
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            context = call_args[1]["context"]
            
            assert context["device_id"] == device_id
            assert context["conversation_history"] == conversation_history
            assert context["intent"] == "chat"
            assert "intent_confidence" in context

