from convertreino.application.llm.client import LLMClient
from convertreino.application.llm.openai_client import GROQ_BASE_URL, OpenAICompatibleLLMClient
from convertreino.infrastructure.config import ChatSettings


def build_llm_client(settings: ChatSettings) -> LLMClient:
    provider = settings.llm_provider
    if provider not in ("openai", "groq"):
        raise ValueError(
            f"Invalid LLM_PROVIDER: {provider!r}. Must be 'openai' or 'groq'."
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        return OpenAICompatibleLLMClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            provider_name="openai",
        )

    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required")
    return OpenAICompatibleLLMClient(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        base_url=GROQ_BASE_URL,
        provider_name="groq",
    )
