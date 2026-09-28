"use client";

import { useState } from "react";

type Locale = "ru" | "kk";
type Result = {
  metric_id: string;
  metric_version: string;
  quality: string;
  data_cutoff: string;
  coverage: Record<string, string>;
  provenance: string[];
  columns: { name: string }[];
  rows: unknown[][];
};

export function AnalyticsPanel({
  locale,
  regionId,
}: {
  locale: Locale;
  regionId: string;
}) {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/core/analytics/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Region-Id": regionId,
        },
        body: JSON.stringify({
          metric_id: "appeals_volume",
          dimensions: ["region_id"],
          filters: { region_id: [regionId] },
          time_range: {
            from: "2026-09-01T00:00:00Z",
            to: "2026-10-01T00:00:00Z",
          },
          granularity: "day",
          limit: 30,
        }),
        cache: "no-store",
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail?.code ?? `HTTP ${response.status}`);
      }
      setResult((await response.json()) as Result);
    } catch (failure) {
      setResult(null);
      setError(
        failure instanceof Error ? failure.message : "analytics_unavailable",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="decision-area" aria-labelledby="analytics-title">
      <h2 id="analytics-title">
        {locale === "ru" ? "Срез аналитики" : "Аналитика кесіндісі"}
      </h2>
      <p>
        {locale === "ru"
          ? "Данные синтетической витрины. Это не оперативный подсчёт обращений и не оценка качества модели."
          : "Синтетикалық витрина деректері. Бұл өтініштердің жедел саны да, модель сапасының бағасы да емес."}
      </p>
      <button
        type="button"
        className="secondary-action"
        disabled={busy}
        onClick={() => void load()}
      >
        {locale === "ru"
          ? "Загрузить API-срез ALA"
          : "ALA API кесіндісін жүктеу"}
      </button>
      {error ? (
        <p role="alert" className="attention">
          {error}
        </p>
      ) : null}
      {result ? (
        <div role="status">
          <p>
            {result.metric_id} · v{result.metric_version} · quality:{" "}
            {result.quality} · ALA: {result.coverage.ALA ?? "missing"}
          </p>
          <p>
            Cutoff: {result.data_cutoff} · Rows: {result.rows.length}
          </p>
          <p>Provenance: {result.provenance.join(", ") || "none"}</p>
          <div className="table-scroll">
            <table className="lab-table">
              <thead>
                <tr>
                  {result.columns.map((column) => (
                    <th key={column.name} scope="col">
                      {column.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.slice(0, 10).map((row, index) => (
                  <tr key={index}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex}>{String(cell ?? "—")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}
