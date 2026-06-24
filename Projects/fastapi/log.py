import logging
import logging.config
import os
from pathlib import Path

# 确保日志目录存在
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 定义配置字典
LOGGING_CONFIG = {
    # 1. 版本号（必填）
    "version": 1,
    # 2. 禁用已有 Logger（强烈建议 False）
    "disable_existing_loggers": False,
    # 3. 定义格式化器（指定输出长什么样）
    "formatters": {
        "standard": {  # 格式化器名称（在 Handler 中引用）
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s | %(message)s"},
    },
    # 4. 定义处理器（指定日志去哪里）
    "handlers": {
        # 控制台 Handler
        "console": {
            "class": "logging.StreamHandler",  # 类路径（必填）
            "level": "DEBUG",  # 该 Handler 的级别
            "formatter": "standard",  # 引用上面定义的 formatter
            "stream": "ext://sys.stdout",  # 输出到标准输出
        },
        # 文件 Handler（按天轮转）
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            # 以下是 TimedRotatingFileHandler 的构造参数
            "filename": "logs/app.log",
            "when": "midnight",  # 每天午夜轮转
            "backupCount": 30,  # 保留 30 个备份
            "encoding": "utf-8",
            "interval": 1,  # 间隔为 1 天
        },
    },
    # 5. 定义根 Logger（兜底配置）
    "root": {"level": "INFO", "handlers": ["console", "file"]},  # 引用上面的 handlers
    # 6. 定义特定模块的 Logger（可选，会继承 root 的部分设置）
    "loggers": {
        # 比如让某个模块输出 DEBUG，而其他模块只输出 INFO
        "myapp.database": {
            "level": "DEBUG",
            "handlers": ["console"],  # 只输出到控制台，不写文件
            "propagate": False,  # 重点：不向上传递给 root，防止重复打印
        },
        "uvicorn": {  # 调整 Uvicorn 自身日志
            "level": "INFO",
            "handlers": ["console"],  # 让它只输出到控制台，不污染日志文件
            "propagate": False,
        },
    },
}


def setup_logging():
    """应用启动时调用，完成日志配置"""
    logging.config.dictConfig(LOGGING_CONFIG)
    # 可选：设置第三方库的日志级别
    # logging.getLogger("urllib3").setLevel(logging.WARNING)


# 注意：如果你希望模块被导入时就自动配置，可以直接调用 setup_logging()
# 但更推荐在 main.py 中显式调用，确保顺序可控。
