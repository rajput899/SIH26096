import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (!path.every(segment => /^[a-zA-Z0-9-]+$/.test(segment))) {
    return Response.json({ detail: 'Invalid path' }, { status: 400 });
  }
  const backend = process.env.BACKEND_INTERNAL_URL;
  if (!backend) return Response.json({ detail: 'Backend unavailable' }, { status: 503 });
  // Mutations require explicit Authorization. Only item-scoped playback accepts cookies.
  const headers = new Headers();
  for (const key of ['authorization', 'content-type', 'range']) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  if (request.method === 'GET' && path[0] === 'staff' && path.at(-1) === 'playback') {
    const cookie = request.headers.get('cookie'); if(cookie) headers.set('cookie',cookie);
  }
  headers.set('x-forwarded-proto', request.nextUrl.protocol.replace(':',''));
  try {
    const chunks: Uint8Array[] = [];
    let size = 0;
    if (request.method === 'POST' && request.body) {
      const reader = request.body.getReader();
      while (true) {
        const next = await reader.read();
        if (next.done) break;
        size += next.value.length;
        if (size > 10 * 1024 * 1024) {
          await reader.cancel();
          return Response.json({ detail: 'Maximum upload size is 10 MiB' }, { status: 413 });
        }
        chunks.push(next.value);
      }
    }
    const response = await fetch(`${backend.replace(/\/$/, '')}/archive/${path.join('/')}${request.nextUrl.search}`, {
      method: request.method, headers, cache: 'no-store',
      body: request.method === 'POST' ? Buffer.concat(chunks) : undefined,
      signal: AbortSignal.timeout(110000),
    });
    const resultHeaders = new Headers({ 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    for (const key of ['content-type', 'content-disposition', 'content-range', 'accept-ranges', 'content-length', 'set-cookie']) {
      const value = response.headers.get(key);
      if (value) resultHeaders.set(key, value);
    }
    return new Response(response.body, { status: response.status, headers: resultHeaders });
  } catch {
    return Response.json({ detail: 'Archive service unavailable' }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;

