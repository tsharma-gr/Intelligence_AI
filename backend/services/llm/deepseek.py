import httpx
from typing import Optional
from backend.services.llm.base import BaseLLMService, token_usage

class DeepSeekService(BaseLLMService):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.deepseek.com/v1/chat/completions"

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("DeepSeek API key is missing. Set DEEPSEEK_API_KEY in your environment.")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Track token usage
            usage = data.get("usage", {})
            token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            token_usage["total_tokens"] += usage.get("total_tokens", 0)
            token_usage["call_count"] += 1

            return data["choices"][0]["message"]["content"]
