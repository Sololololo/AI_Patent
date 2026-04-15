"""AI 专利助手 - 统一配置管理"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置，从 .env 文件或环境变量加载"""

    # LLM 配置
    api_url: str = "https://api.deepseek.com/v1/chat/completions"
    api_key: Optional[str] = None
    model_name: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096

    # 输出路径
    output_dir: str = "output"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def create_settings(**overrides) -> Settings:
    """创建配置实例，支持运行时覆盖"""
    return Settings(**overrides)
