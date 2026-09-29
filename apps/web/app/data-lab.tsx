"use client";

/**
 * Urban intelligence with a way in.
 *
 * The difference between this and a dashboard is that every figure can be
 * opened. A rate an operator cannot trace back to the appeals behind it is
 * something they have to take on faith, and on a service that routes citizen
 * reports, faith is not a reporting standard.
 */

import { useCallback, useEffect, useState } from "react";
import { Skeleton } from "./skeleton";

type Locale = "ru" | "kk";

type CapabilityStatus = {
  state: "available" | "abstained" | "unavailable";
  reason_code: string | null;
};

type Provenance = {
  dataset: string;
  region_id: string;
  generated_at: string;
  rows_considered: number;
  synthetic: boolean;
  metric_version: string;
};

type QualityDimension = {
  name: string;
  numerator: number;
  denominator: number;
  ratio: number | null;
  definition: string;
  drilldown: string | null;
};

type FunnelStage = {
  stage: string;
  definition: string;
  count: number;
  share_of_previous: number | null;
  drilldown: string;
};

type Percentiles = {
  count: number;
  p50: number | null;
  p75: number | null;
  p90: number | null;
  p95: number | null;
};

type Timing = { stage: string; definition: string; overall: Percentiles };

type HandoffEdge = {
  from_service: string;
  to_service: string;
  count: number;
  drilldown: string;
};

type DrilldownAppeal = {
  request_id: string;
  source_request_id: string;
  status: string;
  received_at: string | null;
  received_at_quality: string;
  language: string;
  channel: string;
  service_id: string | null;
  topic_id: string | null;
};

type MetricDefinition = {
  key: string;
  title: string;
  numerator: string;
  denominator: string;
  time_basis: string;
  included: string[];
  excluded: string[];
  metric_version: string;
};

const copy = {
  ru: {
    title: "Лаборатория данных",
    intro:
      "Каждая цифра открывается до конкретных обращений. Рядом с ней всегда написано, на каких данных она посчитана.",
    quality: "Качество данных",
    qualityNote:
      "Шесть измерений вместо одной оценки: одно число не говорит, что именно чинить.",
    process: "Процесс",
    processNote:
      "Срез текущих состояний и достигнутых этапов. Это не конверсия одной когорты.",
    timings: "Сроки",
    timingsNote:
      "Перцентили, а не среднее. Среднее прячет именно те случаи, ради которых это смотрят.",
    handoffs: "Передачи между службами",
    handoffRate: "Доля обращений с передачей",
    loops: "Петли",
    drilldown: "Обращения за этой цифрой",
    close: "Закрыть",
    rows: "строк",
    of: "из",
    definitions: "Что означает метрика",
    numerator: "Числитель",
    denominator: "Знаменатель",
    basis: "Основа времени",
    excluded: "Исключено",
    loading: "Загрузка…",
    empty: "Нет данных для этого среза",
    stageName: "Этап",
    countShort: "Обращений",
    source: "Источник",
    status: "Статус",
    received: "Новые",
    classified: "Классифицировано",
    assigned: "Назначено",
    closed: "Решено",
    district: "Районная служба",
    water: "Водоснабжение",
    roads: "Дороги",
    lighting: "Освещение",
    waste: "Вывоз отходов",
  },
  kk: {
    title: "Деректер зертханасы",
    intro:
      "Әр сан нақты өтініштерге дейін ашылады. Қасында ол қандай деректер бойынша есептелгені жазылады.",
    quality: "Деректер сапасы",
    qualityNote:
      "Бір баға емес, алты өлшем: бір сан нені түзету керегін айтпайды.",
    process: "Процесс",
    processNote:
      "Ағымдағы күйлер мен жеткен кезеңдердің көрінісі. Бұл бір топтың конверсиясы емес.",
    timings: "Мерзімдер",
    timingsNote: "Орташа емес, перцентильдер.",
    handoffs: "Қызметтер арасындағы берулер",
    handoffRate: "Беру болған өтініштер үлесі",
    loops: "Тұйықтар",
    drilldown: "Осы санның артындағы өтініштер",
    close: "Жабу",
    rows: "жол",
    of: "ішінен",
    definitions: "Метрика нені білдіреді",
    numerator: "Алымы",
    denominator: "Бөлімі",
    basis: "Уақыт негізі",
    excluded: "Алынып тасталды",
    loading: "Жүктелуде…",
    empty: "Бұл кесінді үшін дерек жоқ",
    stageName: "Кезең",
    countShort: "Өтініш",
    source: "Дереккөз",
    status: "Мәртебе",
    received: "Жаңа",
    classified: "Санатталды",
    assigned: "Тағайындалды",
    closed: "Шешілді",
    district: "Аудандық қызмет",
    water: "Сумен жабдықтау",
    roads: "Жолдар",
    lighting: "Көше жарығы",
    waste: "Қалдықтарды шығару",
  },
} as const;

function pct(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function humanize(value: string, t: (typeof copy)[Locale]): string {
  const key = value.replace(/^(topic|service):/, "") as keyof typeof t;
  return key in t ? t[key] : value;
}

export function DataLab({
  locale,
  regionId,
}: {
  locale: Locale;
  regionId: string;
}) {
  const t = copy[locale];
  const [quality, setQuality] = useState<{
    status: CapabilityStatus;
    provenance: Provenance;
    dimensions: QualityDimension[];
  } | null>(null);
  const [funnel, setFunnel] = useState<{
    status: CapabilityStatus;
    stages: FunnelStage[];
    largest_drop: string | null;
  } | null>(null);
  const [timings, setTimings] = useState<Timing[]>([]);
  const [handoffs, setHandoffs] = useState<{
    status: CapabilityStatus;
    handoff_rate: number | null;
    appeals_with_handoff: number;
    appeals_total: number;
    edges: HandoffEdge[];
    loops: HandoffEdge[];
  } | null>(null);
  const [definitions, setDefinitions] = useState<MetricDefinition[]>([]);
  const [drill, setDrill] = useState<{
    key: string;
    total: number;
    appeals: DrilldownAppeal[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(
    async <T,>(path: string): Promise<T> => {
      const response = await fetch(`/api/core${path}`, {
        headers: { "X-Region-Id": regionId },
        cache: "no-store",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail?.code ?? `HTTP ${response.status}`);
      }
      return (await response.json()) as T;
    },
    [regionId],
  );

  const load = useCallback(async () => {
    try {
      const [q, f, ti, h, d] = await Promise.all([
        request<typeof quality>("/datalab/quality"),
        request<typeof funnel>("/datalab/process"),
        request<Timing[]>("/datalab/timings"),
        request<typeof handoffs>("/datalab/handoffs"),
        request<MetricDefinition[]>("/datalab/definitions"),
      ]);
      setQuality(q);
      setFunnel(f);
      setTimings(ti);
      setHandoffs(h);
      setDefinitions(d);
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "datalab_unavailable",
      );
    }
  }, [request]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  async function openDrilldown(key: string) {
    try {
      const result = await request<{
        key: string;
        total: number;
        appeals: DrilldownAppeal[];
      }>(`/datalab/drilldown?key=${encodeURIComponent(key)}&limit=50`);
      setDrill(result);
      setError(null);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "drilldown_failed");
    }
  }

  return (
    <section className="data-lab" aria-labelledby="data-lab-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            {regionId}
            {quality ? ` · ${quality.provenance.metric_version}` : ""}
          </p>
          <h1 id="data-lab-title">{t.title}</h1>
          <p>{t.intro}</p>
        </div>
      </div>

      {error ? (
        <p role="alert" className="attention">
          {error}
        </p>
      ) : null}
      {!quality && !error ? (
        <div className="lab-loading" role="status" aria-busy="true">
          <span className="sr-only">{t.loading}</span>
          <article className="lab-card" aria-hidden="true">
            <Skeleton className="skeleton-heading" />
            <Skeleton className="skeleton-copy" />
            <Skeleton className="skeleton-metric-row" />
            <Skeleton className="skeleton-metric-row" />
            <Skeleton className="skeleton-metric-row" />
          </article>
          <article className="lab-card" aria-hidden="true">
            <Skeleton className="skeleton-heading" />
            <Skeleton className="skeleton-copy" />
            <Skeleton className="skeleton-chart" />
          </article>
        </div>
      ) : null}

      {quality ? (
        <article className="lab-card">
          <h2>{t.quality}</h2>
          <p className="war-room-note">{t.qualityNote}</p>
          <ul className="quality-bars">
            {quality.dimensions.map((dimension) => (
              <li key={dimension.name}>
                <div className="quality-head">
                  <strong>{dimension.name}</strong>
                  <span className="codes">
                    {dimension.numerator} {t.of} {dimension.denominator} ·{" "}
                    {pct(dimension.ratio)}
                  </span>
                </div>
                <span
                  className="quality-bar"
                  style={{ width: `${(dimension.ratio ?? 0) * 100}%` }}
                  aria-hidden="true"
                />
                <p className="codes">{dimension.definition}</p>
                {dimension.drilldown ? (
                  <button
                    type="button"
                    className="link-action"
                    onClick={() =>
                      void openDrilldown(dimension.drilldown as string)
                    }
                  >
                    {t.drilldown} →
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </article>
      ) : null}

      {funnel ? (
        <article className="lab-card">
          <h2>{t.process}</h2>
          <p className="war-room-note">{t.processNote}</p>
          <ol className="funnel">
            {funnel.stages.map((stage) => {
              const first = funnel.stages[0]?.count || 1;
              return (
                <li key={stage.stage}>
                  <div className="funnel-head">
                    <strong>{humanize(stage.stage, t)}</strong>
                    <span className="codes">{stage.count}</span>
                  </div>
                  <span
                    className="funnel-bar"
                    style={{
                      width: `${Math.max((stage.count / first) * 100, 1)}%`,
                    }}
                    aria-hidden="true"
                  />
                  <p className="codes">{stage.definition}</p>
                  <button
                    type="button"
                    className="link-action"
                    onClick={() => void openDrilldown(stage.drilldown)}
                  >
                    {t.drilldown} →
                  </button>
                </li>
              );
            })}
          </ol>
        </article>
      ) : null}

      {timings.length > 0 ? (
        <article className="lab-card">
          <h2>{t.timings}</h2>
          <p className="war-room-note">{t.timingsNote}</p>
          <div className="table-scroll">
            <table className="lab-table">
              <thead>
                <tr>
                  <th>{t.stageName}</th>
                  <th>{t.countShort}</th>
                  <th>P50</th>
                  <th>P75</th>
                  <th>P90</th>
                  <th>P95</th>
                </tr>
              </thead>
              <tbody>
                {timings.map((timing) => (
                  <tr key={timing.stage}>
                    <td>{humanize(timing.stage, t)}</td>
                    <td>{timing.overall.count}</td>
                    <td>{timing.overall.p50 ?? "—"}</td>
                    <td>{timing.overall.p75 ?? "—"}</td>
                    <td>{timing.overall.p90 ?? "—"}</td>
                    <td>{timing.overall.p95 ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}

      {handoffs ? (
        <article className="lab-card">
          <h2>{t.handoffs}</h2>
          <p className="codes">
            {t.handoffRate}: {pct(handoffs.handoff_rate)} ·{" "}
            {handoffs.appeals_with_handoff} {t.of} {handoffs.appeals_total}
          </p>
          {handoffs.edges.length === 0 ? (
            <p className="war-room-note">
              {handoffs.status.reason_code ?? t.empty}
            </p>
          ) : (
            <ul className="war-room-list">
              {handoffs.edges.map((edge) => (
                <li key={`${edge.from_service}-${edge.to_service}`}>
                  <strong>
                    {humanize(edge.from_service, t)} →{" "}
                    {humanize(edge.to_service, t)}
                  </strong>
                  <span className="codes">{edge.count}</span>
                  <button
                    type="button"
                    className="link-action"
                    onClick={() => void openDrilldown(edge.drilldown)}
                  >
                    {t.drilldown} →
                  </button>
                </li>
              ))}
            </ul>
          )}
          {handoffs.loops.length > 0 ? (
            <p className="attention">
              {t.loops}:{" "}
              {handoffs.loops
                .map((edge) => `${edge.from_service} ↔ ${edge.to_service}`)
                .join(", ")}
            </p>
          ) : null}
        </article>
      ) : null}

      {drill ? (
        <article className="lab-card drilldown-panel">
          <div className="war-room-head">
            <div>
              <p className="eyebrow">{drill.key}</p>
              <h2>
                {drill.total} {t.rows}
              </h2>
            </div>
            <button
              type="button"
              className="secondary-action"
              onClick={() => setDrill(null)}
            >
              {t.close}
            </button>
          </div>
          <div className="table-scroll">
            <table className="lab-table">
              <thead>
                <tr>
                  <th>{t.source}</th>
                  <th>{t.status}</th>
                  <th>{t.stageName}</th>
                  <th>{t.quality}</th>
                  <th>Язык</th>
                  <th>{t.handoffs}</th>
                </tr>
              </thead>
              <tbody>
                {drill.appeals.map((appeal) => (
                  <tr key={appeal.request_id}>
                    <td>{appeal.source_request_id}</td>
                    <td>{humanize(appeal.status, t)}</td>
                    <td>
                      {appeal.received_at?.slice(0, 16).replace("T", " ") ??
                        "—"}
                    </td>
                    <td>{appeal.received_at_quality}</td>
                    <td>{appeal.language}</td>
                    <td>
                      {appeal.service_id ? humanize(appeal.service_id, t) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}

      {definitions.length > 0 ? (
        <article className="lab-card">
          <h2>{t.definitions}</h2>
          <dl className="definitions">
            {definitions.map((definition) => (
              <div key={definition.key}>
                <dt>
                  {definition.title}{" "}
                  <span className="codes">{definition.metric_version}</span>
                </dt>
                <dd>
                  <p>
                    <strong>{t.numerator}:</strong> {definition.numerator}
                  </p>
                  <p>
                    <strong>{t.denominator}:</strong> {definition.denominator}
                  </p>
                  <p>
                    <strong>{t.basis}:</strong> {definition.time_basis}
                  </p>
                  <p>
                    <strong>{t.excluded}:</strong>{" "}
                    {definition.excluded.join("; ")}
                  </p>
                </dd>
              </div>
            ))}
          </dl>
        </article>
      ) : null}
    </section>
  );
}
