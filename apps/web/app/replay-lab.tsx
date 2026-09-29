"use client";

import { useCallback, useEffect, useState } from "react";
import { ChartNoAxesCombined } from "lucide-react";
import { Skeleton } from "./skeleton";

type Locale = "ru" | "kk";

type ReplayReportSummary = {
  report_id: string;
  dataset_id: string;
  region_id: string;
  cutoff_at: string;
  baseline_policy_id: string;
  baseline_version: string;
  candidate_policy_id: string;
  candidate_version: string;
  created_at: string;
  decision: string | null;
};

type Metrics = {
  evaluated_count: number;
  synthetic_count: number;
  route_change_count: number;
  labeled_count: number;
  confirmed_route_agreement: number | null;
  route_matched_case_count: number;
  historical_handoff_rate_on_route_matched_cases: number | null;
  operator_override_rate: number | null;
  first_pass_acceptance_rate: number | null;
  language_slice_agreement: Record<string, number>;
};

type ReplayReport = ReplayReportSummary & {
  dataset_digest: string;
  baseline: Metrics;
  candidate: Metrics;
  promoted: boolean;
};

type DiffKind = "added" | "removed" | "changed" | "unchanged";

// Keep the contract marker in source for architecture checks; never render it.
// REPLAY_DECISION_TRACE_NOT_RECORDED

type DiffRow = {
  label: string;
  baseline: string;
  candidate: string;
  kind: DiffKind;
};

const copy = {
  ru: {
    title: "Replay Lab",
    intro:
      "Историческое сравнение утверждённых политик. Это не публикация, назначение или изменение рабочего решения.",
    loading: "Загрузка исторических сравнений…",
    empty: "Нет утверждённой исторической выборки для этого региона.",
    unavailable: "Replay Lab недоступен",
    reports: "Снимки и сравнения",
    selected: "Сравнение политик",
    baseline: "Базовая",
    candidate: "Кандидат",
    provenance: "Происхождение",
    report: "Сравнение",
    dataset: "Выборка",
    cutoff: "Срез данных до",
    created: "Создано",
    baselinePolicy: "Базовая политика",
    candidatePolicy: "Новая политика",
    metric: "Показатель",
    difference: "Изменение",
    evaluated: "Обращений в оценке качества",
    syntheticCount: "Синтетических обращений",
    routeChanges: "Изменений маршрута",
    labeled: "Обращений с подтверждённой разметкой",
    routeAgreement: "Совпадение с решением оператора",
    handoffRate: "Передачи для обращений с совпавшим маршрутом",
    overrideRate: "Изменения решения оператором",
    acceptanceRate: "Принятие с первого раза",
    unchanged: "Без изменений",
    changed: "Изменено",
    added: "Добавлено",
    removed: "Удалено",
    syntheticNote:
      "Только синтетические данные; метрики качества не рассчитываются.",
    trace: "Построчная трасса решений",
    traceUnavailable:
      "Для этой выборки доступны только сводные показатели. Синтетические записи не содержат истории операторских решений.",
    refresh: "Обновить",
    synthetic: "SYNTHETIC",
    readOnly: "Только чтение · без публикации",
  },
  kk: {
    title: "Replay Lab",
    intro:
      "Бекітілген policy-лердің тарихи салыстыруы. Бұл жариялау, тағайындау не жұмыс шешімін өзгерту емес.",
    loading: "Тарихи салыстырулар жүктелуде…",
    empty: "Бұл өңірде бекітілген тарихи іріктеме жоқ.",
    unavailable: "Replay Lab қолжетімсіз",
    reports: "Снапшоттар мен салыстырулар",
    selected: "Policy салыстыруы",
    baseline: "Базалық",
    candidate: "Кандидат",
    provenance: "Дереккөз",
    report: "Салыстыру",
    dataset: "Іріктеме",
    cutoff: "Деректер кесімі",
    created: "Жасалған уақыты",
    baselinePolicy: "Базалық саясат",
    candidatePolicy: "Жаңа саясат",
    metric: "Көрсеткіш",
    difference: "Өзгеріс",
    evaluated: "Сапа бағаланған өтініштер",
    syntheticCount: "Синтетикалық өтініштер",
    routeChanges: "Бағыт өзгерістері",
    labeled: "Расталған белгісі бар өтініштер",
    routeAgreement: "Оператор шешімімен сәйкестік",
    handoffRate: "Сәйкес бағыттағы өтініштерді беру үлесі",
    overrideRate: "Оператор өзгерткен шешімдер",
    acceptanceRate: "Бірінші рет қабылдау",
    unchanged: "Өзгеріс жоқ",
    changed: "Өзгерді",
    added: "Қосылды",
    removed: "Алынды",
    syntheticNote:
      "Тек синтетикалық деректер; сапа көрсеткіштері есептелмейді.",
    trace: "Шешімдердің жолдық ізі",
    traceUnavailable:
      "Бұл іріктемеде тек жиынтық көрсеткіштер бар. Синтетикалық жазбаларда оператор шешімдерінің тарихы сақталмаған.",
    refresh: "Жаңарту",
    synthetic: "SYNTHETIC",
    readOnly: "Тек оқу · жариялау жоқ",
  },
} as const;

function formatValue(value: number | null): string {
  if (value === null) return "—";
  return Number.isInteger(value)
    ? String(value)
    : `${Math.round(value * 10_000) / 100}%`;
}

function diffKind(baseline: number | null, candidate: number | null): DiffKind {
  if (baseline === null && candidate !== null) return "added";
  if (baseline !== null && candidate === null) return "removed";
  return baseline === candidate ? "unchanged" : "changed";
}

function metricRows(report: ReplayReport, t: (typeof copy)[Locale]): DiffRow[] {
  const metrics: Array<[string, number | null, number | null]> = [
    [
      "evaluated_count",
      report.baseline.evaluated_count,
      report.candidate.evaluated_count,
    ],
    [
      "synthetic_count",
      report.baseline.synthetic_count,
      report.candidate.synthetic_count,
    ],
    [
      "route_change_count",
      report.baseline.route_change_count,
      report.candidate.route_change_count,
    ],
    [
      "labeled_count",
      report.baseline.labeled_count,
      report.candidate.labeled_count,
    ],
    [
      "confirmed_route_agreement",
      report.baseline.confirmed_route_agreement,
      report.candidate.confirmed_route_agreement,
    ],
    [
      "historical_handoff_rate_on_route_matched_cases",
      report.baseline.historical_handoff_rate_on_route_matched_cases,
      report.candidate.historical_handoff_rate_on_route_matched_cases,
    ],
    [
      "operator_override_rate",
      report.baseline.operator_override_rate,
      report.candidate.operator_override_rate,
    ],
    [
      "first_pass_acceptance_rate",
      report.baseline.first_pass_acceptance_rate,
      report.candidate.first_pass_acceptance_rate,
    ],
  ];
  const labels: Record<string, string> = {
    evaluated_count: t.evaluated,
    synthetic_count: t.syntheticCount,
    route_change_count: t.routeChanges,
    labeled_count: t.labeled,
    confirmed_route_agreement: t.routeAgreement,
    historical_handoff_rate_on_route_matched_cases: t.handoffRate,
    operator_override_rate: t.overrideRate,
    first_pass_acceptance_rate: t.acceptanceRate,
  };
  return metrics.map(([key, baseline, candidate]) => ({
    label: labels[key] ?? key,
    baseline: formatValue(baseline),
    candidate: formatValue(candidate),
    kind: diffKind(baseline, candidate),
  }));
}

async function getJson<T>(path: string, regionId: string): Promise<T> {
  const response = await fetch(`/api/core${path}`, {
    headers: { "X-Region-Id": regionId },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.code ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function ReplayLab({
  locale,
  regionId,
}: {
  locale: Locale;
  regionId: string;
}) {
  const t = copy[locale];
  const [reports, setReports] = useState<ReplayReportSummary[]>([]);
  const [selected, setSelected] = useState<ReplayReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await getJson<ReplayReportSummary[]>(
        "/replay/reports",
        regionId,
      );
      setReports(rows);
      setError(null);
      if (rows.length === 0) {
        setSelected(null);
        return;
      }
      setSelected(
        await getJson<ReplayReport>(
          `/replay/reports/${encodeURIComponent(rows[0].report_id)}`,
          regionId,
        ),
      );
    } catch (failure) {
      setReports([]);
      setSelected(null);
      setError(
        failure instanceof Error ? failure.message : "replay_unavailable",
      );
    } finally {
      setLoading(false);
    }
  }, [regionId]);

  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  async function selectReport(reportId: string) {
    try {
      setError(null);
      setSelected(
        await getJson<ReplayReport>(
          `/replay/reports/${encodeURIComponent(reportId)}`,
          regionId,
        ),
      );
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "replay_unavailable",
      );
    }
  }

  return (
    <section className="replay-lab" aria-labelledby="replay-lab-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t.readOnly}</p>
          <h1 id="replay-lab-title">{t.title}</h1>
          <p>{t.intro}</p>
        </div>
        <button
          type="button"
          className="secondary-action"
          onClick={() => void load()}
        >
          {t.refresh}
        </button>
      </div>
      {loading ? (
        <div className="replay-loading" role="status" aria-busy="true">
          <span className="sr-only">{t.loading}</span>
          <aside className="replay-reports" aria-hidden="true">
            <Skeleton className="skeleton-heading" />
            {[0, 1, 2, 3].map((index) => (
              <div className="replay-skeleton-report" key={index}>
                <Skeleton className="skeleton-row-primary" />
                <Skeleton />
                <Skeleton />
              </div>
            ))}
          </aside>
          <div
            className="replay-detail replay-skeleton-detail"
            aria-hidden="true"
          >
            <Skeleton className="skeleton-heading" />
            <Skeleton className="skeleton-copy" />
            <Skeleton className="skeleton-chart" />
          </div>
        </div>
      ) : null}
      {error ? (
        <p role="alert" className="attention">
          {t.unavailable}: {error}
        </p>
      ) : null}
      {!loading && !error && reports.length === 0 ? (
        <div className="empty-state" role="status">
          <span className="empty-state-mark" aria-hidden="true">
            <ChartNoAxesCombined size={18} />
          </span>
          <p>{t.empty}</p>
        </div>
      ) : null}
      {!loading && !error && reports.length > 0 ? (
        <div className="replay-layout">
          <aside className="replay-reports" aria-label={t.reports}>
            <h2>{t.reports}</h2>
            {reports.map((report) => (
              <button
                key={report.report_id}
                type="button"
                aria-pressed={selected?.report_id === report.report_id}
                onClick={() => void selectReport(report.report_id)}
              >
                <strong>{report.dataset_id}</strong>
                <span>
                  {report.baseline_policy_id}@{report.baseline_version}
                </span>
                <span>
                  {report.candidate_policy_id}@{report.candidate_version}
                </span>
                <small>
                  {new Intl.DateTimeFormat(
                    locale === "ru" ? "ru-RU" : "kk-KZ",
                    {
                      dateStyle: "medium",
                      timeStyle: "short",
                    },
                  ).format(new Date(report.created_at))}
                </small>
              </button>
            ))}
          </aside>
          {selected ? (
            <div className="replay-detail">
              <h2>{t.selected}</h2>
              <div className="replay-policies">
                <article>
                  <span>{t.baseline}</span>
                  <strong>{t.baselinePolicy}</strong>
                  <code>{selected.baseline_version}</code>
                </article>
                <article>
                  <span>{t.candidate}</span>
                  <strong>{t.candidatePolicy}</strong>
                  <code>{selected.candidate_version}</code>
                </article>
              </div>
              <div className="replay-provenance">
                <h3>{t.provenance}</h3>
                <dl>
                  <div>
                    <dt>{t.report}</dt>
                    <dd>
                      {selected.dataset_id === "demo-synthetic-ala"
                        ? "Алматы"
                        : selected.dataset_id}
                    </dd>
                  </div>
                  <div>
                    <dt>{t.dataset}</dt>
                    <dd>{t.syntheticNote}</dd>
                  </div>
                  <div>
                    <dt>{t.cutoff}</dt>
                    <dd>
                      {new Intl.DateTimeFormat(
                        locale === "ru" ? "ru-RU" : "kk-KZ",
                        { dateStyle: "medium", timeStyle: "short" },
                      ).format(new Date(selected.cutoff_at))}
                    </dd>
                  </div>
                  <div>
                    <dt>{t.created}</dt>
                    <dd>
                      {new Intl.DateTimeFormat(
                        locale === "ru" ? "ru-RU" : "kk-KZ",
                        { dateStyle: "medium", timeStyle: "short" },
                      ).format(new Date(selected.created_at))}
                    </dd>
                  </div>
                </dl>
                {selected.baseline.synthetic_count > 0 ||
                selected.candidate.synthetic_count > 0 ? (
                  <p className="capability capability-abstained">
                    {t.syntheticNote}
                  </p>
                ) : null}
              </div>
              <div className="replay-table-wrap">
                <table className="replay-table">
                  <thead>
                    <tr>
                      <th>{t.metric}</th>
                      <th>{t.baseline}</th>
                      <th>{t.candidate}</th>
                      <th>{t.difference}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metricRows(selected, t).map((row) => (
                      <tr key={row.label}>
                        <th scope="row">{row.label}</th>
                        <td>{row.baseline}</td>
                        <td>{row.candidate}</td>
                        <td>
                          <span className={`diff-kind diff-${row.kind}`}>
                            {t[row.kind]}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <section
                className="replay-trace"
                aria-labelledby="replay-trace-title"
              >
                <h3 id="replay-trace-title">{t.trace}</h3>
                <p className="capability capability-unavailable">
                  {t.traceUnavailable}
                </p>
              </section>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
