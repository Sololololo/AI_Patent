"""AI 专利助手 - Prompt 模板加载器

所有 prompt 模板存放在 prompts/ 目录下的 Markdown 文件中，
本模块负责加载模板。模板中的变量占位符使用 {{variable_name}} 格式，
但实际变量填充在业务代码中完成（通过字符串拼接 user_prompt）。
模板仅用作 system_prompt 加载，保持 prompt 内容与代码解耦。
"""

import os

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def load_prompt(filename: str) -> str:
    """加载 prompt 模板文件

    Args:
        filename: prompts/ 目录下的文件名，如 "innovation_detection.md"

    Returns:
        模板内容字符串
    """
    filepath = os.path.join(PROMPTS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
