import httpx
from typing import Optional, Any
from backend.services.llm.base import BaseLLMService, token_usage

class DeepSeekService(BaseLLMService):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.deepseek.com/v1/chat/completions"

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None, job: Optional[Any] = None) -> str:
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
        
        # Only enforce strict JSON mode if the prompt/system instruction specifically asks for it.
        # This prevents breaking the conversational chat endpoint.
        if system_instruction and "json" in system_instruction.lower():
            payload["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Track token usage
            usage = data.get("usage", {})
            p_tokens = usage.get("prompt_tokens", 0)
            c_tokens = usage.get("completion_tokens", 0)
            t_tokens = usage.get("total_tokens", 0)

            # Global fallback
            token_usage["prompt_tokens"] += p_tokens
            token_usage["completion_tokens"] += c_tokens
            token_usage["total_tokens"] += t_tokens
            token_usage["call_count"] += 1

            # Isolated SearchJob metrics (Milestone 4)
            if job:
                await job.update_metrics("prompt_tokens", p_tokens, add=True)
                await job.update_metrics("completion_tokens", c_tokens, add=True)
                await job.update_metrics("total_tokens", t_tokens, add=True)
                await job.update_metrics("call_count", 1, add=True)

            return data["choices"][0]["message"]["content"]
