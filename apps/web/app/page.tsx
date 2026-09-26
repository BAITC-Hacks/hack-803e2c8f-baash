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
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";

import { Intake } from "./intake";
import { AdminPanel } from "./admin-panel";
import { SituationCenter } from "./situation-center";
import { OwnershipHandoffPanel } from "./ownership-handoff-panel";
import { ClosureIntegrityPanel } from "./closure-integrity-panel";
import { IncidentTopologyPanel } from "./incident-topology-panel";
import { ReplayLabPanel } from "./replay-lab-panel";

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
type LatestAssignment = {
  assignment_id: string;
  request_id: string;
  service_id: string;
  assignee_unit_id: string | null;
};

type Locale = "ru" | "kk";
type DemoState =
  | "ready"
  | "loading"
  | "low_confidence"
  | "ml_unavailable"
  | "stale_catalog"
  | "sync_retry"
  | "forbidden_region"
  | "recovered";

const copy = {
  ru: {
    intake: "Подать обращение",
    queue: "Очередь оператора",
    topology: "Топология инцидентов",
    replay: "Replay Lab",
    situation: "Ситуационный центр",
    admin: "Администрирование",
    profile: "Локальный оператор · синтетические данные",
    appeals: "Обращения на проверку",
    synthetic: "синтетических",
    selected: "Выбранное обращение",
    humanDecision: "Решение человека",
    chooseAction: "Выберите действие",
    confirm: "Подтвердить рекомендацию",
    manual: "Сохранить ручное решение",
    correctionReason: "Причина исправления",
    optionalNote: "Необязательная заметка",
    noAssignment: "Назначение не отправляется без подтверждения человека.",
    evidence: "Доказательства",
    similar: "Похожие решённые обращения",
    duplicates: "Кандидаты в дубликаты",
    workflow: "Состояния демо",
    retry: "Повторить синхронизацию",
    ready: "Готово",
    loading: "Загрузка карточки…",
    low_confidence: "Низкая уверенность: требуется проверка",
    ml_unavailable: "ML недоступен: ручной режим активен",
    stale_catalog: "Справочник устарел: ручной выбор обязателен",
    sync_retry: "Внешняя синхронизация ожидает повтора",
    forbidden_region: "Нет доступа к региону",
    recovered: "Сессия восстановлена",
    auditRecorded: "Аудит записан",
  },
  kk: {
    intake: "Өтініш беру",
    queue: "Оператор кезегі",
    topology: "Оқиғалар топологиясы",
    replay: "Replay Lab",
    situation: "Жағдай орталығы",
    admin: "Әкімшілендіру",
    profile: "Жергілікті оператор · синтетикалық деректер",
    appeals: "Тексеруді қажет ететін өтініштер",
    synthetic: "синтетикалық",
    selected: "Таңдалған өтініш",
    humanDecision: "Адам шешімі",
    chooseAction: "Әрекетті таңдаңыз",
    confirm: "Ұсынысты растау",
    manual: "Қолмен шешімді сақтау",
    correctionReason: "Түзету себебі",
    optionalNote: "Міндетті емес ескертпе",
    noAssignment: "Адам растамайынша тағайындау жіберілмейді.",
    evidence: "Дәлелдер",
    similar: "Ұқсас шешілген өтініштер",
    duplicates: "Дубликат үміткерлері",
    workflow: "Демо күйлері",
    retry: "Синхрондауды қайталау",
    ready: "Дайын",
    loading: "Карточка жүктелуде…",
    low_confidence: "Сенім төмен: тексеру қажет",
    ml_unavailable: "ML қолжетімсіз: қолмен режим іске қосылды",
    stale_catalog: "Каталог ескірген: қолмен таңдау қажет",
    sync_retry: "Сыртқы синхрондау қайталауды күтуде",
    forbidden_region: "Аймаққа кіруге рұқсат жоқ",
    recovered: "Сессия қалпына келтірілді",
    auditRecorded: "Аудит жазылды",
  },
} as const;

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
  const [view, setView] = useState<
    "queue" | "situation" | "intake" | "admin" | "topology" | "replay"
  >("queue");
  const [locale, setLocale] = useState<Locale>("ru");
  const [appealsList, setAppealsList] = useState<Appeal[]>(appeals);
  const [isLive, setIsLive] = useState(false);
  const [selectedId, setSelectedId] = useState(appeals[0].id);
  const [latestAssignment, setLatestAssignment] =
    useState<LatestAssignment | null>(null);
  const [decision, setDecision] = useState<"pending" | "confirmed" | "manual">(
    "pending",
  );
  const [demoState, setDemoState] = useState<DemoState>("ready");
  const [decisionAction, setDecisionAction] = useState<
    "confirm" | "manual" | null
  >(null);
  const [correctionReason, setCorrectionReason] = useState("");
  const [operatorNote, setOperatorNote] = useState("");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const decisionTriggerRef = useRef<HTMLButtonElement>(null);
  const [manualTopic, setManualTopic] = useState("Street lighting");
  const [manualService, setManualService] = useState("City services");
  const [priority, setPriority] = useState("Routine");
  const appeal = useMemo(
    () => appealsList.find((item) => item.id === selectedId) ?? appealsList[0],
    [appealsList, selectedId],
  );
  const hasDecision = decision !== "pending";
  const decisionLabel =
    decision === "confirmed"
      ? locale === "ru"
        ? "Рекомендация подтверждена"
        : "Ұсыныс расталды"
      : locale === "ru"
        ? "Ручное решение записано"
        : "Қолмен шешім жазылды";
  const text = copy[locale];

  useEffect(() => {
    document.documentElement.lang = locale === "ru" ? "ru" : "kk";
  }, [locale]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/core/requests?limit=50", {
      headers: { "X-Region-Id": "ALL" },
      cache: "no-store",
    })
      .then(async (res) => {
        if (!res.ok) return null;
        return res.json();
      })
      .then((data) => {
        if (
          cancelled ||
          !data ||
          !Array.isArray(data.items) ||
          data.items.length === 0
        ) {
          return;
        }
        const live: Appeal[] = data.items.map(
          (item: Record<string, unknown>) => ({
            id: String(item.request_id || item.id),
            region: String(item.region_id || "ALA"),
            channel: String(item.channel || "web"),
            time: String(item.received_at_quality || "exact"),
            state: String(item.status || "new"),
            observed: item.created_at
              ? new Date(String(item.created_at)).toLocaleString("en-GB", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : "Recently",
            summary: String(
              item.text || item.summary || "Citizen appeal description.",
            ),
            confidence: "high" as const,
            ood: 0.05,
            topics: [
              {
                id: String(item.category || "roads"),
                label: String(item.category || "Road maintenance"),
                score: 0.88,
              },
              { id: "utilities", label: "Utilities", score: 0.42 },
            ],
            services: [
              { id: "roads-service", label: "Roads department", score: 0.85 },
              { id: "district", label: "District office", score: 0.35 },
            ],
          }),
        );
        setAppealsList(live);
        setIsLive(true);
        setSelectedId(live[0].id);
      })
      .catch(() => {
        // Core offline; keep synthetic fallback
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
        selectedId,
      )
    )
      return;
    let cancelled = false;
    fetch(
      `/api/core/requests/${encodeURIComponent(selectedId)}/assignments/latest`,
      {
        headers: { "X-Region-Id": appeal.region },
        cache: "no-store",
      },
    )
      .then(async (response) => {
        if (!response.ok) throw new Error("assignment_unavailable");
        return (await response.json()) as LatestAssignment;
      })
      .then((assignment) => {
        if (!cancelled) setLatestAssignment(assignment);
      })
      .catch(() => {
        if (!cancelled) setLatestAssignment(null);
      });
    return () => {
      cancelled = true;
    };
  }, [appeal.region, selectedId]);

  useEffect(() => {
    if (decisionAction && dialogRef.current && !dialogRef.current.open) {
      dialogRef.current.showModal();
    }
  }, [decisionAction]);

  function closeDecisionDialog() {
    dialogRef.current?.close();
    setDecisionAction(null);
    decisionTriggerRef.current?.focus();
  }

  function openDecisionDialog(
    action: "confirm" | "manual",
    event: MouseEvent<HTMLButtonElement>,
  ) {
    decisionTriggerRef.current = event.currentTarget;
    setDecisionAction(action);
  }

  function saveDecision() {
    if (decisionAction === "manual" && !correctionReason) return;
    setDecision(decisionAction === "confirm" ? "confirmed" : "manual");
    closeDecisionDialog();
  }

  function selectAppeal(id: string) {
    setSelectedId(id);
    setDecision("pending");
    setCorrectionReason("");
    setOperatorNote("");
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand">Pulse 109</div>
        <div className="view-switch" aria-label="Workspace view" role="group">
          <button
            aria-pressed={view === "intake"}
            onClick={() => setView("intake")}
            type="button"
          >
            {text.intake}
          </button>
          <button
            aria-pressed={view === "queue"}
            onClick={() => setView("queue")}
            type="button"
          >
            {text.queue}
          </button>
          <button
            aria-pressed={view === "topology"}
            onClick={() => setView("topology")}
            type="button"
          >
            {text.topology}
          </button>
          <button
            aria-pressed={view === "replay"}
            onClick={() => setView("replay")}
            type="button"
          >
            {text.replay}
          </button>
          <button
            aria-pressed={view === "situation"}
            onClick={() => setView("situation")}
            type="button"
          >
            {text.situation}
          </button>
          <button
            aria-pressed={view === "admin"}
            onClick={() => setView("admin")}
            type="button"
          >
            {text.admin}
          </button>
        </div>
        <div className="topbar-actions">
          <div className="locale-switch" aria-label="Language" role="group">
            <button
              aria-pressed={locale === "ru"}
              onClick={() => setLocale("ru")}
              type="button"
            >
              RU
            </button>
            <button
              aria-pressed={locale === "kk"}
              onClick={() => setLocale("kk")}
              type="button"
            >
              KZ
            </button>
          </div>
          <div className="profile">{text.profile}</div>
        </div>
      </header>
      {view === "intake" ? (
        <Intake locale={locale} />
      ) : view === "situation" ? (
        <SituationCenter />
      ) : view === "admin" ? (
        <AdminPanel locale={locale} />
      ) : view === "topology" ? (
        <IncidentTopologyPanel locale={locale} regionId={appeal.region} />
      ) : view === "replay" ? (
        <ReplayLabPanel locale={locale} regionId={appeal.region} />
      ) : (
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
                <p className="eyebrow">{text.queue}</p>
                <h1>{text.appeals}</h1>
              </div>
              <span className="count">
                {isLive
                  ? `${appealsList.length} ${locale === "ru" ? "обращений" : "өтініш"}`
                  : `3 ${text.synthetic}`}
              </span>
            </div>
            <section
              className="workflow-state"
              aria-labelledby="workflow-state-title"
            >
              <div>
                <p className="eyebrow">{text.workflow}</p>
                <h2 id="workflow-state-title">{text[demoState]}</h2>
              </div>
              <label>
                <span className="sr-only">{text.workflow}</span>
                <select
                  value={demoState}
                  onChange={(event) =>
                    setDemoState(event.target.value as DemoState)
                  }
                >
                  <option value="ready">{text.ready}</option>
                  <option value="loading">{text.loading}</option>
                  <option value="low_confidence">{text.low_confidence}</option>
                  <option value="ml_unavailable">{text.ml_unavailable}</option>
                  <option value="stale_catalog">{text.stale_catalog}</option>
                  <option value="sync_retry">{text.sync_retry}</option>
                  <option value="forbidden_region">
                    {text.forbidden_region}
                  </option>
                  <option value="recovered">{text.recovered}</option>
                </select>
              </label>
            </section>
            <div
              className="queue"
              role="table"
              aria-label={
                isLive ? "Live appeal queue" : "Synthetic appeal queue"
              }
            >
              <div className="queue-head" role="row">
                <span role="columnheader">Appeal</span>
                <span role="columnheader">Region</span>
                <span role="columnheader">Channel</span>
                <span role="columnheader">Time quality</span>
                <span role="columnheader">State</span>
                <span aria-hidden="true" />
              </div>
              {appealsList.map((item) => (
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
                    className={
                      item.time === "missing" ? "attention" : undefined
                    }
                  >
                    {item.time}
                  </span>
                  <span role="cell">{item.state}</span>
                  <ChevronRight aria-hidden="true" size={17} />
                </button>
              ))}
            </div>

            {demoState === "forbidden_region" ? (
              <section
                className="security-state"
                role="alert"
                aria-labelledby="forbidden-title"
              >
                <ShieldCheck aria-hidden="true" size={24} />
                <h2 id="forbidden-title">{text.forbidden_region}</h2>
                <p>
                  This appeal is outside the signed-in operator&apos;s region
                  scope.
                </p>
              </section>
            ) : (
              <section
                className="appeal-card"
                aria-labelledby="appeal-title"
                aria-busy={demoState === "loading"}
              >
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
                  <span
                    className={`confidence confidence-${appeal.confidence}`}
                  >
                    {appeal.confidence === "out_of_domain"
                      ? "Out of domain"
                      : `${appeal.confidence} confidence`}
                  </span>
                </div>
                <div className="recommendation-grid">
                  <RecommendationList title="Topics" items={appeal.topics} />
                  <RecommendationList
                    title="Services"
                    items={appeal.services}
                  />
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
                      <p className="eyebrow">{text.humanDecision}</p>
                      <h3>{hasDecision ? decisionLabel : text.chooseAction}</h3>
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
                      onClick={(event) => openDecisionDialog("confirm", event)}
                      type="button"
                    >
                      <Check aria-hidden="true" size={16} /> {text.confirm}
                    </button>
                    <button
                      className="secondary-action"
                      disabled={hasDecision}
                      onClick={(event) => openDecisionDialog("manual", event)}
                      type="button"
                    >
                      <FileCheck2 aria-hidden="true" size={16} /> {text.manual}
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
                        onChange={(event) =>
                          setManualService(event.target.value)
                        }
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
                      : text.noAssignment}
                  </p>
                </div>

                <div className="evidence-grid">
                  <EvidencePanel
                    title={text.similar}
                    items={[
                      "Resolved street lighting · 410 m",
                      "School entrance lighting · 1.2 km",
                    ]}
                  />
                  <EvidencePanel
                    title={text.duplicates}
                    items={[
                      "Text overlap 0.52 · distance 0.23 · time 0.14",
                      "Service match · human confirmation required",
                    ]}
                  />
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
                          <span>
                            {modelVersion} · human confirmation required
                          </span>
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
                <OwnershipHandoffPanel
                  key={selectedId}
                  locale={locale}
                  regionId={appeal.region}
                  initialRequestId={appeal.id}
                  assignmentId={
                    latestAssignment?.request_id === selectedId
                      ? latestAssignment.assignment_id
                      : undefined
                  }
                  assignmentServiceId={
                    latestAssignment?.request_id === selectedId
                      ? latestAssignment.service_id
                      : undefined
                  }
                  assignmentUnitId={
                    latestAssignment?.request_id === selectedId
                      ? latestAssignment.assignee_unit_id
                      : undefined
                  }
                />
                <ClosureIntegrityPanel
                  key={`closure-${selectedId}`}
                  locale={locale}
                  regionId={appeal.region}
                  initialRequestId={appeal.id}
                />
              </section>
            )}

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
      )}
      <p className="sr-only" role="status" aria-live="polite">
        {hasDecision
          ? `${text.auditRecorded}: ${decisionLabel}`
          : text[demoState]}
      </p>
      <dialog
        ref={dialogRef}
        className="decision-dialog"
        onCancel={closeDecisionDialog}
      >
        <form
          method="dialog"
          onSubmit={(event) => {
            event.preventDefault();
            saveDecision();
          }}
        >
          <p className="eyebrow">{text.humanDecision}</p>
          <h2>{decisionAction === "confirm" ? text.confirm : text.manual}</h2>
          {decisionAction === "manual" ? (
            <>
              <label htmlFor="correction-reason">
                {text.correctionReason} <span aria-hidden="true">*</span>
              </label>
              <select
                id="correction-reason"
                required
                aria-describedby="correction-reason-help"
                value={correctionReason}
                onChange={(event) => setCorrectionReason(event.target.value)}
              >
                <option value="">
                  {locale === "ru" ? "Выберите причину" : "Себепті таңдаңыз"}
                </option>
                <option value="wrong_topic">
                  {locale === "ru" ? "Неверная категория" : "Қате санат"}
                </option>
                <option value="wrong_service">
                  {locale === "ru" ? "Неверная организация" : "Қате ұйым"}
                </option>
                <option value="missing_context">
                  {locale === "ru"
                    ? "Недостаточно контекста"
                    : "Контекст жеткіліксіз"}
                </option>
              </select>
              <span id="correction-reason-help" className="field-help">
                {locale === "ru"
                  ? "Причина попадёт в аудит."
                  : "Себеп аудитке жазылады."}
              </span>
              <label htmlFor="operator-note">{text.optionalNote}</label>
              <textarea
                id="operator-note"
                value={operatorNote}
                onChange={(event) => setOperatorNote(event.target.value)}
                maxLength={2000}
              />
            </>
          ) : (
            <p>{text.noAssignment}</p>
          )}
          <div className="dialog-actions">
            <button
              className="secondary-action"
              type="button"
              autoFocus
              onClick={closeDecisionDialog}
            >
              {locale === "ru" ? "Отмена" : "Бас тарту"}
            </button>
            <button
              className="primary-action"
              type="submit"
              disabled={decisionAction === "manual" && !correctionReason}
            >
              {locale === "ru" ? "Подтвердить" : "Растау"}
            </button>
          </div>
        </form>
      </dialog>
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

function EvidencePanel({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="evidence-panel" aria-labelledby={`evidence-${title}`}>
      <h3 id={`evidence-${title}`}>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
