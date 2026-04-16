"""AI 专利助手 v3.0 - 简化的用户流程

核心改进：
1. 从6步简化为3步：输入 → 生成 → 导出
2. 一键端到端生成完整专利
3. 智能默认值，减少人工干预
4. 保留专家模式供高级用户使用
"""

import sys
import os
import logging
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import (
    init_session_state,
    render_sidebar,
    render_quick_start,
    render_patent_review,
    render_step6,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

st.set_page_config(
    page_title="AI 专利助手 v3",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
render_sidebar()

st.title("🚀 AI 专利助手 v3")
st.caption("一键生成完整专利文档")

# 根据当前步骤渲染不同界面
step = st.session_state.current_step

if step == 1:
    # 快速开始 - 输入想法
    render_quick_start()
elif step == 0:
    # 专利审查 - 查看和编辑
    render_patent_review()
elif step == -1:
    # 历史记录
    render_history_view()
elif step == 6:
    # 导出
    render_step6()
else:
    # 默认显示快速开始
    st.session_state.current_step = 1
    render_quick_start()


def render_history_view():
    """渲染历史记录视图"""
    st.header("📂 历史项目")
    
    from ui.state import get_session_manager
    
    mgr = get_session_manager()
    sessions = mgr.list_sessions(limit=20)
    
    if not sessions:
        st.info("暂无历史项目")
        if st.button("← 创建新项目"):
            st.session_state.current_step = 1
            st.rerun()
        return
    
    for session in sessions:
        with st.expander(f"📁 {session.invention_name} ({session.created_at[:10]})"):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**技术描述**: {session.technical_description[:100]}...")
                st.markdown(f"**场景数**: {len(session.scenarios) if session.scenarios else 0}")
            
            with col2:
                if st.button("📂 加载", key=f"load_{session.session_id}"):
                    st.session_state.current_session_id = session.session_id
                    mgr.load_session(session.session_id, st.session_state)
                    st.session_state.current_step = 0
                    st.rerun()
            
            with col3:
                if st.button("🗑️ 删除", key=f"del_{session.session_id}"):
                    mgr.delete_session(session.session_id)
                    st.rerun()
    
    if st.button("➕ 新建项目"):
        st.session_state.current_step = 1
        st.rerun()
