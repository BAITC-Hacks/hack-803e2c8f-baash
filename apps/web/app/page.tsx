"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Intake } from "./intake";
import { AnalyticsPanel } from "./analytics-panel";
import { ClosureIntegrityPanel } from "./closure-integrity-panel";
import { DataLab } from "./data-lab";
import { IncidentList } from "./incident-list";
import { IncidentWarRoom } from "./incident-war-room";
import { IncidentWorkflowPanel } from "./incident-workflow-panel";
import { OperationsCenter } from "./operations-center";
import { OwnershipHandoffPanel } from "./ownership-handoff-panel";
import { ReplayLab } from "./replay-lab";

type Locale = "ru" | "kk";
type Appeal = {
  request_id: string;
  source_system: string;
  source_request_id: string;
  region_id: string;
  channel: string;
  text: string | null;
  status: string;
  version: number;
  created_at: string;
  received_at_quality: string;
};
type Decision = {
  topic_id: string;
  service_id: string;
  priority: string;
  action: string;
};
type Detail = Appeal & {
  timeline: { event_id: string; event_type: string; observed_at: string }[];
  current_decision: Decision | null;
  synchronization: { status: string; external_id: string | null } | null;
};
type Recommendation = {
  recommendation_id: string;
  model_version: string;
  confidence_band: string;
  top_topics: { id: string; score: number }[];
  top_services: { id: string; score: number }[];
  priority: string;
};
type AttachmentRef = {
  attachment_id: string;
  file_name: string;
  object_hash: string;
};

// The region is configuration, not a constant of the product. An operator's
// allowed regions come from the session endpoint whenever an identity provider
// supplies them. The demo profile has no identity provider (blocker B08) and its
// local fallback mirrors whatever region it was asked about, so this default
// stands in until a real one is connected.
const DEFAULT_REGION = process.env.NEXT_PUBLIC_PULSE109_REGION ?? "ALA";

type SessionContext = {
  regions: string[];
  authentication_source: string;
};

const labels = {
  ru: {
    operations: "Операционный центр",
    incidents: "Инциденты",
    replay: "Replay Lab",
    datalab: "Лаборатория данных",
    intake: "Подать обращение",
    queue: "Очередь оператора",
    situation: "Статус платформы",
    statusImplemented:
      "Очередь, решения, аудит, outbox и рабочий процесс используют действующие сервисы приложения и PostgreSQL. Обращения и replay-доставка в демо синтетические.",
    statusBlocked:
      "Подключение региональной CRM, утверждённая идентификация, правила классификации и SLA, защищённое хранилище вложений и оценка модели на реальных данных пока недоступны.",
    statusCoverage:
      "API инцидентов, Replay Lab и подписанной конфигурации реализованы шире, чем их операторский интерфейс. Подробности — в матрице функций репозитория.",
    loading: "Загрузка обращений…",
    refresh: "Обновить",
    classify: "Получить рекомендацию",
    manual: "Сохранить ручное решение",
    accept: "Подтвердить рекомендацию",
    assign: "Поставить назначение в очередь",
    status: "Записать статус",
    unavailable: "Рекомендация недоступна; ручной путь остаётся доступным.",
    empty:
      "В этом регионе пока нет обращений. Создайте синтетическое обращение через форму или запустите seed.",
  },
  kk: {
    operations: "Операциялық орталық",
    incidents: "Оқиғалар",
    replay: "Replay Lab",
    datalab: "Деректер зертханасы",
    intake: "Өтініш беру",
    queue: "Оператор кезегі",
    situation: "Платформа мәртебесі",
    statusImplemented:
      "Кезек, шешімдер, аудит, outbox және жұмыс процесі қолданбаның нақты сервистері мен PostgreSQL-ді пайдаланады. Демо өтініштері мен replay жеткізуі синтетикалық.",
    statusBlocked:
      "Өңірлік CRM байланысы, бекітілген сәйкестендіру, жіктеу және SLA ережелері, тіркемелердің қорғалған қоймасы мен нақты деректердегі модель бағасы әзірге қолжетімсіз.",
    statusCoverage:
      "Оқиғалар, Replay Lab және қолтаңбалы конфигурация API-ларының қамтуы оператор интерфейсінен кеңірек. Толық ақпарат репозиторийдегі функциялар матрицасында берілген.",
    loading: "Өтініштер жүктелуде…",
    refresh: "Жаңарту",
    classify: "Ұсыныс алу",
    manual: "Қолмен шешімді сақтау",
    accept: "Ұсынысты растау",
    assign: "Тағайындауды кезекке қою",
    status: "Мәртебені жазу",
    unavailable: "Ұсыныс қолжетімсіз; қолмен жұмыс істеуге болады.",
    empty:
      "Бұл аймақта өтініш жоқ. Синтетикалық өтініш жасаңыз немесе seed іске қосыңыз.",
  },
} as const;

// A server answer, whatever its status. Anything else thrown by api() means the
// outcome is unknown, which is exactly the case where a retry must reuse its key.
class ApiError extends Error {
  readonly status: number;

  constructor(code: string, status: number) {
    super(code);
    this.name = "ApiError";
    this.status = status;
  }
}

async function api<T>(
  path: string,
  regionId: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`/api/core${path}`, {
    ...init,
    headers: { "X-Region-Id": regionId, ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    let code = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      code = body.detail?.code ?? body.detail?.message ?? code;
    } catch {
      /* The HTTP status remains visible. */
    }
    throw new ApiError(code, response.status);
  }
  return (await response.json()) as T;
}

function commandHeaders(idempotencyKey: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "Idempotency-Key": idempotencyKey,
  };
}

export default function OperatorWorkspace() {
  const [locale, setLocale] = useState<Locale>("ru");
  const [regions, setRegions] = useState<string[]>([DEFAULT_REGION]);
  const [region, setRegion] = useState(DEFAULT_REGION);
  // An idempotency key has to survive a retry of the same command. If the server
  // committed the write and only the response was lost, a freshly generated key
  // would reach the server as a second, different command. Keys are therefore
  // held per operation and dropped only once the server has answered, whatever
  // the answer was. A transport failure leaves the key in place for the retry.
  const commandKeys = useRef(new Map<string, string>());

  function commandKey(operation: string): string {
    const existing = commandKeys.current.get(operation);
    if (existing) return existing;
    const created = crypto.randomUUID();
    commandKeys.current.set(operation, created);
    return created;
  }

  const [view, setView] = useState<
    | "operations"
    | "datalab"
    | "queue"
    | "incidents"
    | "replay"
    | "intake"
    | "situation"
  >("operations");
  const [warRoomIncidentId, setWarRoomIncidentId] = useState<string | null>(
    null,
  );
  const [profile, setProfile] = useState<string | null>(null);
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(
    null,
  );
  const [attachments, setAttachments] = useState<AttachmentRef[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [topic, setTopic] = useState("topic:manual-review");
  const [service, setService] = useState("service:manual-review");
  const [priority, setPriority] = useState("routine");
  const [nextStatus, setNextStatus] = useState("triage");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const copy = labels[locale];

  const refreshQueue = useCallback(async () => {
    try {
      const rows = await api<Appeal[]>("/requests?limit=50", region);
      setAppeals(rows);
      if (rows.length === 0) setDetail(null);
      setSelectedId((previous) =>
        previous && rows.some((row) => row.request_id === previous)
          ? previous
          : (rows[0]?.request_id ?? null),
      );
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "queue_unavailable",
      );
    } finally {
      setLoading(false);
    }
    // Changing the region asks a different question of the API, so both readers
    // depend on it and refetch when the operator switches.
  }, [region]);

  const refreshDetail = useCallback(
    async (id: string) => {
      try {
        const row = await api<Detail>(
          `/requests/${encodeURIComponent(id)}`,
          region,
        );
        setDetail(row);
        setTopic(row.current_decision?.topic_id ?? "topic:manual-review");
        setService(row.current_decision?.service_id ?? "service:manual-review");
        setPriority(row.current_decision?.priority ?? "routine");
        try {
          setAttachments(
            await api<AttachmentRef[]>(
              `/requests/${encodeURIComponent(id)}/attachments`,
              region,
            ),
          );
          setAttachmentError(null);
        } catch (failure) {
          setAttachments([]);
          setAttachmentError(
            failure instanceof Error
              ? failure.message
              : "attachments_unavailable",
          );
        }
        setError(null);
      } catch (failure) {
        setDetail(null);
        setAttachments([]);
        setError(
          failure instanceof Error ? failure.message : "appeal_unavailable",
        );
      }
    },
    [region],
  );

  useEffect(() => {
    let cancelled = false;
    void fetch("/api/core/session/context", {
      headers: { "X-Region-Id": DEFAULT_REGION },
      cache: "no-store",
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((body: SessionContext | null) => {
        // The development fallback mirrors the region it was asked about, so
        // it says nothing about what an operator may actually see. Only a
        // verified identity narrows the selector.
        if (
          cancelled ||
          !body ||
          body.authentication_source === "development"
        ) {
          return;
        }
        const allowed = body.regions.filter((item) => item !== "ALL");
        if (allowed.length === 0) return;
        setRegions(allowed);
        setRegion((current) =>
          allowed.includes(current) ? current : allowed[0],
        );
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    api<{ profile: string }>("/health/ready", region)
      .then((health) => setProfile(health.profile))
      .catch(() => setProfile("unavailable"));
    void Promise.resolve().then(refreshQueue);
  }, [refreshQueue, region]);

  useEffect(() => {
    if (selectedId)
      void Promise.resolve().then(() => refreshDetail(selectedId));
  }, [selectedId, refreshDetail]);

  async function run(
    action: () => Promise<void>,
    refresh = true,
    operation?: string,
  ) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      if (operation) commandKeys.current.delete(operation);
      if (refresh) {
        if (selectedId) await refreshDetail(selectedId);
        await refreshQueue();
      }
    } catch (failure) {
      // The server answered, so this key has done its job. Anything else leaves
      // the outcome unknown and the key is kept for the retry.
      if (operation && failure instanceof ApiError) {
        commandKeys.current.delete(operation);
      }
      setError(
        failure instanceof Error ? failure.message : "command_unconfirmed",
      );
    } finally {
      setBusy(false);
    }
  }

  function classify() {
    if (!detail) return;
    const operation = `classify:${detail.request_id}:${detail.version}`;
    void run(
      async () => {
        const result = await api<Recommendation>(
          `/requests/${detail.request_id}/classifications`,
          region,
          {
            method: "POST",
            headers: commandHeaders(commandKey(operation)),
            body: JSON.stringify({ request_version: detail.version }),
          },
        );
        setRecommendation(result);
        setTopic(result.top_topics[0].id);
        setService(result.top_services[0].id);
        setPriority(result.priority);
        setNotice(`${result.model_version} · ${result.confidence_band}`);
      },
      false,
      operation,
    );
  }

  function decide(accept: boolean) {
    if (!detail) return;
    const operation = `decide:${detail.request_id}:${detail.version}:${accept}`;
    void run(
      async () => {
        const result = await api<{ decision_id: string }>(
          `/requests/${detail.request_id}/decisions`,
          region,
          {
            method: "POST",
            headers: commandHeaders(commandKey(operation)),
            body: JSON.stringify({
              request_version: detail.version,
              recommendation_id: accept
                ? recommendation?.recommendation_id
                : null,
              topic_id: topic,
              service_id: service,
              priority,
              action: accept ? "accepted" : "manual",
            }),
          },
        );
        setNotice(`Decision recorded: ${result.decision_id}`);
        setRecommendation(null);
      },
      true,
      operation,
    );
  }

  function assign() {
    if (!detail?.current_decision) return;
    const operation = `assign:${detail.request_id}:${detail.version}`;
    void run(
      async () => {
        const receipt = await api<{ status: string }>(
          `/requests/${detail.request_id}/assignments`,
          region,
          {
            method: "POST",
            headers: commandHeaders(commandKey(operation)),
            body: JSON.stringify({
              request_version: detail.version,
              service_id: detail.current_decision?.service_id,
              reason_code: "operator_confirmed",
            }),
          },
        );
        setNotice(`Outbox: ${receipt.status}`);
      },
      true,
      operation,
    );
  }

  function recordStatus() {
    if (!detail) return;
    const operation = `status:${detail.request_id}:${detail.version}:${nextStatus}`;
    void run(
      async () => {
        // The source event id identifies the same event across retries, so it is
        // derived from the operation key rather than generated per attempt.
        const key = commandKey(operation);
        const event = await api<{ event_id: string }>(
          `/requests/${detail.request_id}/status-events`,
          region,
          {
            method: "POST",
            headers: commandHeaders(key),
            body: JSON.stringify({
              source_event_id: key,
              source_system: detail.source_system,
              status: nextStatus,
              occurred_at: null,
              occurred_at_quality: "missing",
              reason_code: "OPERATOR_REVIEW",
            }),
          },
        );
        setNotice(`Status event recorded: ${event.event_id}`);
      },
      true,
      operation,
    );
  }

  // The shell separates where you are from what you are doing. A row of tabs
  // across the top made every screen look like a setting of one page, which is
  // why the application read as an admin panel rather than a product.
  const primaryViews = [
    "operations",
    "queue",
    "incidents",
    "datalab",
    "replay",
  ] as const;
  const secondaryViews = ["intake", "situation"] as const;

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Sections">
        <strong className="brand">Pulse 109</strong>
        <nav className="sidebar-nav">
          {primaryViews.map((name) => (
            <button
              key={name}
              type="button"
              aria-current={view === name ? "page" : undefined}
              onClick={() => setView(name)}
            >
              {copy[name]}
            </button>
          ))}
          <span className="sidebar-divider" role="presentation" />
          {secondaryViews.map((name) => (
            <button
              key={name}
              type="button"
              aria-current={view === name ? "page" : undefined}
              onClick={() => setView(name)}
            >
              {copy[name]}
            </button>
          ))}
        </nav>
      </aside>

      <main className="shell-main">
        <header className="topbar">
          <div className="topbar-context">
            {regions.length > 1 ? (
              <select
                aria-label="Region"
                value={region}
                onChange={(event) => setRegion(event.target.value)}
              >
                {regions.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            ) : (
              <span className="region-label">{region}</span>
            )}
          </div>
          <div className="topbar-actions">
            <span
              className="profile"
              title={
                profile === "demo"
                  ? "Synthetic municipal data. The application logic, PostgreSQL workflows and worker paths are real."
                  : undefined
              }
            >
              {profile === "demo"
                ? "DEMO · SYNTHETIC"
                : `Profile: ${profile ?? "loading"}`}
            </span>
            <div className="locale-switch" aria-label="Language">
              {(["ru", "kk"] as const).map((name) => (
                <button
                  key={name}
                  type="button"
                  aria-pressed={locale === name}
                  onClick={() => setLocale(name)}
                >
                  {name.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </header>

        {view === "operations" ? (
          <div className="workspace real-workspace">
            {warRoomIncidentId ? (
              <IncidentWarRoom
                locale={locale}
                regionId={region}
                incidentId={warRoomIncidentId}
                onClose={() => setWarRoomIncidentId(null)}
              />
            ) : null}
            <OperationsCenter
              locale={locale}
              regionId={region}
              onOpenIncident={(incidentId) => setWarRoomIncidentId(incidentId)}
            />
          </div>
        ) : null}
        {view === "incidents" ? (
          <div className="workspace real-workspace">
            {warRoomIncidentId ? (
              <IncidentWarRoom
                locale={locale}
                regionId={region}
                incidentId={warRoomIncidentId}
                onClose={() => setWarRoomIncidentId(null)}
              />
            ) : null}
            <IncidentList
              locale={locale}
              regionId={region}
              onOpenIncident={(incidentId) => setWarRoomIncidentId(incidentId)}
            />
          </div>
        ) : null}
        {view === "datalab" ? (
          <div className="workspace real-workspace">
            <DataLab locale={locale} regionId={region} />
          </div>
        ) : null}
        {view === "replay" ? (
          <div className="workspace real-workspace">
            <ReplayLab locale={locale} regionId={region} />
          </div>
        ) : null}
        {view === "intake" ? (
          <Intake
            locale={locale}
            regionId={region}
            demoEnabled={profile === "demo"}
          />
        ) : null}
        {view === "situation" ? (
          <section
            className="workspace real-workspace"
            aria-labelledby="platform-status"
          >
            <div className="content">
              <p className="eyebrow">
                {profile === "demo"
                  ? "DEMO · SYNTHETIC"
                  : `Profile: ${profile}`}
              </p>
              <h1 id="platform-status">{copy.situation}</h1>
              <p>{copy.statusImplemented}</p>
              <p>{copy.statusBlocked}</p>
              <p>{copy.statusCoverage}</p>
              <AnalyticsPanel locale={locale} regionId={region} />
            </div>
          </section>
        ) : null}
        {view === "queue" ? (
          <div className="workspace real-workspace">
            <section className="content" id="queue">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{profile}</p>
                  <h1>{copy.queue}</h1>
                </div>
                <button
                  className="secondary-action"
                  type="button"
                  onClick={() => void refreshQueue()}
                >
                  {copy.refresh}
                </button>
              </div>
              {error ? (
                <p role="alert" className="attention">
                  {error}
                </p>
              ) : null}
              {notice ? <p role="status">{notice}</p> : null}
              {loading ? <p role="status">{copy.loading}</p> : null}
              {!loading && !error && appeals.length === 0 ? (
                <p role="status">{copy.empty}</p>
              ) : null}
              <div className="queue" aria-label="Appeals from PostgreSQL">
                {appeals.map((appeal) => (
                  <button
                    className={`queue-row ${selectedId === appeal.request_id ? "selected" : ""}`}
                    key={appeal.request_id}
                    type="button"
                    onClick={() => {
                      setSelectedId(appeal.request_id);
                      setRecommendation(null);
                      setDetail(null);
                      setAttachments([]);
                    }}
                  >
                    <strong>{appeal.source_request_id}</strong>
                    <span>{appeal.region_id}</span>
                    <span>{appeal.channel}</span>
                    <span>{appeal.received_at_quality}</span>
                    <span>{appeal.status}</span>
                  </button>
                ))}
              </div>
              {detail ? (
                <section className="appeal-card" aria-labelledby="appeal-title">
                  <div className="appeal-header">
                    <div>
                      <p className="eyebrow">
                        {detail.source_system} · v{detail.version}
                      </p>
                      <h2 id="appeal-title">{detail.request_id}</h2>
                      <p className="appeal-summary">
                        {detail.text ?? "No operational text recorded"}
                      </p>
                    </div>
                    <span className="status-chip">{detail.status}</span>
                  </div>
                  <div className="meta-grid">
                    <div>
                      <span>Region</span>
                      <strong>{detail.region_id}</strong>
                    </div>
                    <div>
                      <span>Business time quality</span>
                      <strong>{detail.received_at_quality}</strong>
                    </div>
                    <div>
                      <span>Created</span>
                      <strong>{detail.created_at}</strong>
                    </div>
                    <div>
                      <span>Sync</span>
                      <strong>
                        {detail.synchronization?.status ?? "not required"}
                      </strong>
                    </div>
                  </div>
                  <div className="decision-area">
                    <h3>Human governed routing</h3>
                    <button
                      className="secondary-action"
                      type="button"
                      disabled={busy}
                      onClick={classify}
                    >
                      {copy.classify}
                    </button>
                    {recommendation ? (
                      <p role="status">
                        Local {recommendation.model_version} ·{" "}
                        {recommendation.confidence_band} · topic{" "}
                        {recommendation.top_topics[0].id} (
                        {Math.round(recommendation.top_topics[0].score * 100)}%)
                        · service {recommendation.top_services[0].id} · human
                        confirmation required
                      </p>
                    ) : (
                      <p>{copy.unavailable}</p>
                    )}
                    <div className="manual-fields">
                      <label>
                        Topic ID
                        <input
                          value={topic}
                          onChange={(event) => setTopic(event.target.value)}
                        />
                      </label>
                      <label>
                        Service ID
                        <input
                          value={service}
                          onChange={(event) => setService(event.target.value)}
                        />
                      </label>
                      <label>
                        Priority
                        <select
                          value={priority}
                          onChange={(event) => setPriority(event.target.value)}
                        >
                          <option value="routine">routine</option>
                          <option value="elevated">elevated</option>
                          <option value="urgent">urgent</option>
                          <option value="emergency_handoff">
                            emergency handoff
                          </option>
                        </select>
                      </label>
                    </div>
                    <div className="decision-controls">
                      <button
                        className="primary-action"
                        type="button"
                        disabled={busy || !topic || !service}
                        onClick={() => decide(false)}
                      >
                        {copy.manual}
                      </button>
                      <button
                        className="secondary-action"
                        type="button"
                        disabled={busy || !recommendation}
                        onClick={() => decide(true)}
                      >
                        {copy.accept}
                      </button>
                    </div>
                    {detail.current_decision ? (
                      <p role="status">
                        Recorded: {detail.current_decision.action} ·{" "}
                        {detail.current_decision.service_id}
                      </p>
                    ) : null}
                  </div>
                  <div className="decision-area">
                    <h3>Assignment and status</h3>
                    <button
                      className="primary-action"
                      type="button"
                      disabled={busy || !detail.current_decision}
                      onClick={assign}
                    >
                      {copy.assign}
                    </button>
                    <label>
                      Next status
                      <select
                        value={nextStatus}
                        onChange={(event) => setNextStatus(event.target.value)}
                      >
                        <option value="triage">triage</option>
                        <option value="accepted">accepted</option>
                        <option value="in_progress">in progress</option>
                        <option value="waiting">waiting</option>
                        <option value="resolved">resolved</option>
                      </select>
                    </label>
                    <button
                      className="secondary-action"
                      type="button"
                      disabled={busy}
                      onClick={recordStatus}
                    >
                      {copy.status}
                    </button>
                  </div>
                  <div className="activity-grid">
                    <div>
                      <h3>Durable timeline</h3>
                      <ol className="timeline">
                        {detail.timeline.map((event) => (
                          <li key={event.event_id}>
                            {event.event_type} · {event.observed_at}
                          </li>
                        ))}
                      </ol>
                    </div>
                    <div>
                      <h3>External delivery</h3>
                      <p>{detail.synchronization?.status ?? "not required"}</p>
                      <p>
                        {detail.synchronization?.external_id ??
                          "No external ID"}
                      </p>
                    </div>
                    <div>
                      <h3>
                        {locale === "ru"
                          ? "Доказательства закрытия"
                          : "Жабу дәлелдері"}
                      </h3>
                      {attachmentError ? (
                        <p role="alert">{attachmentError}</p>
                      ) : null}
                      {attachments.length === 0 && !attachmentError ? (
                        <p>
                          {locale === "ru" ? "Вложений нет" : "Тіркеме жоқ"}
                        </p>
                      ) : null}
                      {attachments.map((item) => (
                        <p key={item.attachment_id}>
                          {item.file_name} · sha256:{item.object_hash}
                        </p>
                      ))}
                    </div>
                  </div>
                  <OwnershipHandoffPanel
                    key={detail.request_id}
                    locale={locale}
                    regionId={detail.region_id}
                    initialRequestId={detail.request_id}
                  />
                  <IncidentWorkflowPanel
                    key={`incident-${detail.request_id}`}
                    locale={locale}
                    regionId={detail.region_id}
                    requestId={detail.request_id}
                    choices={appeals}
                    topicId={detail.current_decision?.topic_id ?? null}
                    serviceId={detail.current_decision?.service_id ?? null}
                  />
                  <ClosureIntegrityPanel
                    key={`closure-${detail.request_id}`}
                    locale={locale}
                    regionId={detail.region_id}
                    initialRequestId={detail.request_id}
                  />
                </section>
              ) : null}
            </section>
          </div>
        ) : null}
      </main>
    </div>
  );
}
