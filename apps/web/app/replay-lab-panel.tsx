"use client";

import { Globe, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

type Locale = "ru" | "kk";

type PolicyMetrics = {
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

type ReplayReport = {
  report_id: string;
  dataset_id: string;
  region_id: string;
  dataset_digest: string;
  baseline_policy_id: string;
  baseline_version: string;
  candidate_policy_id: string;
  candidate_version: string;
  cutoff_at: string;
  baseline: PolicyMetrics;
  candidate: PolicyMetrics;
  decision: string;
  promoted: boolean;
};

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
  decision?: string;
};

const text = {
  ru: {
    eyebrow: "Replay Lab · Офлайн-валидация",
    title: "Историческое сравнение политик",
    intro:
      "Оценка моделей и правил на исторических срезах без влияния на продуктив. Анализ языковых срезов (KK, RU, mixed), доли переопределений операторами и перенаправлений.",
    region: "Регион",
    refresh: "Обновить",
    reports: "Исторические отчёты",
    selectReport: "Выберите отчёт для детального анализа",
    baseline: "Базовая политика (Baseline)",
    candidate: "Кандидат (Candidate)",
    routeAgreement: "Согласованность маршрутизации",
    overrideRate: "Доля ручных правок оператора (Override Rate)",
    firstPassRate: "Принятие с первого прохода (First-Pass)",
    handoffRate: "Доля повторных передач (Handoff Churn)",
    languageSlices: "Срезы по языкам обращений",
    kazakh: "Казахский (KK)",
    russian: "Русский (RU)",
    mixed: "Смешанный (Mixed)",
    casesEvaluated: "Оценено обращений",
    syntheticCases: "Синтетических обращений",
    cutoffDate: "Временная граница (Cutoff)",
    governanceNotice:
      "Replay носит дескриптивный характер. Активация политик в контуре требует криптографически подписанного регионального бандла.",
    decisionText: "Заключение симуляции",
    noReports: "Отчётов для региона пока нет",
  },
  kk: {
    eyebrow: "Replay Lab · Офлайн-валидация",
    title: "Саясаттарды тарихи салыстыру",
    intro:
      "Модельдер мен ережелерді өндіріске әсерсіз тарихи деректерде бағалау. Тілдік тіліктер (KK, RU, mixed), оператор түзетулері және қайта бағыттаулар көрсеткіші.",
    region: "Аймақ",
    refresh: "Жаңарту",
    reports: "Тарихи есептер",
    selectReport: "Толық талдау үшін есепті таңдаңыз",
    baseline: "Базалық саясат (Baseline)",
    candidate: "Үміткер саясат (Candidate)",
    routeAgreement: "Бағыттау сәйкестігі",
    overrideRate: "Оператордың қолмен түзету үлесі (Override Rate)",
    firstPassRate: "Бірінші өтуден қабылдау (First-Pass)",
    handoffRate: "Қайта тапсыру үлесі (Handoff Churn)",
    languageSlices: "Өтініштердің тілдік тіліктері",
    kazakh: "Қазақ тілі (KK)",
    russian: "Орыс тілі (RU)",
    mixed: "Аралас тіл (Mixed)",
    casesEvaluated: "Бағаланған өтініштер",
    syntheticCases: "Синтетикалық өтініштер",
    cutoffDate: "Уақыт шегі (Cutoff)",
    governanceNotice:
      "Replay сипаттамалық сипатта. Контурда саясатты іске қосу қол қойылған аймақтық бандлды талап етеді.",
    decisionText: "Симуляция қорытындысы",
    noReports: "Бұл аймақ үшін әлі есептер жоқ",
  },
} as const;

const SAMPLE_REPLAY_REPORT: ReplayReport = {
  report_id: "replay-rep-synthetic-001",
  dataset_id: "dataset-kar-2026-q3",
  region_id: "KAR",
  dataset_digest:
    "a6b4c3d2e1f0a6b4c3d2e1f0a6b4c3d2e1f0a6b4c3d2e1f0a6b4c3d2e1f0a6b4",
  baseline_policy_id: "routing-kar-standard",
  baseline_version: "1.0.0",
  candidate_policy_id: "routing-kar-candidate",
  candidate_version: "1.1.0",
  cutoff_at: "2026-09-10T23:59:00Z",
  baseline: {
    evaluated_count: 120,
    synthetic_count: 120,
    route_change_count: 0,
    labeled_count: 120,
    confirmed_route_agreement: 0.82,
    route_matched_case_count: 98,
    historical_handoff_rate_on_route_matched_cases: 0.08,
    operator_override_rate: 0.18,
    first_pass_acceptance_rate: 0.82,
    language_slice_agreement: {
      kk: 0.8,
      ru: 0.84,
      mixed: 0.81,
    },
  },
  candidate: {
    evaluated_count: 120,
    synthetic_count: 120,
    route_change_count: 14,
    labeled_count: 120,
    confirmed_route_agreement: 0.91,
    route_matched_case_count: 109,
    historical_handoff_rate_on_route_matched_cases: 0.03,
    operator_override_rate: 0.09,
    first_pass_acceptance_rate: 0.91,
    language_slice_agreement: {
      kk: 0.9,
      ru: 0.92,
      mixed: 0.89,
    },
  },
  decision:
    "descriptive historical replay complete; candidate shows improved agreement and reduced handoffs across all language slices",
  promoted: false,
};

const SAMPLE_SUMMARIES: ReplayReportSummary[] = [
  {
    report_id: "replay-rep-synthetic-001",
    dataset_id: "dataset-kar-2026-q3",
    region_id: "KAR",
    cutoff_at: "2026-09-10T23:59:00Z",
    baseline_policy_id: "routing-kar-standard",
    baseline_version: "1.0.0",
    candidate_policy_id: "routing-kar-candidate",
    candidate_version: "1.1.0",
    created_at: "2026-09-11T12:00:00Z",
    decision: "improved agreement and reduced handoffs",
  },
];

function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export function ReplayLabPanel({
  locale,
  regionId = "KAR",
}: {
  locale: Locale;
  regionId?: string;
}) {
  const copy = text[locale];
  const [region, setRegion] = useState(regionId);
  const [reports, setReports] =
    useState<ReplayReportSummary[]>(SAMPLE_SUMMARIES);
  const [selectedReportId, setSelectedReportId] = useState<string>(
    SAMPLE_REPLAY_REPORT.report_id,
  );
  const [activeReport, setActiveReport] =
    useState<ReplayReport>(SAMPLE_REPLAY_REPORT);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadReports() {
      setLoading(true);
      try {
        const res = await fetch("/api/core/replay/reports", {
          headers: { "X-Region-Id": region },
          cache: "no-store",
        });
        if (!res.ok) throw new Error("reports_unavailable");
        const list = (await res.json()) as ReplayReportSummary[];
        if (!cancelled && list.length > 0) {
          setReports(list);
          setSelectedReportId(list[0].report_id);
        }
      } catch {
        // Fallback to sample data for local environment
        if (!cancelled) {
          setReports(SAMPLE_SUMMARIES);
          setSelectedReportId(SAMPLE_REPLAY_REPORT.report_id);
          setActiveReport(SAMPLE_REPLAY_REPORT);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadReports();
    return () => {
      cancelled = true;
    };
  }, [region]);

  useEffect(() => {
    let cancelled = false;
    async function loadDetail() {
      if (!selectedReportId) return;
      try {
        const res = await fetch(
          `/api/core/replay/reports/${encodeURIComponent(selectedReportId)}`,
          {
            headers: { "X-Region-Id": region },
            cache: "no-store",
          },
        );
        if (!res.ok) throw new Error("detail_unavailable");
        const report = (await res.json()) as ReplayReport;
        if (!cancelled) setActiveReport(report);
      } catch {
        // Keep sample detail
        if (!cancelled) setActiveReport(SAMPLE_REPLAY_REPORT);
      }
    }
    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedReportId, region]);

  const b = activeReport.baseline;
  const c = activeReport.candidate;

  return (
    <section className="closure-panel" aria-labelledby="replay-lab-title">
      <header className="closure-heading">
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="replay-lab-title">{copy.title}</h2>
          <p>{copy.intro}</p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <label
            style={{
              fontSize: "12px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Globe size={14} />
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              style={{ padding: "4px 8px", font: "inherit", fontWeight: 700 }}
            >
              <option value="KAR">KAR (Karaganda)</option>
              <option value="AST">AST (Astana)</option>
              <option value="ALA">ALA (Almaty)</option>
            </select>
          </label>
          <button
            type="button"
            className="action-secondary"
            onClick={() => setRegion((prev) => `${prev}`)}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              padding: "4px 8px",
              fontSize: "12px",
            }}
          >
            <RefreshCw size={12} className={loading ? "spin" : ""} />
            {copy.refresh}
          </button>
          <span className="state-present">DESCRIPTIVE ONLY</span>
        </div>
      </header>

      {/* Reports List Carousel/Grid */}
      <div style={{ marginTop: "16px", marginBottom: "16px" }}>
        <h3
          style={{ fontSize: "13px", fontWeight: "700", marginBottom: "8px" }}
        >
          {copy.reports} ({reports.length})
        </h3>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {reports.map((r) => (
            <button
              key={r.report_id}
              type="button"
              onClick={() => setSelectedReportId(r.report_id)}
              style={{
                textAlign: "left",
                padding: "8px 12px",
                border: `1px solid ${selectedReportId === r.report_id ? "var(--teal)" : "var(--line)"}`,
                borderRadius: "4px",
                background:
                  selectedReportId === r.report_id ? "#f0f9f8" : "#fff",
                cursor: "pointer",
                minWidth: "220px",
              }}
            >
              <div style={{ fontSize: "12px", fontWeight: "700" }}>
                {r.report_id}
              </div>
              <div style={{ fontSize: "11px", color: "var(--muted)" }}>
                {r.baseline_policy_id}:v{r.baseline_version} →{" "}
                {r.candidate_policy_id}:v{r.candidate_version}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Comparison Scorecards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        {/* Metric 1: Route Agreement */}
        <div
          style={{
            padding: "12px",
            background: "#fff",
            border: "1px solid var(--line)",
            borderRadius: "4px",
          }}
        >
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.routeAgreement}
          </small>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "8px",
              marginTop: "4px",
            }}
          >
            <span
              style={{
                fontSize: "20px",
                fontWeight: "700",
                color: "var(--teal)",
              }}
            >
              {percent(c.confirmed_route_agreement)}
            </span>
            <span style={{ fontSize: "13px", color: "var(--muted)" }}>
              база: {percent(b.confirmed_route_agreement)}
            </span>
          </div>
          <div
            style={{ fontSize: "11px", color: "var(--teal)", marginTop: "4px" }}
          >
            ▲ +
            {Math.round(
              ((c.confirmed_route_agreement ?? 0) -
                (b.confirmed_route_agreement ?? 0)) *
                100,
            )}
            % прирост
          </div>
        </div>

        {/* Metric 2: Operator Override Rate */}
        <div
          style={{
            padding: "12px",
            background: "#fff",
            border: "1px solid var(--line)",
            borderRadius: "4px",
          }}
        >
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.overrideRate}
          </small>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "8px",
              marginTop: "4px",
            }}
          >
            <span
              style={{
                fontSize: "20px",
                fontWeight: "700",
                color: "var(--teal)",
              }}
            >
              {percent(c.operator_override_rate)}
            </span>
            <span style={{ fontSize: "13px", color: "var(--muted)" }}>
              база: {percent(b.operator_override_rate)}
            </span>
          </div>
          <div
            style={{ fontSize: "11px", color: "var(--teal)", marginTop: "4px" }}
          >
            ▼ -
            {Math.round(
              ((b.operator_override_rate ?? 0) -
                (c.operator_override_rate ?? 0)) *
                100,
            )}
            % снижение правок
          </div>
        </div>

        {/* Metric 3: First-Pass Acceptance */}
        <div
          style={{
            padding: "12px",
            background: "#fff",
            border: "1px solid var(--line)",
            borderRadius: "4px",
          }}
        >
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.firstPassRate}
          </small>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "8px",
              marginTop: "4px",
            }}
          >
            <span
              style={{
                fontSize: "20px",
                fontWeight: "700",
                color: "var(--teal)",
              }}
            >
              {percent(c.first_pass_acceptance_rate)}
            </span>
            <span style={{ fontSize: "13px", color: "var(--muted)" }}>
              база: {percent(b.first_pass_acceptance_rate)}
            </span>
          </div>
          <div
            style={{ fontSize: "11px", color: "var(--teal)", marginTop: "4px" }}
          >
            ▲ +
            {Math.round(
              ((c.first_pass_acceptance_rate ?? 0) -
                (b.first_pass_acceptance_rate ?? 0)) *
                100,
            )}
            % успех
          </div>
        </div>

        {/* Metric 4: Historical Handoff Churn */}
        <div
          style={{
            padding: "12px",
            background: "#fff",
            border: "1px solid var(--line)",
            borderRadius: "4px",
          }}
        >
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.handoffRate}
          </small>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "8px",
              marginTop: "4px",
            }}
          >
            <span
              style={{
                fontSize: "20px",
                fontWeight: "700",
                color: "var(--teal)",
              }}
            >
              {percent(c.historical_handoff_rate_on_route_matched_cases)}
            </span>
            <span style={{ fontSize: "13px", color: "var(--muted)" }}>
              база: {percent(b.historical_handoff_rate_on_route_matched_cases)}
            </span>
          </div>
          <div
            style={{ fontSize: "11px", color: "var(--teal)", marginTop: "4px" }}
          >
            ▼ -
            {Math.round(
              ((b.historical_handoff_rate_on_route_matched_cases ?? 0) -
                (c.historical_handoff_rate_on_route_matched_cases ?? 0)) *
                100,
            )}
            % пересылок
          </div>
        </div>
      </div>

      {/* Language Slices Comparison Table */}
      <div
        style={{
          background: "#fff",
          border: "1px solid var(--line)",
          borderRadius: "4px",
          padding: "16px",
          marginBottom: "20px",
        }}
      >
        <h3
          style={{ fontSize: "14px", fontWeight: "700", marginBottom: "12px" }}
        >
          {copy.languageSlices}
        </h3>
        <div style={{ display: "grid", gap: "10px" }}>
          {/* Kazakh Slice */}
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "12px",
                marginBottom: "4px",
              }}
            >
              <span>{copy.kazakh}</span>
              <span>
                {percent(b.language_slice_agreement.kk)} →{" "}
                <strong>{percent(c.language_slice_agreement.kk)}</strong>
              </span>
            </div>
            <div
              style={{
                height: "8px",
                background: "#f0f2f1",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${(c.language_slice_agreement.kk ?? 0) * 100}%`,
                  background: "var(--teal)",
                }}
              />
            </div>
          </div>

          {/* Russian Slice */}
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "12px",
                marginBottom: "4px",
              }}
            >
              <span>{copy.russian}</span>
              <span>
                {percent(b.language_slice_agreement.ru)} →{" "}
                <strong>{percent(c.language_slice_agreement.ru)}</strong>
              </span>
            </div>
            <div
              style={{
                height: "8px",
                background: "#f0f2f1",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${(c.language_slice_agreement.ru ?? 0) * 100}%`,
                  background: "var(--teal)",
                }}
              />
            </div>
          </div>

          {/* Mixed Slice */}
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "12px",
                marginBottom: "4px",
              }}
            >
              <span>{copy.mixed}</span>
              <span>
                {percent(b.language_slice_agreement.mixed)} →{" "}
                <strong>{percent(c.language_slice_agreement.mixed)}</strong>
              </span>
            </div>
            <div
              style={{
                height: "8px",
                background: "#f0f2f1",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${(c.language_slice_agreement.mixed ?? 0) * 100}%`,
                  background: "var(--teal)",
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Dataset & Cutoff Metadata */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "12px",
          padding: "12px",
          background: "var(--canvas)",
          border: "1px solid var(--line)",
          borderRadius: "4px",
          fontSize: "12px",
          marginBottom: "16px",
        }}
      >
        <div>
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.cutoffDate}
          </small>
          <strong>{activeReport.cutoff_at}</strong>
        </div>
        <div>
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.casesEvaluated}
          </small>
          <strong>{activeReport.candidate.evaluated_count}</strong>
        </div>
        <div>
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.syntheticCases}
          </small>
          <span className="state-stale">
            {activeReport.candidate.synthetic_count}
          </span>
        </div>
        <div>
          <small style={{ color: "var(--muted)", display: "block" }}>
            SHA-256 Digest
          </small>
          <span style={{ fontFamily: "monospace", fontSize: "11px" }}>
            {activeReport.dataset_digest.slice(0, 16)}…
          </span>
        </div>
      </div>

      {/* Decision Summary */}
      <div
        style={{
          padding: "12px",
          background: "#fff",
          border: "1px solid var(--line)",
          borderRadius: "4px",
          marginBottom: "16px",
        }}
      >
        <strong
          style={{ fontSize: "12px", display: "block", marginBottom: "4px" }}
        >
          {copy.decisionText}
        </strong>
        <p style={{ margin: 0, fontSize: "12px", color: "var(--ink)" }}>
          {activeReport.decision}
        </p>
      </div>

      {/* Safety & Non-Promotion Governance Warning */}
      <footer
        style={{
          padding: "10px 14px",
          background: "#fef3f2",
          border: "1px solid #fecdca",
          borderRadius: "4px",
          fontSize: "11px",
          color: "var(--accent)",
          display: "flex",
          gap: "10px",
          alignItems: "center",
        }}
      >
        <ShieldAlert size={18} style={{ flexShrink: 0 }} />
        <span>{copy.governanceNotice}</span>
      </footer>
    </section>
  );
}
