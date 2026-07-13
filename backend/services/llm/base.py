from abc import ABC, abstractmethod
from typing import Optional

# Global token usage tracker shared across all LLM calls in a session
token_usage = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "call_count": 0
}

def reset_token_usage():
    """Reset the token tracker for a new search session."""
    token_usage["prompt_tokens"] = 0
    token_usage["completion_tokens"] = 0
    token_usage["total_tokens"] = 0
    token_usage["call_count"] = 0

class BaseLLMService(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate response from the LLM provider."""
        pass
