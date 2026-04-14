"""AI 专利助手 - 所有 LLM 输出的 Pydantic 模型定义

每个模型对应一个 LLM 调用步骤的输出格式，用于：
1. 生成 prompt 中的 JSON Schema 约束
2. 解析和校验 LLM 输出
3. 在模块间传递结构化数据
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ============================================================
# 枚举类型
# ============================================================

class InnovationLevel(str, Enum):
    """创新程度等级"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class DifficultyLevel(str, Enum):
    """实施难度"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


# ============================================================
# Idea Mining 输出模型
# ============================================================

class Innovation(BaseModel):
    """单个创新点"""
    title: str = Field(description="创新点标题，简洁概括")
    description: str = Field(description="创新点详细描述")
    innovation_type: str = Field(description="创新类型：方法创新/系统创新/算法创新/结构创新/应用创新")
    technical_value: str = Field(description="技术价值说明")
    level: InnovationLevel = Field(description="创新程度：高/中/低")


class InnovationDetectionResult(BaseModel):
    """创新点检测结果"""
    innovations: List[Innovation] = Field(description="检测到的创新点列表")


class NoveltyEvaluation(BaseModel):
    """新颖性评估结果"""
    novelty_score: int = Field(description="新颖性评分 1-10", ge=1, le=10)
    creativity_score: int = Field(description="创造性评分 1-10", ge=1, le=10)
    technical_progress: str = Field(description="技术进步性说明")
    market_value_score: int = Field(description="市场价值评分 1-10", ge=1, le=10)
    overall_score: int = Field(description="综合评分 1-10", ge=1, le=10)
    strengths: List[str] = Field(description="优势列表")
    weaknesses: List[str] = Field(description="不足或风险列表")
    similarity_analysis: str = Field(description="与参考专利的相似性分析", default="无参考专利")


class Suggestion(BaseModel):
    """单个改进建议"""
    direction: str = Field(description="改进方向")
    suggestion: str = Field(description="具体建议内容")
    expected_effect: str = Field(description="预期效果")
    difficulty: DifficultyLevel = Field(description="实施难度：高/中/低")


class SuggestionResult(BaseModel):
    """改进建议结果"""
    suggestions: List[Suggestion] = Field(description="改进建议列表")


class IdeaMiningResult(BaseModel):
    """Idea Mining 完整结果（串联三个子步骤）"""
    innovations: List[Innovation] = Field(description="创新点列表")
    evaluation: NoveltyEvaluation = Field(description="新颖性评估")
    suggestions: List[Suggestion] = Field(description="改进建议列表")


# ============================================================
# 五要素模型
# ============================================================

class FiveElements(BaseModel):
    """专利五要素分析结果"""
    technical_problem: str = Field(description="技术问题：要解决什么问题")
    technical_solution: str = Field(description="技术方案：如何解决问题")
    technical_effect: str = Field(description="技术效果：带来什么有益效果")
    technical_features: List[str] = Field(description="技术特征：关键技术特征列表")
    application_scenarios: List[str] = Field(description="应用场景：可应用的场景列表")


# ============================================================
# 结构化写作输出模型
# ============================================================

class PatentAbstract(BaseModel):
    """专利摘要"""
    abstract: str = Field(description="专利摘要，200-300字")
    keywords: List[str] = Field(description="关键词列表，3-5个")


class Claim(BaseModel):
    """单条权利要求"""
    claim_number: int = Field(description="权利要求编号")
    claim_type: str = Field(description="类型：独立权利要求/从属权利要求")
    content: str = Field(description="权利要求内容")
    depends_on: Optional[int] = Field(description="从属于第几条权利要求（独立权利要求为null）", default=None)


class ClaimSet(BaseModel):
    """权利要求书"""
    claims: List[Claim] = Field(description="权利要求列表")
    main_claim_summary: str = Field(description="独立权利要求核心概括")


# ============================================================
# 专利说明书
# ============================================================

class PatentSpecification(BaseModel):
    """完整专利说明书"""
    title: str = Field(description="发明名称")
    abstract: str = Field(description="摘要")
    technical_field: str = Field(description="技术领域")
    background_art: str = Field(description="背景技术")
    summary: str = Field(description="发明内容摘要")
    detailed_description: str = Field(description="具体实施方式")
    brief_description_of_drawings: str = Field(description="附图说明", default="本发明无附图")
