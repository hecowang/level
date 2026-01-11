import logging
import logging.config
import os
from typing import Dict, Any

LOG_DIR = os.getenv("LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging() -> None:
    """配置日志系统"""
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s][%(name)s][%(levelname)s][%(trace_id)s]\t%(message)s",
            },
            "access": {
                "format": "[%(asctime)s][%(levelname)s][%(trace_id)s]\t%(message)s",
            },
        },
        "filters": {
            "trace_id_filter": {
                "()": "app.utils.traceid_filter.TraceIDFilter",  # 替换为实际的模块路径
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
                "filters": ["trace_id_filter"],
            },
            "file": {
                "class":"logging.handlers.TimedRotatingFileHandler",
                "formatter": "default",
                "filename": os.path.join(LOG_DIR, "app.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": 7,
                "encoding": "utf-8",
                "filters": ["trace_id_filter"],
            },
            "access": {
                "class":"logging.handlers.TimedRotatingFileHandler",
                "formatter": "access",
                "filename": os.path.join(LOG_DIR, "access.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": 7,
                "encoding": "utf-8",
                "filters": ["trace_id_filter"],
            },
        },
        "loggers": {
            "app": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["access"],
                "propagate": True,
            },
            "access": {
                "level": "DEBUG",
                "handlers": ["file"],
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }
    logging.config.dictConfig(config)

# 在应用启动时调用
setup_logging()
logger = logging.getLogger("app")