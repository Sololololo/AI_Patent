"""Step 1: 输入权利说明和场景"""

import streamlit as st
from ui.state import get_session_manager, save_current_session, reset_results


def render_step1():
    st.header("Step 1: 填写权利说明")

    st.markdown("""
    请尽可能详细填写你的**权利说明**。以下信息越充分，生成质量越高：
    - 你主张保护的核心技术点是什么？
    - 权利边界与关键限定条件是什么？
    - 可量化的技术效果或性能指标是什么？
    """)

    invention_name = st.text_input(
        "发明名称",
        value=st.session_state.invention_name,
        placeholder="例如：基于多模态大模型的智能文档审核方法",
    )

    technical_description = st.text_area(
        "权利说明",
        value=st.session_state.technical_description,
        height=250,
        placeholder="请详细填写权利说明，包括核心权利点、边界条件、关键技术特征、预期技术效果等...",
    )

    st.subheader("应用场景（必填，至少 1 个）")
    st.caption("提供具体的应用场景，帮助 AI 发散出更多创新点")

    scenarios = st.session_state.get("scenarios", [])
    for i, scene in enumerate(scenarios):
        col1, col2 = st.columns([9, 1])
        with col1:
            scenarios[i] = st.text_input(f"场景 {i+1}", value=scene, key=f"scene_{i}")
        with col2:
            if st.button("🗑️", key=f"del_scene_{i}"):
                scenarios.pop(i)
                st.rerun()

    new_scene = st.text_input("添加新场景", key="new_scene", placeholder="例如：金融合同审核、医疗报告分析")
    if st.button("➕ 添加场景") and new_scene.strip():
        scenarios.append(new_scene.strip())
        st.session_state.scenarios = scenarios
        st.rerun()

    st.session_state.scenarios = scenarios

    can_proceed = (
        invention_name.strip()
        and technical_description.strip()
        and len(scenarios) >= 1
    )

    if not can_proceed:
        st.info("请填写发明名称、权利说明和至少 1 个应用场景")

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
