"use client";

/**
 * Where the city needs attention right now.
 *
 * The counters answer "how much". The feed answers "what should I open first",
 * which is the question a supervisor actually has, so the feed is the main
 * element and every row leads somewhere.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { ArrivalChart, type Bucket } from "./arrival-chart";
import { ReportMap, type ReportPoint } from "./report-map";
import { AskPulse } from "./ask-pulse";
import { Skeleton } from "./skeleton";

type Locale = "ru" | "kk";

type CapabilityStatus = {
  state: "available" | "abstained" | "unavailable";
  reason_code: string | null;
};

type AttentionItem = {
  kind: string;
  severity: "critical" | "elevated" | "routine";
  region_id: string;
  detected_at: string;
  summary_code: string;
  count: number;
  target_kind: "incident" | "cluster" | "appeal" | "integration";
  target_id: string | null;
  detail: Record<string, string | number | null>;
};

type Feed = {
  status: CapabilityStatus;
  region_id: string;
  generated_at: string;
  pulse: {
    open_appeals: number;
    active_incidents: number;
    emerging_patterns: number;
    unowned_incidents: number;
    queued_deliveries: number;
    failed_deliveries: number;
  };
  items: AttentionItem[];
  synthetic: boolean;
};

type Arrivals = {
  status: CapabilityStatus;
  buckets: Bucket[];
  peak: Bucket | null;
  baseline_per_bucket: number | null;
  excluded_untrusted_time: number;
};

type ClusterMember = {
  request_id: string;
  source_request_id: string;
  score: number;
  membership_reasons: string[];
  received_at: string | null;
  language: string;
  longitude: number | null;
  latitude: number | null;
};

type ClusterDetail = {
  cluster_id: string;
  state: string;
  appeal_count: number;
  first_seen_at: string;
  last_seen_at: string;
  radius_m: number | null;
  centroid_longitude: number | null;
  centroid_latitude: number | null;
  cohesion_score: number;
  novelty_score: number;
  cluster_score: number;
  signals_used: string[];
  top_topics: [string, number][];
  languages: Record<string, number>;
  algorithm_version: string;
  members: ClusterMember[];
};

type RequestLocation = {
  source_request_id?: string;
  point?: { longitude?: number | null; latitude?: number | null } | null;
};

const copy = {
  ru: {
    title: "Операционный центр",
    kicker: "01 / Ситуация сейчас",
    loading: "Загружаем данные об операционной ситуации…",
    intro:
      "Что требует внимания прямо сейчас. Каждая строка открывается, ни одна не создаёт работу автоматически.",
    attention: "Требует внимания",
    scan: "Поиск возникающих проблем",
    scanning: "Ищем…",
    quiet:
      "Ничего не превысило порог внимания. Счётчики выше показывают состояние, лента показывает то, что уже требует действия.",
    open: "Открытые обращения",
    incidents: "Активные инциденты",
    emerging: "Возникающие паттерны",
    unowned: "Без ответственного",
    queued: "В очереди на доставку",
    failed: "Доставка не удалась",
    activity: "Обращения за сутки",
    mapOverview: "География обращений",
    activityChartDescription:
      "Динамика обращений за сутки по достоверному времени поступления",
    activityNote:
      "Считаются только обращения с достоверным временем поступления. Наведите на точку, чтобы увидеть разбивку по темам.",
    excluded: "Не попали в график, время не достоверно",
    noSeries: "Недостаточно данных за это окно",
    peakLabel: "Пик",
    cluster: "Кластер",
    members: "Обращения",
    window: "Окно",
    radius: "Радиус",
    novelty: "Новизна",
    cohesion: "Связность",
    signals: "Сигналы",
    languages: "Языки",
    semanticOff:
      "Семантический сигнал не используется: исходного текста обращений нет.",
    promote: "Создать инцидент из кластера",
    dismiss: "Отклонить",
    known: "Известный паттерн",
    close: "Закрыть",
    noGeo: "Координат нет",
    advisory:
      "Радар сообщает, что появилась группа похожих обращений. Причину определяет человек.",
    timeline: "Как нарастало",
  },
  kk: {
    title: "Операциялық орталық",
    kicker: "01 / Қазіргі жағдай",
    loading: "Операциялық деректер жүктелуде…",
    intro:
      "Қазір неге назар керек. Әр жол ашылады, ешқайсысы өздігінен жұмыс жасамайды.",
    attention: "Назар аудару керек",
    scan: "Пайда болған мәселелерді іздеу",
    scanning: "Ізделуде…",
    quiet:
      "Ештеңе назар шегінен аспады. Жоғарыдағы есептегіштер жағдайды, тізім әрекет қажет ететінді көрсетеді.",
    open: "Ашық өтініштер",
    incidents: "Белсенді оқиғалар",
    emerging: "Пайда болған үлгілер",
    unowned: "Жауаптысыз",
    queued: "Жеткізу кезегінде",
    failed: "Жеткізілмеді",
    activity: "Өтініштер тәулік ішінде",
    mapOverview: "Өтініштердің географиясы",
    activityChartDescription:
      "Сенімді қабылдау уақыты бар өтініштердің тәуліктік динамикасы",
    activityNote: "Тек сенімді түсу уақыты бар өтініштер есептеледі.",
    excluded: "Графикке кірмеді, уақыты сенімсіз",
    noSeries: "Бұл терезе үшін дерек жеткіліксіз",
    peakLabel: "Шың",
    cluster: "Кластер",
    members: "Өтініштер",
    window: "Терезе",
    radius: "Радиус",
    novelty: "Жаңалық",
    cohesion: "Байланыс",
    signals: "Сигналдар",
    languages: "Тілдер",
    semanticOff: "Семантикалық сигнал қолданылмайды: өтініш мәтіні жоқ.",
    promote: "Кластерден оқиға жасау",
    dismiss: "Қабылдамау",
    known: "Белгілі үлгі",
    close: "Жабу",
    noGeo: "Координат жоқ",
    advisory:
      "Радар ұқсас өтініштер тобы пайда болғанын хабарлайды. Себебін адам анықтайды.",
    timeline: "Қалай өсті",
  },
} as const;

function localTime(value: string | number, locale: Locale): string {
  return new Intl.DateTimeFormat(locale === "ru" ? "ru-RU" : "kk-KZ", {
    timeZone: "Asia/Almaty",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(value));
}

function appealCount(count: number, locale: Locale): string {
  if (locale === "kk") return `${count} өтініш`;
  const ending = count % 10;
  const teen = count % 100;
  const noun =
    ending === 1 && teen !== 11
      ? "обращение"
      : ending >= 2 && ending <= 4 && (teen < 12 || teen > 14)
        ? "обращения"
        : "обращений";
  return `${count} ${noun}`;
}

function attentionTitle(item: AttentionItem, locale: Locale): string {
  if (item.kind === "emerging_cluster") {
    return locale === "ru" ? "Новый локальный сигнал" : "Жаңа жергілікті белгі";
  }
  if (item.kind === "adapter_lag") {
    return locale === "ru" ? "Задержка доставки" : "Жеткізу кідірісі";
  }
  return item.summary_code.replaceAll("_", " ");
}

function attentionDescription(item: AttentionItem, locale: Locale): string {
  if (item.kind === "emerging_cluster") {
    const radius = item.detail.radius_m;
    const spread =
      typeof radius === "number"
        ? ` · ${copy[locale].radius.toLowerCase()} ${Math.round(radius)} м`
        : "";
    return `${appealCount(item.count, locale)}${spread}`;
  }
  return `${item.count} · ${Object.entries(item.detail)
    .filter(([, value]) => value !== null)
    .map(([key, value]) => `${key}=${value}`)
    .join(" · ")}`;
}

function signalLabel(signal: string, locale: Locale): string {
  const labels: Record<string, [string, string]> = {
    geo: ["география", "география"],
    time: ["время", "уақыт"],
    taxonomy: ["темы", "тақырыптар"],
    novelty: ["новизна", "жаңалық"],
    semantic: ["смысл", "мағына"],
  };
  return labels[signal]?.[locale === "ru" ? 0 : 1] ?? signal;
}

export function OperationsCenter({
  locale,
  regionId,
  onOpenIncident,
}: {
  locale: Locale;
  regionId: string;
  onOpenIncident: (incidentId: string) => void;
}) {
  const t = copy[locale];
  const [feed, setFeed] = useState<Feed | null>(null);
  const [arrivals, setArrivals] = useState<Arrivals | null>(null);
  const [cluster, setCluster] = useState<ClusterDetail | null>(null);
  const [overviewPoints, setOverviewPoints] = useState<ReportPoint[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [semanticOff, setSemanticOff] = useState(false);

  const request = useCallback(
    async <T,>(path: string, init?: RequestInit): Promise<T> => {
      const response = await fetch(`/api/core${path}`, {
        ...init,
        headers: {
          "X-Region-Id": regionId,
          ...(init?.body ? { "Content-Type": "application/json" } : {}),
          ...init?.headers,
        },
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

  const loadFeed = useCallback(async () => {
    try {
      const [feedResult, seriesResult] = await Promise.all([
        request<Feed>("/operations/attention-feed"),
        request<Arrivals>(
          "/datalab/arrivals?window_hours=24&bucket_minutes=60",
        ),
      ]);
      setFeed(feedResult);
      setArrivals(seriesResult);
      setError(null);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "feed_unavailable");
    }
  }, [request]);

  useEffect(() => {
    // Deferred so the first paint is not a cascading render, matching how the
    // operator queue loads its own data.
    void Promise.resolve().then(loadFeed);
  }, [loadFeed]);

  useEffect(() => {
    let active = true;
    void request<RequestLocation[]>("/requests?limit=100&offset=0")
      .then((rows) => {
        if (!active) return;
        setOverviewPoints(
          rows.flatMap((row) =>
            typeof row.point?.longitude === "number" &&
            typeof row.point.latitude === "number"
              ? [
                  {
                    longitude: row.point.longitude,
                    latitude: row.point.latitude,
                    label: row.source_request_id,
                  },
                ]
              : [],
          ),
        );
      })
      .catch(() => {
        if (active) setOverviewPoints([]);
      });
    return () => {
      active = false;
    };
  }, [request]);

  async function scan() {
    setBusy(true);
    setNotice(null);
    try {
      const report = await request<{
        status: CapabilityStatus;
        semantic_status: CapabilityStatus;
        scanned_appeals: number;
        clusters: { cluster_id: string }[];
      }>("/discovery/scans?window_hours=6", { method: "POST" });
      setSemanticOff(report.semantic_status.state !== "available");
      setNotice(
        `${report.status.state} · ${report.scanned_appeals} · ${report.clusters.length}`,
      );
      await loadFeed();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "scan_failed");
    } finally {
      setBusy(false);
    }
  }

  async function openCluster(clusterId: string) {
    try {
      setCluster(
        await request<ClusterDetail>(
          `/discovery/clusters/${encodeURIComponent(clusterId)}`,
        ),
      );
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "cluster_unavailable",
      );
    }
  }

  async function promote(detail: ClusterDetail) {
    setBusy(true);
    try {
      const topic = detail.top_topics[0]?.[0] ?? "topic:manual-review";
      const incident = await request<{ incident_id: string }>("/incidents", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          region_id: regionId,
          topic_id: topic,
          service_id: null,
          member_request_ids: detail.members
            .slice(0, 20)
            .map((member) => member.request_id),
          proposal_source: "operator",
          rationale: ["EMERGING_CLUSTER_REVIEW"],
        }),
      });
      await request(
        `/discovery/clusters/${encodeURIComponent(detail.cluster_id)}/reviews` +
          `?promoted_incident_id=${encodeURIComponent(incident.incident_id)}`,
        {
          method: "POST",
          body: JSON.stringify({
            decision: "promote",
            reason_code: "OPERATOR_PROMOTED",
          }),
        },
      );
      setCluster(null);
      await loadFeed();
      onOpenIncident(incident.incident_id);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "promote_failed");
    } finally {
      setBusy(false);
    }
  }

  async function review(
    detail: ClusterDetail,
    decision: string,
    reason: string,
  ) {
    setBusy(true);
    try {
      await request(
        `/discovery/clusters/${encodeURIComponent(detail.cluster_id)}/reviews`,
        {
          method: "POST",
          body: JSON.stringify({ decision, reason_code: reason }),
        },
      );
      setCluster(null);
      await loadFeed();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "review_failed");
    } finally {
      setBusy(false);
    }
  }

  const points: ReportPoint[] = (cluster?.members ?? [])
    .filter((member) => member.longitude !== null && member.latitude !== null)
    .map((member) => ({
      longitude: member.longitude as number,
      latitude: member.latitude as number,
      label: member.source_request_id,
    }));

  return (
    <section className="operations" aria-labelledby="operations-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t.kicker}</p>
          <h1 id="operations-title">{t.title}</h1>
          <p>{t.intro}</p>
        </div>
        <button
          type="button"
          className="primary-action"
          onClick={() => void scan()}
          disabled={busy}
        >
          {busy ? t.scanning : t.scan}
        </button>
      </div>

      {error ? (
        <p role="alert" className="attention">
          {error}
        </p>
      ) : null}
      {notice ? <p role="status">{notice}</p> : null}
      {semanticOff ? <p className="war-room-note">{t.semanticOff}</p> : null}

      {!feed && !error ? (
        <div className="operations-kpi-loading" role="status" aria-busy="true">
          <span className="sr-only">{t.loading}</span>
          <dl className="city-pulse" aria-hidden="true">
            {Array.from({ length: 6 }, (_, index) => (
              <div key={index}>
                <Skeleton className="skeleton-label" />
                <Skeleton className="skeleton-value" />
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      {feed ? (
        <dl className="city-pulse">
          <div>
            <dt>{t.open}</dt>
            <dd>
              <AnimatedCount value={feed.pulse.open_appeals} locale={locale} />
            </dd>
          </div>
          <div>
            <dt>{t.incidents}</dt>
            <dd>
              <AnimatedCount
                value={feed.pulse.active_incidents}
                locale={locale}
              />
            </dd>
          </div>
          <div>
            <dt>{t.emerging}</dt>
            <dd>
              <AnimatedCount
                value={feed.pulse.emerging_patterns}
                locale={locale}
              />
            </dd>
          </div>
          <div>
            <dt>{t.unowned}</dt>
            <dd>
              <AnimatedCount
                value={feed.pulse.unowned_incidents}
                locale={locale}
              />
            </dd>
          </div>
          <div>
            <dt>{t.queued}</dt>
            <dd>
              <AnimatedCount
                value={feed.pulse.queued_deliveries}
                locale={locale}
              />
            </dd>
          </div>
          <div>
            <dt>{t.failed}</dt>
            <dd>
              <AnimatedCount
                value={feed.pulse.failed_deliveries}
                locale={locale}
              />
            </dd>
          </div>
        </dl>
      ) : null}

      <div className="operations-panels">
        <section className="operations-chart-panel" aria-label={t.activity}>
          {!arrivals && !error ? (
            <article
              className="lab-card chart-skeleton"
              role="status"
              aria-busy="true"
            >
              <span className="sr-only">{t.loading}</span>
              <Skeleton className="skeleton-heading" />
              <Skeleton className="skeleton-copy" />
              <Skeleton className="skeleton-chart" />
            </article>
          ) : null}

          {arrivals ? (
            <article className="lab-card">
              <h2>{t.activity}</h2>
              <p className="war-room-note">{t.activityNote}</p>
              <ArrivalChart
                buckets={arrivals.buckets}
                baseline={arrivals.baseline_per_bucket}
                peakStart={arrivals.peak?.start ?? null}
                excluded={arrivals.excluded_untrusted_time}
                excludedLabel={t.excluded}
                emptyLabel={t.noSeries}
                description={t.activityChartDescription}
              />
              {arrivals.peak ? (
                <p className="codes">
                  {t.peakLabel}: {arrivals.peak.start.slice(11, 16)} ·{" "}
                  {arrivals.peak.count} ·{" "}
                  {Object.entries(arrivals.peak.by_topic)
                    .sort((left, right) => right[1] - left[1])
                    .slice(0, 3)
                    .map(([topic, count]) => `${topic} ${count}`)
                    .join(" · ")}
                </p>
              ) : null}
            </article>
          ) : null}
        </section>

        <section className="operations-feed-panel" aria-label={t.attention}>
          <h2>{t.attention}</h2>
          {feed && feed.items.length === 0 ? (
            <p className="war-room-note">{t.quiet}</p>
          ) : null}

          <ul className="attention-feed">
            {(feed?.items ?? []).map((item, index) => (
              <li
                key={`${item.summary_code}-${index}`}
                className={`severity-${item.severity}`}
              >
                <div className="attention-main">
                  <span
                    className={`severity-dot severity-dot-${item.severity}`}
                    aria-hidden="true"
                  />
                  <div>
                    <strong>{attentionTitle(item, locale)}</strong>
                    <p className="codes">
                      {attentionDescription(item, locale)}
                    </p>
                  </div>
                </div>
                {item.target_kind === "cluster" && item.target_id ? (
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={() => void openCluster(item.target_id as string)}
                  >
                    {t.cluster}
                  </button>
                ) : null}
                {item.target_kind === "incident" && item.target_id ? (
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={() => onOpenIncident(item.target_id as string)}
                  >
                    {t.incidents}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <article className="lab-card operations-map-card">
        <h2>{t.mapOverview}</h2>
        <ReportMap
          points={overviewPoints}
          emptyLabel={t.noGeo}
          mode="overview"
          locale={locale}
          countLabel={appealCount(overviewPoints.length, locale)}
          ariaLabel={t.mapOverview}
        />
      </article>

      <AskPulse key={regionId} locale={locale} regionId={regionId} />

      {cluster ? (
        <article className="cluster-inspector">
          <div className="war-room-head">
            <div>
              <p className="eyebrow">
                {t.cluster} ·{" "}
                {cluster.state === "open"
                  ? locale === "ru"
                    ? "новый сигнал"
                    : "жаңа белгі"
                  : cluster.state}
              </p>
              <h2>{appealCount(cluster.appeal_count, locale)}</h2>
            </div>
            <button
              type="button"
              className="secondary-action"
              onClick={() => setCluster(null)}
            >
              {t.close}
            </button>
          </div>

          <dl className="war-room-stats">
            <div>
              <dt>{t.window}</dt>
              <dd>
                {localTime(cluster.first_seen_at, locale)}–
                {localTime(cluster.last_seen_at, locale)}
              </dd>
            </div>
            <div>
              <dt>{t.radius}</dt>
              <dd>
                {cluster.radius_m === null
                  ? "—"
                  : `${Math.round(cluster.radius_m)} m`}
              </dd>
            </div>
            <div>
              <dt>{t.novelty}</dt>
              <dd>{Math.round(cluster.novelty_score * 100)}%</dd>
            </div>
            <div>
              <dt>{t.cohesion}</dt>
              <dd>{Math.round(cluster.cohesion_score * 100)}%</dd>
            </div>
          </dl>

          <ReportMap
            points={points}
            centroid={
              cluster.centroid_longitude !== null &&
              cluster.centroid_latitude !== null
                ? {
                    longitude: cluster.centroid_longitude,
                    latitude: cluster.centroid_latitude,
                  }
                : null
            }
            spreadMetres={cluster.radius_m}
            emptyLabel={t.noGeo}
            mode="cluster"
            locale={locale}
            countLabel={appealCount(cluster.appeal_count, locale)}
            ariaLabel={t.cluster}
          />

          <h3>{t.timeline}</h3>
          <ArrivalHistogram members={cluster.members} locale={locale} />

          <p className="codes">
            {t.signals}:{" "}
            {cluster.signals_used
              .map((signal) => signalLabel(signal, locale))
              .join(" · ")}{" "}
            · {t.languages}:{" "}
            {Object.entries(cluster.languages)
              .map(([code, count]) => `${code} ${count}`)
              .join(" · ")}
          </p>
          <p className="war-room-note">{t.advisory}</p>

          <div className="cluster-actions">
            <button
              type="button"
              className="primary-action"
              disabled={busy}
              onClick={() => void promote(cluster)}
            >
              {t.promote}
            </button>
            <button
              type="button"
              className="secondary-action"
              disabled={busy}
              onClick={() =>
                void review(cluster, "known_pattern", "KNOWN_SEASONAL_PATTERN")
              }
            >
              {t.known}
            </button>
            <button
              type="button"
              className="secondary-action"
              disabled={busy}
              onClick={() => void review(cluster, "dismiss", "NOT_A_PATTERN")}
            >
              {t.dismiss}
            </button>
          </div>
        </article>
      ) : null}
    </section>
  );
}

function AnimatedCount({ value, locale }: { value: number; locale: Locale }) {
  const [displayValue, setDisplayValue] = useState(value);
  const previousValue = useRef(0);
  const reduceMotion = useSyncExternalStore(
    (callback) => {
      const query = window.matchMedia("(prefers-reduced-motion: reduce)");
      query.addEventListener("change", callback);
      return () => query.removeEventListener("change", callback);
    },
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
  const format = (count: number) =>
    new Intl.NumberFormat(locale === "ru" ? "ru-KZ" : "kk-KZ", {
      maximumFractionDigits: 0,
    }).format(count);

  useEffect(() => {
    const from = previousValue.current;
    previousValue.current = value;
    if (from === value) return;
    if (reduceMotion) return;

    const duration = 420;
    let frame = 0;
    let startedAt = 0;
    const animate = (timestamp: number) => {
      if (startedAt === 0) startedAt = timestamp;
      const progress = Math.min((timestamp - startedAt) / duration, 1);
      const eased = 1 - (1 - progress) ** 3;
      setDisplayValue(Math.round(from + (value - from) * eased));
      if (progress < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [reduceMotion, value]);

  const visibleValue = reduceMotion ? value : displayValue;

  return (
    <>
      <span aria-hidden="true">{format(visibleValue)}</span>
      <span className="sr-only">{format(value)}</span>
    </>
  );
}

/** How the reports arrived over time, in five-minute buckets. */
function ArrivalHistogram({
  members,
  locale,
}: {
  members: ClusterMember[];
  locale: Locale;
}) {
  const times = members
    .map((member) =>
      member.received_at ? Date.parse(member.received_at) : null,
    )
    .filter((value): value is number => value !== null);
  if (times.length === 0) return null;

  const start = Math.min(...times);
  const end = Math.max(...times);
  const bucketMs = 5 * 60 * 1000;
  const buckets = Math.max(1, Math.ceil((end - start) / bucketMs) + 1);
  const counts = new Array<number>(buckets).fill(0);
  for (const time of times) {
    counts[Math.floor((time - start) / bucketMs)] += 1;
  }
  const peak = Math.max(...counts, 1);

  return (
    <ol className="arrival-histogram">
      {counts.map((count, index) => (
        <li key={index}>
          <span className="time">
            {localTime(start + index * bucketMs, locale)}
          </span>
          <span
            className="bar"
            style={{ width: `${(count / peak) * 100}%` }}
            aria-hidden="true"
          />
          <span className="count">{count}</span>
        </li>
      ))}
    </ol>
  );
}
