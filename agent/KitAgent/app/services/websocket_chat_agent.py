"""WebSocket Chat Agent 会话处理类"""
import json
from typing import Optional
from fastapi import WebSocket
from app.services.audio_service import audio_service
from app.services.chat_service import chat_service
from app.services.agent_service import agent_service
from app.services.chat_state_machine import ChatStateMachine, ChatState
from app.models.chat_message import ServerResponse
from app.utils.logger import logger


class ChatService:
    """
    Chat Service 会话处理类
    管理单个 WebSocket 连接的状态机和消息处理
    """
    
    def __init__(self, websocket: WebSocket):
        """
        初始化 Chat Service
        
        Args:
            websocket: WebSocket 连接对象
        """
        self.websocket = websocket
        self.state_machine = ChatStateMachine()
    
    async def send_response(self, response_type: str, status: str, message: str, data: dict = None):
        """
        发送响应消息
        
        Args:
            response_type: 响应类型
            status: 状态 (success/error)
            message: 消息内容
            data: 附加数据
        """
        response = ServerResponse(
            type=response_type,
            status=status,
            message=message,
            data=data
        )
        await self.websocket.send_text(response.model_dump_json())
    
    async def handle_auth(self, message_data: dict):
        """
        处理 API Key 认证
        
        Args:
            message_data: 消息数据
        """
        current_state = self.state_machine.get_state()
        
        if current_state != ChatState.INIT:
            await self.send_response(
                "error",
                "error",
                f"当前状态 {current_state.value} 无法进行认证",
                {"state": current_state.value}
            )
            return
        
        api_key = message_data.get("data", {}).get("api_key")
        if not api_key:
            await self.send_response(
                "auth",
                "error",
                "缺少 API Key",
                {"state": current_state.value}
            )
            return
        
        # 验证 API Key
        if chat_service.validate_api_key(api_key):
            self.state_machine.authenticate(api_key)
            await self.send_response(
                "auth",
                "success",
                "API Key 验证成功，请提供 Device ID",
                {"state": self.state_machine.get_state().value}
            )
        else:
            await self.send_response(
                "auth",
                "error",
                "API Key 验证失败",
                {"state": current_state.value}
            )
    
    async def handle_register(self, message_data: dict):
        """
        处理设备注册
        
        Args:
            message_data: 消息数据
        """
        current_state = self.state_machine.get_state()
        
        if current_state != ChatState.AUTHENTICATED:
            await self.send_response(
                "error",
                "error",
                f"当前状态 {current_state.value} 无法注册设备",
                {"state": current_state.value}
            )
            return
        
        device_id = message_data.get("data", {}).get("device_id")
        if not device_id:
            await self.send_response(
                "register",
                "error",
                "缺少 Device ID",
                {"state": current_state.value}
            )
            return
        
        # 注册设备
        chat_history = chat_service.register_device(device_id)
        self.state_machine.register_device(device_id)
        self.state_machine.start_chatting()
        
        logger.info(f"设备 {device_id} 注册成功，准备开始聊天")
        
        await self.send_response(
            "register",
            "success",
            f"Device ID 注册成功，可以开始聊天",
            {
                "state": self.state_machine.get_state().value,
                "device_id": device_id,
                "history_count": len(chat_history.get_history())
            }
        )
    
    async def on_message(self, content: str, message_type: str = "text"):
        """
        处理文本消息
        
        Args:
            content: 消息内容
            message_type: 消息类型 (text/audio)
        """
        current_state = self.state_machine.get_state()
        
        # 只有在 READY 或 CHATTING 状态下才处理消息
        if current_state != ChatState.READY and current_state != ChatState.CHATTING:
            await self.send_response(
                "error",
                "error",
                f"当前状态 {current_state.value} 无法处理消息，请先完成认证和注册",
                {"state": current_state.value}
            )
            return
        
        device_id = self.state_machine.device_id
        
        if not content:
            await self.send_response(
                "chat",
                "error",
                "消息内容不能为空",
                {"state": current_state.value}
            )
            return
        
        # 保存用户消息到历史
        chat_service.save_message(device_id, "user", content, message_type)
        
        # 进入聊天状态
        if current_state == ChatState.READY:
            self.state_machine.start_chatting()
        
        logger.info(f"设备 {device_id} 收到消息: {message_type} - {len(content)} 字符")
        
        # 获取对话上下文
        conversation_history = chat_service.get_conversation_context(device_id)
        
        # 调用 Agent 服务处理消息（基于 LangChain 的意图分类和工作流）
        agent_result = await agent_service.process(
            user_input=content,
            device_id=device_id,
            conversation_history=conversation_history
        )
        
        # 获取 Agent 回复
        assistant_response = agent_result.get("reply", "抱歉，未能生成回复。")
        intent = agent_result.get("intent", "unknown")
        workflow = agent_result.get("workflow", "unknown")
        
        # 保存助手回复到历史
        chat_service.save_message(device_id, "assistant", assistant_response, "text")
        
        await self.send_response(
            "chat",
            "success",
            "消息已接收",
            {
                "response": assistant_response,
                "intent": intent,
                "workflow": workflow,
                "context_count": len(conversation_history)
            }
        )
    
    async def on_audio(self, audio_data: bytes):
        """
        处理音频消息
        
        Args:
            audio_data: 音频二进制数据
        """
        current_state = self.state_machine.get_state()
        
        # 只有在 READY 或 CHATTING 状态下才处理语音
        if current_state != ChatState.READY and current_state != ChatState.CHATTING:
            await self.send_response(
                "error",
                "error",
                f"当前状态 {current_state.value} 不支持语音消息，请先完成认证和注册",
                {"state": current_state.value}
            )
            return
        
        device_id = self.state_machine.device_id
        
        logger.info(f"设备 {device_id} 收到语音数据: {len(audio_data)} 字节")
        
        # 保存音频文件
        result = await audio_service.save_audio(audio_data)
        
        if result.get("success"):
            # 保存用户语音消息（保存文件路径作为内容）
            chat_service.save_message(device_id, "user", result["filename"], "audio")
            
            # 进入聊天状态
            if current_state == ChatState.READY:
                self.state_machine.start_chatting()
            
            # TODO: 语音转文本（STT - Speech to Text）
            # 这里暂时将音频文件名作为输入，实际应该先进行语音转文本
            audio_query = f"收到语音消息，文件: {result['filename']}"
            
            # 获取对话上下文
            conversation_history = chat_service.get_conversation_context(device_id)
            
            # 调用 Agent 服务处理（实际应该先用 STT 转换，这里用模拟输入）
            # TODO: 集成语音转文本服务
            agent_result = await agent_service.process(
                user_input=audio_query,
                device_id=device_id,
                conversation_history=conversation_history
            )
            
            assistant_response = agent_result.get("reply", "收到您的语音消息，语音转文本功能开发中")
            intent = agent_result.get("intent", "unknown")
            workflow = agent_result.get("workflow", "unknown")
            
            chat_service.save_message(device_id, "assistant", assistant_response, "text")
            
            await self.send_response(
                "chat",
                "success",
                "语音消息已接收",
                {
                    "response": assistant_response,
                    "audio_file": result["filename"]
                }
            )
        else:
            await self.send_response(
                "chat",
                "error",
                result.get("error", "保存语音文件失败"),
                {"state": current_state.value}
            )
    
    async def process_message(self, message_data: dict):
        """
        处理接收到的消息（根据消息类型分发）
        
        Args:
            message_data: JSON 解析后的消息数据
        """
        message_type = message_data.get("type")
        current_state = self.state_machine.get_state()
        
        # 根据消息类型分发处理
        if message_type == "auth":
            await self.handle_auth(message_data)
        elif message_type == "register":
            await self.handle_register(message_data)
        elif message_type == "chat":
            chat_data = message_data.get("data", {})
            content = chat_data.get("content", "")
            message_type_str = chat_data.get("message_type", "text")
            await self.on_message(content, message_type_str)
        else:
            await self.send_response(
                "error",
                "error",
                f"不支持的消息类型: {message_type}",
                {"state": current_state.value}
            )
    
    async def start(self):
        """
        启动 Chat Service 会话处理循环
        """
        await self.websocket.accept()
        logger.info("WebSocket 连接已建立，等待认证")
        
        # 发送欢迎消息
        await self.send_response(
            "welcome",
            "success",
            "连接成功，请先进行 API Key 认证",
            {"state": self.state_machine.get_state().value}
        )
        
        try:
            while True:
                # 接收数据
                data = await self.websocket.receive()
                
                # 处理文本消息（JSON 格式）
                if "text" in data:
                    try:
                        message_data = json.loads(data["text"])
                        await self.process_message(message_data)
                    except json.JSONDecodeError:
                        await self.send_response(
                            "error",
                            "error",
                            "消息格式错误，需要 JSON 格式",
                            {"state": self.state_machine.get_state().value}
                        )
                    except Exception as e:
                        logger.error(f"处理消息时出错: {e}", exc_info=True)
                        await self.send_response(
                            "error",
                            "error",
                            f"处理消息时出错: {str(e)}",
                            {"state": self.state_machine.get_state().value}
                        )
                
                # 处理二进制数据（语音）
                elif "bytes" in data:
                    audio_data = data["bytes"]
                    try:
                        await self.on_audio(audio_data)
                    except Exception as e:
                        logger.error(f"处理音频时出错: {e}", exc_info=True)
                        await self.send_response(
                            "error",
                            "error",
                            f"处理音频时出错: {str(e)}",
                            {"state": self.state_machine.get_state().value}
                        )
                else:
                    logger.warning(f"收到未知类型数据: {data}")
        
        except Exception as e:
            device_id = self.state_machine.device_id
            if device_id:
                logger.info(f"WebSocket 客户端断开连接，设备 ID: {device_id}")
            else:
                logger.info(f"WebSocket 客户端断开连接（未完成认证）")
            
            # 重新抛出异常以便上层处理
            raise

