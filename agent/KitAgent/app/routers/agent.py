from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.services.agent_service import start_task, get_task_result
from app.services.websocket_chat_agent import ChatService as WebSocketChatService
from app.utils.logger import logger

router = APIRouter()

class AgentRequest(BaseModel):
    prompt: str


@router.websocket("/agent/chat")
async def do_chat(websocket: WebSocket):
    """
    Chat Agent WebSocket 入口
    
    状态机流程:
    1. INIT -> 等待 API Key 校验
    2. AUTHENTICATED -> 等待 Device ID 注册
    3. READY -> 准备就绪，可以开始聊天
    4. CHATTING -> 正在聊天中
    
    消息协议:
    - 客户端发送 JSON 格式消息: {"type": "auth", "data": {"api_key": "..."}}
    - 客户端发送: {"type": "register", "data": {"device_id": "..."}}
    - 客户端发送: {"type": "chat", "data": {"content": "...", "message_type": "text/audio"}}
    """
    # 创建 ChatService 实例并启动会话处理
    chat_service = WebSocketChatService(websocket)
    
    try:
        await chat_service.start()
    except WebSocketDisconnect:
        # WebSocket 正常断开，已在 ChatAgent 中记录日志
        pass
    except Exception as e:
        logger.error(f"WebSocket 会话错误: {e}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass


@router.get("/agent/chat/test")
async def chat_test_page():
    """返回 Chat Agent 测试页面"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>语音交互 WebSocket 测试</title>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            button {
                padding: 10px 20px;
                margin: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            #messages {
                margin-top: 20px;
                padding: 10px;
                border: 1px solid #ddd;
                min-height: 200px;
                background-color: #f9f9f9;
            }
            .message {
                margin: 5px 0;
                padding: 5px;
            }
            .info { color: blue; }
            .success { color: green; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <h1>Chat Agent 测试页面</h1>
        <div>
            <div>
                <label>API Key: <input type="text" id="apiKey" placeholder="输入 API Key" style="width: 300px;"></label>
                <button id="authBtn">认证</button>
            </div>
            <div style="margin-top: 10px;">
                <label>Device ID: <input type="text" id="deviceId" placeholder="输入 Device ID" style="width: 300px;"></label>
                <button id="registerBtn">注册设备</button>
            </div>
            <div style="margin-top: 10px;">
                <button id="connectBtn">连接 WebSocket</button>
                <button id="disconnectBtn">断开连接</button>
                <button id="sendTextBtn">发送文本消息</button>
                <button id="sendAudioBtn">发送音频文件</button>
            </div>
            <div style="margin-top: 10px;">
                <input type="text" id="chatInput" placeholder="输入聊天消息" style="width: 400px;">
                <input type="file" id="audioFile" accept="audio/*">
            </div>
            <div style="margin-top: 10px;">
                <span id="stateDisplay">状态: 未连接</span>
            </div>
        </div>
        <div id="messages"></div>
        <script>
            let ws = null;
            let currentState = 'init';
            const messagesDiv = document.getElementById('messages');
            const stateDisplay = document.getElementById('stateDisplay');
            
            function addMessage(msg, type = 'info') {
                const p = document.createElement('p');
                p.className = 'message ' + type;
                p.textContent = new Date().toLocaleTimeString() + ' - ' + msg;
                messagesDiv.appendChild(p);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            function updateState(state) {
                currentState = state;
                stateDisplay.textContent = '状态: ' + state;
            }
            
            function sendJSONMessage(type, data) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type: type, data: data}));
                    return true;
                }
                addMessage('WebSocket 未连接', 'error');
                return false;
            }
            
            document.getElementById('connectBtn').onclick = function() {
                const wsUrl = 'ws://localhost:8000/api/v1/agent/chat';
                ws = new WebSocket(wsUrl);
                ws.onopen = () => {
                    addMessage('已连接到 Chat Agent 服务', 'success');
                    updateState('init');
                };
                ws.onmessage = (event) => {
                    try {
                        const response = JSON.parse(event.data);
                        addMessage(`[${response.type}] ${response.message}`, response.status);
                        if (response.data && response.data.state) {
                            updateState(response.data.state);
                        }
                        if (response.type === 'chat' && response.data && response.data.response) {
                            addMessage('AI 回复: ' + response.data.response, 'success');
                        }
                    } catch (e) {
                        addMessage('收到消息: ' + event.data, 'info');
                    }
                };
                ws.onerror = (error) => addMessage('连接错误', 'error');
                ws.onclose = () => {
                    addMessage('连接已断开', 'info');
                    updateState('未连接');
                };
            };
            
            document.getElementById('authBtn').onclick = function() {
                const apiKey = document.getElementById('apiKey').value;
                if (!apiKey) {
                    addMessage('请输入 API Key', 'error');
                    return;
                }
                if (sendJSONMessage('auth', {api_key: apiKey})) {
                    addMessage('发送 API Key 认证请求', 'info');
                }
            };
            
            document.getElementById('registerBtn').onclick = function() {
                const deviceId = document.getElementById('deviceId').value;
                if (!deviceId) {
                    addMessage('请输入 Device ID', 'error');
                    return;
                }
                if (sendJSONMessage('register', {device_id: deviceId})) {
                    addMessage('发送设备注册请求', 'info');
                }
            };
            
            document.getElementById('disconnectBtn').onclick = function() {
                if (ws) {
                    ws.close();
                    ws = null;
                    updateState('未连接');
                }
            };
            
            document.getElementById('sendTextBtn').onclick = function() {
                const input = document.getElementById('chatInput');
                const content = input.value.trim();
                if (!content) {
                    addMessage('请输入消息内容', 'error');
                    return;
                }
                if (sendJSONMessage('chat', {content: content, message_type: 'text'})) {
                    addMessage('发送消息: ' + content, 'info');
                    input.value = '';
                }
            };
            
            document.getElementById('sendAudioBtn').onclick = function() {
                const fileInput = document.getElementById('audioFile');
                if (fileInput.files.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    const file = fileInput.files[0];
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        ws.send(e.target.result);
                        addMessage('已发送音频文件: ' + file.name + ' (' + file.size + ' 字节)', 'info');
                    };
                    reader.onerror = () => addMessage('读取文件失败', 'error');
                    reader.readAsArrayBuffer(file);
                } else {
                    addMessage('请先选择音频文件并连接 WebSocket', 'error');
                }
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

