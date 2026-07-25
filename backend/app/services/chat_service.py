import os
from pathlib import Path
from typing import Protocol

import httpx
from fastapi import HTTPException
from dotenv import load_dotenv

from app.schemas.search import SearchResult

DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"


class ChatService(Protocol):
    def answer(self, question: str, sources: list[SearchResult]) -> str:
        """Generate an answer for a question using retrieved sources."""


class DeepSeekChatService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.deepseek.com/chat/completions",
        timeout_seconds: float = 30.0,
    ) -> None:
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model or os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def answer(self, question: str, sources: list[SearchResult]) -> str:
        if not self.api_key:
            raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个文档问答助手。请只根据提供的资料回答问题；"
                        "如果资料中没有答案，请回答“上传的资料中没有找到相关信息”。"
                        "回答要简洁、自然、便于阅读。"
                    ),
                },
                {
                    "role": "user",
                    "content": _build_user_prompt(question, sources),
                },
            ],
            "temperature": 0.2,
        }
        try:
            response = httpx.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="DeepSeek 服务请求失败，请稍后重试或检查模型配置。",
            ) from exc

        data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="DeepSeek response format is invalid") from exc


def _build_user_prompt(question: str, sources: list[SearchResult]) -> str:
    context = "\n\n".join(
        (
            f"[来源 {index}] 文件: {source.filename}, 页码: {source.page}, "
            f"片段: {source.content}"
        )
        for index, source in enumerate(sources, start=1)
    )
    if not context:
        context = "无检索结果。"
    return (
        f"资料内容:\n{context}\n\n"
        f"用户问题:\n{question}\n\n"
        "回答要求:\n"
        "1. 只基于资料内容回答。\n"
        "2. 不要编造资料中不存在的信息。\n"
        "3. 用简洁中文回答，优先使用短句和自然段。\n"
        "4. 不要使用 Markdown 标记，例如 **、#、-、反引号 或代码块。\n"
        "5. 不要大段复述原文，只总结和回答用户问题。\n"
        "6. 不要在回答正文中列出来源编号，系统会在引用来源区域展示来源。"
    )
