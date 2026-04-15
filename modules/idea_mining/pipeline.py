"""AI 专利助手 - Idea Mining 流水线

核心设计：
1. 三步串联：创新点检测 → 新颖性评估 → 改进建议
2. 生成者-审查者自博弈（3轮迭代）：创新点必须经过多轮质疑-反驳-优化
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
    """场景驱动的创新点挖掘流水线（含3轮自博弈迭代）"""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.game_rounds = 3

    def run(
        self,
        technical_description: str,
        scenarios: List[str],
        reference_patents: Optional[List[str]] = None,
    ) -> IdeaMiningResult:
        ref_patents_str = self._format_reference_patents(reference_patents)
        scenarios_str = self._format_scenarios(scenarios)

        # Step 1: 创新点检测（生成者）
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

        # Step 2: 3轮自博弈迭代优化
        logger.info(f"Step 2: 开始 {self.game_rounds} 轮自博弈迭代...")
        final_innovations, game_issues = self._multi_round_self_play(
            technical_description, innovations, ref_patents_str
        )
        innovations = InnovationDetectionResult(innovations=final_innovations)

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

        all_issues = anti_issues + depth_issues + game_issues
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
                summary=f"反模式/自博弈发现 {len(all_issues)} 个问题。",
            )

        return result

    def run_multi_version(
        self,
        technical_description: str,
        scenarios: List[str],
        reference_patents: Optional[List[str]] = None,
        num_versions: int = 2,
    ) -> List[IdeaMiningResult]:
        """多版本对比生成：生成2-3个不同的创新点挖掘版本供用户选择

        Args:
            technical_description: 技术描述
            scenarios: 应用场景列表
            reference_patents: 参考专利列表
            num_versions: 生成版本数，建议2-3个

        Returns:
            多个IdeaMiningResult实例，供用户对比选择
        """
        results: List[IdeaMiningResult] = []
        for version_idx in range(num_versions):
            logger.info(f"正在生成第 {version_idx + 1}/{num_versions} 个版本...")
            # 每个版本使用略微不同的temperature
            original_temp = getattr(self.llm, 'temperature', 0.7)
            self.llm.temperature = original_temp + (version_idx - (num_versions - 1) / 2) * 0.15
            try:
                result = self.run(technical_description, scenarios, reference_patents)
                results.append(result)
            finally:
                self.llm.temperature = original_temp
        return results

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

    def _multi_round_self_play(
        self,
        technical_description: str,
        innovations: InnovationDetectionResult,
        ref_patents_str: str,
    ) -> (List[Innovation], List[QualityIssue]):
        """3轮自博弈迭代：质疑→反驳→优化→再质疑..."""
        from pydantic import BaseModel, Field

        class RoundResult(BaseModel):
            round_num: int
            actions: List[str]
            optimized_innovations: List[Innovation]
            filtered_titles: List[str]
            game_log: str

        current_innovations = innovations.innovations.copy()
        all_issues: List[QualityIssue] = []
        filtered_in_all_rounds = set()

        for round_idx in range(1, self.game_rounds + 1):
            logger.info(f"自博弈第 {round_idx}/{self.game_rounds} 轮...")

            innovations_str = json.dumps(
                [inn.model_dump() for inn in current_innovations],
                ensure_ascii=False, indent=2,
            )

            # 每轮有不同的审查视角
            perspectives = [
                "本领域技术人员",
                "专利审查员",
                "竞争对手",
            ]
            perspective = perspectives[(round_idx - 1) % len(perspectives)]

            system_prompt = (
                f"你是一位严格的{perspective}（审查者角色）。这是第{round_idx}轮审查。\n\n"
                "任务流程：\n"
                "1. 对每个创新点提出质疑：为什么不是显而易见的？本领域技术人员是否能轻易想到？\n"
                "2. 切换为发明人角色进行反驳：指出具体技术差异、说明非预期效果、解释为什么不是简单组合\n"
                "3. 如果无法反驳，标记为过滤；如果可以反驳，给出优化建议\n"
                "4. 对保留的创新点进行优化，让创新性论证更强\n\n"
                f"本轮重点：{'基础逻辑审查' if round_idx == 1 else '创造性高度审查' if round_idx == 2 else '最终可专利性审查'}"
            )

            user_prompt = (
                f"技术描述：\n{technical_description}\n\n"
                f"当前创新点（第{round_idx}轮开始）：\n{innovations_str}\n\n"
                f"参考专利：\n{ref_patents_str}\n\n"
                f"请完成第{round_idx}轮质疑-反驳-优化流程。"
            )

            try:
                result = self.llm.chat_structured(system_prompt, user_prompt, RoundResult)

                filtered_in_this_round = set(result.filtered_titles)
                filtered_in_all_rounds.update(filtered_in_this_round)

                for title in filtered_in_this_round:
                    all_issues.append(QualityIssue(
                        severity="中",
                        title=f"自博弈第{round_idx}轮过滤：{title}",
                        detail=f"经{perspective}视角审查，无法给出令人信服的创新性论证。",
                        suggestion="请补充具体技术差异或非预期效果。",
                        location=f"Step 3 / 自博弈第{round_idx}轮",
                    ))

                current_innovations = result.optimized_innovations
                logger.info(f"第{round_idx}轮后保留 {len(current_innovations)} 个创新点")

            except Exception as e:
                logger.warning(f"自博弈第{round_idx}轮失败: {e}")
                continue

        final_innovations = [
            inn for inn in current_innovations
            if inn.title not in filtered_in_all_rounds
        ]

        if not final_innovations:
            final_innovations = innovations.innovations

        return final_innovations, all_issues

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
