"""Step 5: 专利说明书"""

import streamlit as st
from core.output_schema import PatentSpecification
from core.validator import validate_specification
from ui.state import get_llm_client, save_current_session


def render_step5():
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

        # 合规校验
        spec_issues = validate_specification(spec)
        if spec_issues:
            with st.expander(f"⚠️ 说明书合规校验（{len(spec_issues)} 个问题）", expanded=True):
                for idx, issue in enumerate(spec_issues, 1):
                    icon = "🔴" if issue.severity == "高" else "🟡"
                    st.markdown(f"{icon} **{issue.title}**：{issue.detail}")

        st.info("说明书支持在线编辑，保存后再导出。")
        title = st.text_input("发明名称", value=spec.title, key="spec_title")
        abstract = st.text_area("摘要", value=spec.abstract, key="spec_abstract", height=120)
        technical_field = st.text_area("技术领域", value=spec.technical_field, key="spec_field", height=100)
        background_art = st.text_area("背景技术", value=spec.background_art, key="spec_bg", height=180)
        summary = st.text_area("发明内容", value=spec.summary, key="spec_summary", height=180)
        detailed_description = st.text_area(
            "具体实施方式",
            value=spec.detailed_description,
            key="spec_detail",
            height=320,
        )
        drawings = st.text_area(
            "附图说明",
            value=spec.brief_description_of_drawings,
            key="spec_drawings",
            height=100,
        )

        if st.button("💾 保存本页修改", key="save_step5_edits"):
            st.session_state.specification = PatentSpecification(
                title=title.strip(),
                abstract=abstract.strip(),
                technical_field=technical_field.strip(),
                background_art=background_art.strip(),
                summary=summary.strip(),
                detailed_description=detailed_description.strip(),
                brief_description_of_drawings=drawings.strip() or "本发明无附图",
            )
            save_current_session()
            st.success("Step 5 修改已保存")
            st.rerun()

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🔄 重新生成"):
                st.session_state.specification = None
                st.rerun()
        with col2:
            if st.button("导出报告 →", type="primary"):
                st.session_state.current_step = 6
                st.rerun()
