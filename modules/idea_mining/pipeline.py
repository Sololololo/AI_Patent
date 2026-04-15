"""AI 专利助手 - Idea Mining 流水线

核心设计：
1. 三步串联：创新点检测 → 新颖性评估 → 改进建议
2. 生成者-审查者自博弈：创新点必须经过质疑和反驳
3. 参考专利强制对比：有参考专利时必须逐条对比差异
4. 反模式过滤：排除AI领域显而易见的技术组合
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
    QualityIssue,
)
from core.prompt_loader import load_prompt
from core.anti_patterns import check_anti_patterns, check_innovation_depth

logger = logging.getLogger(__name__)


class IdeaMiningPipeline:
    """场景驱动的创新点挖掘流水线（含自博弈机制）"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(
        self,
        technical_description: str,
        scenarios: List[str],
        reference_patents: Optional[List[str]] = None,
    ) -> IdeaMiningResult:
        ref_patents_str = self._format_reference_patents(reference_patents)
        scenarios_str = self._format_scenarios(scenarios)

        # Step 1: 创新点检测
        logger.info("Step 1: 检测创新点...")
        innovations = self._detect_innovations(
            technical_description, scenarios_str, ref_patents_str
        )
        logger.info(f"检测到 {len(innovations.innovations)} 个创新点")

        # Step 1.5: 反模式过滤
        anti_issues = check_anti_patterns(innovations.innovations)
        depth_issues = check_innovation_depth(innovations.innovations)
        if anti_issues or depth_issues:
            logger.info(f"反模式检测发现 {len(anti_issues)} 个疑似问题，{len(depth_issues)} 个深度问题")

        # Step 2: 自博弈质疑
        logger.info("Step 2: 审查者质疑创新点...")
        challenge_result = self._challenge_innovations(
            technical_description, innovations, ref_patents_str
        )
        if challenge_result.filtered_innovations:
            logger.info(f"自博弈过滤后保留 {len(challenge_result.filtered_innovations)} 个创新点")
            innovations = InnovationDetectionResult(
                innovations=challenge_result.filtered_innovations
            )

        # Step 3: 新颖性评估（结构化推理）
        logger.info("Step 3: 评估新颖性...")
        evaluation = self._evaluate_novelty(
            technical_description, innovations, ref_patents_str
        )
        logger.info(f"综合评分: {evaluation.overall_score}/10")

        # Step 4: 生成改进建议
        logger.info("Step 4: 生成改进建议...")
        suggestions = self._generate_suggestions(
            technical_description, innovations, evaluation
        )
        logger.info(f"生成 {len(suggestions.suggestions)} 条改进建议")

        result = IdeaMiningResult(
            innovations=innovations.innovations,
            evaluation=evaluation,
            suggestions=suggestions.suggestions,
        )

        all_issues = anti_issues + depth_issues + (challenge_result.issues or [])
        if all_issues:
            from core.output_schema import ScoreBreakdown
            existing_breakdown = result.score_breakdown
            existing_issues = existing_breakdown.issues if existing_breakdown else []
            result.score_breakdown = ScoreBreakdown(
                strictness="标准",
                raw_scores={"overall_score": evaluation.overall_score},
                adjusted_scores={"overall_score": evaluation.overall_score},
                input_quality=0.0,
                consistency=0.0,
                verifiability=0.0,
                trust_score=0.0,
                final_factor=1.0,
                issues=existing_issues + all_issues,
                summary=f"反模式/深度检测发现 {len(all_issues)} 个问题。",
            )

        return result

    def _detect_innovations(
        self, technical_description: str, scenarios_str: str, ref_patents_str: str
    ) -> InnovationDetectionResult:
        system_prompt = load_prompt("innovation_detection.md")
        user_prompt = (
            f"技术描述：\n{technical_description}\n\n"
            f"应用场景：\n{scenarios_str}\n\n"
            f"参考专利：\n{ref_patents_str}"
        )
        return self.llm.chat_structured(
            system_prompt, user_prompt, InnovationDetectionResult
        )

    def _challenge_innovations(
        self,
        technical_description: str,
        innovations: InnovationDetectionResult,
        ref_patents_str: str,
    ) -> "ChallengeResult":
        """生成者-审查者自博弈：审查者质疑每个创新点，生成者必须反驳"""
        from pydantic import BaseModel, Field

        class ChallengedInnovation(BaseModel):
            title: str
            challenge: str
            defense: str
            is_valid: bool
            reason: str

        class ChallengeResult(BaseModel):
            challenges: List[ChallengedInnovation]
            filtered_innovations: List[Innovation]
            issues: List[QualityIssue] = []

        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations.innovations],
            ensure_ascii=False, indent=2,
        )

        system_prompt = (
            "你是一位严格的专利审查员（审查者角色）。你的任务是对每个创新点提出质疑：\n"
            "1. 这个创新点为什么不是显而易见的？\n"
            "2. 本领域技术人员是否能轻易想到？\n"
            "3. 是否存在已知的等效替代方案？\n\n"
            "然后切换为发明人角色进行反驳：\n"
            "1. 指出具体技术差异\n"
            "2. 说明非预期效果\n"
            "3. 解释为什么不是简单组合\n\n"
            "如果发明人无法给出令人信服的反驳，则该创新点 is_valid=false。"
        )

        user_prompt = (
            f"技术描述：\n{technical_description}\n\n"
            f"创新点：\n{innovations_str}\n\n"
            f"参考专利：\n{ref_patents_str}\n\n"
            "请对每个创新点进行质疑-反驳博弈，判断其是否真正具有创新性。"
        )

        try:
            result = self.llm.chat_structured(system_prompt, user_prompt, ChallengeResult)
            valid_titles = {c.title for c in result.challenges if c.is_valid}
            filtered = [
                inn for inn in innovations.innovations
                if inn.title in valid_titles or not valid_titles
            ]
            if not filtered:
                filtered = innovations.innovations

            issues = []
            for c in result.challenges:
                if not c.is_valid:
                    issues.append(QualityIssue(
                        severity="中",
                        title=f"自博弈过滤：{c.title}",
                        detail=c.reason,
                        suggestion="补充具体技术差异或非预期效果来增强创新性论证。",
                        location="Step 3 / 自博弈审查",
                    ))

            return ChallengeResult(
                challenges=result.challenges,
                filtered_innovations=filtered,
                issues=issues,
            )
        except Exception as e:
            logger.warning(f"自博弈环节失败，跳过过滤: {e}")
            return ChallengeResult(
                challenges=[],
                filtered_innovations=innovations.innovations,
                issues=[],
            )

    def _evaluate_novelty(
        self,
        technical_description: str,
        innovations: InnovationDetectionResult,
        ref_patents_str: str,
    ) -> NoveltyEvaluation:
        system_prompt = load_prompt("novelty_evaluation.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations.innovations],
            ensure_ascii=False, indent=2,
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
        system_prompt = load_prompt("suggestion_generation.md")
        innovations_str = json.dumps(
            [inn.model_dump() for inn in innovations.innovations],
            ensure_ascii=False, indent=2,
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
            return (
                "无参考专利。\n"
                "注意：缺少参考专利时，你必须自行列举你所知的最接近现有技术，"
                "并说明本方案与这些现有技术的具体差异。"
            )
        parts = []
        for i, patent in enumerate(reference_patents, 1):
            parts.append(f"参考专利 {i}：\n{patent[:3000]}")
        parts.append(
            "\n重要：请逐条对比本方案与上述参考专利的技术差异，"
            "差异必须具体到技术特征，不能只说'应用场景不同'。"
        )
        return "\n\n".join(parts)
