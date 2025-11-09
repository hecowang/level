"""配置管理 - 从环境变量和 .env 文件加载配置"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=str(env_path), override=True)


class Settings(BaseSettings):
    """应用配置 - 从环境变量读取"""
    APP_NAME: str = os.getenv("APP_NAME", "AI Agent Server")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    
    # 音频配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    
    # AI模型配置
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "openai")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    API_KEY: str = os.getenv("API_KEY", "")
    API_KEYS: str = os.getenv("API_KEYS", "111111,222222,333333")
    
    # LangChain Agent 配置
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    
    # Chat Agent 配置
    MAX_CHAT_HISTORY: int = int(os.getenv("MAX_CHAT_HISTORY", "100"))
    CHAT_CONTEXT_LIMIT: int = int(os.getenv("CHAT_CONTEXT_LIMIT", "10"))
    
    # 性能配置
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2000"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # ✅ 新版写法（替代 class Config）
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )


# 创建全局配置实例
settings = Settings()
