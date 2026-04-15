"""Step 3: 创新点挖掘"""

import streamlit as st
from core.output_schema import Innovation, NoveltyEvaluation, Suggestion, IdeaMiningResult
from core.llm_client import LLMNotConfiguredError, LLMResponseParseError
from core.scoring import apply_quality_scoring
from ui.state import get_llm_client, save_current_session, lines_to_list


def _apply_v2_scoring(result: IdeaMiningResult) -> IdeaMiningResult:
    return apply_quality_scoring(
        result=result,
        technical_description=st.session_state.technical_description,
        scenarios=st.session_state.scenarios,
        reference_patents=st.session_state.reference_patent_texts or None,
        strictness=st.session_state.get("score_strictness", "标准"),
        llm_client=get_llm_client(),
    )


def render_step3():
    st.header("Step 3: 创新点挖掘")

    with st.expander("查看输入信息", expanded=False):
        st.markdown(f"**发明名称**：{st.session_state.invention_name}")
        st.markdown(f"**权利说明**：\n{st.session_state.technical_description}")
        st.markdown(f"**应用场景**：\n" + "\n".join(f"- {s}" for s in st.session_state.scenarios))
        ref_count = len(st.session_state.reference_patent_texts)
        st.markdown(f"**参考专利**：{ref_count} 篇" if ref_count else "**参考专利**：无")

    if st.session_state.idea_mining_result is None:
        if st.button("🚀 开始创新点挖掘", type="primary"):
            with st.spinner("AI 正在分析你的权利说明，挖掘创新点...（可能需要 2-3 分钟，含自博弈审查）"):
                try:
                    from modules.idea_mining import IdeaMiningPipeline
                    pipeline = IdeaMiningPipeline(get_llm_client())
                    result = pipeline.run(
                        technical_description=st.session_state.technical_description,
                        scenarios=st.session_state.scenarios,
                        reference_patents=st.session_state.reference_patent_texts or None,
                    )
                    result = _apply_v2_scoring(result)
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

        st.info("以下内容均可直接编辑，修改后点击\"保存本页修改\"。支持按当前严格度进行 V2 重评分。")

        breakdown = result.score_breakdown
        if breakdown:
            st.subheader("V2 评分拆解")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            raw_overall = breakdown.raw_scores.get("overall_score", result.evaluation.overall_score)
            adjusted_overall = breakdown.adjusted_scores.get("overall_score", result.evaluation.overall_score)
            col_m1.metric("原始综合分", f"{raw_overall}/10")
            col_m2.metric("可信度", f"{round(breakdown.trust_score * 10, 1)}/10")
            col_m3.metric("校准综合分", f"{adjusted_overall}/10")
            col_m4.metric("评分因子", f"{breakdown.final_factor:.3f}")

            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.progress(float(breakdown.input_quality), text=f"输入质量 {breakdown.input_quality:.2f}")
            col_s2.progress(float(breakdown.consistency), text=f"一致性 {breakdown.consistency:.2f}")
            col_s3.progress(float(breakdown.verifiability), text=f"可验证性 {breakdown.verifiability:.2f}")

            if breakdown.issues:
                with st.expander(f"问题清单（{len(breakdown.issues)}）", expanded=False):
                    for idx, issue in enumerate(breakdown.issues, 1):
                        st.markdown(
                            f"**{idx}. [{issue.severity}] {issue.title}**\n\n"
                            f"- 详情：{issue.detail}\n"
                            f"- 建议：{issue.suggestion}\n"
                            f"- 位置：{issue.location}"
                        )
            st.caption(breakdown.summary)
        else:
            st.warning("当前结果尚未生成 V2 评分拆解，请点击\"V2 重评分\"。")

        st.subheader(f"创新点（共 {len(result.innovations)} 条）")
        edited_innovations = []
        for i, inn in enumerate(result.innovations, 1):
            with st.expander(f"创新点 {i}: {inn.title}", expanded=(i <= 2)):
                title = st.text_input("标题", value=inn.title, key=f"inn_title_{i}")
                innovation_type = st.text_input("类型", value=inn.innovation_type, key=f"inn_type_{i}")
                level = st.selectbox(
                    "创新程度",
                    options=["高", "中", "低"],
                    index=["高", "中", "低"].index(str(inn.level)) if str(inn.level) in ["高", "中", "低"] else 1,
                    key=f"inn_level_{i}",
                )
                description = st.text_area("描述", value=inn.description, key=f"inn_desc_{i}", height=120)
                technical_value = st.text_area("技术价值", value=inn.technical_value, key=f"inn_value_{i}", height=90)
                edited_innovations.append(
                    Innovation(
                        title=title.strip(),
                        innovation_type=innovation_type.strip(),
                        level=level,
                        description=description.strip(),
                        technical_value=technical_value.strip(),
                    )
                )

        st.subheader("新颖性评估（可编辑）")
        eval_ = result.evaluation
        col1, col2, col3, col4 = st.columns(4)
        novelty_score = int(col1.number_input("新颖性", min_value=1, max_value=10, value=int(eval_.novelty_score), step=1))
        creativity_score = int(col2.number_input("创造性", min_value=1, max_value=10, value=int(eval_.creativity_score), step=1))
        market_value_score = int(col3.number_input("市场价值", min_value=1, max_value=10, value=int(eval_.market_value_score), step=1))
        overall_score = int(col4.number_input("综合评分", min_value=1, max_value=10, value=int(eval_.overall_score), step=1))
        technical_progress = st.text_area("技术进步性", value=eval_.technical_progress, key="eval_progress", height=100)
        similarity_analysis = st.text_area("相似性分析", value=eval_.similarity_analysis, key="eval_similarity", height=80)
        strengths_raw = st.text_area("优势（每行一条）", value="\n".join(eval_.strengths), key="eval_strengths", height=110)
        weaknesses_raw = st.text_area("不足/风险（每行一条）", value="\n".join(eval_.weaknesses), key="eval_weaknesses", height=110)

        edited_evaluation = NoveltyEvaluation(
            novelty_score=novelty_score,
            creativity_score=creativity_score,
            market_value_score=market_value_score,
            overall_score=overall_score,
            technical_progress=technical_progress.strip(),
            strengths=lines_to_list(strengths_raw),
            weaknesses=lines_to_list(weaknesses_raw),
            similarity_analysis=similarity_analysis.strip() or "无参考专利",
        )

        st.subheader("改进建议（可编辑）")
        edited_suggestions = []
        for i, sug in enumerate(result.suggestions, 1):
            with st.expander(f"建议 {i}: {sug.direction}", expanded=False):
                direction = st.text_input("改进方向", value=sug.direction, key=f"sug_direction_{i}")
                suggestion = st.text_area("具体建议", value=sug.suggestion, key=f"sug_text_{i}", height=120)
                expected_effect = st.text_area("预期效果", value=sug.expected_effect, key=f"sug_effect_{i}", height=90)
                difficulty = st.selectbox(
                    "实施难度",
                    options=["高", "中", "低"],
                    index=["高", "中", "低"].index(str(sug.difficulty)) if str(sug.difficulty) in ["高", "中", "低"] else 1,
                    key=f"sug_diff_{i}",
                )
                edited_suggestions.append(
                    Suggestion(
                        direction=direction.strip(),
                        suggestion=suggestion.strip(),
                        expected_effect=expected_effect.strip(),
                        difficulty=difficulty,
                    )
                )

        if st.button("💾 保存本页修改", key="save_step3_edits"):
            updated_result = IdeaMiningResult(
                innovations=edited_innovations,
                evaluation=edited_evaluation,
                suggestions=edited_suggestions,
            )
            st.session_state.idea_mining_result = _apply_v2_scoring(updated_result)
            save_current_session()
            st.success("Step 3 修改已保存")
            st.rerun()

        col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
        with col1:
            if st.button("🔄 重新挖掘"):
                st.session_state.idea_mining_result = None
                st.rerun()
        with col2:
            if st.button("🧮 V2 重评分"):
                st.session_state.idea_mining_result = _apply_v2_scoring(result)
                save_current_session()
                st.success("已按当前严格度完成重评分")
                st.rerun()
        with col3:
            if st.button("下一步 →", type="primary"):
                st.session_state.current_step = 4
                st.rerun()
