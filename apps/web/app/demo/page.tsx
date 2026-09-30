import type { Metadata } from "next";
import DemoEntry from "./demo-entry";

export const metadata: Metadata = {
  title: "Interactive Demo",
  description: "Pulse 109 interactive demo workspace with synthetic records.",
};

export const dynamic = "force-dynamic";

export default function DemoPage() {
  return <DemoEntry mockMode={process.env.PULSE109_DEMO_MOCKS === "1"} />;
}
