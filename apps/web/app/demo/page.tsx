import type { Metadata } from "next";
import OperatorWorkspace from "../operator-workspace";

export const metadata: Metadata = {
  title: "Interactive Demo",
  description:
    "Pulse 109 operations workspace with synthetic municipal demo data.",
};

export default function DemoPage() {
  return <OperatorWorkspace />;
}
