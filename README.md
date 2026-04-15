# AI 专利助手 v2.0

从技术描述到完整专利文档，逐步引导生成。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用（API Key 在界面侧边栏配置）
streamlit run app.py
```

## 使用流程

```mermaid
flowchart TD
    subgraph 输入层["📥 Step 1-2: 输入"]
        A1["输入技术描述\n+ 应用场景"]
        A2["上传参考专利\n(推荐, PDF 或粘贴)"]
        A1 --> A2
    end

    subgraph 创新层["💡 Step 3: 创新点挖掘"]
        B1["创新点检测\n场景发散 + 跨域启发"]
        B1a{"反模式过滤\n8条AI领域反模式"}
        B2["生成者-审查者自博弈\n质疑 → 反驳 → 过滤"]
        B3["结构化新颖性推理\n5步推理链强制说理"]
        B4["改进建议生成"]
        B1 --> B1a --> B2 --> B3 --> B4
    end

    subgraph 评分层["🧮 V2 评分引擎"]
        S1["输入质量\n长度+术语密度+场景"]
        S2["语义一致性\njieba+LLM语义评分"]
        S3["可验证性\n量化指标+边界条件"]
        S4["校准输出\n原始分+可信度+校准分"]
        S1 --> S4
        S2 --> S4
        S3 --> S4
    end

    subgraph 写作层["✍️ Step 4: 结构化写作"]
        C1["五要素分析\n问题/方案/效果/特征/场景"]
        C2["专利摘要生成\n关键词提取"]
        C3["权利要求书撰写\n独立 + 从属权利要求"]
        C4{"合规校验\n从属关系/字数/完整性"}
        C1 --> C2 --> C3 --> C4
    end

    subgraph 生成层["📄 Step 5: 说明书"]
        D1["完整专利说明书生成\n技术领域/背景/实施方式"]
        D2{"说明书合规校验\n各节完整性+实施例数量"}
        D1 --> D2
    end

    subgraph 导出层["💾 Step 6: 导出"]
        E1["Markdown 报告"]
        E2["Word 文档"]
    end

    A2 --> B1
    B4 --> S4
    S4 --> C1
    C4 --> D1
    D2 --> E1
    D2 --> E2

    style 输入层 fill:#e1f5fe
    style 创新层 fill:#fff3e0
    style 评分层 fill:#fff9c4
    style 写作层 fill:#e8f5e9
    style 生成层 fill:#fce4ec
    style 导出层 fill:#f3e5f5
```

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
├── app.py                  # Streamlit 主入口（55行，调用ui模块）
├── config.py               # 统一配置管理（Pydantic Settings）
├── core/                   # 核心基础设施
│   ├── llm_client.py       # LLM 客户端（结构化输出 + JSON Mode）
│   ├── output_schema.py    # Pydantic 输出模型定义
│   ├── prompt_loader.py    # Prompt 模板加载器
│   ├── session_manager.py  # 会话持久化管理
│   ├── scoring.py          # V2 评分引擎（jieba + LLM语义评分）
│   ├── validator.py        # 专利合规校验（纯规则）
│   └── anti_patterns.py    # AI领域反模式库（8条规则）
├── modules/                # 业务模块
│   ├── idea_mining/        # 创新点挖掘流水线（含自博弈机制）
│   ├── structured_writing/ # 五要素 → 摘要 → 权利要求
│   ├── patent_generator/   # 专利说明书生成
│   ├── patent_search/      # 参考专利 PDF/文本解析
│   └── presentation/       # 报告导出（Markdown + Word）
├── ui/                     # Streamlit UI 模块
│   ├── state.py            # Session State 管理
│   ├── sidebar.py          # 侧边栏（会话+配置+评分+进度）
│   ├── step1_input.py      # Step 1: 输入权利说明
│   ├── step2_search.py     # Step 2: 上传参考专利
│   ├── step3_mining.py     # Step 3: 创新点挖掘
│   ├── step4_writing.py    # Step 4: 五要素+摘要+权利要求
│   ├── step5_spec.py       # Step 5: 专利说明书
│   └── step6_export.py     # Step 6: 导出报告
├── prompts/                # Prompt 模板（8个 Markdown 文件）
├── sessions/               # 会话数据存储目录
└── output/                 # 导出文件存放目录
```

## 项目会话管理

每个专利项目都会自动保存到 `sessions/` 目录，支持：

- **自动保存**：每步生成完成后自动保存
- **手动保存**：侧边栏随时点击"💾 保存"
- **续写**：关闭页面后，下次打开可从历史项目中继续
- **历史记录**：保留最近 10 个项目，可随时加载或删除

```mermaid
flowchart LR
    A["📝 新建项目"] --> B["💻 填写信息"]
    B --> C["🤖 AI 生成"]
    C -->|"自动保存"| D["💾 本地存储"]
    D -->|"随时"| E["📂 加载历史"]
    E --> B
```

## 版本对比

| 维度 | v1 | v2 | v3 (本次) |
|------|----|----|-----------|
| LLM 调用 | LangChain LLMChain（已废弃） | openai SDK 直调 | 同v2 |
| 输出解析 | 逐行字符串匹配 | Pydantic + JSON Mode | 同v2 |
| 创新挖掘 | 三步独立无串联 | 三步串联流水线 | **+自博弈+反模式+跨域启发** |
| 新颖性评估 | LLM给个分数 | LLM给个分数 | **5步推理链强制说理** |
| 一致性评分 | Jaccard词汇重叠 | Jaccard词汇重叠 | **jieba+LLM语义评分** |
| 合规校验 | 无 | 无 | **纯规则：从属关系/字数/完整性** |
| 参考专利 | 可选，无强制对比 | 可选，无强制对比 | **推荐，强制逐条对比差异** |
| app.py | 1012行单文件 | 1012行单文件 | **55行+8个ui模块** |
| 术语提取 | 正则匹配 | 正则匹配 | **jieba关键词提取** |
| 依赖数量 | 30+ 个 | 7 个 | 8 个（+jieba） |
