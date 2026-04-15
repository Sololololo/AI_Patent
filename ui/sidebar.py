"""侧边栏：会话管理 + LLM 配置 + 评分引擎 + 进度"""

import streamlit as st
from ui.state import (
    get_session_manager,
    save_current_session,
    start_new_project,
    reset_results,
    load_session_to_state,
    get_llm_client,
)


def render_sidebar():
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
                            start_new_project()
                            st.rerun()
        else:
            st.info("暂无打开的项目")
            if st.button("➕ 新建项目", key="new_session_empty", type="primary"):
                start_new_project()
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

        st.header("⚙️ LLM 配置")
        api_url = st.text_input(
            "API URL",
            value=st.session_state.get("api_url", "https://api.deepseek.com/v1/chat/completions"),
            help="OpenAI 兼容的 API 地址",
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

        llm = get_llm_client()
        if llm.is_configured:
            st.success("✅ LLM 已配置")
        else:
            st.error("❌ 请先配置 API Key")

        st.divider()
        st.header("🧮 V2 评分引擎")
        score_strictness = st.selectbox(
            "评分严格度",
            options=["严格", "标准", "宽松"],
            index=["严格", "标准", "宽松"].index(st.session_state.get("score_strictness", "标准")),
            help="严格度越高，对低质量输入降权越明显。",
        )
        st.session_state.score_strictness = score_strictness
        st.caption("评分展示：原始分 + 可信度 + 校准分（可重评分）")
        with st.expander("核心计算原则", expanded=False):
            st.markdown(
                "- 证据优先：输入质量、一致性、可验证性共同决定可信度。\n"
                "- 低信息保护：当权利说明或可验证性过低时，综合分触发硬上限封顶。\n"
                "- 严格度单调：严格 > 标准 > 宽松，容错逐级提高。\n"
                "- 可解释输出：保留原始分，并展示校准因子与问题清单。"
            )

        st.divider()
        st.header("📍 当前进度")
        steps = [
            "1. 输入权利说明",
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
