"use client";

import {
  Check,
  ChevronRight,
  Clock3,
  Database,
  FileCheck2,
  History,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import { useMemo, useState } from "react";

type Recommendation = { id: string; label: string; score: number };
type Appeal = {
  id: string;
  region: string;
  channel: string;
  time: string;
  state: string;
  observed: string;
  summary: string;
  confidence: "high" | "medium" | "out_of_domain";
  ood: number;
  topics: Recommendation[];
  services: Recommendation[];
};

const appeals: Appeal[] = [
  {
    id: "SYN-109-014",
    region: "AST",
    channel: "phone",
    time: "exact",
    state: "new",
    observed: "11 Sep 2026, 09:42",
    summary: "Street lighting is unavailable near the school entrance.",
    confidence: "high",
    ood: 0.08,
    topics: [
      { id: "lighting", label: "Street lighting", score: 0.94 },
      { id: "roads", label: "Road maintenance", score: 0.48 },
      { id: "utilities", label: "Utilities", score: 0.31 },
    ],
    services: [
      { id: "city-services", label: "City services", score: 0.91 },
      { id: "roads-service", label: "Roads department", score: 0.44 },
      { id: "district", label: "District office", score: 0.29 },
    ],
  },
  {
    id: "SYN-109-013",
    region: "ALA",
    channel: "web",
    time: "date only",
    state: "triage",
    observed: "11 Sep 2026, 08:17",
    summary: "A pothole is affecting access to a residential courtyard.",
    confidence: "medium",
    ood: 0.34,
    topics: [
      { id: "roads", label: "Road maintenance", score: 0.74 },
      { id: "lighting", label: "Street lighting", score: 0.38 },
      { id: "utilities", label: "Utilities", score: 0.22 },
    ],
    services: [
      { id: "roads-service", label: "Roads department", score: 0.72 },
      { id: "city-services", label: "City services", score: 0.51 },
      { id: "district", label: "District office", score: 0.35 },
    ],
  },
  {
    id: "SYN-109-012",
    region: "ALA",
    channel: "import",
    time: "missing",
    state: "new",
    observed: "11 Sep 2026, 07:03",
    summary:
      "The request needs a manual review before a service can be selected.",
    confidence: "out_of_domain",
    ood: 0.95,
    topics: [
      { id: "manual", label: "Manual catalog review", score: 0.4 },
      { id: "district", label: "District services", score: 0.3 },
      { id: "other", label: "Other", score: 0.2 },
    ],
    services: [
      { id: "district", label: "District office", score: 0.4 },
      { id: "city-services", label: "City services", score: 0.3 },
      { id: "manual", label: "Manual assignment", score: 0.2 },
    ],
  },
];

const modelVersion = "lexical-baseline-1.0.0";
const taxonomyVersion = "temporary/1.0.0";
const scoreLabel = (score: number) => `${Math.round(score * 100)}%`;

export default function OperatorWorkspace() {
  const [selectedId, setSelectedId] = useState(appeals[0].id);
  const [decision, setDecision] = useState<"pending" | "confirmed" | "manual">(
    "pending",
  );
  const [manualTopic, setManualTopic] = useState("Street lighting");
  const [manualService, setManualService] = useState("City services");
  const [priority, setPriority] = useState("Routine");
  const appeal = useMemo(
    () => appeals.find((item) => item.id === selectedId) ?? appeals[0],
    [selectedId],
  );
  const hasDecision = decision !== "pending";
  const decisionLabel =
    decision === "confirmed"
      ? "Recommendation confirmed"
      : "Manual decision recorded";

  function selectAppeal(id: string) {
    setSelectedId(id);
    setDecision("pending");
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand">Pulse 109</div>
        <div className="profile">Local operator · synthetic data</div>
      </header>
      <div className="workspace">
        <aside aria-label="Primary navigation">
          <nav>
            <a className="active" href="#queue">
              Queue
            </a>
            <a href="#quality">Data quality</a>
            <a href="#systems">Systems</a>
          </nav>
          <div className="fallback">
            <WifiOff aria-hidden="true" size={18} />
            <div>
              <strong>Manual mode</strong>
              <span>ML is optional</span>
            </div>
          </div>
        </aside>

        <section className="content" id="queue">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Operator queue</p>
              <h1>Appeals requiring review</h1>
            </div>
            <span className="count">3 synthetic</span>
          </div>
          <div
            className="queue"
            role="table"
            aria-label="Synthetic appeal queue"
          >
            <div className="queue-head" role="row">
              <span role="columnheader">Appeal</span>
              <span role="columnheader">Region</span>
              <span role="columnheader">Channel</span>
              <span role="columnheader">Time quality</span>
              <span role="columnheader">State</span>
              <span aria-hidden="true" />
            </div>
            {appeals.map((item) => (
              <button
                className={`queue-row ${item.id === selectedId ? "selected" : ""}`}
                key={item.id}
                onClick={() => selectAppeal(item.id)}
                role="row"
                type="button"
              >
                <strong role="cell">{item.id}</strong>
                <span role="cell">{item.region}</span>
                <span role="cell">{item.channel}</span>
                <span
                  role="cell"
                  className={item.time === "missing" ? "attention" : undefined}
                >
                  {item.time}
                </span>
                <span role="cell">{item.state}</span>
                <ChevronRight aria-hidden="true" size={17} />
              </button>
            ))}
          </div>

          <section className="appeal-card" aria-labelledby="appeal-title">
            <div className="appeal-header">
              <div>
                <p className="eyebrow">Selected appeal</p>
                <h2 id="appeal-title">{appeal.id}</h2>
                <p className="appeal-summary">{appeal.summary}</p>
              </div>
              <div className="appeal-status">
                <span className="status-chip">{appeal.state}</span>
                <span className="sync-chip">
                  <WifiOff aria-hidden="true" size={14} /> Sync pending
                </span>
              </div>
            </div>
            <div className="meta-grid">
              <div>
                <span>Region</span>
                <strong>{appeal.region}</strong>
              </div>
              <div>
                <span>Channel</span>
                <strong>{appeal.channel}</strong>
              </div>
              <div>
                <span>Observed</span>
                <strong>{appeal.observed}</strong>
              </div>
              <div>
                <span>Business time</span>
                <strong
                  className={
                    appeal.time === "missing" ? "attention" : undefined
                  }
                >
                  {appeal.time}
                </strong>
              </div>
            </div>
            <div className="advisory-heading">
              <div>
                <p className="eyebrow">Advisory routing</p>
                <h3>AI proposes; operator confirms</h3>
              </div>
              <span className={`confidence confidence-${appeal.confidence}`}>
                {appeal.confidence === "out_of_domain"
                  ? "Out of domain"
                  : `${appeal.confidence} confidence`}
              </span>
            </div>
            <div className="recommendation-grid">
              <RecommendationList title="Topics" items={appeal.topics} />
              <RecommendationList title="Services" items={appeal.services} />
              <div className="model-panel">
                <span className="panel-label">Model signal</span>
                <div className="signal-row">
                  <span>Confidence</span>
                  <strong>
                    {scoreLabel(
                      appeal.confidence === "out_of_domain"
                        ? 0.2
                        : appeal.topics[0].score,
                    )}
                  </strong>
                </div>
                <div className="signal-row">
                  <span>OOD score</span>
                  <strong>{scoreLabel(appeal.ood)}</strong>
                </div>
                <div className="signal-row">
                  <span>Model</span>
                  <strong>{modelVersion}</strong>
                </div>
                <div className="signal-row">
                  <span>Taxonomy</span>
                  <strong>{taxonomyVersion}</strong>
                </div>
              </div>
            </div>

            <div className="decision-area">
              <div className="decision-title">
                <div>
                  <p className="eyebrow">Human decision</p>
                  <h3>{hasDecision ? decisionLabel : "Choose an action"}</h3>
                </div>
                {hasDecision && (
                  <span className="recorded">
                    <Check aria-hidden="true" size={15} /> Recorded locally
                  </span>
                )}
              </div>
              <div className="decision-controls">
                <button
                  className="primary-action"
                  disabled={hasDecision}
                  onClick={() => setDecision("confirmed")}
                  type="button"
                >
                  <Check aria-hidden="true" size={16} /> Confirm recommendation
                </button>
                <button
                  className="secondary-action"
                  disabled={hasDecision}
                  onClick={() => setDecision("manual")}
                  type="button"
                >
                  <FileCheck2 aria-hidden="true" size={16} /> Save manual
                  decision
                </button>
              </div>
              <div className="manual-fields">
                <label>
                  Topic
                  <select
                    disabled={hasDecision}
                    onChange={(event) => setManualTopic(event.target.value)}
                    value={manualTopic}
                  >
                    <option>Street lighting</option>
                    <option>Road maintenance</option>
                    <option>Utilities</option>
                    <option>Manual catalog review</option>
                  </select>
                </label>
                <label>
                  Service
                  <select
                    disabled={hasDecision}
                    onChange={(event) => setManualService(event.target.value)}
                    value={manualService}
                  >
                    <option>City services</option>
                    <option>Roads department</option>
                    <option>District office</option>
                    <option>Manual assignment</option>
                  </select>
                </label>
                <label>
                  Priority
                  <select
                    disabled={hasDecision}
                    onChange={(event) => setPriority(event.target.value)}
                    value={priority}
                  >
                    <option>Routine</option>
                    <option>Elevated</option>
                    <option>Urgent</option>
                    <option>Emergency handoff</option>
                  </select>
                </label>
              </div>
              <p className="decision-note">
                {hasDecision
                  ? `${manualTopic} · ${manualService} · ${priority}`
                  : "No assignment is sent until a human confirms the route."}
              </p>
            </div>

            <div className="activity-grid">
              <div>
                <div className="activity-heading">
                  <History aria-hidden="true" size={17} />
                  <h3>Timeline</h3>
                </div>
                <ol className="timeline">
                  <li>
                    <span className="timeline-dot" />
                    <div>
                      <strong>Appeal received</strong>
                      <span>{appeal.observed} · source channel</span>
                    </div>
                  </li>
                  <li>
                    <span className="timeline-dot" />
                    <div>
                      <strong>Advisory produced</strong>
                      <span>{modelVersion} · human confirmation required</span>
                    </div>
                  </li>
                  {hasDecision && (
                    <li>
                      <span className="timeline-dot complete" />
                      <div>
                        <strong>{decisionLabel}</strong>
                        <span>Local operator · just now</span>
                      </div>
                    </li>
                  )}
                </ol>
              </div>
              <div>
                <div className="activity-heading">
                  <ShieldCheck aria-hidden="true" size={17} />
                  <h3>Audit and sync</h3>
                </div>
                <div className="audit-list">
                  <div>
                    <span>Audit event</span>
                    <strong>
                      {hasDecision ? "Recorded" : "Awaiting decision"}
                    </strong>
                  </div>
                  <div>
                    <span>External sync</span>
                    <strong className="attention">Pending</strong>
                  </div>
                  <div>
                    <span>Raw reference</span>
                    <strong>Opaque only</strong>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section
            className="status-band"
            id="quality"
            aria-labelledby="foundation-status"
          >
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Foundation status</p>
                <h2 id="foundation-status">Local critical path</h2>
              </div>
            </div>
            <div className="status-grid">
              <div>
                <Database aria-hidden="true" size={20} />
                <strong>Canonical data</strong>
                <span>Version 1.0.0</span>
              </div>
              <div>
                <ShieldCheck aria-hidden="true" size={20} />
                <strong>PII boundary</strong>
                <span>Opaque references only</span>
              </div>
              <div>
                <Clock3 aria-hidden="true" size={20} />
                <strong>Business time</strong>
                <span>Quality is explicit</span>
              </div>
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}

function RecommendationList({
  title,
  items,
}: {
  title: string;
  items: Recommendation[];
}) {
  return (
    <div className="recommendation-panel">
      <span className="panel-label">{title}</span>
      <ol>
        {items.map((item) => (
          <li key={item.id}>
            <span>
              <b>{item.label}</b>
              <small>{item.id}</small>
            </span>
            <strong>{scoreLabel(item.score)}</strong>
          </li>
        ))}
      </ol>
    </div>
  );
}
