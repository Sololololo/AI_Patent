"""AI 专利助手 - LLM 客户端封装

统一管理 LLM 调用，支持：
- OpenAI 兼容 API（DeepSeek / GLM / Qwen / OpenAI）
- 结构化输出（JSON Mode + Pydantic 校验）
- 动态配置切换
"""

import json
import logging
from typing import Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMNotConfiguredError(Exception):
    """LLM 未配置异常"""
    pass


class LLMResponseParseError(Exception):
    """LLM 输出解析异常"""

    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response


class LLMClient:
    """LLM 客户端，支持配置动态切换和结构化输出"""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or Settings()
        self._client: Optional[OpenAI] = None
        self._init_client()

    def _init_client(self):
        """初始化 OpenAI 客户端"""
        if not self._settings.api_key:
            logger.warning("API Key 未配置，LLM 功能不可用")
            return

        # 从 api_url 提取 base_url（去掉 /chat/completions 后缀）
        base_url = self._settings.api_url
        if "/chat/completions" in base_url:
            base_url = base_url.replace("/chat/completions", "")
        if "/v1" not in base_url:
            base_url = base_url.rstrip("/") + "/v1"

        self._client = OpenAI(
            api_key=self._settings.api_key,
            base_url=base_url,
        )
        logger.info(f"LLM 客户端初始化完成: model={self._settings.model_name}, base_url={base_url}")

    def reconfigure(self, settings: Settings):
        """动态切换配置"""
        self._settings = settings
        self._client = None
        self._init_client()

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def chat(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None) -> str:
        """基础对话接口，返回原始文本"""
        if not self.is_configured:
            raise LLMNotConfiguredError("请先在侧边栏配置 API Key 和 API URL")

        temp = temperature if temperature is not None else self._settings.temperature

        response = self._client.chat.completions.create(
            model=self._settings.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temp,
            max_tokens=self._settings.max_tokens,
        )

        content = response.choices[0].message.content
        logger.debug(f"LLM 响应: {content[:200]}...")
        return content

    def chat_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T],
                        temperature: Optional[float] = None) -> T:
        """结构化输出接口，返回 Pydantic 模型实例

        策略：先尝试 JSON Mode，再用 Pydantic 校验；失败则尝试从文本中提取 JSON。
        """
        if not self.is_configured:
            raise LLMNotConfiguredError("请先在侧边栏配置 API Key 和 API URL")

        temp = temperature if temperature is not None else self._settings.temperature

        # 在 user_prompt 末尾追加 JSON 输出要求
        schema_hint = response_model.model_json_schema()
        json_instruction = (
            f"\n\n请严格按照以下 JSON Schema 输出，不要输出任何其他内容：\n"
            f"```json\n{json.dumps(schema_hint, ensure_ascii=False, indent=2)}\n```"
        )
        full_user_prompt = user_prompt + json_instruction

        # 尝试 JSON Mode
        try:
            response = self._client.chat.completions.create(
                model=self._settings.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_user_prompt},
                ],
                temperature=temp,
                max_tokens=self._settings.max_tokens,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return response_model.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"JSON Mode 解析失败，尝试文本提取: {e}")
        except Exception as e:
            # 某些模型不支持 response_format，降级到普通模式
            logger.warning(f"JSON Mode 不支持，降级到普通模式: {e}")

        # 降级：普通请求 + 文本中提取 JSON
        try:
            content = self.chat(system_prompt, full_user_prompt, temperature=temp)
            return self._extract_json_from_text(content, response_model)
        except Exception as e:
            raise LLMResponseParseError(f"无法解析 LLM 输出为 {response_model.__name__}: {e}", content)

    def _extract_json_from_text(self, text: str, model: Type[T]) -> T:
        """从 LLM 输出文本中提取 JSON 并解析为 Pydantic 模型"""
        # 尝试找到 JSON 块
        json_str = text

        # 提取 ```json ... ``` 块
        import re
        json_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_block:
            json_str = json_block.group(1).strip()

        # 尝试找到第一个 { 到最后一个 }
        if "{" in json_str and "}" in json_str:
            start = json_str.index("{")
            end = json_str.rindex("}") + 1
            json_str = json_str[start:end]

        return model.model_validate_json(json_str)
