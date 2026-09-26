from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from core.config import Settings, normalized_provider, require_llm_credentials


def build_llm(settings: Settings, temperature: float = 0.0):
    provider = normalized_provider(settings)
    require_llm_credentials(settings)

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
    if provider == "openai":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
        )
    if provider == "anthropic":
        return ChatAnthropic(
            model=settings.model_name,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
        )
    if provider == "openrouter":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temperature,
        )
    if provider == "ollama":
        return ChatOllama(
            model=settings.model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )
    if provider == "custom":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.custom_llm_api_key or "unused",
            base_url=settings.custom_llm_base_url,
            temperature=temperature,
        )
    if provider == "mock":
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        class ToolCapableFakeChatModel(FakeListChatModel):
            # create_agent goi bind_tools; mock bo qua tools va tra loi co dinh.
            def bind_tools(self, tools, **kwargs):
                return self

        return ToolCapableFakeChatModel(responses=["This is a mock response from the scholarly corpus."])
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")


class LLMBudgetExceeded(RuntimeError):
    pass


class LLMBudget:
    """Dem va gioi han so lan goi LLM cho 1 cau hoi (tiet kiem chi phi)."""

    def __init__(self, settings: Settings, limit: int = 3):
        self.settings = settings
        self.limit = limit
        self.used = 0

    def invoke(self, messages, tools: list | None = None):
        if self.used >= self.limit:
            raise LLMBudgetExceeded(f"LLM call budget exceeded ({self.limit} per question)")
        self.used += 1
        llm = build_llm(settings=self.settings, temperature=0.0)
        return (llm.bind_tools(tools) if tools else llm).invoke(messages)


def message_text(message) -> str:
    """Lay text tu AIMessage; Gemini co the tra `content` dang list content blocks."""
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return str(content)
