import type { Metadata } from "next";
import DemoEntry from "./demo-entry";

export const metadata: Metadata = {
  title: "Interactive Demo",
  description: "Pulse 109 interactive local demo workspace.",
};

export default function DemoPage() {
  return <DemoEntry />;
}
