"""AI领域专利反模式库

过滤"显而易见"的技术组合，这些组合在AI领域几乎不可能获批。
纯规则判断，不需要LLM。
"""

import re
from typing import List, Tuple

from core.output_schema import Innovation, QualityIssue


ANTI_PATTERNS: List[Tuple[str, str, str]] = [
    # ============== 模型使用类 ==============
    (
        r"(?:直接|简单|直接将|简单将).*(?:预训练|大模型|LLM|基础模型|开源模型).*(?:用于|应用到|应用于|用到)",
        "直接将预训练模型用于特定任务",
        "在特定任务上使用预训练模型属于本领域常规手段，不具备新颖性。需要说明模型选择、适配方式、微调策略等方面的特殊设计。",
    ),
    (
        r"(?:用|采用|使用|利用).*(?:LoRA|PEFT|适配器|adapter).*(?:微调|训练|优化)",
        "用LoRA/PEFT微调模型",
        "LoRA/PEFT等参数高效微调方法已成为标准技术，除非有特殊的适配器设计或混合策略，否则不具备新颖性。",
    ),
    (
        r"(?:用|采用|使用|利用).*(?:指令微调|instruction tuning|SFT|有监督微调).*(?:训练|优化|提升)",
        "用指令微调训练模型",
        "指令微调已成为大模型训练的标准流程，除非有特殊的指令设计或数据构造策略，否则不具备新颖性。",
    ),
    (
        r"(?:用|采用|使用|利用).*(?:蒸馏|知识蒸馏|distillation).*(?:压缩|优化|提升)",
        "用知识蒸馏压缩模型",
        "知识蒸馏是模型压缩的常规手段，除非有特殊的蒸馏策略或损失函数设计，否则不具备新颖性。",
    ),
    (
        r"(?:用|采用|使用|利用).*(?:量化|quantization|剪枝|pruning).*(?:压缩|优化|加速)",
        "用量化/剪枝优化模型",
        "量化/剪枝等模型压缩技术已广泛应用，除非有特殊的量化策略或稀疏化方法，否则不具备新颖性。",
    ),

    # ============== 架构组件类 ==============
    (
        r"(?:用|采用|使用|利用).*(?:注意力机制|attention|自注意力|self-attention|多头注意力|multi-head).*(?:改进|优化|提升|增强)",
        "用注意力机制改进某任务",
        "注意力机制是深度学习基本组件，除非有特殊结构设计（如跨模态注意力、稀疏注意力、线性注意力等），否则属于常规手段。",
    ),
    (
        r"(?:用|采用|使用|利用).*(?:Transformer|CNN|RNN|GRU|LSTM|GAN|扩散模型|diffusion).*(?:实现|改进|优化)",
        "用标准架构实现某功能",
        "Transformer/CNN/RNN/GAN等标准架构已广泛应用，除非有特殊的架构变体或改进，否则不具备新颖性。",
    ),
    (
        r"(?:用|采用|使用|利用).*(?:激活函数|损失函数|优化器).*(?:改进|优化|提升)",
        "替换激活函数/损失函数/优化器",
        "简单替换标准组件（如ReLU换GELU、Adam换Lion）属于常规选择，除非有特殊的组合或改进，否则不具备新颖性。",
    ),

    # ============== 模块组合类 ==============
    (
        r"(?:将|把).*(?:A|模块A|组件A).*(?:和B|与B|与模块B|和模块B).*(?:串联|拼接|简单组合|直接连接|顺序执行)",
        "简单串联两个模块",
        "将A和B简单串联缺乏协同效应说明，需要阐述两者之间的交互机制和产生的非预期效果。",
    ),
    (
        r"(?:并行|并行执行|同时使用).*(?:A|B|多个模型|多个模块).*(?:投票|集成|ensemble)",
        "多个模型简单集成/投票",
        "多个模型并行投票是常规集成策略，除非有特殊的集成策略或门控机制，否则不具备新颖性。",
    ),

    # ============== 对齐与安全类 ==============
    (
        r"(?:用|采用).*(?:RLHF|人类反馈强化学习|偏好对齐|RLAIF).*(?:优化|训练|微调|改进)",
        "用RLHF/RLAIF优化模型",
        "RLHF/RLAIF已成为大模型对齐的标准流程，除非有特殊的奖励模型设计或反馈机制创新，否则不具备新颖性。",
    ),
    (
        r"(?:用|采用|使用).*(?:内容过滤|安全过滤|敏感词过滤|safety|content filter).*(?:检测|防护)",
        "用内容过滤防护安全问题",
        "内容过滤是AI安全的常规手段，除非有特殊的检测策略或多级防护机制，否则不具备新颖性。",
    ),

    # ============== RAG与检索类 ==============
    (
        r"(?:基于|利用).*(?:RAG|检索增强|检索增强生成|retrieval augmented).*(?:实现|完成|进行)",
        "基于RAG实现某功能",
        "RAG已成为LLM应用的标准架构，需要说明检索策略、融合方式、排序机制、查询重写等方面的特殊设计。",
    ),
    (
        r"(?:用|采用|使用).*(?:向量数据库|vector database|Faiss|Milvus|Chroma).*(?:存储|检索)",
        "用向量数据库存储和检索",
        "向量数据库是RAG的标准组件，除非有特殊的索引策略或检索优化，否则不具备新颖性。",
    ),
    (
        r"(?:重写|改写|重构).*(?:查询|query|问题).*(?:检索|搜索)",
        "查询重写改进检索",
        "查询重写是RAG的常规优化手段，除非有特殊的重写策略或多轮改写机制，否则不具备新颖性。",
    ),

    # ============== Prompt与推理类 ==============
    (
        r"(?:用|采用|使用).*(?:prompt|提示词|提示工程|prompt engineering).*(?:实现|完成|解决)",
        "用提示工程解决问题",
        "提示工程是LLM使用的基本技能，需要说明提示结构设计、动态生成策略、元提示等非显而易见的创新。",
    ),
    (
        r"(?:用|采用|使用).*(?:思维链|Chain of Thought|CoT|少样本|Few-Shot|零样本|Zero-Shot).*(?:推理|解决)",
        "用思维链/少样本/零样本推理",
        "思维链、Few-Shot、Zero-Shot是LLM推理的标准方法，除非有特殊的提示策略或推理增强机制，否则不具备新颖性。",
    ),
    (
        r"(?:用|采用|使用).*(?:反思|reflection|自我修正|self-correction).*(?:改进|优化)",
        "用反思/自我修正改进输出",
        "反思/自我修正是Agent的常规组件，除非有特殊的反思策略或修正机制，否则不具备新颖性。",
    ),
    (
        r"(?:用|采用|使用).*(?:ReAct|ToT|Tree of Thoughts|GoT|Graph of Thoughts).*(?:推理|规划)",
        "用ReAct/ToT/GoT等推理框架",
        "ReAct/ToT/GoT等推理框架已成为标准，除非有特殊的框架变体或改进，否则不具备新颖性。",
    ),

    # ============== 知识与多模态类 ==============
    (
        r"(?:将|把).*(?:知识图谱|知识库|KG).*(?:和|与).*(?:大模型|LLM).*(?:结合|融合|集成)",
        "知识图谱与大模型简单结合",
        "知识图谱增强LLM是常见方案，需要说明知识注入方式、推理机制、图谱构建方法等方面的创新。",
    ),
    (
        r"(?:用|采用).*(?:多模态|multimodal|跨模态|cross-modal).*(?:实现|完成|进行)",
        "用多模态实现某功能",
        "多模态融合已成为标准技术路线，需要说明融合架构、对齐方式、模态交互机制等方面的创新。",
    ),

    # ============== 应用场景类 ==============
    (
        r"(?:用于|应用于|应用到).*(?:文本分类|情感分析|机器翻译|问答|QA|摘要|summarization).*(?:任务|场景)",
        "用于常规NLP任务",
        "文本分类、情感分析、机器翻译等是NLP的常规任务，除非有特殊的模型适配或任务改造，否则不具备新颖性。",
    ),
    (
        r"(?:用于|应用于|应用到).*(?:图像识别|目标检测|图像分割|OCR|语音识别|ASR).*(?:任务|场景)",
        "用于常规CV/语音任务",
        "图像识别、目标检测、语音识别等是CV/语音的常规任务，除非有特殊的模型适配或任务改造，否则不具备新颖性。",
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
