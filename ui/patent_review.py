"""专利审查与编辑界面"""

import streamlit as st
from core.validator import validate_claims, validate_abstract
from ui.state import save_current_session


def render_patent_review():
    """渲染专利审查和编辑界面"""
    st.header("📋 专利审查与编辑")
    
    if st.session_state.idea_mining_result is None:
        st.warning("请先生成专利内容")
        if st.button("← 返回快速开始"):
            st.session_state.current_step = 1
            st.rerun()
        return
    
    # 显示评分
    result = st.session_state.idea_mining_result
    if hasattr(result, 'evaluation') and result.evaluation:
        eval_ = result.evaluation
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("新颖性", f"{eval_.novelty_score}/10")
        col2.metric("创造性", f"{eval_.creativity_score}/10")
        col3.metric("市场价值", f"{eval_.market_value_score}/10")
        col4.metric("综合评分", f"{eval_.overall_score}/10")
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["💡 创新点", "📝 权利要求", "📄 说明书", "✨ 优化建议"])
    
    with tab1:
        render_innovations_review(result)
    
    with tab2:
        render_claims_review()
    
    with tab3:
        render_specification_review()
    
    with tab4:
        render_suggestions_review(result)
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← 重新生成", use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()
    
    with col2:
        if st.button("💾 保存修改", use_container_width=True):
            save_current_session()
            st.success("已保存！")
    
    with col3:
        if st.button("📤 导出专利 →", type="primary", use_container_width=True):
            st.session_state.current_step = 6
            st.rerun()


def render_innovations_review(result):
    """渲染创新点审查"""
    st.subheader("💡 创新点分析")
    
    if not hasattr(result, 'innovations') or not result.innovations:
        st.info("暂无创新点数据")
        return
    
    for i, inn in enumerate(result.innovations, 1):
        with st.expander(f"创新点 {i}: {inn.title if hasattr(inn, 'title') else '未命名'}", expanded=(i <= 2)):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                title = st.text_input("标题", value=inn.title if hasattr(inn, 'title') else "", key=f"inn_title_{i}")
                description = st.text_area("描述", value=inn.description if hasattr(inn, 'description') else "", height=100, key=f"inn_desc_{i}")
            
            with col2:
                level = st.selectbox("创新程度", ["高", "中", "低"], index=1, key=f"inn_level_{i}")
                if hasattr(inn, 'innovation_type'):
                    innovation_type = st.text_input("类型", value=inn.innovation_type, key=f"inn_type_{i}")
    
    st.markdown(f"**共 {len(result.innovations)} 个创新点**")


def render_claims_review():
    """渲染权利要求审查"""
    st.subheader("📝 权利要求书")
    
    claims = st.session_state.get("claims")
    if not claims:
        st.info("暂无权利要求数据")
        return
    
    # 验证
    validation_issues = validate_claims(claims)
    if validation_issues:
        with st.expander(f"⚠️ 合规问题（{len(validation_issues)}个）", expanded=True):
            for issue in validation_issues:
                icon = "🔴" if issue.severity == "高" else "🟡"
                st.markdown(f"{icon} **{issue.title}**：{issue.detail}")
    else:
        st.success("✅ 权利要求通过合规检查")
    
    # 渲染权利要求
    edited_claims = []
    for i, claim in enumerate(claims.claims if hasattr(claims, 'claims') else [], 1):
        with st.expander(f"第 {i} 条权利要求", expanded=(i <= 3)):
            claim_type = st.selectbox(
                "类型",
                ["独立权利要求", "从属权利要求"],
                index=0 if (hasattr(claim, 'claim_type') and claim.claim_type == "独立权利要求") else 1,
                key=f"claim_type_{i}"
            )
            
            depends_on = None
            if claim_type == "从属权利要求":
                depends_on = st.number_input(
                    "从属于第几条",
                    min_value=1,
                    value=int(claim.depends_on) if (hasattr(claim, 'depends_on') and claim.depends_on) else max(1, i-1),
                    key=f"claim_dep_{i}"
                )
            
            claim_text = st.text_area(
                "权利要求内容",
                value=claim.claim_text if hasattr(claim, 'claim_text') else str(claim),
                height=150,
                key=f"claim_text_{i}"
            )
    
    st.markdown(f"**共 {len(claims.claims) if hasattr(claims, 'claims') else 0} 条权利要求**")


def render_specification_review():
    """渲染说明书审查"""
    st.subheader("📄 专利说明书")
    
    spec_text = st.session_state.get("specification_text", "")
    if not spec_text:
        st.info("暂无说明书数据")
        
        if st.button("🔄 生成说明书"):
            with st.spinner("正在生成说明书..."):
                try:
                    from modules.patent_generator import PatentGenerator
                    llm = st.session_state.get("llm_client")
                    if llm:
                        gen = PatentGenerator(llm)
                        spec = gen.generate_specification(
                            st.session_state.technical_description,
                            st.session_state.five_elements,
                            st.session_state.claims,
                        )
                        st.session_state.specification_text = spec.content
                        save_current_session()
                        st.rerun()
                except Exception as e:
                    st.error(f"生成失败：{e}")
        return
    
    edited_spec = st.text_area(
        "说明书内容",
        value=spec_text,
        height=500,
        help="可在此处编辑说明书内容"
    )
    
    st.session_state.specification_text = edited_spec


def render_suggestions_review(result):
    """渲染优化建议"""
    st.subheader("✨ 优化建议")
    
    if not hasattr(result, 'suggestions') or not result.suggestions:
        st.info("暂无优化建议")
        return
    
    for i, sug in enumerate(result.suggestions, 1):
        with st.expander(f"建议 {i}: {sug.direction if hasattr(sug, 'direction') else '未命名'}"):
            st.markdown(f"**方向**: {sug.direction if hasattr(sug, 'direction') else ''}")
            st.markdown(f"**具体建议**: {sug.suggestion if hasattr(sug, 'suggestion') else ''}")
            st.markdown(f"**预期效果**: {sug.expected_effect if hasattr(sug, 'expected_effect') else ''}")
            
            difficulty = sug.difficulty if hasattr(sug, 'difficulty') else "中"
            icon = "🔴" if difficulty == "高" else ("🟡" if difficulty == "中" else "🟢")
            st.markdown(f"{icon} 实施难度: {difficulty}")
    
    if st.button("🔄 基于建议优化"):
        st.info("功能开发中...")
