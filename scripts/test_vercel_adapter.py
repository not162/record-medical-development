import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("services/ai-api"))

# Import the adapter
import api.index as vercel_api

async def test():
    paths_to_test = [
        ("/", "/"),
        ("/health", "/health"),
        ("/api/v1/health", "/api/v1/health"),
        ("/api/v1/auth/login", "/api/v1/auth/login"),
    ]
    
    for raw_url, expected in paths_to_test:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET" if "login" not in raw_url else "POST",
            "path": "/api/index",
            "raw_path": b"/api/index",
            "query_string": f"__vercel_path={raw_url}".encode("latin1"),
            "headers": [(b"host", b"test")],
            "root_path": "/api/index",
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 80),
        }
        status_code = None
        body = []
        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}
        async def send(msg):
            nonlocal status_code
            if msg["type"] == "http.response.start":
                status_code = msg["status"]
            elif msg["type"] == "http.response.body":
                body.append(msg.get("body", b""))
        await vercel_api.app(scope, receive, send)
        res_text = b"".join(body).decode(errors="ignore")[:60]
        print(f"Path: {raw_url} -> Status: {status_code} -> Body: {res_text}")

if __name__ == "__main__":
    asyncio.run(test())
