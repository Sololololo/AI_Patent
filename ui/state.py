"""Session State 管理"""

import streamlit as st
from config import Settings, create_settings
from core.llm_client import LLMClient
from core.session_manager import SessionManager
from core.output_schema import (
    IdeaMiningResult,
    FiveElements,
    PatentAbstract,
    ClaimSet,
    PatentSpecification,
)


def init_session_state():
    defaults = {
        "current_step": 1,
        "current_session_id": None,
        "has_unsaved_changes": False,
        "technical_description": "",
        "scenarios": [],
        "reference_patent_texts": [],
        "invention_name": "",
        "idea_mining_result": None,
        "five_elements": None,
        "abstract_result": None,
        "claims": None,
        "specification": None,
        "score_strictness": "标准",
        "export_path": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_llm_client() -> LLMClient:
    settings = create_settings(
        api_url=st.session_state.get("api_url", "https://api.deepseek.com/v1/chat/completions"),
        api_key=st.session_state.get("api_key", ""),
        model_name=st.session_state.get("model_name", "deepseek-chat"),
        temperature=st.session_state.get("temperature", 0.7),
    )
    return LLMClient(settings)


def reset_results():
    st.session_state.idea_mining_result = None
    st.session_state.five_elements = None
    st.session_state.abstract_result = None
    st.session_state.claims = None
    st.session_state.specification = None
    st.session_state.export_path = None


def start_new_project():
    st.session_state.current_session_id = None
    st.session_state.current_step = 1
    st.session_state.has_unsaved_changes = False
    st.session_state.invention_name = ""
    st.session_state.technical_description = ""
    st.session_state.scenarios = []
    st.session_state.reference_patent_texts = []
    reset_results()


def get_session_manager() -> SessionManager:
    return SessionManager()


def save_current_session():
    if st.session_state.current_session_id is None:
        return
    mgr = get_session_manager()
    session = mgr.load(st.session_state.current_session_id)
    if session is None:
        return
    session.invention_name = st.session_state.invention_name
    session.technical_description = st.session_state.technical_description
    session.scenarios = st.session_state.scenarios
    session.reference_patent_texts = st.session_state.reference_patent_texts
    session.current_step = st.session_state.current_step
    session.idea_mining_result = (
        st.session_state.idea_mining_result.model_dump() if st.session_state.idea_mining_result else None
    )
    session.five_elements = (
        st.session_state.five_elements.model_dump() if st.session_state.five_elements else None
    )
    session.abstract_result = (
        st.session_state.abstract_result.model_dump() if st.session_state.abstract_result else None
    )
    session.claims = (
        st.session_state.claims.model_dump() if st.session_state.claims else None
    )
    session.specification = (
        st.session_state.specification.model_dump() if st.session_state.specification else None
    )
    mgr.save(session)


def load_session_to_state(session_id: str):
    mgr = get_session_manager()
    session = mgr.load(session_id)
    if session is None:
        return
    st.session_state.current_session_id = session.session_id
    st.session_state.current_step = session.current_step
    st.session_state.invention_name = session.invention_name
    st.session_state.technical_description = session.technical_description
    st.session_state.scenarios = session.scenarios
    st.session_state.reference_patent_texts = session.reference_patent_texts
    st.session_state.idea_mining_result = None
    st.session_state.five_elements = None
    st.session_state.abstract_result = None
    st.session_state.claims = None
    st.session_state.specification = None
    st.session_state.export_path = None
    if session.idea_mining_result:
        st.session_state.idea_mining_result = IdeaMiningResult(**session.idea_mining_result)
    if session.five_elements:
        st.session_state.five_elements = FiveElements(**session.five_elements)
    if session.abstract_result:
        st.session_state.abstract_result = PatentAbstract(**session.abstract_result)
    if session.claims:
        st.session_state.claims = ClaimSet(**session.claims)
    if session.specification:
        st.session_state.specification = PatentSpecification(**session.specification)


def lines_to_list(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]
