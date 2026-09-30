"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ChartNoAxesCombined,
  ClipboardPlus,
  Inbox,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  RotateCcw,
  ShieldCheck,
  Siren,
} from "lucide-react";
import { Intake } from "./intake";
import { AnalyticsPanel } from "./analytics-panel";
import { ClosureIntegrityPanel } from "./closure-integrity-panel";
import { DataLab } from "./data-lab";
import { IncidentList } from "./incident-list";
import { IncidentWarRoom } from "./incident-war-room";
import { IncidentWorkflowPanel } from "./incident-workflow-panel";
import { OperationsCenter } from "./operations-center";
import { OwnershipHandoffPanel } from "./ownership-handoff-panel";
import {
  createWaterPreset,
  DEMO_WATER_PRESET,
  PresenterPanel,
  type PresenterPreset,
} from "./presenter-panel";
import { ReplayLab } from "./replay-lab";
import { Skeleton } from "./skeleton";

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

function statusLabel(status: string, locale: Locale): string {
  const labels: Record<string, { ru: string; kk: string }> = {
    received: { ru: "Новое", kk: "Жаңа" },
    triage: { ru: "На проверке", kk: "Тексерілуде" },
    classified: { ru: "Классифицировано", kk: "Санатталды" },
    assigned: { ru: "Назначено", kk: "Тағайындалды" },
    accepted: { ru: "Принято", kk: "Қабылданды" },
    in_progress: { ru: "В работе", kk: "Жұмыста" },
    waiting: { ru: "Ожидает ответа", kk: "Жауап күтуде" },
    resolved: { ru: "Решено", kk: "Шешілді" },
    closed: { ru: "Закрыто", kk: "Жабылды" },
    needs_attention: { ru: "Требует внимания", kk: "Назар аудару қажет" },
    delivery_failed: { ru: "Ошибка доставки", kk: "Жеткізу қатесі" },
  };
  return labels[status]?.[locale] ?? status;
}

const viewIcons = {
  operations: Activity,
  queue: Inbox,
  incidents: Siren,
  datalab: ChartNoAxesCombined,
  replay: RotateCcw,
  intake: ClipboardPlus,
  situation: ShieldCheck,
} as const;

type SessionContext = {
  regions: string[];
  authentication_source: string;
};

const labels = {
  ru: {
    navigation: "Разделы",
    skipContent: "Перейти к рабочей области",
    region: "Регион",
    language: "Язык",
    profile: "Профиль",
    profileLoading: "загрузка",
    record: "Обращение",
    channel: "Канал",
    timeQuality: "Надёжность времени",
    statusField: "Статус",
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
    advisoryEmpty: "Получите подсказку модели или сохраните ручное решение.",
    advisoryTitle: "Маршрутизация: решение оператора",
    advisoryOnly: "Рекомендация · подтверждение человеком обязательно",
    rankingLabel: "Темы по оценке модели",
    rankingScore: "Оценка ранжирования",
    suggestedService: "Предложенная служба",
    suggestedPriority: "Предложенный приоритет",
    modelNote:
      "Локальный лексический baseline. Оценки ранжирования не являются измеренной точностью модели.",
    topicLabel: "Тема",
    serviceLabel: "Служба",
    priorityLabel: "Приоритет",
    createdLabel: "Создано",
    syncLabel: "Доставка",
    recordedLabel: "Записано",
    assignmentTitle: "Назначение и статус",
    nextStatusLabel: "Следующий статус",
    timelineTitle: "История обращения",
    deliveryTitle: "Внешняя доставка",
    noText: "Текст обращения недоступен",
    notRequired: "не требуется",
    noExternalId: "Внешнего ID нет",
    empty:
      "В этом регионе пока нет обращений. Создайте синтетическое обращение через форму или запустите seed.",
  },
  kk: {
    navigation: "Бөлімдер",
    skipContent: "Жұмыс аймағына өту",
    region: "Өңір",
    language: "Тіл",
    profile: "Профиль",
    profileLoading: "жүктелуде",
    record: "Өтініш",
    channel: "Арна",
    timeQuality: "Уақыт сенімділігі",
    statusField: "Мәртебе",
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
    advisoryEmpty: "Модель ұсынысын алыңыз немесе қолмен шешім сақтаңыз.",
    advisoryTitle: "Бағыттау: оператор шешімі",
    advisoryOnly: "Ұсыныс · адам растауы қажет",
    rankingLabel: "Модель бағалаған тақырыптар",
    rankingScore: "Ранжирлеу бағасы",
    suggestedService: "Ұсынылған қызмет",
    suggestedPriority: "Ұсынылған басымдық",
    modelNote:
      "Жергілікті лексикалық baseline. Ранжирлеу бағасы модельдің өлшенген дәлдігі емес.",
    topicLabel: "Тақырып",
    serviceLabel: "Қызмет",
    priorityLabel: "Басымдық",
    createdLabel: "Құрылды",
    syncLabel: "Жеткізу",
    recordedLabel: "Жазылды",
    assignmentTitle: "Тағайындау және мәртебе",
    nextStatusLabel: "Келесі мәртебе",
    timelineTitle: "Өтініш тарихы",
    deliveryTitle: "Сыртқы жеткізу",
    noText: "Өтініш мәтіні қолжетімсіз",
    notRequired: "қажет емес",
    noExternalId: "Сыртқы ID жоқ",
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
  >(() =>
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("presenter") === "1"
      ? "intake"
      : "operations",
  );
  const [warRoomIncidentId, setWarRoomIncidentId] = useState<string | null>(
    null,
  );
  const [profile, setProfile] = useState<string | null>(null);
  const isDemoProfile = profile === "demo" || profile === "demo-mock";
  const demoDataDisclosure =
    profile === "demo-mock"
      ? "Используются вымышленные муниципальные записи. Интерфейс и сценарии работают через локальный mock API; база данных и внешняя доставка не подключены."
      : "Используются синтетические муниципальные записи. Демо работает через API, PostgreSQL, аудит и worker. Региональная CRM не подключена; доставка воспроизводится demo adapter-ом.";
  const [demoDisclosureOpen, setDemoDisclosureOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [presenterMode, setPresenterMode] = useState(
    () =>
      typeof window !== "undefined" &&
      new URLSearchParams(window.location.search).get("presenter") === "1",
  );
  const [presenterPreset, setPresenterPreset] =
    useState<PresenterPreset | null>(() =>
      typeof window !== "undefined" &&
      new URLSearchParams(window.location.search).get("presenter") === "1"
        ? DEMO_WATER_PRESET
        : null,
    );
  useEffect(() => {
    function closeDemoDisclosure(event: KeyboardEvent) {
      if (event.key === "Escape") setDemoDisclosureOpen(false);
    }
    window.addEventListener("keydown", closeDemoDisclosure);
    return () => window.removeEventListener("keydown", closeDemoDisclosure);
  }, []);
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

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      try {
        setSidebarCollapsed(
          window.localStorage?.getItem("pulse109-sidebar-collapsed") === "1",
        );
      } catch {
        setSidebarCollapsed(false);
      }
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  function toggleSidebar() {
    if (window.matchMedia("(max-width: 760px)").matches) {
      setSidebarOpen((open) => !open);
      return;
    }
    setSidebarCollapsed((collapsed) => {
      try {
        window.localStorage?.setItem(
          "pulse109-sidebar-collapsed",
          collapsed ? "0" : "1",
        );
      } catch {
        // Collapsing still works when storage is unavailable.
      }
      return !collapsed;
    });
  }

  useEffect(() => {
    function togglePresenter(event: KeyboardEvent) {
      if (event.key === "Escape") setSidebarOpen(false);
      if (
        (event.ctrlKey || event.metaKey) &&
        event.shiftKey &&
        event.key.toLowerCase() === "d"
      ) {
        event.preventDefault();
        setPresenterMode((current) => !current);
      }
    }
    window.addEventListener("keydown", togglePresenter);
    return () => window.removeEventListener("keydown", togglePresenter);
  }, []);

  const refreshQueue = useCallback(
    async (preferredId?: string) => {
      try {
        const rows = await api<Appeal[]>("/requests?limit=50", region);
        setAppeals(rows);
        if (rows.length === 0) setDetail(null);
        setSelectedId((previous) => {
          if (preferredId) return preferredId;
          return previous && rows.some((row) => row.request_id === previous)
            ? previous
            : (rows[0]?.request_id ?? null);
        });
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
    },
    [region],
  );

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
    void Promise.resolve().then(() => refreshQueue());
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
        if (result.top_topics[0]) setTopic(result.top_topics[0].id);
        if (result.top_services[0]) setService(result.top_services[0].id);
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
  const intakePresenterPreset =
    presenterPreset ?? (isDemoProfile ? DEMO_WATER_PRESET : null);

  function navigateView(target: typeof view) {
    if (target === "intake" && isDemoProfile && !presenterPreset) {
      setPresenterPreset(createWaterPreset());
    }
    setView(target);
  }

  function openSubmittedAppeal(requestId: string) {
    setRecommendation(null);
    setDetail(null);
    setSelectedId(requestId);
    setView("queue");
    void refreshQueue(requestId);
  }

  return (
    <div
      className={`shell${sidebarCollapsed ? " sidebar-collapsed" : ""}${sidebarOpen ? " sidebar-open" : ""}`}
      lang={locale}
    >
      <a className="skip-link" href="#workspace-main">
        {copy.skipContent}
      </a>
      <aside className="sidebar" aria-label={copy.navigation}>
        <div className="sidebar-brand-row">
          <Link className="brand" href="/" aria-label="Pulse 109 — на главную">
            <span className="brand-signal" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <span>Pulse 109</span>
          </Link>
          <button
            className="sidebar-collapse"
            type="button"
            aria-label={sidebarCollapsed ? "Развернуть меню" : "Свернуть меню"}
            title={sidebarCollapsed ? "Развернуть меню" : "Свернуть меню"}
            aria-expanded={!sidebarCollapsed}
            onClick={toggleSidebar}
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen size={17} aria-hidden="true" />
            ) : (
              <PanelLeftClose size={17} aria-hidden="true" />
            )}
          </button>
        </div>
        <nav className="sidebar-nav">
          {primaryViews.map((name) => {
            const Icon = viewIcons[name];
            return (
              <button
                key={name}
                type="button"
                aria-current={view === name ? "page" : undefined}
                title={sidebarCollapsed ? copy[name] : undefined}
                aria-label={copy[name]}
                onClick={() => {
                  navigateView(name);
                  setSidebarOpen(false);
                }}
              >
                <Icon
                  size={16}
                  aria-hidden="true"
                  focusable="false"
                  strokeWidth={1.8}
                />
                <span>{copy[name]}</span>
              </button>
            );
          })}
          <span className="sidebar-divider" role="presentation" />
          {secondaryViews.map((name) => {
            const Icon = viewIcons[name];
            return (
              <button
                key={name}
                type="button"
                aria-current={view === name ? "page" : undefined}
                title={sidebarCollapsed ? copy[name] : undefined}
                aria-label={copy[name]}
                onClick={() => {
                  navigateView(name);
                  setSidebarOpen(false);
                }}
              >
                <Icon
                  size={16}
                  aria-hidden="true"
                  focusable="false"
                  strokeWidth={1.8}
                />
                <span>{copy[name]}</span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <Link
            href="/"
            className="sidebar-portal-link"
            aria-label="Вернуться на главную"
          >
            <span>← {locale === "ru" ? "Главная страница" : "Басты бет"}</span>
          </Link>
          <span className="sidebar-version-badge">v1.4.0 · BENTO</span>
        </div>
      </aside>

      {sidebarOpen ? (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Закрыть меню"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}

      <main className="shell-main" id="workspace-main" tabIndex={-1}>
        <header className="topbar">
          <button
            className="shell-menu-toggle"
            type="button"
            aria-label="Открыть меню"
            onClick={toggleSidebar}
          >
            <Menu size={18} aria-hidden="true" />
          </button>
          <div className="topbar-context" aria-label={copy.region}>
            <span className="topbar-module-badge">{copy[view]}</span>
            <span className="topbar-context-divider" aria-hidden="true">
              /
            </span>
            {regions.length > 1 ? (
              <select
                aria-label={copy.region}
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
              <span className="region-label" aria-label={copy.region}>
                {region}
              </span>
            )}
          </div>
          <div className="topbar-actions">
            {isDemoProfile ? (
              <div className="demo-disclosure-wrap">
                <button
                  type="button"
                  className="profile demo-data-badge"
                  title={demoDataDisclosure}
                  aria-label="DEMO DATA: информация о данных"
                  aria-expanded={demoDisclosureOpen}
                  aria-controls="demo-data-tooltip"
                  onClick={() => setDemoDisclosureOpen((open) => !open)}
                >
                  DEMO DATA
                </button>
                {demoDisclosureOpen ? (
                  <div
                    id="demo-data-tooltip"
                    className="demo-data-tooltip"
                    role="tooltip"
                  >
                    {demoDataDisclosure}
                  </div>
                ) : null}
              </div>
            ) : (
              <span className="profile">
                {`${copy.profile}: ${profile ?? copy.profileLoading}`}
              </span>
            )}
            <div
              className="locale-switch"
              role="group"
              aria-label={copy.language}
            >
              {(["ru", "kk"] as const).map((name) => (
                <button
                  key={name}
                  type="button"
                  aria-pressed={locale === name}
                  title={name === "ru" ? "Русский" : "Қазақша"}
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
            key={intakePresenterPreset?.id ?? "normal"}
            locale={locale}
            regionId={region}
            demoEnabled={isDemoProfile}
            presenterPreset={intakePresenterPreset}
            onOpenSubmitted={openSubmittedAppeal}
          />
        ) : null}
        {view === "situation" ? (
          <section
            className="workspace real-workspace"
            aria-labelledby="platform-status"
          >
            <div className="content">
              <p className="eyebrow">{copy.situation}</p>
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
                  <p className="eyebrow">{copy.queue}</p>
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
              {!loading && !error && appeals.length === 0 ? (
                <div className="empty-state" role="status">
                  <span className="empty-state-mark" aria-hidden="true">
                    <Inbox size={18} />
                  </span>
                  <p>{copy.empty}</p>
                </div>
              ) : null}
              {loading ? (
                <div
                  className="queue queue-loading"
                  role="status"
                  aria-busy="true"
                >
                  <span className="sr-only">{copy.loading}</span>
                  {[0, 1, 2, 3, 4].map((index) => (
                    <div className="queue-row" key={index}>
                      <Skeleton className="skeleton-row-primary" />
                      <Skeleton />
                      <Skeleton />
                      <Skeleton />
                      <Skeleton />
                    </div>
                  ))}
                </div>
              ) : appeals.length > 0 ? (
                <div className="queue" role="group" aria-label={copy.queue}>
                  <div className="queue-head" aria-hidden="true">
                    <span>{copy.record}</span>
                    <span>{copy.region}</span>
                    <span>{copy.channel}</span>
                    <span>{copy.timeQuality}</span>
                    <span>{copy.statusField}</span>
                  </div>
                  {appeals.map((appeal) => (
                    <button
                      className={`queue-row ${selectedId === appeal.request_id ? "selected" : ""}`}
                      key={appeal.request_id}
                      type="button"
                      aria-label={`${copy.record} ${appeal.source_request_id}; ${copy.region} ${appeal.region_id}; ${copy.statusField} ${statusLabel(appeal.status, locale)}`}
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
                      <span className={`status-chip status-${appeal.status}`}>
                        {statusLabel(appeal.status, locale)}
                      </span>
                    </button>
                  ))}
                </div>
              ) : null}
              {detail ? (
                <section className="appeal-card" aria-labelledby="appeal-title">
                  <div className="appeal-header">
                    <div>
                      <p className="eyebrow">
                        {detail.source_system} · v{detail.version}
                      </p>
                      <h2 id="appeal-title">{detail.source_request_id}</h2>
                      <p className="appeal-summary">
                        {detail.text ?? copy.noText}
                      </p>
                    </div>
                    <span className={`status-chip status-${detail.status}`}>
                      {statusLabel(detail.status, locale)}
                    </span>
                  </div>
                  <div className="meta-grid">
                    <div>
                      <span>{copy.region}</span>
                      <strong>{detail.region_id}</strong>
                    </div>
                    <div>
                      <span>{copy.timeQuality}</span>
                      <strong>{detail.received_at_quality}</strong>
                    </div>
                    <div>
                      <span>{copy.createdLabel}</span>
                      <strong>
                        {new Intl.DateTimeFormat(
                          locale === "ru" ? "ru-RU" : "kk-KZ",
                          {
                            dateStyle: "short",
                            timeStyle: "short",
                            timeZone: "Asia/Almaty",
                          },
                        ).format(new Date(detail.created_at))}
                      </strong>
                    </div>
                    <div>
                      <span>{copy.syncLabel}</span>
                      <strong>
                        {detail.synchronization?.status ?? copy.notRequired}
                      </strong>
                    </div>
                  </div>
                  <div className="decision-area">
                    <h3>{copy.advisoryTitle}</h3>
                    <button
                      className="secondary-action"
                      type="button"
                      disabled={busy}
                      onClick={classify}
                    >
                      {copy.classify}
                    </button>
                    {recommendation ? (
                      <div className="recommendation-result" role="status">
                        <p className="advisory-chip">{copy.advisoryOnly}</p>
                        <div className="recommendation-grid">
                          <section className="recommendation-panel">
                            <span className="panel-label">
                              {copy.rankingLabel}
                            </span>
                            <ol>
                              {recommendation.top_topics
                                .slice(0, 3)
                                .map((item) => (
                                  <li key={item.id}>
                                    <span>
                                      <b>{item.id}</b>
                                      <small>{copy.rankingScore}</small>
                                    </span>
                                    <strong>{item.score.toFixed(2)}</strong>
                                  </li>
                                ))}
                            </ol>
                          </section>
                          <section className="recommendation-panel">
                            <span className="panel-label">
                              {copy.suggestedService}
                            </span>
                            <p>
                              <strong>
                                {recommendation.top_services[0]?.id ?? "—"}
                              </strong>
                            </p>
                            <span className="panel-label">
                              {copy.suggestedPriority}
                            </span>
                            <p>
                              <strong>{recommendation.priority}</strong>
                            </p>
                          </section>
                          <section className="model-panel">
                            <span className="panel-label">
                              {recommendation.model_version}
                            </span>
                            <p>
                              <strong>{recommendation.confidence_band}</strong>
                            </p>
                            <p>{copy.modelNote}</p>
                          </section>
                        </div>
                      </div>
                    ) : (
                      <p>{copy.advisoryEmpty}</p>
                    )}
                    <div className="manual-fields">
                      <label>
                        {copy.topicLabel}
                        <input
                          value={topic}
                          onChange={(event) => setTopic(event.target.value)}
                        />
                      </label>
                      <label>
                        {copy.serviceLabel}
                        <input
                          value={service}
                          onChange={(event) => setService(event.target.value)}
                        />
                      </label>
                      <label>
                        {copy.priorityLabel}
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
                        {copy.recordedLabel}: {detail.current_decision.action} ·{" "}
                        {detail.current_decision.service_id}
                      </p>
                    ) : null}
                  </div>
                  <div className="decision-area">
                    <h3>{copy.assignmentTitle}</h3>
                    <button
                      className="primary-action"
                      type="button"
                      disabled={busy || !detail.current_decision}
                      onClick={assign}
                    >
                      {copy.assign}
                    </button>
                    <label>
                      {copy.nextStatusLabel}
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
                      <h3>{copy.timelineTitle}</h3>
                      <ol className="timeline">
                        {detail.timeline.map((event) => (
                          <li key={event.event_id}>
                            {event.event_type} · {event.observed_at}
                          </li>
                        ))}
                      </ol>
                    </div>
                    <div>
                      <h3>{copy.deliveryTitle}</h3>
                      <p>
                        {detail.synchronization?.status ?? copy.notRequired}
                      </p>
                      <p>
                        {detail.synchronization?.external_id ??
                          copy.noExternalId}
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
      {isDemoProfile && presenterMode ? (
        <PresenterPanel
          regionId={region}
          onNavigate={(target) => setView(target)}
          onLoadPreset={setPresenterPreset}
          onClose={() => setPresenterMode(false)}
        />
      ) : null}
    </div>
  );
}
