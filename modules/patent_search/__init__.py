"""AI 专利助手 - 专利检索与解析模块

用户上传相似专利 PDF → 提取文本 → LLM 提取关键技术信息
"""

import io
import logging
from typing import Optional

from core.llm_client import LLMClient
from core.output_schema import BaseModel, Field
from core.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class ExtractedPatentInfo(BaseModel):
    """从专利文档提取的结构化信息"""
    title: str = Field(description="专利标题")
    technical_field: str = Field(description="技术领域")
    technical_problem: str = Field(description="要解决的技术问题")
    technical_solution: str = Field(description="采用的技术方案")
    technical_effect: str = Field(description="技术效果")
    key_features: list[str] = Field(description="关键技术特征列表")
    main_claim: str = Field(description="独立权利要求内容")


class PatentSearchService:
    """专利检索与解析服务"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_from_pdf(self, pdf_file: io.BytesIO) -> ExtractedPatentInfo:
        """从上传的 PDF 文件中提取专利信息

        Args:
            pdf_file: 上传的 PDF 文件字节流

        Returns:
            ExtractedPatentInfo: 提取的结构化信息
        """
        text = self._read_pdf(pdf_file)
        if not text or len(text.strip()) < 50:
            raise ValueError("PDF 内容为空或过短，无法提取有效信息")
        return self._extract_patent_info(text)

    def extract_from_text(self, text: str) -> ExtractedPatentInfo:
        """从粘贴的专利文本中提取信息"""
        if not text or len(text.strip()) < 50:
            raise ValueError("文本内容过短，无法提取有效信息")
        return self._extract_patent_info(text)

    def _extract_patent_info(self, patent_text: str) -> ExtractedPatentInfo:
        """用 LLM 从专利文本中提取关键信息"""
        logger.info("提取专利文本信息...")
        system_prompt = load_prompt("patent_text_extract.md")
        user_prompt = f"专利文本内容：\n{patent_text[:8000]}"  # 截断避免超长
        return self.llm.chat_structured(system_prompt, user_prompt, ExtractedPatentInfo)

    @staticmethod
    def _read_pdf(pdf_file: io.BytesIO) -> str:
        """读取 PDF 文件文本内容"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_file)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            raise ImportError("请安装 pypdf: pip install pypdf")
        except Exception as e:
            logger.error(f"PDF 读取失败: {e}")
            raise ValueError(f"PDF 读取失败: {e}")
