"""AI 专利助手 - Idea Mining 流水线

核心设计：三步串联，前一步的输出是后一步的输入。
用户输入：技术描述 + 应用场景 + 参考专利（可选）
"""

import json
import logging
from typing import List, Optional

from core.llm_client import LLMClient
from core.output_schema import (
    Innovation,
    InnovationDetectionResult,
    NoveltyEvaluation,
    Suggestion,
    SuggestionResult,
    IdeaMiningResult,
)
from core.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class IdeaMiningPipeline:
    """场景驱动的创新点挖掘流水线"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(
        self,
        technical_description: str,
        scenarios: List[str],
        reference_patents: Optional[List[str]] = None,
    ) -> IdeaMiningResult:
        """执行完整的 Idea Mining 流水线

        Args:
            technical_description: 用户的技术描述
            scenarios: 用户提供的应用场景列表
            reference_patents: 参考专利文本列表（可选）

        Returns:
            IdeaMiningResult: 包含创新点、评估、建议的完整结果
        """
        # 格式化参考专利
        ref_patents_str = self._format_reference_patents(reference_patents)
        scenarios_str = self._format_scenarios(scenarios)

        # Step 1: 创新点检测
        logger.info("Step 1: 检测创新点...")
        innovations = self._detect_innovations(
            technical_description, scenarios_str, ref_patents_str
        )
        logger.info(f"检测到 {len(innovations.innovations)} 个创新点")

        # Step 2: 新颖性评估（基于创新点）
        logger.info("Step 2: 评估新颖性...")
        evaluation = self._evaluate_novelty(
            technical_description, innovations, ref_patents_str
        )
        logger.info(f"综合评分: {evaluation.overall_score}/10")

        # Step 3: 生成改进建议（基于评估结果）
        logger.info("Step 3: 生成改进建议...")
        suggestions = self._generate_suggestions(
            technical_description, innovations, evaluation
        )
        logger.info(f"生成 {len(suggestions.suggestions)} 条改进建议")

        return IdeaMiningResult(
            innovations=innovations.innovations,
            evaluation=evaluation,
            suggestions=suggestions.suggestions,
        )

    def _detect_innovations(
        self, technical_description: str, scenarios_str: str, ref_patents_str: str
    ) -> InnovationDetectionResult:
        """Step 1: 基于场景发散创新点"""
        system_prompt = load_prompt("innovation_detection.md")
        user_prompt = (
            f"技术描述：\n{technical_description}\n\n"
            f"应用场景：\n{scenarios_str}\n\n"
            f"参考专利：\n{ref_patents_str}"
        )
        return self.llm.chat_structured(
            system_prompt, user_prompt, InnovationDetectionResult
        )

    def _evaluate_novelty(
        self,
        technical_description: str,
        innovations: InnovationDetectionResult,
        ref_patents_str: str,
    ) -> NoveltyEvaluation:
        """Step 2: 评估新颖性（基于创新点结果）"""
        system_prompt = load_prompt("novelty_evaluation.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations.innovations],
            ensure_ascii=False,
            indent=2,
        )
        user_prompt = (
            f"技术描述：\n{technical_description}\n\n"
            f"已识别的创新点：\n{innovations_str}\n\n"
            f"参考专利：\n{ref_patents_str}"
        )
        return self.llm.chat_structured(system_prompt, user_prompt, NoveltyEvaluation)

    def _generate_suggestions(
        self,
        technical_description: str,
        innovations: InnovationDetectionResult,
        evaluation: NoveltyEvaluation,
    ) -> SuggestionResult:
        """Step 3: 生成改进建议（基于评估结果）"""
        system_prompt = load_prompt("suggestion_generation.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations.innovations],
            ensure_ascii=False,
            indent=2,
        )
        evaluation_str = evaluation.model_dump_json(indent=2)
        user_prompt = (
            f"技术描述：\n{technical_description}\n\n"
            f"已识别的创新点：\n{innovations_str}\n\n"
            f"新颖性评估结果：\n{evaluation_str}"
        )
        return self.llm.chat_structured(system_prompt, user_prompt, SuggestionResult)

    @staticmethod
    def _format_scenarios(scenarios: List[str]) -> str:
        if not scenarios:
            return "用户未提供具体场景，请基于技术描述自行推断可能的应用场景"
        return "\n".join(f"- {s}" for s in scenarios)

    @staticmethod
    def _format_reference_patents(reference_patents: Optional[List[str]]) -> str:
        if not reference_patents:
            return "无参考专利"
        parts = []
        for i, patent in enumerate(reference_patents, 1):
            parts.append(f"参考专利 {i}：\n{patent[:3000]}")  # 截断避免过长
        return "\n\n".join(parts)
