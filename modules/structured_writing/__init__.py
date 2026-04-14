"""AI 专利助手 - 结构化写作模块

流程：五要素分析 → 摘要生成 → 权利要求书生成
"""

import json
import logging
from typing import List

from core.llm_client import LLMClient
from core.output_schema import (
    Innovation,
    FiveElements,
    PatentAbstract,
    ClaimSet,
    NoveltyEvaluation,
)
from core.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class StructuredWritingService:
    """结构化写作服务：五要素 → 摘要 → 权利要求"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze_five_elements(
        self, technical_description: str, innovations: List[Innovation]
    ) -> FiveElements:
        """五要素分析"""
        logger.info("分析五要素...")
        system_prompt = load_prompt("five_elements.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations], ensure_ascii=False, indent=2
        )
        user_prompt = (
            f"技术描述：\n{technical_description}\n\n"
            f"创新点：\n{innovations_str}"
        )
        return self.llm.chat_structured(system_prompt, user_prompt, FiveElements)

    def generate_abstract(
        self,
        technical_description: str,
        five_elements: FiveElements,
        innovations: List[Innovation],
    ) -> PatentAbstract:
        """生成专利摘要"""
        logger.info("生成摘要...")
        system_prompt = load_prompt("abstract_generation.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations], ensure_ascii=False, indent=2
        )
        user_prompt = (
            f"技术描述：\n{technical_description}\n\n"
            f"五要素分析：\n{five_elements.model_dump_json(indent=2)}\n\n"
            f"创新点：\n{innovations_str}"
        )
        return self.llm.chat_structured(system_prompt, user_prompt, PatentAbstract)

    def generate_claims(
        self,
        invention_name: str,
        technical_description: str,
        five_elements: FiveElements,
        innovations: List[Innovation],
        evaluation: NoveltyEvaluation,
    ) -> ClaimSet:
        """生成权利要求书"""
        logger.info("生成权利要求书...")
        system_prompt = load_prompt("claims_generation.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations], ensure_ascii=False, indent=2
        )
        user_prompt = (
            f"发明名称：{invention_name}\n\n"
            f"技术描述：\n{technical_description}\n\n"
            f"五要素分析：\n{five_elements.model_dump_json(indent=2)}\n\n"
            f"创新点：\n{innovations_str}\n\n"
            f"新颖性评估：\n{evaluation.model_dump_json(indent=2)}"
        )
        return self.llm.chat_structured(system_prompt, user_prompt, ClaimSet)
