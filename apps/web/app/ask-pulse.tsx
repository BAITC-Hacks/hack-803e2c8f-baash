"use client";

import { useRef, useState } from "react";
import {
  ArrowUpRight,
  Download,
  RotateCcw,
  Send,
  Sparkles,
} from "lucide-react";
import { AnalyticsChart } from "./analytics-chart";
import type { AskResponse, Locale } from "./ask-pulse-types";
import { Skeleton } from "./skeleton";
import styles from "./ask-pulse.module.css";

const EXPORT_PURPOSE =
  process.env.NEXT_PUBLIC_PULSE109_EXPORT_PURPOSE ?? "analytics-review";

const copy = {
  ru: {
    intro:
      "Задайте вопрос о динамике, темах или нагрузке. Ответ рассчитывается по доступным данным.",
    label: "Вопрос к данным",
    placeholder: "Как менялось число обращений за последние 7 дней?",
    send: "Спросить",
    loading: "Рассчитываем ответ…",
    fresh: "Новый вопрос",
    suggestions: [
      "Сколько обращений сегодня?",
      "Динамика обращений за последние 7 дней",
      "Какие темы самые частые за месяц?",
      "Где сейчас необычные всплески?",
      "Прогноз нагрузки на следующий месяц",
    ],
    followups: [
      "Покажи по дням",
      "Сравни с предыдущим периодом",
      "Есть ли там необычный всплеск?",
    ],
    total: "Обращений за период",
    signals: "Активных сигналов всплеска",
    forecastTotal: "Ожидаемых обращений за горизонт",
    metricTotal: "Значение метрики",
    previous: "Предыдущий период",
    comparison: "Изменение к предыдущему периоду",
    noComparison: "Процент изменения не определён",
    peak: "Пик",
    calculation: "Как рассчитано",
    parser: "Разбор вопроса",
    fallback: "Резервный CPU-парсер",
    evaluation: "Кандидат для оценки; качество не подтверждено",
    synthetic: "Синтетические данные",
    cutoff: "Данные до",
    period: "Период",
    metric: "Метрика",
    definition: "Определение",
    coverage: "Покрытие",
    missing: "Отсутствуют регионы",
    source: "Источники",
    excluded: "Исключено записей с недостоверным временем",
    unknown: "Не определено",
    quality: "Качество данных",
    drilldown: "Показать обращения",
    drillTitle: "Обращения за результатом",
    close: "Закрыть",
    excel: "Скачать Excel",
    pdf: "Скачать PDF",
    exporting: "Готовим файл…",
    clarify: "Нужно уточнение",
    abstained: "Нет достаточных оснований для ответа",
    unavailable: "Расчёт недоступен",
    retry: "Повторить запрос",
    failure: "Не удалось получить ответ",
    observed: "Наблюдалось",
    baseline: "Базовый уровень",
    forecast: "Прогноз",
    interval: "Интервал",
    received: "Поступило",
    service: "Служба",
    status: "Статус",
    timeQuality: "Достоверность времени",
    identifier: "Идентификатор источника",
    present: "есть данные",
    absent: "нет данных",
    stale: "устаревшие данные",
    partial: "частичное",
    complete: "полное",
    all: "Все доступные регионы",
    emptyDrill: "Для этого результата нет доступных обращений.",
  },
  kk: {
    intro:
      "Динамика, тақырыптар немесе жүктеме туралы сұраңыз. Жауап қолжетімді деректерден есептеледі.",
    label: "Деректерге сұрақ",
    placeholder: "Соңғы 7 күнде өтініштер саны қалай өзгерді?",
    send: "Сұрау",
    loading: "Жауап есептелуде…",
    fresh: "Жаңа сұрақ",
    suggestions: [
      "Бүгін қанша өтініш түсті?",
      "Соңғы 7 күндегі өтініштер динамикасы",
      "Соңғы айда қандай тақырыптар жиі кездеседі?",
      "Қазір қайда ерекше өсім бар?",
      "Келесі айға жүктеме болжамы",
    ],
    followups: [
      "Күндер бойынша көрсет",
      "Алдыңғы кезеңмен салыстыр",
      "Ол жерде ерекше өсім бар ма?",
    ],
    total: "Кезеңдегі өтініштер",
    signals: "Белсенді ауытқу сигналдары",
    forecastTotal: "Болжам кезеңіндегі өтініштер",
    metricTotal: "Метрика мәні",
    previous: "Алдыңғы кезең",
    comparison: "Алдыңғы кезеңге қатысты өзгеріс",
    noComparison: "Өзгеріс пайызы анықталмаған",
    peak: "Шың",
    calculation: "Қалай есептелді",
    parser: "Сұрақты талдау",
    fallback: "Резервтік CPU талдағышы",
    evaluation: "Бағалау кандидаты; сапасы расталмаған",
    synthetic: "Синтетикалық деректер",
    cutoff: "Деректердің шегі",
    period: "Кезең",
    metric: "Метрика",
    definition: "Анықтама",
    coverage: "Қамту",
    missing: "Деректері жоқ өңірлер",
    source: "Дереккөздер",
    excluded: "Уақыты сенімсіз болғандықтан есепке алынбаған",
    unknown: "Анықталмаған",
    quality: "Дерек сапасы",
    drilldown: "Өтініштерді көрсету",
    drillTitle: "Нәтиженің артындағы өтініштер",
    close: "Жабу",
    excel: "Excel жүктеу",
    pdf: "PDF жүктеу",
    exporting: "Файл дайындалуда…",
    clarify: "Нақтылау қажет",
    abstained: "Жауап беруге негіз жеткіліксіз",
    unavailable: "Есептеу қолжетімсіз",
    retry: "Қайта сұрау",
    failure: "Жауап алу мүмкін болмады",
    observed: "Бақыланған",
    baseline: "Базалық деңгей",
    forecast: "Болжам",
    interval: "Аралық",
    received: "Түскен уақыты",
    service: "Қызмет",
    status: "Мәртебе",
    timeQuality: "Уақыттың сенімділігі",
    identifier: "Дереккөз идентификаторы",
    present: "дерек бар",
    absent: "дерек жоқ",
    stale: "ескірген деректер",
    partial: "ішінара",
    complete: "толық",
    all: "Қолжетімді өңірлер",
    emptyDrill: "Бұл нәтиже үшін қолжетімді өтініштер жоқ.",
  },
} as const;

type Drilldown = {
  appeals: {
    request_id: string;
    source_request_id: string;
    status: string;
    received_at: string | null;
    received_at_quality: string;
    language: string;
    service_id: string | null;
  }[];
};

function dateTime(value: string, locale: Locale) {
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? date.toLocaleString(`${locale}-KZ`, {
        timeZone: "Asia/Qyzylorda",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : value;
}

async function checkResponse(response: Response): Promise<Response> {
  if (response.ok) return response;
  const body = await response.json().catch(() => null);
  throw new Error(
    body?.detail?.code ?? body?.code ?? `HTTP ${response.status}`,
  );
}

export function AskPulse({
  locale,
  regionId,
}: {
  locale: Locale;
  regionId: string;
}) {
  const t = copy[locale];
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [contextToken, setContextToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [drill, setDrill] = useState<Drilldown | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Scope changes remount this component in Operations Center. No context is
  // persisted in browser storage or shared with another actor or region.
  const headers = {
    "Content-Type": "application/json",
    "X-Region-Id": regionId,
  };

  async function ask(value: string, token = contextToken) {
    const trimmed = value.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    setActionError(null);
    setDrill(null);
    setAsked(trimmed);
    setQuestion("");
    setResult(null);
    try {
      const response = await checkResponse(
        await fetch("/api/core/analytics/ask", {
          method: "POST",
          headers,
          body: JSON.stringify({
            question: trimmed,
            locale: `${locale}-KZ`,
            ...(token ? { context_token: token } : {}),
          }),
          cache: "no-store",
        }),
      );
      const payload = (await response.json()) as AskResponse;
      if (payload.schema_version !== "ask-pulse-v1")
        throw new Error("unsupported_ask_schema");
      setResult(payload);
      setContextToken(payload.context_token);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "ask_unavailable");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setResult(null);
    setContextToken(null);
    setAsked("");
    setQuestion("");
    setError(null);
    setActionError(null);
    setDrill(null);
    inputRef.current?.focus();
  }

  async function download(format: "pdf" | "xlsx") {
    if (!result?.actions.export_token || actionBusy) return;
    setActionBusy(format);
    setActionError(null);
    try {
      const response = await checkResponse(
        await fetch("/api/core/analytics/ask/export", {
          method: "POST",
          headers: { ...headers, "X-Export-Purpose": EXPORT_PURPOSE },
          body: JSON.stringify({
            result_token: result.actions.export_token,
            format,
          }),
          cache: "no-store",
        }),
      );
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `pulse109-analytics.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (failure) {
      setActionError(
        failure instanceof Error ? failure.message : "export_unavailable",
      );
    } finally {
      setActionBusy(null);
    }
  }

  async function openDrilldown() {
    const path = result?.actions.drilldown_url;
    if (!path || actionBusy) return;
    setActionBusy("drilldown");
    setActionError(null);
    try {
      // Only the published Ask Pulse drill-down route is accepted. API-provided
      // links cannot send the operator's identity to another origin.
      const target = new URL(path, window.location.origin);
      if (
        target.origin !== window.location.origin ||
        target.pathname !== "/v1/analytics/ask/drilldown"
      )
        throw new Error("invalid_drilldown_route");
      const response = await checkResponse(
        await fetch(`/api/core${target.pathname.slice(3)}`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            context_token: result.context_token,
            limit: 100,
          }),
          cache: "no-store",
        }),
      );
      setDrill((await response.json()) as Drilldown);
    } catch (failure) {
      setActionError(
        failure instanceof Error ? failure.message : "drilldown_unavailable",
      );
    } finally {
      setActionBusy(null);
    }
  }

  const provenance = result?.provenance;
  const number = (value: number) =>
    value.toLocaleString(`${locale}-KZ`, { maximumFractionDigits: 1 });
  const stateLabel =
    result?.status === "clarification_required"
      ? t.clarify
      : result?.status === "abstained"
        ? t.abstained
        : t.unavailable;
  const coverageLabel = (value: string) =>
    value === "present" ? t.present : value === "missing" ? t.absent : t.stale;
  const totalLabel =
    result?.intent?.intent_type === "surge"
      ? t.signals
      : result?.intent?.intent_type === "forecast"
        ? t.forecastTotal
        : result?.query?.metric_id === "appeals_volume"
          ? t.total
          : t.metricTotal;

  return (
    <article
      className={styles.panel}
      aria-labelledby="ask-pulse-title"
      aria-busy={busy}
    >
      <header className={styles.heading}>
        <div>
          <h2 id="ask-pulse-title">
            <Sparkles size={18} aria-hidden="true" /> Ask Pulse
          </h2>
          <p className={styles.note}>{t.intro}</p>
        </div>
        {asked || contextToken ? (
          <button
            type="button"
            className={styles.reset}
            disabled={busy || actionBusy !== null}
            onClick={reset}
          >
            <RotateCcw size={14} aria-hidden="true" />
            {t.fresh}
          </button>
        ) : null}
      </header>
      {result?.query && contextToken ? (
        <ul className={styles.chips} aria-label={t.period}>
          <li>
            {result.query.filters
              .find((filter) => filter.field === "region_id")
              ?.value.toString() ?? (regionId === "ALL" ? t.all : regionId)}
          </li>
          {result.query.filters
            .filter((filter) => filter.field !== "region_id")
            .map((filter) => (
              <li key={filter.field}>{filter.value.toString()}</li>
            ))}
          <li>
            {dateTime(result.query.time_from, locale)} —{" "}
            {dateTime(result.query.time_to, locale)}
          </li>
        </ul>
      ) : null}
      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          void ask(question);
        }}
      >
        <label htmlFor="ask-pulse-question" className={styles.inputLabel}>
          {t.label}
        </label>
        <div className={styles.inputRow}>
          <Sparkles
            className={styles.composerIcon}
            size={17}
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            id="ask-pulse-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t.placeholder}
            maxLength={2000}
            disabled={busy}
            autoComplete="off"
          />
          <button
            type="submit"
            className="primary-action"
            disabled={busy || !question.trim()}
            aria-label={busy ? t.loading : t.send}
          >
            <Send size={16} aria-hidden="true" />
            <span className="sr-only">{busy ? t.loading : t.send}</span>
          </button>
        </div>
      </form>
      {!result && !busy && !asked ? (
        <div className={styles.suggestions}>
          {t.suggestions.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => void ask(prompt, null)}
            >
              {prompt}
              <ArrowUpRight size={13} aria-hidden="true" />
            </button>
          ))}
        </div>
      ) : null}
      <div aria-live="polite" aria-atomic="true">
        {busy ? (
          <div className={styles.loading} role="status" aria-busy="true">
            <span className="sr-only">{t.loading}</span>
            <Skeleton className="skeleton-heading" />
            <Skeleton className="skeleton-copy" />
            <Skeleton className="skeleton-chart" />
          </div>
        ) : null}
        {error ? (
          <div className={styles.state} role="alert">
            <strong>{t.failure}</strong>
            <p className="codes">{error}</p>
            <button
              type="button"
              className="secondary-action"
              onClick={() => void ask(asked)}
            >
              {t.retry}
            </button>
          </div>
        ) : null}
        {result ? (
          <section className={styles.result} aria-label={asked}>
            <div className={styles.resultHeading}>
              <p className={styles.question}>{asked}</p>
              {result.synthetic ? (
                <span className={styles.synthetic}>{t.synthetic}</span>
              ) : null}
            </div>
            {result.inference ? (
              <p className={styles.note}>
                {t.parser}: {result.inference.model_name} ·{" "}
                {result.inference.model_alias} · {result.inference.runtime}
                {result.inference.fallback_used
                  ? ` · ${t.fallback} (${result.inference.fallback_reason ?? "—"})`
                  : ""}
                {result.inference.approval_state === "evaluation"
                  ? ` · ${t.evaluation}`
                  : ""}
              </p>
            ) : null}
            {result.status !== "available" ? (
              <div className={styles.state}>
                <strong>{stateLabel}</strong>
                <p>{result.answer.text}</p>
                {result.reason_code ? (
                  <p className="codes">{result.reason_code}</p>
                ) : null}
                {result.clarification ? (
                  <div
                    className={styles.suggestions}
                    aria-label={result.clarification.prompt}
                  >
                    <p>{result.clarification.prompt}</p>
                    {result.clarification.options.map((option) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() =>
                          void ask(`${asked} ${option}`, contextToken)
                        }
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <>
                <p className={styles.answer}>{result.answer.text}</p>
                {result.answer.total !== null ? (
                  <dl className={styles.numbers}>
                    <div>
                      <dt>{totalLabel}</dt>
                      <dd>{number(result.answer.total)}</dd>
                    </div>
                    {result.answer.previous_total !== null ? (
                      <div>
                        <dt>{t.previous}</dt>
                        <dd>{number(result.answer.previous_total)}</dd>
                      </div>
                    ) : null}
                    {result.answer.change_pct !== null ? (
                      <div>
                        <dt>{t.comparison}</dt>
                        <dd>
                          {result.answer.change_pct > 0 ? "+" : ""}
                          {number(result.answer.change_pct)}%
                        </dd>
                      </div>
                    ) : result.answer.previous_total !== null ? (
                      <div>
                        <dt>{t.comparison}</dt>
                        <dd className={styles.noComparison}>
                          {t.noComparison}
                        </dd>
                      </div>
                    ) : null}
                  </dl>
                ) : null}
                {result.chart ? (
                  <AnalyticsChart spec={result.chart} locale={locale} />
                ) : null}
                {result.answer.peak ? (
                  <p className={styles.note}>
                    {t.peak}: {dateTime(result.answer.peak.period, locale)} ·{" "}
                    {number(result.answer.peak.value)}
                  </p>
                ) : null}
                {result.forecast ? (
                  <p className={styles.note}>
                    {t.forecast}:{" "}
                    {result.forecast.baseline === null
                      ? "—"
                      : number(result.forecast.baseline)}{" "}
                    · {t.interval}:{" "}
                    {result.forecast.lower_bound === null
                      ? "—"
                      : number(result.forecast.lower_bound)}
                    –
                    {result.forecast.upper_bound === null
                      ? "—"
                      : number(result.forecast.upper_bound)}{" "}
                    · {result.forecast.method} · {result.forecast.version}
                  </p>
                ) : null}
                {result.alerts.length ? (
                  <ul className={styles.alerts}>
                    {result.alerts.map((alert) => (
                      <li key={alert.alert_id}>
                        <strong>
                          {alert.region_id} · {alert.type}
                        </strong>
                        <span>
                          {dateTime(alert.detected_at, locale)} · {t.observed}:{" "}
                          {alert.observed_value === null
                            ? "—"
                            : number(alert.observed_value)}{" "}
                          · {t.baseline}:{" "}
                          {alert.baseline === null
                            ? "—"
                            : number(alert.baseline)}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            )}
            {provenance ? (
              <>
                <p className={styles.cutoff}>
                  {t.cutoff}: {dateTime(provenance.data_cutoff, locale)} ·{" "}
                  {t.coverage}:{" "}
                  {Object.entries(provenance.coverage)
                    .map(
                      ([region, state]) => `${region}: ${coverageLabel(state)}`,
                    )
                    .join(" · ")}
                </p>
                <details className={styles.calculation}>
                  <summary>{t.calculation}</summary>
                  <dl className={styles.provenance}>
                    <div>
                      <dt>{t.metric}</dt>
                      <dd>
                        {provenance.metric_id} · v{provenance.metric_version}
                      </dd>
                    </div>
                    <div>
                      <dt>{t.definition}</dt>
                      <dd>{provenance.definition}</dd>
                    </div>
                    <div>
                      <dt>{t.period}</dt>
                      <dd>
                        {dateTime(provenance.time_from, locale)} —{" "}
                        {dateTime(provenance.time_to, locale)} (UTC+05:00)
                      </dd>
                    </div>
                    <div>
                      <dt>{t.cutoff}</dt>
                      <dd>{dateTime(provenance.data_cutoff, locale)}</dd>
                    </div>
                    <div>
                      <dt>{t.excluded}</dt>
                      <dd>
                        {provenance.excluded_records === null
                          ? t.unknown
                          : number(provenance.excluded_records)}
                      </dd>
                    </div>
                    <div>
                      <dt>{t.missing}</dt>
                      <dd>{provenance.missing_regions.join(", ") || "—"}</dd>
                    </div>
                    <div>
                      <dt>{t.source}</dt>
                      <dd>{provenance.source_refs.join(" · ") || t.unknown}</dd>
                    </div>
                    {result.result ? (
                      <div>
                        <dt>{t.quality}</dt>
                        <dd>
                          {result.result.quality === "complete"
                            ? t.complete
                            : result.result.quality === "partial"
                              ? t.partial
                              : coverageLabel(result.result.quality)}
                        </dd>
                      </div>
                    ) : null}
                  </dl>
                  {provenance.limitations.length ? (
                    <ul className={styles.limitations}>
                      {provenance.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  ) : null}
                </details>
              </>
            ) : null}
            {result.status === "available" ? (
              <div className={styles.actions}>
                {result.actions.drilldown_url ? (
                  <button
                    type="button"
                    className="secondary-action"
                    disabled={actionBusy !== null}
                    onClick={() => void openDrilldown()}
                  >
                    {t.drilldown}
                    <ArrowUpRight size={14} aria-hidden="true" />
                  </button>
                ) : null}
                {result.actions.export_token
                  ? result.actions.export_formats.map((format) => (
                      <button
                        key={format}
                        type="button"
                        className="secondary-action"
                        disabled={actionBusy !== null}
                        onClick={() => void download(format)}
                      >
                        <Download size={14} aria-hidden="true" />
                        {actionBusy === format
                          ? t.exporting
                          : format === "pdf"
                            ? t.pdf
                            : t.excel}
                      </button>
                    ))
                  : null}
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
      {actionError ? (
        <p className="attention" role="alert">
          {actionError}
        </p>
      ) : null}
      {actionBusy === "drilldown" ? (
        <p role="status" className={styles.note}>
          {t.loading}
        </p>
      ) : null}
      {drill ? (
        <section className={styles.drilldown} aria-label={t.drillTitle}>
          <div className={styles.heading}>
            <h3>{t.drillTitle}</h3>
            <button
              type="button"
              className="secondary-action"
              onClick={() => setDrill(null)}
            >
              {t.close}
            </button>
          </div>
          {drill.appeals.length ? (
            <div className={styles.tableScroll}>
              <table className="lab-table">
                <thead>
                  <tr>
                    <th scope="col">{t.identifier}</th>
                    <th scope="col">{t.status}</th>
                    <th scope="col">{t.received}</th>
                    <th scope="col">{t.timeQuality}</th>
                    <th scope="col">{t.service}</th>
                  </tr>
                </thead>
                <tbody>
                  {drill.appeals.map((appeal) => (
                    <tr key={appeal.request_id}>
                      <td>{appeal.source_request_id}</td>
                      <td>{appeal.status}</td>
                      <td>
                        {appeal.received_at
                          ? dateTime(appeal.received_at, locale)
                          : "—"}
                      </td>
                      <td>{appeal.received_at_quality}</td>
                      <td>{appeal.service_id ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>{t.emptyDrill}</p>
          )}
        </section>
      ) : null}
      {result?.status === "available" && contextToken ? (
        <div className={styles.suggestions}>
          {t.followups.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={busy || actionBusy !== null}
              onClick={() => void ask(prompt)}
            >
              {prompt}
              <ArrowUpRight size={13} aria-hidden="true" />
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}
