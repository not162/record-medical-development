import os
import sys
import urllib.parse

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

os.environ.setdefault("VERCEL", "1")

from app.main import app as fastapi_app

async def app(scope, receive, send):
    """
    ASGI adapter for Vercel Serverless Function.
    Ensures that incoming request paths rewritten to /api/index
    are correctly restored to their original clinical API routes.
    """
    if scope.get("type") in ("http", "websocket"):
        scope = dict(scope)
        headers = dict(scope.get("headers", []))
        qs = scope.get("query_string", b"")
        orig_path = scope.get("path", "")
        
        target_path = None
        
        # 1. Check __vercel_path parameter injected by Vercel rewrite
        if qs and b"__vercel_path=" in qs:
            try:
                params = urllib.parse.parse_qs(qs.decode("latin1", errors="ignore"))
                if "__vercel_path" in params and params["__vercel_path"]:
                    val = params["__vercel_path"][0]
                    if not val.startswith("/"):
                        val = "/" + val
                    while val.startswith("//"):
                        val = val[1:]
                    target_path = val
            except Exception:
                pass
            
            # Clean __vercel_path from query string so endpoints don't receive it
            try:
                pairs = [p for p in qs.split(b"&") if not p.startswith(b"__vercel_path=")]
                scope["query_string"] = b"&".join(pairs)
            except Exception:
                pass

        # 2. Fallback to Vercel headers if query parameter is absent
        if not target_path:
            matched = (
                headers.get(b"x-matched-path", b"").decode("latin1", errors="ignore")
                or headers.get(b"x-forwarded-uri", b"").decode("latin1", errors="ignore")
                or headers.get(b"x-invoke-path", b"").decode("latin1", errors="ignore")
            )
            if matched:
                clean = matched.split("?")[0]
                if clean and not clean.startswith("/api/index"):
                    target_path = clean

        # 3. Fallback to path prefix manipulation
        if not target_path:
            if orig_path.startswith("/api/index/"):
                target_path = orig_path[len("/api/index"):] or "/"
            elif orig_path.startswith("/api/index.py/"):
                target_path = orig_path[len("/api/index.py"):] or "/"
            elif orig_path in ("/api/index", "/api/index/", "/api/index.py"):
                target_path = "/"
            else:
                target_path = orig_path

        while target_path.startswith("//"):
            target_path = target_path[1:]
        if not target_path:
            target_path = "/"

        scope["path"] = target_path
        scope["raw_path"] = target_path.encode("latin1")

    await fastapi_app(scope, receive, send)
