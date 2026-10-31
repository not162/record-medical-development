import { NextRequest, NextResponse } from "next/server";

async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const pathStr = path.join("/");
  const searchParams = request.nextUrl.searchParams.toString();
  const queryString = searchParams ? `?${searchParams}` : "";

  // Priority: BACKEND_API_URL -> NEXT_PUBLIC_API_URL -> fallback production ai-api
  const rawBackend = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "https://ai-api-dusky-eight.vercel.app";
  const backendBase = rawBackend.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");
  const targetUrl = `${backendBase}/api/v1/${pathStr}${queryString}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!["host", "content-length", "connection"].includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const method = request.method;
  const init: RequestInit = {
    method,
    headers,
    cache: "no-store",
  };

  if (!["GET", "HEAD"].includes(method)) {
    try {
      init.body = await request.blob();
    } catch {
      // no body
    }
  }

  try {
    const backendRes = await fetch(targetUrl, init);

    const responseHeaders = new Headers();
    backendRes.headers.forEach((val, key) => {
      if (!["content-encoding", "content-length", "transfer-encoding"].includes(key.toLowerCase())) {
        responseHeaders.set(key, val);
      }
    });

    // Ensure SSE streaming headers are preserved for real-time responses
    if (backendRes.headers.get("content-type")?.includes("text/event-stream")) {
      responseHeaders.set("Content-Type", "text/event-stream");
      responseHeaders.set("Cache-Control", "no-cache, no-transform");
      responseHeaders.set("Connection", "keep-alive");
    }

    return new Response(backendRes.body, {
      status: backendRes.status,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      {
        error: "Backend API gateway error",
        target_url: targetUrl,
        detail: errorMsg,
        tip: "Pastikan backend FastAPI telah berjalan atau atur variabel BACKEND_API_URL pada Vercel Dashboard.",
      },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const OPTIONS = proxyRequest;
