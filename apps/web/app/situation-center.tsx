"use client";

import {
  AlertTriangle,
  BarChart3,
  Check,
  Clock3,
  FileSpreadsheet,
  FileText,
  MapPinned,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";

const trend = [8, 10, 9, 12, 11, 13, 8];
const maxTrend = Math.max(...trend);

export function SituationCenter() {
  const [alertState, setAlertState] = useState<"new" | "acknowledged">("new");
  const [reportState, setReportState] = useState<"idle" | "pdf" | "xlsx">(
    "idle",
  );

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
              <p className="eyebrow">Action required</p>
              <h2 id="alert-title">Data quality alert</h2>
            </div>
            <AlertTriangle aria-hidden="true" size={20} />
          </div>
          <dl className="alert-details">
            <div>
              <dt>Region</dt>
              <dd>KAR</dd>
            </div>
            <div>
              <dt>State</dt>
              <dd>{alertState}</dd>
            </div>
            <div>
              <dt>Evidence</dt>
              <dd>Source batch missing</dd>
            </div>
          </dl>
          <button
            className="secondary-action"
            disabled={alertState === "acknowledged"}
            onClick={() => setAlertState("acknowledged")}
            type="button"
          >
            <Check aria-hidden="true" size={16} /> Acknowledge
          </button>
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
