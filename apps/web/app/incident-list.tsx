"use client";

/** Incidents as city problems, filterable by the state an operator cares about. */

import { useCallback, useEffect, useState } from "react";

type Locale = "ru" | "kk";

type IncidentRow = {
  incident_id: string;
  state: string;
  topic_id: string;
  service_id: string | null;
  version: number;
  created_at: string;
  confirmed_count: number;
  candidate_count: number;
  member_count: number;
  first_reported_at: string | null;
  last_reported_at: string | null;
};

const FILTERS = [
  "all",
  "proposed",
  "confirmed",
  "monitoring",
  "resolved",
] as const;

const copy = {
  ru: {
    title: "Инциденты",
    intro:
      "Каждый инцидент это одна городская проблема. Обращения внутри сохраняют свои идентификаторы и историю.",
    all: "Все",
    proposed: "Предложены",
    confirmed: "Подтверждены",
    monitoring: "Наблюдение",
    resolved: "Решены",
    empty:
      "Инцидентов в этом срезе нет. Создайте его из кластера в операционном центре.",
    reports: "обращений",
    confirmedCount: "подтверждено",
    open: "Открыть карточку",
    age: "возраст",
  },
  kk: {
    title: "Оқиғалар",
    intro:
      "Әр оқиға бір қалалық мәселе. Ішіндегі өтініштер өз идентификаторы мен тарихын сақтайды.",
    all: "Барлығы",
    proposed: "Ұсынылған",
    confirmed: "Расталған",
    monitoring: "Бақылауда",
    resolved: "Шешілген",
    empty: "Бұл кесіндіде оқиға жоқ.",
    reports: "өтініш",
    confirmedCount: "расталды",
    open: "Картаны ашу",
    age: "жасы",
  },
} as const;

function age(from: string): string {
  const minutes = Math.max(0, (Date.now() - Date.parse(from)) / 60000);
  if (minutes < 60) return `${Math.round(minutes)}m`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h`;
  return `${Math.round(minutes / (60 * 24))}d`;
}

export function IncidentList({
  locale,
  regionId,
  onOpenIncident,
}: {
  locale: Locale;
  regionId: string;
  onOpenIncident: (incidentId: string) => void;
}) {
  const t = copy[locale];
  const [rows, setRows] = useState<IncidentRow[]>([]);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const query = filter === "all" ? "" : `?state=${filter}`;
      const response = await fetch(`/api/core/incidents${query}`, {
        headers: { "X-Region-Id": regionId },
        cache: "no-store",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail?.code ?? `HTTP ${response.status}`);
      }
      setRows((await response.json()) as IncidentRow[]);
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "incidents_unavailable",
      );
    }
  }, [filter, regionId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  return (
    <section className="incident-list" aria-labelledby="incident-list-title">
      <div className="section-heading">
        <div>
          <h1 id="incident-list-title">{t.title}</h1>
          <p>{t.intro}</p>
        </div>
      </div>

      <nav className="filter-row" aria-label="State">
        {FILTERS.map((name) => (
          <button
            key={name}
            type="button"
            aria-pressed={filter === name}
            onClick={() => setFilter(name)}
          >
            {t[name]}
          </button>
        ))}
      </nav>

      {error ? (
        <p role="alert" className="attention">
          {error}
        </p>
      ) : null}

      {rows.length === 0 && !error ? (
        <p className="war-room-note">{t.empty}</p>
      ) : (
        <ul className="incident-cards">
          {rows.map((row) => (
            <li key={row.incident_id}>
              <div>
                <p className="eyebrow">
                  {row.state} · v{row.version} · {t.age} {age(row.created_at)}
                </p>
                <strong>{row.topic_id}</strong>
                <p className="codes">
                  {row.member_count} {t.reports} · {row.confirmed_count}{" "}
                  {t.confirmedCount}
                  {row.service_id ? ` · ${row.service_id}` : ""}
                </p>
              </div>
              <button
                type="button"
                className="secondary-action"
                onClick={() => onOpenIncident(row.incident_id)}
              >
                {t.open}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
