"""AI 专利助手 - Streamlit 主入口

多步骤向导式流程：
Step 1: 配置 LLM → Step 2: 输入技术描述+场景+参考专利 → Step 3: 创新点挖掘
→ Step 4: 五要素+摘要+权利要求 → Step 5: 说明书生成 → Step 6: 导出报告
"""

import sys
import os
import logging
import streamlit as st

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Settings, create_settings
from core.llm_client import LLMClient, LLMNotConfiguredError, LLMResponseParseError
from core.session_manager import SessionManager

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="AI 专利助手",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Session State 初始化
# ============================================================
def init_session_state():
    """初始化所有 session state 变量"""
    defaults = {
        "current_step": 1,
        "current_session_id": None,
        "has_unsaved_changes": False,
        # 用户输入
        "technical_description": "",
        "scenarios": [],
        "reference_patent_texts": [],
        "invention_name": "",
        # LLM 结果（逐步填充）
        "idea_mining_result": None,
        "five_elements": None,
        "abstract_result": None,
        "claims": None,
        "specification": None,
        # 导出
        "export_path": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


def get_llm_client() -> LLMClient:
    """获取或创建 LLM 客户端（基于当前侧边栏配置）"""
    settings = create_settings(
        api_url=st.session_state.get("api_url", "https://api.deepseek.com/v1/chat/completions"),
        api_key=st.session_state.get("api_key", ""),
        model_name=st.session_state.get("model_name", "deepseek-chat"),
        temperature=st.session_state.get("temperature", 0.7),
    )
    return LLMClient(settings)


def reset_results():
    """重置所有 LLM 结果（用户修改输入后需要重新生成）"""
    st.session_state.idea_mining_result = None
    st.session_state.five_elements = None
    st.session_state.abstract_result = None
    st.session_state.claims = None
    st.session_state.specification = None
    st.session_state.export_path = None


def get_session_manager() -> SessionManager:
    return SessionManager()


def save_current_session():
    """保存当前会话到磁盘"""
    if st.session_state.current_session_id is None:
        return
    mgr = get_session_manager()
    session = mgr.load(st.session_state.current_session_id)
    if session is None:
        return
    session.invention_name = st.session_state.invention_name
    session.technical_description = st.session_state.technical_description
    session.scenarios = st.session_state.scenarios
    session.reference_patent_texts = st.session_state.reference_patent_texts
    session.current_step = st.session_state.current_step
    session.idea_mining_result = (
        st.session_state.idea_mining_result.model_dump() if st.session_state.idea_mining_result else None
    )
    session.five_elements = (
        st.session_state.five_elements.model_dump() if st.session_state.five_elements else None
    )
    session.abstract_result = (
        st.session_state.abstract_result.model_dump() if st.session_state.abstract_result else None
    )
    session.claims = (
        st.session_state.claims.model_dump() if st.session_state.claims else None
    )
    session.specification = (
        st.session_state.specification.model_dump() if st.session_state.specification else None
    )
    mgr.save(session)


def load_session_to_state(session_id: str):
    """加载会话到 session_state"""
    mgr = get_session_manager()
    session = mgr.load(session_id)
    if session is None:
        return
    st.session_state.current_session_id = session.session_id
    st.session_state.current_step = session.current_step
    st.session_state.invention_name = session.invention_name
    st.session_state.technical_description = session.technical_description
    st.session_state.scenarios = session.scenarios
    st.session_state.reference_patent_texts = session.reference_patent_texts
    st.session_state.idea_mining_result = None
    st.session_state.five_elements = None
    st.session_state.abstract_result = None
    st.session_state.claims = None
    st.session_state.specification = None
    st.session_state.export_path = None
    if session.idea_mining_result:
        from core.output_schema import IdeaMiningResult
        st.session_state.idea_mining_result = IdeaMiningResult(**session.idea_mining_result)
    if session.five_elements:
        from core.output_schema import FiveElements
        st.session_state.five_elements = FiveElements(**session.five_elements)
    if session.abstract_result:
        from core.output_schema import PatentAbstract
        st.session_state.abstract_result = PatentAbstract(**session.abstract_result)
    if session.claims:
        from core.output_schema import ClaimSet
        st.session_state.claims = ClaimSet(**session.claims)
    if session.specification:
        from core.output_schema import PatentSpecification
        st.session_state.specification = PatentSpecification(**session.specification)


# ============================================================
# 侧边栏：会话管理 + LLM 配置
# ============================================================
with st.sidebar:
    st.header("📁 项目会话")

    mgr = get_session_manager()
    sessions = mgr.list_sessions()
    current_id = st.session_state.current_session_id

    if current_id:
        for session in sessions:
            if session.session_id == current_id:
                col_name, col_del = st.columns([4, 1])
                with col_name:
                    st.success(f"📄 {session.display_name}")
                with col_del:
                    if st.button("🗑️", key=f"del_session_{session.session_id}", help="删除此项目"):
                        mgr.delete(session.session_id)
                        st.session_state.current_session_id = None
                        st.session_state.current_step = 1
                        st.session_state.invention_name = ""
                        st.session_state.technical_description = ""
                        st.session_state.scenarios = []
                        st.session_state.reference_patent_texts = []
                        reset_results()
                        st.rerun()
                st.caption(f"进度：{session.progress()} | {session.step_label()}")

                col_save, col_new = st.columns(2)
                with col_save:
                    if st.button("💾 保存", key="save_session_btn"):
                        save_current_session()
                        st.success("已保存！")
                with col_new:
                    if st.button("➕ 新建项目", key="new_session_btn"):
                        reset_results()
                        st.session_state.current_session_id = None
                        st.session_state.current_step = 1
                        st.rerun()
    else:
        st.info("暂无打开的项目")
        if st.button("➕ 新建项目", key="new_session_empty", type="primary"):
            st.session_state.current_step = 1
            st.rerun()

    if sessions:
        with st.expander("📂 历史项目", expanded=False):
            for session in sessions[:10]:
                if session.session_id == current_id:
                    continue
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"{session.display_name[:20]}",
                        key=f"load_session_{session.session_id}",
                    ):
                        load_session_to_state(session.session_id)
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_hist_{session.session_id}"):
                        mgr.delete(session.session_id)
                        st.rerun()
                st.caption(f"  {session.progress()} | {session.updated_at[:10]}")

    st.divider()

    # LLM 配置
    st.header("⚙️ LLM 配置")

    api_url = st.text_input(
        "API URL",
        value=st.session_state.get("api_url", "https://api.deepseek.com/v1/chat/completions"),
        help="OpenAI 兼容的 API 地址，支持 DeepSeek / GLM / Qwen / OpenAI",
    )
    api_key = st.text_input(
        "API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
        help="你的 API 密钥",
    )
    model_name = st.text_input(
        "模型名称",
        value=st.session_state.get("model_name", "deepseek-chat"),
    )
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.get("temperature", 0.7),
        step=0.1,
    )

    st.session_state.api_url = api_url
    st.session_state.api_key = api_key
    st.session_state.model_name = model_name
    st.session_state.temperature = temperature

    # 检测配置状态
    llm = get_llm_client()
    if llm.is_configured:
        st.success("✅ LLM 已配置")
    else:
        st.error("❌ 请先配置 API Key")

    st.divider()

    # 进度指示器
    st.header("📍 当前进度")
    steps = [
        "1. 输入技术描述",
        "2. 上传参考专利",
        "3. 创新点挖掘",
        "4. 五要素 & 摘要 & 权利要求",
        "5. 专利说明书",
        "6. 导出报告",
    ]
    for i, step in enumerate(steps, 1):
        if i < st.session_state.current_step:
            st.markdown(f"✅ ~~{step}~~")
        elif i == st.session_state.current_step:
            st.markdown(f"**👉 {step}**")
        else:
            st.markdown(f"⬜ {step}")


# ============================================================
# 主内容区：分步骤向导
# ============================================================

st.title("📋 AI 专利助手")
st.caption("从技术描述到完整专利文档，逐步引导生成")

step = st.session_state.current_step


# ============================================================
# Step 1: 输入技术描述和场景
# ============================================================
if step == 1:
    st.header("Step 1: 描述你的技术方案")

    st.markdown("""
    请尽可能详细地描述你的技术方案。以下信息越充分，生成质量越高：
    - 你要解决什么问题？
    - 你的技术方案是什么？
    - 方案的关键技术特征有哪些？
    """)

    invention_name = st.text_input(
        "发明名称",
        value=st.session_state.invention_name,
        placeholder="例如：基于多模态大模型的智能文档审核方法",
    )

    technical_description = st.text_area(
        "技术描述",
        value=st.session_state.technical_description,
        height=250,
        placeholder="请详细描述你的技术方案，包括要解决的问题、采用的技术手段、预期的技术效果等...",
    )

    st.subheader("应用场景（必填，至少 1 个）")
    st.caption("提供具体的应用场景，帮助 AI 发散出更多创新点")

    scenarios = st.session_state.get("scenarios", [])
    # 显示已有场景
    for i, scene in enumerate(scenarios):
        col1, col2 = st.columns([9, 1])
        with col1:
            scenarios[i] = st.text_input(f"场景 {i+1}", value=scene, key=f"scene_{i}")
        with col2:
            if st.button("🗑️", key=f"del_scene_{i}"):
                scenarios.pop(i)
                st.rerun()

    # 添加新场景
    new_scene = st.text_input("添加新场景", key="new_scene", placeholder="例如：金融合同审核、医疗报告分析")
    if st.button("➕ 添加场景") and new_scene.strip():
        scenarios.append(new_scene.strip())
        st.session_state.scenarios = scenarios
        st.rerun()

    st.session_state.scenarios = scenarios

    # 下一步
    can_proceed = (
        invention_name.strip()
        and technical_description.strip()
        and len(scenarios) >= 1
    )

    if not can_proceed:
        st.info("请填写发明名称、技术描述和至少 1 个应用场景")

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("下一步 →", disabled=not can_proceed, type="primary"):
            st.session_state.invention_name = invention_name.strip()
            st.session_state.technical_description = technical_description.strip()
            if st.session_state.current_session_id is None:
                mgr = get_session_manager()
                session = mgr.create(
                    invention_name=invention_name.strip(),
                    technical_description=technical_description.strip(),
                    scenarios=st.session_state.scenarios,
                )
                st.session_state.current_session_id = session.session_id
            else:
                save_current_session()
            st.session_state.current_step = 2
            st.rerun()


# ============================================================
# Step 2: 上传参考专利（可选）
# ============================================================
elif step == 2:
    st.header("Step 2: 参考专利（可选）")
    st.markdown("""
    上传 1-3 篇与你技术方案相近的已有专利（PDF 或直接粘贴文本），AI 会分析你的方案与它们的差异，更精准地挖掘创新点和评估新颖性。
    
    没有参考专利也可以跳过，AI 会基于自身知识进行分析。
    """)

    reference_patent_texts = st.session_state.get("reference_patent_texts", [])

    # 已添加的参考专利
    for i, ref_text in enumerate(reference_patent_texts):
        with st.expander(f"参考专利 {i+1}", expanded=False):
            st.text_area("内容", value=ref_text[:500] + ("..." if len(ref_text) > 500 else ""),
                         height=100, disabled=True, key=f"ref_display_{i}")
            if st.button(f"删除参考专利 {i+1}", key=f"del_ref_{i}"):
                reference_patent_texts.pop(i)
                st.session_state.reference_patent_texts = reference_patent_texts
                st.rerun()

    # 上传 PDF
    if len(reference_patent_texts) < 3:
        st.subheader("上传专利 PDF")
        uploaded_file = st.file_uploader(
            "选择 PDF 文件",
            type=["pdf"],
            key="patent_pdf_uploader",
        )
        if uploaded_file and st.button("解析 PDF"):
            with st.spinner("正在解析 PDF..."):
                try:
                    from modules.patent_search import PatentSearchService
                    import io
                    service = PatentSearchService(get_llm_client())
                    pdf_bytes = io.BytesIO(uploaded_file.getvalue())
                    extracted = service.extract_from_pdf(pdf_bytes)
                    # 将提取的结构化信息转为文本存入
                    ref_text = (
                        f"标题：{extracted.title}\n"
                        f"技术领域：{extracted.technical_field}\n"
                        f"技术问题：{extracted.technical_problem}\n"
                        f"技术方案：{extracted.technical_solution}\n"
                        f"技术效果：{extracted.technical_effect}\n"
                        f"关键特征：{', '.join(extracted.key_features)}\n"
                        f"独立权利要求：{extracted.main_claim}"
                    )
                    reference_patent_texts.append(ref_text)
                    st.session_state.reference_patent_texts = reference_patent_texts
                    st.success("PDF 解析完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"解析失败：{e}")

        # 粘贴文本
        st.subheader("或直接粘贴专利文本")
        pasted_text = st.text_area(
            "粘贴专利文本",
            height=150,
            key="paste_patent_text",
            placeholder="将专利全文或摘要粘贴到这里...",
        )
        if st.button("添加文本") and pasted_text.strip():
            with st.spinner("正在提取专利信息..."):
                try:
                    from modules.patent_search import PatentSearchService
                    service = PatentSearchService(get_llm_client())
                    extracted = service.extract_from_text(pasted_text.strip())
                    ref_text = (
                        f"标题：{extracted.title}\n"
                        f"技术领域：{extracted.technical_field}\n"
                        f"技术问题：{extracted.technical_problem}\n"
                        f"技术方案：{extracted.technical_solution}\n"
                        f"技术效果：{extracted.technical_effect}\n"
                        f"关键特征：{', '.join(extracted.key_features)}\n"
                        f"独立权利要求：{extracted.main_claim}"
                    )
                    reference_patent_texts.append(ref_text)
                    st.session_state.reference_patent_texts = reference_patent_texts
                    st.success("提取完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"提取失败：{e}")
    else:
        st.info("已达到参考专利上限（3篇）")

    st.session_state.reference_patent_texts = reference_patent_texts

    # 导航
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("← 上一步"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        if st.button("开始挖掘 →", type="primary"):
            reset_results()
            st.session_state.current_step = 3
            st.rerun()


# ============================================================
# Step 3: 创新点挖掘
# ============================================================
elif step == 3:
    st.header("Step 3: 创新点挖掘")

    # 回显输入
    with st.expander("查看输入信息", expanded=False):
        st.markdown(f"**发明名称**：{st.session_state.invention_name}")
        st.markdown(f"**技术描述**：\n{st.session_state.technical_description}")
        st.markdown(f"**应用场景**：\n" + "\n".join(f"- {s}" for s in st.session_state.scenarios))
        ref_count = len(st.session_state.reference_patent_texts)
        st.markdown(f"**参考专利**：{ref_count} 篇" if ref_count else "**参考专利**：无")

    if st.session_state.idea_mining_result is None:
        if st.button("🚀 开始创新点挖掘", type="primary"):
            with st.spinner("AI 正在分析你的技术方案，挖掘创新点...（可能需要 1-2 分钟）"):
                try:
                    from modules.idea_mining import IdeaMiningPipeline
                    pipeline = IdeaMiningPipeline(get_llm_client())
                    result = pipeline.run(
                        technical_description=st.session_state.technical_description,
                        scenarios=st.session_state.scenarios,
                        reference_patents=st.session_state.reference_patent_texts or None,
                    )
                    st.session_state.idea_mining_result = result
                    save_current_session()
                    st.rerun()
                except LLMNotConfiguredError as e:
                    st.error(f"配置错误：{e}")
                except LLMResponseParseError as e:
                    st.error(f"AI 输出解析失败，请重试：{e}")
                except Exception as e:
                    st.error(f"发生错误：{e}")
    else:
        result = st.session_state.idea_mining_result

        # 创新点展示
        st.subheader(f"发现 {len(result.innovations)} 个创新点")
        for i, inn in enumerate(result.innovations, 1):
            level_color = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(inn.level, "⚪")
            with st.expander(f"{level_color} 创新点 {i}: {inn.title}", expanded=(i <= 3)):
                st.markdown(f"**类型**：{inn.innovation_type}")
                st.markdown(f"**描述**：{inn.description}")
                st.markdown(f"**技术价值**：{inn.technical_value}")
                st.markdown(f"**创新程度**：{inn.level}")

        # 新颖性评估
        st.subheader("新颖性评估")
        eval_ = result.evaluation
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("新颖性", f"{eval_.novelty_score}/10")
        col2.metric("创造性", f"{eval_.creativity_score}/10")
        col3.metric("市场价值", f"{eval_.market_value_score}/10")
        col4.metric("综合评分", f"{eval_.overall_score}/10")

        st.markdown(f"**技术进步性**：{eval_.technical_progress}")

        col_s, col_w = st.columns(2)
        with col_s:
            st.markdown("**优势**")
            for s in eval_.strengths:
                st.markdown(f"- {s}")
        with col_w:
            st.markdown("**不足/风险**")
            for w in eval_.weaknesses:
                st.markdown(f"- {w}")

        # 改进建议
        if result.suggestions:
            st.subheader("改进建议")
            for i, sug in enumerate(result.suggestions, 1):
                diff_color = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(sug.difficulty, "⚪")
                with st.expander(f"{diff_color} 建议 {i}: {sug.direction}"):
                    st.markdown(f"**建议**：{sug.suggestion}")
                    st.markdown(f"**预期效果**：{sug.expected_effect}")
                    st.markdown(f"**实施难度**：{sug.difficulty}")

        # 重新生成 or 下一步
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🔄 重新挖掘"):
                st.session_state.idea_mining_result = None
                st.rerun()
        with col2:
            if st.button("下一步 →", type="primary"):
                st.session_state.current_step = 4
                st.rerun()
        with col3:
            pass


# ============================================================
# Step 4: 五要素 + 摘要 + 权利要求
# ============================================================
elif step == 4:
    st.header("Step 4: 五要素分析 & 摘要 & 权利要求")

    need_generate = (
        st.session_state.five_elements is None
        or st.session_state.abstract_result is None
        or st.session_state.claims is None
    )

    if need_generate:
        if st.button("🚀 生成五要素、摘要和权利要求", type="primary"):
            from modules.structured_writing import StructuredWritingService
            service = StructuredWritingService(get_llm_client())
            result = st.session_state.idea_mining_result

            with st.spinner("正在分析五要素..."):
                try:
                    five_elements = service.analyze_five_elements(
                        st.session_state.technical_description,
                        result.innovations,
                    )
                    st.session_state.five_elements = five_elements
                except Exception as e:
                    st.error(f"五要素分析失败：{e}")
                    st.stop()

            with st.spinner("正在生成摘要..."):
                try:
                    abstract = service.generate_abstract(
                        st.session_state.technical_description,
                        five_elements,
                        result.innovations,
                    )
                    st.session_state.abstract_result = abstract
                except Exception as e:
                    st.error(f"摘要生成失败：{e}")
                    st.stop()

            with st.spinner("正在生成权利要求书..."):
                try:
                    claims = service.generate_claims(
                        st.session_state.invention_name,
                        st.session_state.technical_description,
                        five_elements,
                        result.innovations,
                        result.evaluation,
                    )
                    st.session_state.claims = claims
                except Exception as e:
                    st.error(f"权利要求生成失败：{e}")
                    st.stop()

            st.success("生成完成！")
            save_current_session()
            st.rerun()
    else:
        # 展示结果
        five_elements = st.session_state.five_elements
        abstract_result = st.session_state.abstract_result
        claims = st.session_state.claims

        # 五要素
        st.subheader("五要素分析")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**技术问题**")
            st.info(five_elements.technical_problem)
            st.markdown("**技术方案**")
            st.info(five_elements.technical_solution)
        with col2:
            st.markdown("**技术效果**")
            st.info(five_elements.technical_effect)
            st.markdown("**技术特征**")
            for feat in five_elements.technical_features:
                st.markdown(f"- {feat}")

        st.markdown("**应用场景**")
        for scene in five_elements.application_scenarios:
            st.markdown(f"- {scene}")

        # 摘要
        st.subheader("专利摘要")
        st.markdown(abstract_result.abstract)
        st.caption(f"关键词：{'、'.join(abstract_result.keywords)}")

        # 权利要求
        st.subheader("权利要求书")
        for claim in claims.claims:
            type_label = "【独立】" if claim.claim_type == "独立权利要求" else f"【从属于第{claim.depends_on}条】"
            st.markdown(f"**第 {claim.claim_number} 条** {type_label}")
            st.markdown(claim.content)
            st.divider()

        # 导航
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🔄 重新生成"):
                st.session_state.five_elements = None
                st.session_state.abstract_result = None
                st.session_state.claims = None
                st.rerun()
        with col2:
            if st.button("生成说明书 →", type="primary"):
                st.session_state.current_step = 5
                st.rerun()


# ============================================================
# Step 5: 专利说明书
# ============================================================
elif step == 5:
    st.header("Step 5: 专利说明书")

    if st.session_state.specification is None:
        if st.button("🚀 生成完整专利说明书", type="primary"):
            from modules.patent_generator import PatentGeneratorService
            service = PatentGeneratorService(get_llm_client())

            with st.spinner("正在生成专利说明书...（可能需要 2-3 分钟）"):
                try:
                    spec = service.generate_specification(
                        invention_name=st.session_state.invention_name,
                        technical_description=st.session_state.technical_description,
                        five_elements=st.session_state.five_elements,
                        innovations=st.session_state.idea_mining_result.innovations,
                        evaluation=st.session_state.idea_mining_result.evaluation,
                        claims=st.session_state.claims,
                        abstract_result=st.session_state.abstract_result,
                    )
                    st.session_state.specification = spec
                    st.success("说明书生成完成！")
                    save_current_session()
                    st.rerun()
                except Exception as e:
                    st.error(f"生成失败：{e}")
    else:
        spec = st.session_state.specification

        st.subheader(spec.title)

        with st.expander("技术领域", expanded=True):
            st.markdown(spec.technical_field)

        with st.expander("背景技术", expanded=True):
            st.markdown(spec.background_art)

        with st.expander("发明内容", expanded=True):
            st.markdown(spec.summary)

        with st.expander("具体实施方式", expanded=True):
            st.markdown(spec.detailed_description)

        with st.expander("附图说明", expanded=False):
            st.markdown(spec.brief_description_of_drawings)

        # 导航
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🔄 重新生成"):
                st.session_state.specification = None
                st.rerun()
        with col2:
            if st.button("导出报告 →", type="primary"):
                st.session_state.current_step = 6
                st.rerun()


# ============================================================
# Step 6: 导出报告
# ============================================================
elif step == 6:
    st.header("Step 6: 导出报告")

    result = st.session_state.idea_mining_result
    five_elements = st.session_state.five_elements
    abstract_result = st.session_state.abstract_result
    claims = st.session_state.claims
    specification = st.session_state.specification

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Markdown 报告")
        if st.button("导出 Markdown", type="primary"):
            from modules.presentation import ReportExporter
            exporter = ReportExporter()
            filepath = exporter.export_full_report(
                invention_name=st.session_state.invention_name,
                technical_description=st.session_state.technical_description,
                idea_mining_result=result,
                five_elements=five_elements,
                abstract_result=abstract_result,
                claims=claims,
                specification=specification,
            )
            st.session_state.export_path = filepath
            with open(filepath, "r", encoding="utf-8") as f:
                st.download_button(
                    "⬇️ 下载 Markdown",
                    data=f.read(),
                    file_name=os.path.basename(filepath),
                    mime="text/markdown",
                )

    with col2:
        st.subheader("📝 Word 文档")
        if st.button("导出 Word"):
            from modules.presentation import ReportExporter
            exporter = ReportExporter()
            try:
                filepath = exporter.export_word(
                    invention_name=st.session_state.invention_name,
                    technical_description=st.session_state.technical_description,
                    idea_mining_result=result,
                    five_elements=five_elements,
                    abstract_result=abstract_result,
                    claims=claims,
                    specification=specification,
                )
                with open(filepath, "rb") as f:
                    st.download_button(
                        "⬇️ 下载 Word",
                        data=f.read(),
                        file_name=os.path.basename(filepath),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
            except ImportError as e:
                st.error(str(e))

    st.divider()

    # 回到任意步骤修改
    st.subheader("返回修改")
    cols = st.columns(6)
    step_names = ["技术描述", "参考专利", "创新点", "五要素&摘要", "说明书", "导出"]
    for i, (col, name) in enumerate(zip(cols, step_names), 1):
        with col:
            if st.button(name, key=f"go_step_{i}"):
                st.session_state.current_step = i
                st.rerun()
