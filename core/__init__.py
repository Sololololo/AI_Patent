"""AI 专利助手 - 核心包"""

from .llm_client import LLMClient
from .output_schema import (
    Innovation,
    InnovationDetectionResult,
    NoveltyEvaluation,
    Suggestion,
    SuggestionResult,
    FiveElements,
    PatentAbstract,
    ClaimSet,
    PatentSpecification,
    IdeaMiningResult,
)

__all__ = [
    "LLMClient",
    "Innovation",
    "InnovationDetectionResult",
    "NoveltyEvaluation",
    "Suggestion",
    "SuggestionResult",
    "FiveElements",
    "PatentAbstract",
    "ClaimSet",
    "PatentSpecification",
    "IdeaMiningResult",
]
