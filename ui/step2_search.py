"""Step 2: 上传参考专利"""

import io
import streamlit as st
from ui.state import reset_results, get_llm_client


def render_step2():
    st.header("Step 2: 参考专利（推荐提供）")
    st.markdown("""
    上传 1-3 篇与你权利说明**相关、邻近**的已有专利（PDF 或直接粘贴文本），AI 会分析你的方案与它们的差异，更精准地挖掘创新点和评估新颖性。
    
    **强烈建议提供参考专利**——缺少对比基准时，创新性评估可信度会显著降低。
    """)
    st.warning("请尽量选择技术路线接近、问题域相邻的参考专利。参考专利的选择准确性、合法性和使用后果由用户自行负责。")

    reference_patent_texts = st.session_state.get("reference_patent_texts", [])

    for i, ref_text in enumerate(reference_patent_texts):
        with st.expander(f"参考专利 {i+1}", expanded=False):
            st.text_area("内容", value=ref_text[:500] + ("..." if len(ref_text) > 500 else ""),
                         height=100, disabled=True, key=f"ref_display_{i}")
            if st.button(f"删除参考专利 {i+1}", key=f"del_ref_{i}"):
                reference_patent_texts.pop(i)
                st.session_state.reference_patent_texts = reference_patent_texts
                st.rerun()

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
                    service = PatentSearchService(get_llm_client())
                    pdf_bytes = io.BytesIO(uploaded_file.getvalue())
                    extracted = service.extract_from_pdf(pdf_bytes)
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

    if not reference_patent_texts:
        st.warning("⚠️ 未提供参考专利，创新性评估可信度将降低。AI 需要自行推断最接近现有技术。")

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
