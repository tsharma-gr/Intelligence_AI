from backend.api.config import settings
from backend.services.llm.base import BaseLLMService
from backend.services.llm.deepseek import DeepSeekService
from backend.services.llm.openai import OpenAIService
from backend.services.llm.gemini import GeminiService

class LLMFactory:
    @staticmethod
    def get_service() -> BaseLLMService:
        provider = settings.llm_provider.lower()
        if provider == "deepseek":
            return DeepSeekService(api_key=settings.deepseek_api_key)
        elif provider == "openai":
            return OpenAIService(api_key=settings.openai_api_key)
        elif provider == "gemini":
            return GeminiService(api_key=settings.gemini_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
