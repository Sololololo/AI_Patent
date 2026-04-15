"""专利合规校验层

纯规则校验，不依赖 LLM：
1. 权利要求从属关系合法性
2. 摘要字数与关键词数量
3. 说明书各节完整性
4. 独立权利要求存在性
"""

import re
from typing import List

from core.output_schema import (
    ClaimSet,
    PatentAbstract,
    PatentSpecification,
    QualityIssue,
)


class ValidationResult:
    def __init__(self, issues: List[QualityIssue]):
        self.issues = issues
        self.errors = [i for i in issues if i.severity == "高"]
        self.warnings = [i for i in issues if i.severity == "中"]
        self.is_pass = len(self.errors) == 0

    def __repr__(self):
        return f"ValidationResult(errors={len(self.errors)}, warnings={len(self.warnings)}, pass={self.is_pass})"


def validate_claims(claims: ClaimSet) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    if not claims or not claims.claims:
        issues.append(QualityIssue(
            severity="高", title="权利要求为空",
            detail="权利要求书不能为空，至少需要1条独立权利要求。",
            suggestion="请生成权利要求书。", location="Step 4 / 权利要求",
        ))
        return issues

    claim_map = {c.claim_number: c for c in claims.claims}

    independent_claims = [c for c in claims.claims if c.claim_type == "独立权利要求"]
    if not independent_claims:
        issues.append(QualityIssue(
            severity="高", title="缺少独立权利要求",
            detail="权利要求书中没有独立权利要求，这是致命缺陷。",
            suggestion="确保第1条权利要求为独立权利要求。", location="Step 4 / 权利要求",
        ))

    for claim in claims.claims:
        if claim.claim_type == "从属权利要求":
            if claim.depends_on is None:
                issues.append(QualityIssue(
                    severity="高", title=f"第{claim.claim_number}条从属权利要求缺少引用",
                    detail=f"从属权利要求必须明确引用前述权利要求的编号。",
                    suggestion=f"为第{claim.claim_number}条设置 depends_on 字段。",
                    location=f"Step 4 / 第{claim.claim_number}条",
                ))
            elif claim.depends_on == claim.claim_number:
                issues.append(QualityIssue(
                    severity="高", title=f"第{claim.claim_number}条循环引用自身",
                    detail="从属权利要求不能引用自身。",
                    suggestion=f"修改第{claim.claim_number}条的 depends_on 为其他权利要求编号。",
                    location=f"Step 4 / 第{claim.claim_number}条",
                ))
            elif claim.depends_on not in claim_map:
                issues.append(QualityIssue(
                    severity="高", title=f"第{claim.claim_number}条引用了不存在的编号",
                    detail=f"引用了第{claim.depends_on}条，但该编号不存在。",
                    suggestion=f"修改 depends_on 为1-{len(claims.claims)}之间的有效编号。",
                    location=f"Step 4 / 第{claim.claim_number}条",
                ))

    visited = set()
    for claim in claims.claims:
        if claim.claim_type != "从属权利要求" or claim.depends_on is None:
            continue
        chain = []
        cur = claim
        while cur and cur.claim_type == "从属权利要求" and cur.depends_on is not None:
            if cur.claim_number in chain:
                issues.append(QualityIssue(
                    severity="高", title=f"第{claim.claim_number}条存在循环依赖链",
                    detail=f"依赖链：{'→'.join(str(n) for n in chain)}→{cur.claim_number} 形成环。",
                    suggestion="检查从属权利要求的引用关系，消除循环。",
                    location=f"Step 4 / 第{claim.claim_number}条",
                ))
                break
            chain.append(cur.claim_number)
            cur = claim_map.get(cur.depends_on)

    return issues


def validate_abstract(abstract: PatentAbstract) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    if not abstract:
        issues.append(QualityIssue(
            severity="高", title="摘要为空",
            detail="专利摘要不能为空。", suggestion="请生成摘要。",
            location="Step 4 / 摘要",
        ))
        return issues

    text = abstract.abstract.strip()
    char_count = len(re.sub(r'\s', '', text))

    if char_count < 50:
        issues.append(QualityIssue(
            severity="高", title="摘要过短",
            detail=f"摘要仅{char_count}字，远低于200字下限。",
            suggestion="补充技术领域、技术问题、技术方案和效果。",
            location="Step 4 / 摘要",
        ))
    elif char_count < 200:
        issues.append(QualityIssue(
            severity="中", title="摘要偏短",
            detail=f"摘要{char_count}字，建议200-300字。",
            suggestion="补充关键技术效果或应用场景。",
            location="Step 4 / 摘要",
        ))
    elif char_count > 400:
        issues.append(QualityIssue(
            severity="中", title="摘要偏长",
            detail=f"摘要{char_count}字，超过300字上限。",
            suggestion="精简摘要，保留核心技术方案和效果。",
            location="Step 4 / 摘要",
        ))

    if not abstract.keywords or len(abstract.keywords) < 3:
        issues.append(QualityIssue(
            severity="中", title="关键词不足",
            detail=f"当前{len(abstract.keywords) if abstract.keywords else 0}个关键词，建议3-5个。",
            suggestion="补充与技术方案核心相关的关键词。",
            location="Step 4 / 摘要",
        ))

    return issues


def validate_specification(spec: PatentSpecification) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    if not spec:
        issues.append(QualityIssue(
            severity="高", title="说明书为空",
            detail="专利说明书不能为空。", suggestion="请生成说明书。",
            location="Step 5 / 说明书",
        ))
        return issues

    required_sections = {
        "technical_field": "技术领域",
        "background_art": "背景技术",
        "summary": "发明内容",
        "detailed_description": "具体实施方式",
    }

    for field, label in required_sections.items():
        content = getattr(spec, field, "").strip()
        if not content or len(content) < 10:
            issues.append(QualityIssue(
                severity="高", title=f"说明书缺少「{label}」",
                detail=f"「{label}」部分内容为空或过短。",
                suggestion=f"补充{label}部分。",
                location=f"Step 5 / {label}",
            ))

    detail = spec.detailed_description or ""
    example_count = len(re.findall(r'实施例\s*[一二三四五六七八九十\d]+', detail))
    if example_count < 2:
        issues.append(QualityIssue(
            severity="中", title="具体实施方式中实施例不足",
            detail=f"检测到{example_count}个实施例，建议至少2个。",
            suggestion="补充不同场景或参数下的实施例。",
            location="Step 5 / 具体实施方式",
        ))

    return issues


def validate_all(
    claims: ClaimSet = None,
    abstract: PatentAbstract = None,
    specification: PatentSpecification = None,
) -> ValidationResult:
    all_issues: List[QualityIssue] = []
    if claims:
        all_issues.extend(validate_claims(claims))
    if abstract:
        all_issues.extend(validate_abstract(abstract))
    if specification:
        all_issues.extend(validate_specification(specification))
    return ValidationResult(all_issues)
