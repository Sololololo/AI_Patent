"""AI 专利助手 - 专利说明书生成模块"""

import json
import logging

from core.llm_client import LLMClient
from core.output_schema import (
    Innovation,
    FiveElements,
    ClaimSet,
    PatentAbstract,
    PatentSpecification,
    NoveltyEvaluation,
)
from core.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class PatentGeneratorService:
    """专利说明书生成服务"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_specification(
        self,
        invention_name: str,
        technical_description: str,
        five_elements: FiveElements,
        innovations: list[Innovation],
        evaluation: NoveltyEvaluation,
        claims: ClaimSet,
        abstract_result: PatentAbstract,
    ) -> PatentSpecification:
        """生成完整专利说明书"""
        logger.info("生成专利说明书...")
        system_prompt = load_prompt("specification_generation.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations], ensure_ascii=False, indent=2
        )
        user_prompt = (
            f"发明名称：{invention_name}\n\n"
            f"技术描述：\n{technical_description}\n\n"
            f"五要素分析：\n{five_elements.model_dump_json(indent=2)}\n\n"
            f"创新点：\n{innovations_str}\n\n"
            f"新颖性评估：\n{evaluation.model_dump_json(indent=2)}\n\n"
            f"权利要求书：\n{claims.model_dump_json(indent=2)}\n\n"
            f"摘要：\n{abstract_result.abstract}"
        )
        return self.llm.chat_structured(system_prompt, user_prompt, PatentSpecification)
