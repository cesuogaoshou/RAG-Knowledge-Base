import httpx
import pytest
from fastapi import HTTPException

from app.services.chat_service import DeepSeekChatService, _build_user_prompt


def test_deepseek_chat_service_uses_current_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    service = DeepSeekChatService(api_key="test-key")

    assert service.model == "deepseek-v4-flash"


def test_deepseek_chat_service_hides_provider_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(*args: object, **kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "The supported API model names are deepseek-v4-pro or deepseek-v4-flash",
                }
            },
            request=request,
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    service = DeepSeekChatService(api_key="test-key", model="bad-model")

    with pytest.raises(HTTPException) as exc_info:
        service.answer(question="memory讲了什么", sources=[])

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "DeepSeek 服务请求失败，请稍后重试或检查模型配置。"


def test_user_prompt_requests_plain_text_without_markdown_symbols() -> None:
    prompt = _build_user_prompt(question="memory讲了什么", sources=[])

    assert "不要使用 Markdown 标记" in prompt
    assert "**" in prompt
    assert "反引号" in prompt
    assert "不要在回答正文中列出来源编号" in prompt
