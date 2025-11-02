# WebSocket 音频服务器

基于 FastAPI 的 WebSocket 服务器，接收语音数据并保存为文件，文本数据暂时忽略。

## 环境要求

- Python >= 3.8
- [uv](https://github.com/astral-sh/uv) (Python 包管理器)

## 安装 uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 快速开始

1. **安装依赖并创建虚拟环境**
   ```bash
   uv sync
   ```

2. **运行服务器**
   ```bash
   uv run python main.py
   ```
   或
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **访问测试页面**
   - 打开浏览器访问 `http://localhost:8000`
   - 使用页面上的按钮进行 WebSocket 连接测试

## 项目结构

```
.
├── main.py                  # FastAPI 应用主文件
├── test_websocket_audio.py  # WebSocket 音频测试文件
├── pyproject.toml            # 项目配置和依赖
├── pytest.ini               # pytest 配置文件
├── requirements.txt          # 传统 pip 依赖（备用）
├── .gitignore
├── uploads/                  # 语音文件保存目录（自动创建）
└── logs/                     # 日志文件目录（自动创建）
```

## 功能说明

- **WebSocket 端点** (`/ws`): 接收客户端连接
- **语音处理**: 接收二进制数据并保存为 `.wav` 文件到 `uploads/` 目录
- **文本处理**: 接收文本数据，暂时忽略（仅打印日志）

## 运行测试

1. **安装测试依赖和 TTS 库**
   ```bash
   uv sync --extra test --extra tts
   ```
   或分别安装：
   ```bash
   # 安装测试依赖
   uv sync --extra test
   
   # 安装 TTS 库（pyttsx3 或 gTTS）
   uv sync --extra tts
   ```

2. **启动服务器**（在另一个终端）
   ```bash
   uv run python main.py
   ```

3. **运行测试**
   ```bash
   # 使用 pytest 运行
   uv run pytest test_websocket_audio.py -v
   
   # 或直接运行测试文件
   uv run python test_websocket_audio.py
   ```

### TTS 库说明

测试支持两种文本转语音库：

- **pyttsx3**: 本地 TTS 引擎，无需网络，但需要系统安装语音引擎（Windows 自带）
- **gTTS**: Google Text-to-Speech，需要网络连接，支持多语言

至少安装其中一个即可运行测试。

## uv 常用命令

```bash
# 安装依赖
uv sync

# 添加新依赖
uv add package-name

# 运行 Python 脚本
uv run python main.py

# 运行命令（在虚拟环境中）
uv run uvicorn main:app --reload

# 更新依赖
uv sync --upgrade
```

## Docker
command:
    fastapi dev app/main.py

requirements gen:
   pipreqs app --encoding=utf8 --force --savepath ./requirements.txt


docker:
   docker build -t my-fastapi-app . --platform linux/amd64
   docker run -d --name my-fastapi -p 8000:8000 my-fastapi-app -v /var/logs/rtc-ai-agent-jx:/service/logs
