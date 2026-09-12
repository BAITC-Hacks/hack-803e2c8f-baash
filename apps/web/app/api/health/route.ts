export function GET() {
  return Response.json({ service: "web", status: "ready", version: "0.1.0" });
}
