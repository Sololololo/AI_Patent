"""Step 4: 五要素 + 摘要 + 权利要求"""

import streamlit as st
from core.output_schema import FiveElements, PatentAbstract, Claim, ClaimSet
from core.validator import validate_claims, validate_abstract
from ui.state import get_llm_client, save_current_session, lines_to_list


def render_step4():
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
        five_elements = st.session_state.five_elements
        abstract_result = st.session_state.abstract_result
        claims = st.session_state.claims

        # 合规校验
        validation_issues = validate_claims(claims) + validate_abstract(abstract_result)
        if validation_issues:
            with st.expander(f"⚠️ 合规校验（{len(validation_issues)} 个问题）", expanded=True):
                for idx, issue in enumerate(validation_issues, 1):
                    icon = "🔴" if issue.severity == "高" else "🟡"
                    st.markdown(f"{icon} **{issue.title}**：{issue.detail}")

        st.info("以下内容均可编辑，建议先人工修订再进入说明书和导出。")

        st.subheader("五要素分析（可编辑）")
        technical_problem = st.text_area("技术问题", value=five_elements.technical_problem, key="fe_problem", height=100)
        technical_solution = st.text_area("技术方案", value=five_elements.technical_solution, key="fe_solution", height=120)
        technical_effect = st.text_area("技术效果", value=five_elements.technical_effect, key="fe_effect", height=100)
        technical_features_raw = st.text_area(
            "技术特征（每行一条）",
            value="\n".join(five_elements.technical_features),
            key="fe_features",
            height=120,
        )
        app_scenarios_raw = st.text_area(
            "应用场景（每行一条）",
            value="\n".join(five_elements.application_scenarios),
            key="fe_scenarios",
            height=100,
        )

        st.subheader("专利摘要（可编辑）")
        abstract_text = st.text_area("摘要正文", value=abstract_result.abstract, key="abs_text", height=180)
        keywords_raw = st.text_input("关键词（用中文逗号分隔）", value="、".join(abstract_result.keywords), key="abs_keywords")

        st.subheader("权利要求书（可编辑）")
        edited_claims = []
        for i, claim in enumerate(claims.claims, 1):
            with st.expander(f"第 {i} 条", expanded=(i <= 2)):
                claim_type = st.selectbox(
                    "类型",
                    options=["独立权利要求", "从属权利要求"],
                    index=0 if claim.claim_type == "独立权利要求" else 1,
                    key=f"claim_type_{i}",
                )
                depends_on = None
                if claim_type == "从属权利要求":
                    depends_on = int(
                        st.number_input(
                            "从属于第几条",
                            min_value=1,
                            value=int(claim.depends_on) if claim.depends_on else max(1, i - 1),
                            step=1,
                            key=f"claim_dep_{i}",
                        )
                    )
                content = st.text_area("权利要求内容", value=claim.content, key=f"claim_content_{i}", height=140)
                edited_claims.append(
                    Claim(
                        claim_number=i,
                        claim_type=claim_type,
                        content=content.strip(),
                        depends_on=depends_on,
                    )
                )

        main_claim_summary = st.text_area(
            "独立权利要求核心概括",
            value=claims.main_claim_summary,
            key="main_claim_summary",
            height=100,
        )

        if st.button("💾 保存本页修改", key="save_step4_edits"):
            st.session_state.five_elements = FiveElements(
                technical_problem=technical_problem.strip(),
                technical_solution=technical_solution.strip(),
                technical_effect=technical_effect.strip(),
                technical_features=lines_to_list(technical_features_raw),
                application_scenarios=lines_to_list(app_scenarios_raw),
            )
            st.session_state.abstract_result = PatentAbstract(
                abstract=abstract_text.strip(),
                keywords=[k.strip() for k in keywords_raw.replace("，", "、").split("、") if k.strip()],
            )
            st.session_state.claims = ClaimSet(
                claims=edited_claims,
                main_claim_summary=main_claim_summary.strip(),
            )
            save_current_session()
            st.success("Step 4 修改已保存")
            st.rerun()

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
