"""AI 专利助手 - 会话管理模块

支持：
- 会话持久化（JSON 文件存储在 sessions/ 目录）
- 续写：从断点继续，不需要从头填
- 自动保存 + 手动保存
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from core.output_schema import (
    Innovation,
    NoveltyEvaluation,
    Suggestion,
    IdeaMiningResult,
    FiveElements,
    PatentAbstract,
    ClaimSet,
    PatentSpecification,
)

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"


class SessionData:
    """会话数据模型"""

    def __init__(
        self,
        session_id: str,
        invention_name: str,
        technical_description: str,
        scenarios: List[str],
        reference_patent_texts: List[str],
        current_step: int,
        idea_mining_result: Optional[dict] = None,
        five_elements: Optional[dict] = None,
        abstract_result: Optional[dict] = None,
        claims: Optional[dict] = None,
        specification: Optional[dict] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        display_name: Optional[str] = None,
    ):
        self.session_id = session_id
        self.invention_name = invention_name
        self.technical_description = technical_description
        self.scenarios = scenarios
        self.reference_patent_texts = reference_patent_texts
        self.current_step = current_step
        self.idea_mining_result = idea_mining_result
        self.five_elements = five_elements
        self.abstract_result = abstract_result
        self.claims = claims
        self.specification = specification
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.display_name = display_name or invention_name[:30]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "invention_name": self.invention_name,
            "technical_description": self.technical_description,
            "scenarios": self.scenarios,
            "reference_patent_texts": self.reference_patent_texts,
            "current_step": self.current_step,
            "idea_mining_result": self.idea_mining_result,
            "five_elements": self.five_elements,
            "abstract_result": self.abstract_result,
            "claims": self.claims,
            "specification": self.specification,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionData":
        return cls(**data)

    def step_label(self) -> str:
        labels = ["", "技术描述", "参考专利", "创新点挖掘", "五要素&摘要&权利要求", "说明书", "导出"]
        if 1 <= self.current_step <= 6:
            return labels[self.current_step]
        return "已完成"

    def progress(self) -> str:
        return f"Step {self.current_step}/6"

    def model_dump(self) -> dict:
        """返回可 JSON 序列化的字典，用于存储"""
        return self.to_dict()


class SessionManager:
    """会话管理器"""

    def __init__(self, sessions_dir: Path = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def create(
        self,
        invention_name: str = "",
        technical_description: str = "",
        scenarios: Optional[List[str]] = None,
        reference_patent_texts: Optional[List[str]] = None,
    ) -> SessionData:
        """创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        session = SessionData(
            session_id=session_id,
            invention_name=invention_name,
            technical_description=technical_description,
            scenarios=scenarios or [],
            reference_patent_texts=reference_patent_texts or [],
            current_step=1,
        )
        self.save(session)
        return session

    def save(self, session: SessionData) -> None:
        """保存会话"""
        session.updated_at = datetime.now().isoformat()
        filepath = self._session_file(session.session_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, ensure_ascii=False, indent=2)

    def load(self, session_id: str) -> Optional[SessionData]:
        """加载会话"""
        filepath = self._session_file(session_id)
        if not filepath.exists():
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SessionData.from_dict(data)

    def list_sessions(self) -> List[SessionData]:
        """列出所有会话，按更新时间倒序"""
        sessions = []
        for filepath in self.sessions_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(SessionData.from_dict(data))
            except Exception:
                continue
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def delete(self, session_id: str) -> bool:
        """删除会话"""
        filepath = self._session_file(session_id)
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def rename(self, session_id: str, new_name: str) -> Optional[SessionData]:
        """重命名会话"""
        session = self.load(session_id)
        if session:
            session.display_name = new_name
            self.save(session)
            return session
        return None
