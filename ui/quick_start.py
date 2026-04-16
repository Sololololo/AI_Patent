"""快速生成模式 - 一键端到端生成完整专利"""

import streamlit as st
from ui.state import get_llm_client, save_current_session, get_session_manager


def render_quick_start():
    """渲染快速开始界面"""
    st.header("🚀 快速生成专利")
    st.markdown("""
    **简单3步，获得完整专利文档：**
    1. 输入你的技术想法
    2. 点击生成
    3. 查看和导出结果
    """)
    
    # 创建两列布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        invention_name = st.text_input(
            "🎯 发明名称",
            placeholder="例如：基于深度学习的智能图像识别系统",
            help="用简洁的语言描述你的发明"
        )
        
        technical_description = st.text_area(
            "📝 技术描述",
            height=250,
            placeholder="""详细描述你的技术方案，包括：
- 核心技术原理
- 关键技术特征
- 预期达到的技术效果
- 解决的技术问题

例如：开发了一种基于注意力机制和多尺度特征融合的图像识别方法，通过引入轻量级卷积块和特征金字塔网络，实现了在保持高精度的同时大幅降低计算复杂度。该方法适用于移动端实时图像处理场景。""",
        )
        
        # 高级选项折叠
        with st.expander("⚙️ 高级选项（可选）", expanded=False):
            scenarios_input = st.text_area(
                "应用场景",
                placeholder="输入应用场景，每行一个（可选）\n例如：\n智能安防监控\n自动驾驶感知\n医疗影像诊断",
                height=100,
            )
            
            reference_patents = st.text_area(
                "参考专利",
                placeholder="粘贴参考专利文本，每篇用---分隔（可选）",
                height=150,
            )
    
    with col2:
        st.markdown("### 💡 生成选项")
        quality_level = st.select_slider(
            "质量要求",
            options=["基础", "标准", "高质量"],
            value="标准",
            help="基础：快速生成\n标准：符合专利法要求\n高质量：专业级专利文档",
        )
        
        st.markdown("### 📋 将生成")
        st.markdown("""
        ✅ 摘要  
        ✅ 权利要求书  
        ✅ 说明书  
        ✅ 创新点分析  
        ✅ 新颖性评估
        """)
    
    # 验证输入
    can_generate = bool(invention_name.strip() and technical_description.strip())
    
    if not can_generate:
        st.info("💡 请填写发明名称和技术描述")
    
    # 生成按钮
    col_gen1, col_gen2, col_gen3 = st.columns([3, 1, 1])
    
    with col_gen1:
        if st.button("🎯 开始生成完整专利", type="primary", disabled=not can_generate, use_container_width=True):
            _handle_generation(
                invention_name,
                technical_description,
                scenarios_input,
                reference_patents,
                quality_level,
            )
    
    with col_gen2:
        if st.button("📂 加载历史", use_container_width=True):
            st.session_state.current_step = -1
            st.rerun()
    
    with col_gen3:
        if st.button("📊 专家模式", use_container_width=True):
            st.info("💡 专家模式开发中，敬请期待！")


def _handle_generation(
    invention_name: str,
    technical_description: str,
    scenarios_input: str,
    reference_patents: str,
    quality_level: str,
):
    """处理生成请求"""
    with st.spinner("🤖 AI正在生成完整专利文档（这可能需要1-2分钟）..."):
        try:
            from modules.end_to_end import EndToEndPatentGenerator
            
            llm = get_llm_client()
            generator = EndToEndPatentGenerator(llm)
            
            # 解析场景
            scenarios = []
            if scenarios_input.strip():
                scenarios = [s.strip() for s in scenarios_input.split("\n") if s.strip()]
            
            # 解析参考专利
            references = []
            if reference_patents.strip():
                references = [r.strip() for r in reference_patents.split("---") if r.strip()]
            
            # 生成专利
            result = generator.generate_complete_patent(
                invention_name=invention_name.strip(),
                technical_description=technical_description.strip(),
                scenarios=scenarios,
                reference_patents=references if references else None,
                quality_level=quality_level,
            )
            
            # 保存到session
            st.session_state.idea_mining_result = result
            st.session_state.five_elements = _extract_five_elements(result)
            st.session_state.abstract_result = _extract_abstract(result)
            st.session_state.claims = _extract_claims(result)
            st.session_state.specification_text = _extract_specification(result)
            st.session_state.invention_name = invention_name.strip()
            st.session_state.technical_description = technical_description.strip()
            st.session_state.scenarios = scenarios
            
            # 创建会话
            if st.session_state.get("current_session_id") is None:
                mgr = get_session_manager()
                session = mgr.create(
                    invention_name=invention_name.strip(),
                    technical_description=technical_description.strip(),
                    scenarios=scenarios,
                )
                st.session_state.current_session_id = session.session_id
            
            save_current_session()
            
            st.success("✅ 生成完成！")
            
            # 显示摘要
            if result.evaluation:
                st.balloons()
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("新颖性", f"{result.evaluation.novelty_score}/10")
                col2.metric("创造性", f"{result.evaluation.creativity_score}/10")
                col3.metric("市场价值", f"{result.evaluation.market_value_score}/10")
                col4.metric("综合评分", f"{result.evaluation.overall_score}/10")
            
            # 自动跳转到审查页面
            st.session_state.current_step = 0
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 生成失败：{str(e)}")
            st.info("💡 请检查API配置是否正确，或稍后重试")


def _extract_five_elements(result):
    """从结果中提取五要素"""
    if hasattr(result, 'innovations') and result.innovations:
        innovations_text = "\n".join([
            f"- {inn.title}: {inn.description}" 
            for inn in result.innovations[:3]
        ])
        
        from core.output_schema import FiveElements
        return FiveElements(
            technical_problem="见创新点描述",
            technical_solution=innovations_text,
            technical_effect="具有显著的技术进步",
            technical_features=[inn.title for inn in result.innovations[:5]],
            application_scenarios=st.session_state.get("scenarios", []),
        )
    return None


def _extract_abstract(result):
    """从结果中提取摘要"""
    if hasattr(result, 'evaluation'):
        from core.output_schema import PatentAbstract
        return PatentAbstract(
            abstract=f"本发明提供了一种{result.innovations[0].title if result.innovations else '技术方案'}，具有{result.evaluation.technical_progress}的特点。",
            keywords=["技术创新", "专利申请"],
        )
    return None


def _extract_claims(result):
    """从结果中提取权利要求"""
    # 权利要求已经在result中生成了
    # 这里返回None，让审查界面显示结果中的claims
    return getattr(result, 'claims', None) or st.session_state.get("claims")


def _extract_specification(result):
    """从结果中提取说明书"""
    return f"""## 技术领域
本发明涉及{result.innovations[0].title if result.innovations else '技术创新'}领域。

## 背景技术
随着技术的发展，{st.session_state.technical_description[:200]}...

## 发明内容
{result.evaluation.technical_progress if hasattr(result, 'evaluation') else '见创新点描述'}

## 附图说明
本发明的具体实现方式可参考附图。

## 详细描述
{st.session_state.technical_description}

## 具体实施方式
{chr(10).join([f"实施例{i+1}: {inn.description}" for i, inn in enumerate(result.innovations[:3])]) if result.innovations else '详见技术描述'}"""
