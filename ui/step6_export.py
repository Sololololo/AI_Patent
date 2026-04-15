"""Step 6: 导出报告"""

import os
import streamlit as st


def render_step6():
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

    st.subheader("返回修改")
    cols = st.columns(6)
    step_names = ["权利说明", "参考专利", "创新点", "五要素&摘要", "说明书", "导出"]
    for i, (col, name) in enumerate(zip(cols, step_names), 1):
        with col:
            if st.button(name, key=f"go_step_{i}"):
                st.session_state.current_step = i
                st.rerun()
