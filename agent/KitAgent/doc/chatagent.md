GitHub Copilot

下面是基于 chat_agent.py 中 process_message 与相关方法的详细 WebSocket 交互文档（中文）。

概览
- 连接建立：服务端在 accept 后发送一条 welcome 响应，提示进行 API Key 认证。
- 支持的客户端消息类型（文本 JSON 或 二进制音频帧）：
  - auth — 进行 API Key 验证
  - register — 注册设备（Device ID）
  - chat — 文本会话消息（可携带 message_type）
  - 二进制帧 — 作为音频消息处理（on_audio）
- 服务端统一使用 ServerResponse 格式回复：{ type, status, message, data }（以 JSON 文本发送）。

状态机（ChatState）与允许操作
- INIT
  - 允许：auth
  - 不允许：register, chat, audio（这些请求会返回 error）
- AUTHENTICATED
  - 允许：register
  - 不允许：chat, audio（直到注册完成）
- READY
  - 允许：chat（首次发送会转为 CHATTING），audio
- CHATTING
  - 允许：chat, audio

连接建立流程
1. 客户端建立 WebSocket 连接。
2. 服务端 accept 并立即发送 welcome 响应：
   - type: "welcome"
   - status: "success"
   - message: "连接成功，请先进行 API Key 认证"
   - data.state: 当前状态（初始为 INIT）

文本消息格式（必须是 JSON 字符串）
- 顶层字段：
  - type: "auth" | "register" | "chat"
  - data: object
- 示例 — API Key 验证请求：
  ```json
  {
    "type": "auth",
    "data": { "api_key": "YOUR_API_KEY" }
  }
  ```
- 示例 — 设备注册请求：
  ```json
  {
    "type": "register",
    "data": { "device_id": "device-1234" }
  }
  ```
- 示例 — 文本聊天请求：
  ```json
  {
    "type": "chat",
    "data": {
      "content": "你好",
      "message_type": "text"    // 可选，默认 "text"
    }
  }
  ```

音频消息
- 客户端发送二进制帧（不是 JSON 文本）到 WebSocket。
- 服务端把整帧当作 audio_data bytes 处理并调用 on_audio。
- on_audio 将调用 audio_service.save_audio(audio_data)，期望返回 dict，示例：
  - 成功：{ "success": True, "filename": "audio_2025-11-09.wav" }
  - 失败：{ "success": False, "error": "..." }
- 成功后保存为用户消息并用 agent_service.process(...) 生成回复，返回 chat 类型的 success 响应，data 包含 audio_file 与 assistant 生成的 response（或占位文本）。

ServerResponse（常见 type 与字段）
- 公共字段：type, status ("success" | "error"), message, data (object 或 null)
- welcome（连接建立）
  - data: { state: "INIT" }
- auth
  - 成功：status="success", message="API Key 验证成功，请提供 Device ID", data: { state: "AUTHENTICATED" }
  - 失败：status="error", message="缺少 API Key" 或 "API Key 验证失败"
- register
  - 成功：status="success", message="Device ID 注册成功，可以开始聊天", data: { state: "READY", device_id, history_count }
  - 失败：status="error", message="缺少 Device ID" 或 "当前状态 ... 无法注册设备"
- chat（文本或语音产生后的回复确认）
  - 成功：status="success", message="消息已接收" 或 "语音消息已接收"
    - data 可能包含:
      - response: assistant 生成的文本回复
      - intent: Agent 判定的意图
      - workflow: Agent 选择的工作流
      - context_count: 上下文条目数
      - audio_file: 已保存的音频文件名（语音场景）
  - 失败：status="error", message 描述错误（例如 "消息内容不能为空"）
- error（通用错误）
  - 用于状态不允许、JSON 解析失败等：
    - message: 错误描述
    - data 通常包含 { state: 当前状态 }

错误与异常处理（常见场景）
- 非 JSON 文本或 JSONDecodeError：
  - 返回 type="error", status="error", message="消息格式错误，需要 JSON 格式"
- 未认证就进行 register/chat：
  - 返回 error，message 指明当前状态不能执行该操作，并返回当前 state
- auth 未携带 api_key：
  - 返回 auth error，message="缺少 API Key"
- register 未携带 device_id：
  - 返回 register error，message="缺少 Device ID"
- chat data.content 为空：
  - 返回 chat error，message="消息内容不能为空"
- audio 保存失败：
  - 返回 chat error，message=result.get("error", "保存语音文件失败")

交互示例（序列）
1. 连接建立
   - Server -> Client: welcome success
2. 客户端 -> Server: auth 消息
   - 若成功：
     - Server -> Client: auth success (state -> AUTHENTICATED)
3. 客户端 -> Server: register 消息
   - 若成功：
     - Server -> Client: register success (state -> READY)
4. 客户端 -> Server: chat 消息（文本）
   - Server 保存用户消息、调用 agent_service.process(...) 生成回复
   - Server -> Client: chat success，data 包含 assistant 回复、intent、workflow、context_count
5. 客户端 -> Server: 发送二进制音频帧
   - Server 保存音频文件、（STT TODO）调用 agent，返回 chat success，data 包含 audio_file 与 assistant 对应回复

注意事项与实现细节提示
- 文本消息必须为 JSON 字符串；音频必须以二进制 WebSocket 框发送。
- agent_service.process(...) 返回的结构至少应包含 "reply"（助手文本），可选 "intent" 和 "workflow"。
- on_audio 当前以文件名代替 STT（语音转文本）结果；若集成 STT，请在 agent 调用前将 audio 转为文本并使用该文本。
- ServerResponse 使用 response.model_dump_json() 发送（Pydantic/V1->V2 语法），客户端应按此约定解析。

快速示例响应（样例 JSON 字符串）
- welcome:
  ```json
  {"type":"welcome","status":"success","message":"连接成功，请先进行 API Key 认证","data":{"state":"INIT"}}
  ```
- auth 成功:
  ```json
  {"type":"auth","status":"success","message":"API Key 验证成功，请提供 Device ID","data":{"state":"AUTHENTICATED"}}
  ```
- chat 成功:
  ```json
  {"type":"chat","status":"success","message":"消息已接收","data":{"response":"你好，我能帮您什么？","intent":"greeting","workflow":"default","context_count":5}}
  ```

如需，将根据代码中 ChatState 的精确定义（枚举成员名称）更新文档或生成一个更多示例（包含二进制帧发送示例的客户端伪代码）。