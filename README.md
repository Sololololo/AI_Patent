# AI 专利助手 v2.0

从技术描述到完整专利文档，逐步引导生成。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用（API Key 在界面侧边栏配置）
cd ai_patent
streamlit run app.py
```

## 使用流程

**6 步向导，每一步都能回退修改：**

1. **输入技术描述**：详细描述你的技术方案，并提供至少 1 个应用场景
2. **上传参考专利**（可选）：上传 1-3 篇相似专利 PDF 或粘贴文本，AI 会分析差异
3. **创新点挖掘**：AI 基于场景发散创新点，评估新颖性，生成改进建议
4. **五要素 & 摘要 & 权利要求**：自动生成专利五要素分析、摘要和权利要求书
5. **专利说明书**：生成完整的专利说明书
6. **导出报告**：导出为 Markdown 或 Word 文档

## 支持的 LLM

任何 OpenAI 兼容的 API 均可使用，在侧边栏配置即可切换：

| 提供商 | API URL | 模型名称 |
|--------|---------|----------|
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` | `deepseek-chat` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | `glm-4` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | `qwen-plus` |
| OpenAI | `https://api.openai.com/v1/chat/completions` | `gpt-4o` |

## 项目结构

```
ai_patent/
├── app.py                  # Streamlit 主入口（6步向导）
├── config.py               # 统一配置管理（Pydantic Settings）
├── core/                   # 核心基础设施
│   ├── llm_client.py       # LLM 客户端（结构化输出 + JSON Mode）
│   ├── output_schema.py    # Pydantic 输出模型定义
│   └── prompt_loader.py    # Prompt 模板加载器
├── modules/                # 业务模块
│   ├── idea_mining/        # 创新点挖掘流水线（3步串联）
│   ├── structured_writing/ # 五要素 → 摘要 → 权利要求
│   ├── patent_generator/   # 专利说明书生成
│   ├── patent_search/      # 参考专利 PDF/文本解析
│   └── presentation/       # 报告导出（Markdown + Word）
├── prompts/                # Prompt 模板（8个 Markdown 文件）
└── output/                 # 导出文件存放目录
```

## 与原项目对比

| 维度 | 原项目 (v1) | 重构后 (v2) |
|------|-------------|-------------|
| LLM 调用 | LangChain LLMChain（已废弃） | openai SDK 直调 |
| 输出解析 | 逐行字符串匹配 | Pydantic 结构化模型 + JSON Mode |
| 配置管理 | 全局单例，改配置需重启 | 依赖注入，侧边栏改了立刻生效 |
| 代码重复 | 6 处相同 _init_llm() | 统一 LLMClient |
| 降级策略 | 返回假数据 | 抛异常 + UI 明确提示 |
| 专利数据 | 不可用的 CNIPA 爬虫 | 用户上传参考专利 |
| 创新挖掘 | 三步独立无串联 | 三步串联流水线 |
| 用户输入 | 只需技术描述 | 技术描述 + 场景 + 参考专利 |
| Prompt 管理 | 硬编码在代码中 | 外置 Markdown 文件 |
| 依赖数量 | 30+ 个（含未使用的） | 6 个核心依赖 |
