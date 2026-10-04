export const dynamic = "force-dynamic";

export async function GET() {
  const backend = process.env.BACKEND_INTERNAL_URL;
  if (!backend) {
    return Response.json({ status: "unavailable" }, { status: 503 });
  }
  try {
    const response = await fetch(`${backend.replace(/\/$/, "")}/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(12000),
    });
    if (response.status !== 200 && response.status !== 503) throw new Error("Invalid health response");
    return Response.json(await response.json(), {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ status: "unavailable" }, { status: 503 });
  }
}

