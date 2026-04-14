"""AI 专利助手 - Idea Mining 模块

场景驱动的创新点挖掘流水线：
1. 基于技术描述 + 场景 → 发散创新点
2. 基于创新点 + 参考专利 → 评估新颖性
3. 基于评估结果 → 生成改进建议
"""

from .pipeline import IdeaMiningPipeline

__all__ = ["IdeaMiningPipeline"]
