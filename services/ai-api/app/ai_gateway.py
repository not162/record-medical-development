import os
import json
import httpx
from typing import AsyncGenerator, Dict, Any, Optional

AI_GATEWAY_BASE_URL = os.getenv("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh/v1")

def get_gateway_api_key() -> str:
    """Retrieves the Vercel AI Gateway API key safely from environment variable."""
    return os.getenv("AI_GATEWAY_API_KEY", "").strip()

async def stream_text_ai_gateway(
    prompt: str,
    model: str = "openai/gpt-6-astra",
    system_prompt: Optional[str] = "Anda adalah Asisten Medis Klinis AI RSUKT terverifikasi.",
    temperature: float = 0.3,
) -> AsyncGenerator[str, None]:
    """
    Streams text generation through Vercel AI Gateway using SSE.
    Compatible with openai/gpt-6-astra and all multimodal catalog models.
    """
    api_key = get_gateway_api_key()
    if not api_key:
        yield "[AI Gateway Error]: AI_GATEWAY_API_KEY environment variable is not configured."
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }

    url = f"{AI_GATEWAY_BASE_URL}/chat/completions"

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code == 403:
                    body = await response.aread()
                    try:
                        err_json = json.loads(body.decode("utf-8"))
                        msg = err_json.get("error", {}).get("message", "")
                        if "credit card" in msg or "customer_verification_required" in str(body):
                            yield (
                                "[AI Gateway] Kredensial Vercel terverifikasi (vck_*). "
                                "Diperlukan aktivasi kartu kredit di dashboard Vercel untuk membuka kuota gratis: "
                                "https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%3Fmodal%3Dadd-credit-card"
                            )
                            return
                    except Exception:
                        pass
                    yield f"[AI Gateway Error 403]: {body.decode('utf-8', errors='ignore')}"
                    return

                if response.status_code != 200:
                    body = await response.aread()
                    yield f"[AI Gateway Error {response.status_code}]: {body.decode('utf-8', errors='ignore')}"
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"[AI Gateway Connection Error]: {str(e)}"
