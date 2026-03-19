"""
日志配置模块
"""
import logging
import sys
from .settings import settings

# 统一日志格式：时间戳(含毫秒) - logger名称 - 级别 - 消息
formatter = logging.Formatter(
    '%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 配置根 logger，使 uvicorn、httpx 等第三方库日志格式一致
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(settings.LOG_LEVEL.upper())
if not root_logger.handlers:
    root_logger.addHandler(console_handler)
else:
    for h in root_logger.handlers:
        h.setFormatter(formatter)

# 项目默认 logger（各模块也可直接用 logging.getLogger(__name__)）
logger = logging.getLogger("tts_platform")

# 导出 logger
__all__ = ["logger"]
