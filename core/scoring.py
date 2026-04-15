"""V2 评分引擎

目标：
1. 保留模型原始评分（raw）；
2. 根据输入质量、一致性、可验证性进行可解释校准；
3. 输出可直接展示的评分拆解和问题清单。
"""

import re
from statistics import mean
from typing import Dict, List, Optional

from core.output_schema import (
    IdeaMiningResult,
    NoveltyEvaluation,
    QualityIssue,
    ScoreBreakdown,
)


STRICTNESS_PROFILES: Dict[str, Dict[str, float]] = {
    "严格": {
        "input_floor": 0.18,
        "consistency_floor": 0.20,
        "verifiability_floor": 0.16,
        "issue_penalty": 0.08,
        "input_weight": 0.45,
        "consistency_weight": 0.25,
        "verifiability_weight": 0.30,
        "cap_low_input": 4.0,
        "cap_low_verifiability": 5.0,
    },
    "标准": {
        "input_floor": 0.30,
        "consistency_floor": 0.30,
        "verifiability_floor": 0.24,
        "issue_penalty": 0.06,
        "input_weight": 0.40,
        "consistency_weight": 0.30,
        "verifiability_weight": 0.30,
        "cap_low_input": 5.0,
        "cap_low_verifiability": 6.0,
    },
    "宽松": {
        "input_floor": 0.42,
        "consistency_floor": 0.40,
        "verifiability_floor": 0.34,
        "issue_penalty": 0.04,
        "input_weight": 0.35,
        "consistency_weight": 0.35,
        "verifiability_weight": 0.30,
        "cap_low_input": 6.0,
        "cap_low_verifiability": 7.0,
    },
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _extract_terms(text: str) -> List[str]:
    """提取中英术语词元（jieba关键词提取 + 英文词元）。"""
    if not text:
        return []

    english = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())

    try:
        import jieba.analyse
        chinese_terms = jieba.analyse.extract_tags(text, topK=30)
    except ImportError:
        chinese_sequences = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        chinese_terms = []
        for seq in chinese_sequences:
            if len(seq) <= 3:
                chinese_terms.append(seq)
                continue
            for n in (2, 3, 4):
                for i in range(0, len(seq) - n + 1):
                    chinese_terms.append(seq[i : i + n])

    terms = english + chinese_terms
    return [t for t in terms if len(t.strip()) >= 2]


def _score_input_quality(
    technical_description: str,
    scenarios: List[str],
    reference_patents: Optional[List[str]],
) -> float:
    desc = (technical_description or "").strip()
    compact_len = len("".join(desc.split()))

    # 长度分
    if compact_len <= 8:
        length_score = 0.05
    elif compact_len < 40:
        length_score = 0.20
    elif compact_len < 120:
        length_score = 0.45
    elif compact_len < 260:
        length_score = 0.70
    else:
        length_score = 0.95

    # 术语密度分
    terms = _extract_terms(desc)
    unique_terms = len(set(terms))
    term_score = _clamp(unique_terms / 30.0, 0.05, 1.0)

    # 场景分
    scenario_count = len([s for s in scenarios if s.strip()])
    scenario_chars = sum(len(s.strip()) for s in scenarios)
    scenario_score = _clamp(0.2 + min(0.6, scenario_count * 0.15) + min(0.2, scenario_chars / 250), 0.05, 1.0)

    # 参考材料分
    refs = reference_patents or []
    ref_chars = sum(len(r.strip()) for r in refs)
    ref_score = _clamp(0.25 + min(0.75, ref_chars / 4000), 0.10, 1.0) if refs else 0.30

    return _clamp(
        0.45 * length_score + 0.25 * term_score + 0.20 * scenario_score + 0.10 * ref_score,
        0.0,
        1.0,
    )


def _score_consistency(technical_description: str, result: IdeaMiningResult, llm_client=None) -> float:
    desc_terms = set(_extract_terms(technical_description))
    if not desc_terms:
        return 0.15

    innovation_text = " ".join(
        f"{inn.title} {inn.description} {inn.technical_value}" for inn in result.innovations
    )
    innovation_terms = set(_extract_terms(innovation_text))

    overlap = len(desc_terms & innovation_terms)
    overlap_ratio = overlap / max(1, min(len(desc_terms), 60))

    duplication_penalty = 0.0
    titles = [inn.title.strip().lower() for inn in result.innovations if inn.title.strip()]
    if len(titles) != len(set(titles)):
        duplication_penalty += 0.12

    weak_eval_penalty = 0.0
    if len(result.evaluation.weaknesses) == 0:
        weak_eval_penalty += 0.10

    lexical_score = _clamp(0.20 + overlap_ratio * 1.2, 0.0, 1.0)

    if llm_client and llm_client.is_configured:
        try:
            llm_score = _score_consistency_llm(technical_description, result, llm_client)
            base = 0.4 * lexical_score + 0.6 * llm_score
        except Exception:
            base = lexical_score
    else:
        base = lexical_score

    return _clamp(base - duplication_penalty - weak_eval_penalty, 0.0, 1.0)


def _score_consistency_llm(technical_description: str, result: IdeaMiningResult, llm_client) -> float:
    from pydantic import BaseModel, Field
    from core.llm_client import LLMClient

    class ConsistencyScore(BaseModel):
        score: float = Field(ge=0.0, le=1.0, description="一致性评分0-1")

    innovations_str = "\n".join(
        f"- {inn.title}: {inn.description}" for inn in result.innovations
    )
    system_prompt = "你是一个专利审查一致性评估器。评估创新点与原始技术描述的语义一致性，返回0-1的分数。"
    user_prompt = (
        f"技术描述：\n{technical_description[:2000]}\n\n"
        f"创新点：\n{innovations_str[:2000]}\n\n"
        f"请评估这些创新点与技术描述的语义一致性（0=完全无关，1=高度一致）。"
    )
    response = llm_client.chat_structured(system_prompt, user_prompt, ConsistencyScore)
    return _clamp(response.score, 0.0, 1.0)


def _score_verifiability(result: IdeaMiningResult) -> float:
    text_blob = " ".join(
        [
            " ".join(f"{inn.description} {inn.technical_value}" for inn in result.innovations),
            result.evaluation.technical_progress,
            " ".join(result.evaluation.strengths),
            " ".join(result.evaluation.weaknesses),
        ]
    )
    text_blob = text_blob or ""

    # 指标/数字信号
    metric_signals = len(re.findall(r"\d+(\.\d+)?\s*(%|ms|毫秒|秒|x|倍|万|千)?", text_blob, flags=re.I))
    metric_keywords = [
        "准确率",
        "召回",
        "延迟",
        "吞吐",
        "成本",
        "时延",
        "precision",
        "recall",
        "latency",
        "throughput",
    ]
    metric_kw_hits = sum(1 for kw in metric_keywords if kw.lower() in text_blob.lower())

    # 边界/失败条件信号
    boundary_keywords = ["异常", "失败", "边界", "极端", "回退", "降级", "在.*情况下", "当.*时"]
    boundary_hits = 0
    for pattern in boundary_keywords:
        if ".*" in pattern:
            if re.search(pattern, text_blob):
                boundary_hits += 1
        elif pattern in text_blob:
            boundary_hits += 1

    metric_score = _clamp(0.1 + metric_signals * 0.08 + metric_kw_hits * 0.10, 0.0, 1.0)
    boundary_score = _clamp(0.1 + boundary_hits * 0.2, 0.0, 1.0)

    return _clamp(0.70 * metric_score + 0.30 * boundary_score, 0.0, 1.0)


def _build_issues(
    technical_description: str,
    scenarios: List[str],
    input_quality: float,
    consistency: float,
    verifiability: float,
) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    compact_len = len("".join((technical_description or "").split()))

    if compact_len < 40:
        issues.append(
            QualityIssue(
                severity="高",
                title="权利说明过短",
                detail="当前权利说明信息密度偏低，评分可信度会明显下降。",
                suggestion="补充目标问题、关键技术路径、核心模块与预期效果。",
                location="Step 1 / 权利说明",
            )
        )
    if len([s for s in scenarios if s.strip()]) < 2:
        issues.append(
            QualityIssue(
                severity="中",
                title="应用场景不足",
                detail="场景过少会导致创新点发散不足，评分稳定性下降。",
                suggestion="至少提供 2-3 个差异化场景，包含边界场景。",
                location="Step 1 / 应用场景",
            )
        )
    if input_quality < 0.45:
        issues.append(
            QualityIssue(
                severity="高",
                title="输入质量偏低",
                detail="输入质量评分较低，已触发严格降权。",
                suggestion="补充技术细节、约束条件、可量化指标后重评分。",
                location="Step 3 / 评分面板",
            )
        )
    if consistency < 0.50:
        issues.append(
            QualityIssue(
                severity="中",
                title="内容一致性不足",
                detail="权利说明与创新点术语重叠偏低，可能存在跑题风险。",
                suggestion="将创新点描述中的关键术语与原始权利说明对齐。",
                location="Step 3 / 创新点编辑",
            )
        )
    if verifiability < 0.50:
        issues.append(
            QualityIssue(
                severity="中",
                title="可验证性不足",
                detail="文本中缺少可量化指标或边界条件，结论可证性弱。",
                suggestion="增加性能指标、对照基线、异常处理或失败条件。",
                location="Step 3 / 创新点与评估",
            )
        )
    return issues


def apply_quality_scoring(
    result: IdeaMiningResult,
    technical_description: str,
    scenarios: List[str],
    reference_patents: Optional[List[str]] = None,
    strictness: str = "标准",
    llm_client=None,
) -> IdeaMiningResult:
    """对结果执行 V2 评分校准并返回更新后的结果对象。"""
    profile = STRICTNESS_PROFILES.get(strictness, STRICTNESS_PROFILES["标准"])

    input_quality = _score_input_quality(technical_description, scenarios, reference_patents)
    consistency = _score_consistency(technical_description, result, llm_client)
    verifiability = _score_verifiability(result)

    input_adj = max(profile["input_floor"], input_quality)
    consistency_adj = max(profile["consistency_floor"], consistency)
    verifiability_adj = max(profile["verifiability_floor"], verifiability)

    weighted_sum = (
        input_adj * profile["input_weight"]
        + consistency_adj * profile["consistency_weight"]
        + verifiability_adj * profile["verifiability_weight"]
    )
    trust_score = _clamp(weighted_sum, 0.0, 1.0)
    final_factor = _clamp(
        (0.45 + 0.55 * input_adj) * (0.60 + 0.40 * consistency_adj) * (0.50 + 0.50 * verifiability_adj),
        0.10,
        1.0,
    )

    issues = _build_issues(
        technical_description=technical_description,
        scenarios=scenarios,
        input_quality=input_quality,
        consistency=consistency,
        verifiability=verifiability,
    )

    high_issue_count = sum(1 for item in issues if item.severity == "高")
    issue_penalty = high_issue_count * profile["issue_penalty"]
    final_factor = _clamp(final_factor - issue_penalty, 0.10, 1.0)

    # 若已有拆解，优先沿用首轮原始分，避免重复重评分造成累计衰减。
    prior_raw = result.score_breakdown.raw_scores if result.score_breakdown else {}
    raw_scores = {
        "novelty_score": int(prior_raw.get("novelty_score", result.evaluation.novelty_score)),
        "creativity_score": int(prior_raw.get("creativity_score", result.evaluation.creativity_score)),
        "market_value_score": int(prior_raw.get("market_value_score", result.evaluation.market_value_score)),
        "overall_score": int(prior_raw.get("overall_score", result.evaluation.overall_score)),
    }
    adjusted_scores = {
        key: int(_clamp(round(value * final_factor), 1, 10))
        for key, value in raw_scores.items()
    }

    # 核心原则：低输入质量或低可验证性时，对综合分设置硬上限，防止“信息稀薄高分”。
    cap_reasons: List[str] = []
    if input_quality < 0.22:
        cap = int(profile["cap_low_input"])
        adjusted_scores["overall_score"] = min(adjusted_scores["overall_score"], cap)
        cap_reasons.append(f"输入质量过低，综合分封顶 {cap}/10")
        issues.append(
            QualityIssue(
                severity="高",
                title="触发低输入硬封顶",
                detail="权利说明信息不足，系统已对综合评分启用上限保护。",
                suggestion="补充权利边界、关键限定条件与技术效果指标后重评分。",
                location="Step 1 / 权利说明",
            )
        )
    if verifiability < 0.25:
        cap = int(profile["cap_low_verifiability"])
        adjusted_scores["overall_score"] = min(adjusted_scores["overall_score"], cap)
        cap_reasons.append(f"可验证性偏低，综合分封顶 {cap}/10")
        issues.append(
            QualityIssue(
                severity="中",
                title="触发低可验证性硬封顶",
                detail="缺少可度量指标或边界条件，系统限制综合评分上限。",
                suggestion="增加量化指标、对照基线和异常/边界处理说明。",
                location="Step 3 / 创新点与评估",
            )
        )

    result.evaluation = NoveltyEvaluation(
        novelty_score=adjusted_scores["novelty_score"],
        creativity_score=adjusted_scores["creativity_score"],
        market_value_score=adjusted_scores["market_value_score"],
        overall_score=adjusted_scores["overall_score"],
        technical_progress=result.evaluation.technical_progress,
        strengths=result.evaluation.strengths,
        weaknesses=result.evaluation.weaknesses,
        similarity_analysis=result.evaluation.similarity_analysis,
    )
    result.score_breakdown = ScoreBreakdown(
        strictness=strictness,
        raw_scores=raw_scores,
        adjusted_scores=adjusted_scores,
        input_quality=round(input_quality, 3),
        consistency=round(consistency, 3),
        verifiability=round(verifiability, 3),
        trust_score=round(trust_score, 3),
        final_factor=round(final_factor, 3),
        issues=issues,
        summary=(
            f"原始综合分 {raw_scores['overall_score']}/10，"
            f"可信度 {round(trust_score * 10, 1)}/10，"
            f"校准后 {adjusted_scores['overall_score']}/10。"
            + (f"（{'; '.join(cap_reasons)}）" if cap_reasons else "")
        ),
    )
    return result
