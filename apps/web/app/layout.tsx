import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";

export const metadata: Metadata = {
  title: {
    default: "Pulse 109 — City Intelligence",
    template: "%s | Pulse 109",
  },
  description:
    "A governed operations layer that connects citizen appeals, operator decisions and city response.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
