"use client";

import {
  AlertTriangle,
  BarChart3,
  Check,
  CheckCircle2,
  Clock3,
  FileSpreadsheet,
  FileText,
  MapPinned,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { useState } from "react";

import { SituationMap } from "./situation-map";

interface ActionableAlert {
  id: string;
  type: "data_quality" | "model_drift" | "incident_growth" | "sla_risk";
  title: string;
  region: string;
  severity: "critical" | "high" | "warning" | "info";
  status: "new" | "acknowledged" | "resolved" | "dismissed";
  evidence: string;
  detector: string;
  metricId: string;
}

const initialAlerts: ActionableAlert[] = [
  {
    id: "alert-dq-01",
    type: "data_quality",
    title: "Data quality alert",
    region: "KAR",
    severity: "warning",
    status: "new",
    evidence: "Source batch missing",
    detector: "source_freshness",
    metricId: "coverage · v1.0.0",
  },
  {
    id: "alert-hl-02",
    type: "model_drift",
    title: "Handoff loop alert",
    region: "ALA",
    severity: "high",
    status: "new",
    evidence: "Cycle: roads -> utilities -> roads (req-ala-109)",
    detector: "handoff_loop",
    metricId: "appeals_volume · v1.0.0",
  },
  {
    id: "alert-rs-03",
    type: "incident_growth",
    title: "Reopen spike alert",
    region: "AST",
    severity: "high",
    status: "new",
    evidence: "3 reopens within 24h on heating infrastructure",
    detector: "reopen_spike",
    metricId: "appeals_volume · v1.0.0",
  },
  {
    id: "alert-al-04",
    type: "sla_risk",
    title: "Adapter delivery lag",
    region: "ALA",
    severity: "warning",
    status: "new",
    evidence: "Outbox delivery delay 420s (2 retries)",
    detector: "adapter_lag",
    metricId: "sla_risk · v1.0.0",
  },
];

const trend = [8, 10, 9, 12, 11, 13, 8];
const maxTrend = Math.max(...trend);

export function SituationCenter() {
  const [alerts, setAlerts] = useState<ActionableAlert[]>(initialAlerts);
  const [selectedAlertId, setSelectedAlertId] = useState<string>("alert-dq-01");
  const [dispositionCode, setDispositionCode] = useState<string>(
    "VERIFIED_BY_OPERATOR",
  );
  const [lastReviewReceipt, setLastReviewReceipt] = useState<string | null>(
    null,
  );
  const [reportState, setReportState] = useState<"idle" | "pdf" | "xlsx">(
    "idle",
  );

  const selectedAlert =
    alerts.find((a) => a.id === selectedAlertId) ?? alerts[0];

  function handleReview(action: "acknowledge" | "resolve" | "dismiss") {
    const targetStatus =
      action === "acknowledge"
        ? "acknowledged"
        : action === "resolve"
          ? "resolved"
          : "dismissed";
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === selectedAlert.id ? { ...a, status: targetStatus } : a,
      ),
    );
    setLastReviewReceipt(
      `Alert ${selectedAlert.id} [${action.toUpperCase()}]: ${dispositionCode} at ${new Date().toISOString()}`,
    );
  }

  return (
    <section className="situation" aria-labelledby="situation-title">
      <div className="situation-heading">
        <div>
          <p className="eyebrow">Situation center</p>
          <h1 id="situation-title">Regional service overview</h1>
        </div>
        <div className="cutoff">
          <Clock3 aria-hidden="true" size={16} />
          <span>Cutoff 10 Sep 2026, 23:59 UTC</span>
        </div>
      </div>

      <section className="coverage-band" aria-labelledby="coverage-title">
        <div className="band-title">
          <MapPinned aria-hidden="true" size={19} />
          <div>
            <h2 id="coverage-title">Coverage and freshness</h2>
            <span>Metric ID: coverage · v1.0.0</span>
          </div>
        </div>
        <div className="coverage-list">
          <div>
            <strong>ALA</strong>
            <span className="state-present">Present</span>
            <small>Current at cutoff</small>
          </div>
          <div>
            <strong>AST</strong>
            <span className="state-stale">Stale</span>
            <small>Last source batch 8 Sep</small>
          </div>
          <div>
            <strong>KAR</strong>
            <span className="state-missing">Missing</span>
            <small>No source batch in range</small>
          </div>
        </div>
      </section>

      <div className="situation-grid">
        <SituationMap />
        <section className="trend-panel" aria-labelledby="trend-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Observed volume</p>
              <h2 id="trend-title">Seven-day trend</h2>
            </div>
            <BarChart3 aria-hidden="true" size={20} />
          </div>
          <div
            className="trend-chart"
            aria-label="Daily appeal volume: 8, 10, 9, 12, 11, 13, 8"
            role="img"
          >
            {trend.map((value, index) => (
              <div key={`${index}-${value}`}>
                <span
                  style={{ height: `${Math.round((value / maxTrend) * 100)}%` }}
                />
                <small>{index + 4} Sep</small>
              </div>
            ))}
          </div>
          <div className="metric-footer">
            <span>Metric ID: appeals_volume · v1.0.0</span>
            <strong>Synthetic fixture</strong>
          </div>
        </section>

        <section className="sla-panel" aria-labelledby="sla-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Service level</p>
              <h2 id="sla-title">SLA risk</h2>
            </div>
            <RefreshCw aria-hidden="true" size={19} />
          </div>
          <div className="empty-metric">
            <strong>Policy not approved</strong>
            <span>No risk value is calculated.</span>
          </div>
          <div className="metric-footer">
            <span>Metric ID: sla_risk · v1.0.0</span>
            <strong>Missing, not zero</strong>
          </div>
        </section>

        <section className="alert-panel" aria-labelledby="alert-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Action required · {selectedAlert.detector}
              </p>
              <h2 id="alert-title">{selectedAlert.title}</h2>
            </div>
            <AlertTriangle aria-hidden="true" size={20} />
          </div>

          <div
            style={{
              display: "flex",
              gap: "6px",
              margin: "8px 0 12px 0",
              overflowX: "auto",
              paddingBottom: "4px",
            }}
          >
            {alerts.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedAlertId(item.id)}
                style={{
                  fontSize: "12px",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  border:
                    item.id === selectedAlert.id
                      ? "1px solid var(--accent, #0066cc)"
                      : "1px solid var(--line, #ccc)",
                  background:
                    item.id === selectedAlert.id
                      ? "var(--accent-subtle, #e6f0fa)"
                      : "transparent",
                  cursor: "pointer",
                  fontWeight: item.id === selectedAlert.id ? 600 : 400,
                  whiteSpace: "nowrap",
                }}
              >
                {item.region}: {item.title.replace(" alert", "")} (
                {item.status.slice(0, 3)})
              </button>
            ))}
          </div>

          <dl className="alert-details">
            <div>
              <dt>Region</dt>
              <dd>{selectedAlert.region}</dd>
            </div>
            <div>
              <dt>State</dt>
              <dd>{selectedAlert.status}</dd>
            </div>
            <div>
              <dt>Severity</dt>
              <dd>{selectedAlert.severity.toUpperCase()}</dd>
            </div>
            <div>
              <dt>Evidence</dt>
              <dd>{selectedAlert.evidence}</dd>
            </div>
          </dl>

          <div
            style={{
              margin: "8px 0",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            <label
              htmlFor="disposition-select"
              style={{ fontSize: "11px", color: "var(--muted, #666)" }}
            >
              Review disposition code:
            </label>
            <select
              id="disposition-select"
              value={dispositionCode}
              onChange={(e) => setDispositionCode(e.target.value)}
              style={{
                fontSize: "12px",
                padding: "4px 8px",
                borderRadius: "4px",
                border: "1px solid var(--line, #ccc)",
                background: "var(--surface, #fff)",
              }}
            >
              <option value="VERIFIED_BY_OPERATOR">VERIFIED_BY_OPERATOR</option>
              <option value="RECONFIGURED">RECONFIGURED</option>
              <option value="EXTERNAL_BATCH_RETRIEVED">
                EXTERNAL_BATCH_RETRIEVED
              </option>
              <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
              <option value="ESCALATED_TO_SUPERVISOR">
                ESCALATED_TO_SUPERVISOR
              </option>
            </select>
          </div>

          <div
            style={{
              display: "flex",
              gap: "8px",
              marginTop: "auto",
              flexWrap: "wrap",
            }}
          >
            <button
              className="secondary-action"
              disabled={selectedAlert.status !== "new"}
              onClick={() => handleReview("acknowledge")}
              type="button"
            >
              <Check aria-hidden="true" size={16} /> Acknowledge
            </button>
            <button
              className="secondary-action"
              disabled={
                selectedAlert.status === "resolved" ||
                selectedAlert.status === "dismissed"
              }
              onClick={() => handleReview("resolve")}
              type="button"
              style={{ color: "var(--success, #008800)" }}
            >
              <CheckCircle2 aria-hidden="true" size={16} /> Resolve
            </button>
            <button
              className="secondary-action"
              disabled={
                selectedAlert.status === "resolved" ||
                selectedAlert.status === "dismissed"
              }
              onClick={() => handleReview("dismiss")}
              type="button"
              style={{ color: "var(--muted, #888)" }}
            >
              <XCircle aria-hidden="true" size={16} /> Dismiss
            </button>
          </div>

          {lastReviewReceipt && (
            <p
              style={{
                fontSize: "11px",
                color: "var(--muted, #666)",
                marginTop: "8px",
                wordBreak: "break-all",
              }}
            >
              <ShieldAlert
                aria-hidden="true"
                size={12}
                style={{ display: "inline", marginRight: "4px" }}
              />
              {lastReviewReceipt}
            </p>
          )}

          <div className="metric-footer" style={{ marginTop: "8px" }}>
            <span>Metric ID: {selectedAlert.metricId}</span>
            <strong>{selectedAlert.severity}</strong>
          </div>
        </section>

        <section className="forecast-panel" aria-labelledby="forecast-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Forecast</p>
              <h2 id="forecast-title">Seasonal naive</h2>
            </div>
          </div>
          <div className="forecast-values">
            <div>
              <span>Baseline</span>
              <strong>8</strong>
            </div>
            <div>
              <span>Lower</span>
              <strong>5.5</strong>
            </div>
            <div>
              <span>Upper</span>
              <strong>10.5</strong>
            </div>
          </div>
          <div className="metric-footer">
            <span>seasonal-naive-1.0.0</span>
            <strong>ALA only</strong>
          </div>
        </section>
      </div>

      <section className="report-band" aria-labelledby="report-title">
        <div>
          <p className="eyebrow">Governed exports</p>
          <h2 id="report-title">Situation report</h2>
          <span>Metric ID, version and cutoff are shared with this view.</span>
        </div>
        <div className="report-actions">
          <button
            onClick={() => setReportState("pdf")}
            type="button"
            title="Create PDF report"
          >
            <FileText aria-hidden="true" size={17} /> PDF
          </button>
          <button
            onClick={() => setReportState("xlsx")}
            type="button"
            title="Create spreadsheet report"
          >
            <FileSpreadsheet aria-hidden="true" size={17} /> XLSX
          </button>
        </div>
        <strong className="report-state" role="status">
          {reportState === "idle"
            ? "No report queued"
            : `${reportState.toUpperCase()} report queued`}
        </strong>
      </section>
    </section>
  );
}
