import { NextResponse } from "next/server";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

async function proxy(request: Request, path: string[]) {
  const apiUrl = process.env.API_URL;
  if (!apiUrl) {
    return NextResponse.json(
      { code: "core_unavailable", message: "Core API is not configured." },
      { status: 503 },
    );
  }

  const target = new URL(`/v1/${path.join("/")}`, apiUrl);
  const headers = new Headers();
  // Forward only the public API contract headers. In particular, never trust
  // browser-supplied development identity or proxy headers.
  for (const name of [
    "authorization",
    "content-type",
    "idempotency-key",
    "x-correlation-id",
    "x-export-purpose",
    "x-region-id",
  ]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const response = await fetch(target, {
    method: request.method,
    headers,
    body:
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : request.body,
    cache: "no-store",
    // The request body is streamed through without being interpreted by the web tier.
    // @ts-expect-error Next's fetch RequestInit accepts duplex at runtime.
    duplex: "half",
  });
  return new NextResponse(response.body, {
    status: response.status,
    headers: response.headers,
  });
}

export async function GET(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, (await context.params).path);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, (await context.params).path);
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, (await context.params).path);
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, (await context.params).path);
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  return proxy(request, (await context.params).path);
}

export function OPTIONS() {
  return NextResponse.json({ allowed: METHODS });
}
