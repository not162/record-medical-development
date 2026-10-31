import asyncio
import os
import sys

# Load .env if present
try:
    from dotenv import load_dotenv
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-api", ".env"))
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

# Add services/ai-api to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-api")))

from app.ai_gateway import stream_text_ai_gateway

async def main():
    print("=== Testing Streaming Text Generation through Vercel AI Gateway ===")
    prompt = "Jelaskan peran integrasi Vercel AI Gateway dan Continuous Batching dalam skalabilitas rumah sakit RSUKT."
    model = "openai/gpt-6-astra"
    print(f"Model: {model}")
    print(f"Prompt: {prompt}")
    print("--- Streaming Output ---")
    
    full_output = []
    async for chunk in stream_text_ai_gateway(prompt, model=model):
        print(chunk, end="", flush=True)
        full_output.append(chunk)
    print("\n--- End of Stream ---")

if __name__ == "__main__":
    asyncio.run(main())
