# from pydantic import BaseSettings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "AI Agent Server"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # 日志配置
    # LOG_LEVEL: str = "INFO"
    # LOG_FILE: str = "app.log"
    
    # AI模型配置
    MODEL_PROVIDER: str = "openai"  # 或 local, huggingface等
    MODEL_NAME: str = "gpt-3.5-turbo"
    API_KEY: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    
    # 邮件配置
    email_sender: str = ""
    email_receiver: str = ""
    email_passwd: str = ""
    
    # 性能配置
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 允许忽略未定义的字段，避免验证错误
        extra = "ignore"

settings = Settings()