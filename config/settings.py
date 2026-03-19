"""
配置文件
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 59012
    DEBUG: bool = True
    
    # TTS 配置
    DEFAULT_TTS_CHANNEL: str = "default"
    AUDIO_OUTPUT_DIR: str = "./output/audio"
    
    # 支持的音频格式
    SUPPORTED_FORMATS: List[str] = ["mp3", "wav", "ogg", "aac", "pcm"]
    
    # 默认语音参数
    DEFAULT_VOICE: str = "alloy"
    DEFAULT_SPEED: float = 1.0
    DEFAULT_PITCH: float = 1.0
    
    # 认证配置
    ADMIN_PASSWORD: str = "admin"

    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"


settings = Settings()
