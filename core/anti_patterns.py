"""AI领域专利反模式库

过滤"显而易见"的技术组合，这些组合在AI领域几乎不可能获批。
纯规则判断，不需要LLM。
"""

import re
from typing import List, Tuple

from core.output_schema import Innovation, QualityIssue


ANTI_PATTERNS: List[Tuple[str, str, str]] = [
    (
        r"(?:直接|简单|直接将|简单将).*(?:预训练|大模型|LLM|基础模型).*(?:用于|应用到|应用于)",
        "直接将预训练模型用于特定任务",
        "在特定任务上使用预训练模型属于本领域常规手段，不具备新颖性。需要说明模型选择、适配方式、微调策略等方面的特殊设计。",
    ),
    (
        r"(?:用|采用|使用|利用).*(?:注意力机制|attention|自注意力|self-attention).*(?:改进|优化|提升|增强)",
        "用注意力机制改进某任务",
        "注意力机制是深度学习基本组件，除非有特殊结构设计（如跨模态注意力、稀疏注意力等），否则属于常规手段。",
    ),
    (
        r"(?:将|把).*(?:A|模块A|组件A).*(?:和B|与B|与模块B|和模块B).*(?:串联|拼接|简单组合|直接连接)",
        "简单串联两个模块",
        "将A和B简单串联缺乏协同效应说明，需要阐述两者之间的交互机制和产生的非预期效果。",
    ),
    (
        r"(?:用|采用).*(?:RLHF|人类反馈强化学习|偏好对齐).*(?:优化|训练|微调|改进)",
        "用RLHF优化模型",
        "RLHF已成为大模型训练的标准流程，除非有特殊的奖励模型设计或反馈机制创新，否则不具备新颖性。",
    ),
    (
        r"(?:基于|利用).*(?:RAG|检索增强|检索增强生成).*(?:实现|完成|进行)",
        "基于RAG实现某功能",
        "RAG已成为LLM应用的标准架构，需要说明检索策略、融合方式、排序机制等方面的特殊设计。",
    ),
    (
        r"(?:用|采用|使用).*(?:prompt|提示词|提示工程|prompt engineering).*(?:实现|完成|解决)",
        "用提示工程解决问题",
        "提示工程是LLM使用的基本技能，需要说明提示结构设计、动态生成策略等非显而易见的创新。",
    ),
    (
        r"(?:将|把).*(?:知识图谱|知识库).*(?:和|与).*(?:大模型|LLM).*(?:结合|融合|集成)",
        "知识图谱与大模型简单结合",
        "知识图谱增强LLM是常见方案，需要说明知识注入方式、推理机制、图谱构建方法等方面的创新。",
    ),
    (
        r"(?:用|采用).*(?:多模态|multimodal).*(?:实现|完成|进行)",
        "用多模态实现某功能",
        "多模态融合已成为标准技术路线，需要说明融合架构、对齐方式、模态交互机制等方面的创新。",
    ),
]


def check_anti_patterns(innovations: List[Innovation]) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    for inn in innovations:
        text = f"{inn.title} {inn.description} {inn.technical_value}"
        for pattern, name, reason in ANTI_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(QualityIssue(
                    severity="中",
                    title=f"疑似反模式：{name}",
                    detail=reason,
                    suggestion=f"创新点「{inn.title}」可能属于AI领域常规手段，请补充具体的技术差异和非预期效果。",
                    location="Step 3 / 创新点挖掘",
                ))
                break
    return issues


def check_innovation_depth(innovations: List[Innovation]) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    for inn in innovations:
        desc = inn.description.strip()
        value = inn.technical_value.strip()

        if len(desc) < 20:
            issues.append(QualityIssue(
                severity="中",
                title=f"创新点「{inn.title}」描述过短",
                detail=f"描述仅{len(desc)}字，无法判断创新深度。",
                suggestion="补充技术方案的具体实现细节和与现有方法的差异。",
                location="Step 3 / 创新点挖掘",
            ))

        if not value or len(value) < 10:
            issues.append(QualityIssue(
                severity="中",
                title=f"创新点「{inn.title}」缺少技术价值说明",
                detail="技术价值为空或过短，无法评估创新意义。",
                suggestion="说明该创新带来的具体技术效果，如性能提升、成本降低等。",
                location="Step 3 / 创新点挖掘",
            ))

        if str(inn.level) == "低" and len(innovations) <= 2:
            issues.append(QualityIssue(
                severity="中",
                title="高创新度创新点不足",
                detail=f"当前{len(innovations)}个创新点中缺少高创新度的点。",
                suggestion="尝试从跨领域迁移、非预期效果等角度挖掘更多创新点。",
                location="Step 3 / 创新点挖掘",
            ))

    return issues
