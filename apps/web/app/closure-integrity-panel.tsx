"use client";

import { useRef, useState, type FormEvent } from "react";

type Locale = "ru" | "kk";
type Preflight = {
  preflight_id: string;
  request_id: string;
  region_id: string;
  evidence_hash: string;
  expected_appeal_version: number;
  requires_human_confirmation: true;
  source_status_sufficient: false;
};
type ClosureReceipt = {
  closure_id: string;
  request_id: string;
  region_id: string;
  status: "closed";
  evidence_hash: string;
  audit_event_id: string;
  outbox_event_id: string;
  replayed: boolean;
};
type Recurrence = {
  request_id: string;
  request_version: number;
  region_id: string;
  topic_id: string | null;
  state:
    | "insufficient_context"
    | "no_verified_history"
    | "history_present"
    | "recurring_pattern"
    | "possible_failed_resolution";
  window_days: number;
  verified_incident_count: number;
  recent_closure_count: number;
  evaluated_at: string | null;
  reason_codes: string[];
  incidents: {
    incident_id: string;
    first_reported_at: string;
    last_verified_closure_at: string;
    supporting_appeal_count: number;
  }[];
  advisory_only: true;
  requires_human_confirmation: true;
};
type PendingConfirmation = {
  body: {
    preflight_id: string;
    evidence_hash: string;
    confirm: true;
    reason_code: string;
    expected_appeal_version: number;
  };
  idempotencyKey: string;
  correlationId: string;
};

const hashPattern = /^sha256:[0-9a-f]{64}$/;
const codePattern = /^[A-Z][A-Z0-9_]{0,63}$/;
const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function stateLabel(locale: Locale, state: Recurrence["state"]) {
  const labels = {
    ru: {
      insufficient_context: "Недостаточно контекста",
      no_verified_history: "Нет подтверждённой истории",
      history_present: "Есть подтверждённая история",
      recurring_pattern: "Повторяющаяся закономерность",
      possible_failed_resolution: "Возможно, проблема не устранена",
    },
    kk: {
      insufficient_context: "Контекст жеткіліксіз",
      no_verified_history: "Расталған тарих жоқ",
      history_present: "Расталған тарих бар",
      recurring_pattern: "Қайталану үлгісі бар",
      possible_failed_resolution: "Мәселе шешілмеуі мүмкін",
    },
  };
  return labels[locale][state];
}

const copy = {
  ru: {
    title: "Проверка закрытия и повторные инциденты",
    description:
      "Доказательства привязываются к обращению. Закрытие выполняется только после явного подтверждения оператора.",
    advisory: "Только рекомендация",
    request: "UUID обращения",
    version: "Текущая версия обращения",
    resolution: "Код результата",
    evidence: "Хэш доказательства SHA-256",
    evidenceHelp:
      "Формат: sha256: и 64 шестнадцатеричных символа. Дубликаты доказательств не допускаются.",
    evidenceType: "Тип доказательства",
    prepare: "Проверить доказательства",
    preflight: "Проверка пройдена. Это не закрывает обращение.",
    preflightError:
      "Не удалось проверить доказательства. Проверьте регион, версию и данные.",
    human: "Я проверил доказательства и подтверждаю закрытие этого обращения.",
    reason: "Код причины закрытия",
    confirm: "Подтвердить закрытие",
    retry: "Повторить ту же отправку",
    saving: "Сохраняем закрытие и аудит…",
    pending: "Ответ не получен. Можно безопасно повторить ту же операцию.",
    success: "Обращение закрыто оператором.",
    replayed: "Сервер вернул сохранённый результат повтора.",
    audit: "Аудит",
    days: "дней",
    conflict:
      "Версия обращения изменилась или проверка устарела. Обновите карточку и выполните проверку заново.",
    error: "Операция отклонена. Проверьте данные и доступ к региону.",
    recurrence: "Оценка повторяемости",
    assess: "Проверить историю инцидентов",
    abstention: "Недостаточно подтверждённых данных для оценки повторяемости.",
    topic: "Тема",
    counts: "Подтверждённых инцидентов / недавних закрытий",
    incidents: "Подтверждённые инциденты",
    reasons: "Коды причин",
    currentVersion: "Оценка относится к версии обращения",
    stale:
      "Версия оценки отличается от указанной версии обращения. Обновите карточку перед использованием.",
    noAuto:
      "Оценка не меняет статус и не объединяет обращения. Решение принимает оператор.",
    loadError: "Оценка недоступна. Проверьте UUID и регион.",
    fields: "Введите корректные UUID, версию, коды и SHA-256 хэш.",
  },
  kk: {
    title: "Жабуды тексеру және қайталанатын оқиғалар",
    description:
      "Дәлелдер өтінішке байланысады. Жабу тек оператордың нақты растауынан кейін орындалады.",
    advisory: "Тек ұсыныс",
    request: "Өтініш UUID-і",
    version: "Өтініштің ағымдағы нұсқасы",
    resolution: "Нәтиже коды",
    evidence: "SHA-256 дәлел хэші",
    evidenceHelp:
      "Пішімі: sha256: және 64 он алтылық таңба. Қайталанатын дәлелдерге жол берілмейді.",
    evidenceType: "Дәлел түрі",
    prepare: "Дәлелдерді тексеру",
    preflight: "Тексеру өтті. Бұл өтінішті жаппайды.",
    preflightError:
      "Дәлелдерді тексеру мүмкін болмады. Аймақты, нұсқаны және деректерді тексеріңіз.",
    human: "Дәлелдерді тексеріп, осы өтінішті жабуды растаймын.",
    reason: "Жабу себебінің коды",
    confirm: "Жабуды растау",
    retry: "Сол жіберілімді қайталау",
    saving: "Жабу мен аудит сақталуда…",
    pending: "Жауап алынбады. Сол операцияны қауіпсіз қайталауға болады.",
    success: "Өтініш оператор арқылы жабылды.",
    replayed: "Сервер бұрын сақталған қайталау нәтижесін берді.",
    audit: "Аудит",
    days: "күн",
    conflict:
      "Өтініш нұсқасы өзгерді немесе тексеру ескірді. Карточканы жаңартып, тексеруді қайта орындаңыз.",
    error: "Операция қабылданбады. Деректер мен аймаққа кіруді тексеріңіз.",
    recurrence: "Қайталану бағасы",
    assess: "Оқиғалар тарихын тексеру",
    abstention: "Қайталануды бағалауға расталған дерек жеткіліксіз.",
    topic: "Тақырып",
    counts: "Расталған оқиғалар / соңғы жабылулар",
    incidents: "Расталған оқиғалар",
    reasons: "Себеп кодтары",
    currentVersion: "Бағалау өтініш нұсқасына қатысты",
    stale:
      "Бағалау нұсқасы көрсетілген өтініш нұсқасынан өзгеше. Қолданар алдында карточканы жаңартыңыз.",
    noAuto:
      "Бағалау күйді өзгертпейді және өтініштерді біріктірмейді. Шешімді оператор қабылдайды.",
    loadError: "Бағалау қолжетімсіз. UUID пен аймақты тексеріңіз.",
    fields: "Дұрыс UUID, нұсқа, кодтар және SHA-256 хэш енгізіңіз.",
  },
} as const;

export function ClosureIntegrityPanel({
  locale,
  regionId,
  initialRequestId,
}: {
  locale: Locale;
  regionId: string;
  initialRequestId: string;
}) {
  const t = copy[locale];
  const [requestId, setRequestId] = useState(initialRequestId);
  const canonicalRequestId = requestId.trim().toLowerCase();
  const [versionText, setVersionText] = useState("");
  const [resolutionCode, setResolutionCode] = useState("");
  const [evidenceHash, setEvidenceHash] = useState("");
  const [evidenceType, setEvidenceType] = useState("");
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [preflightError, setPreflightError] = useState(false);
  const [reasonCode, setReasonCode] = useState("");
  const [humanConfirmed, setHumanConfirmed] = useState(false);
  const [pending, setPending] = useState<PendingConfirmation | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmationError, setConfirmationError] = useState("");
  const [receipt, setReceipt] = useState<ClosureReceipt | null>(null);
  const [recurrence, setRecurrence] = useState<Recurrence | null>(null);
  const [recurrenceBusy, setRecurrenceBusy] = useState(false);
  const [recurrenceError, setRecurrenceError] = useState(false);
  const confirmationInFlight = useRef(false);

  const version = Number(versionText);
  const validInput =
    uuidPattern.test(canonicalRequestId) &&
    Number.isInteger(version) &&
    version >= 1 &&
    codePattern.test(resolutionCode) &&
    hashPattern.test(evidenceHash) &&
    /^[a-z][a-z0-9_]{0,63}$/.test(evidenceType);

  function resetPreflight() {
    setPreflight(null);
    setHumanConfirmed(false);
    setPending(null);
    setReceipt(null);
    setConfirmationError("");
  }

  async function runPreflight(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validInput || preflightBusy || pending) return;
    setPreflightBusy(true);
    setPreflightError(false);
    setPreflight(null);
    setReceipt(null);
    try {
      const response = await fetch(
        `/api/core/requests/${encodeURIComponent(canonicalRequestId)}/closure-preflight`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Region-Id": regionId,
            "X-Correlation-Id": crypto.randomUUID(),
          },
          body: JSON.stringify({
            resolution_code: resolutionCode,
            evidence: [
              { reference: evidenceHash, evidence_type: evidenceType },
            ],
            expected_appeal_version: version,
          }),
          cache: "no-store",
        },
      );
      if (!response.ok) throw new Error("preflight");
      const result = (await response.json()) as Preflight;
      if (
        result.request_id !== canonicalRequestId ||
        result.region_id !== regionId ||
        result.expected_appeal_version !== version ||
        result.requires_human_confirmation !== true ||
        result.source_status_sufficient !== false
      )
        throw new Error("preflight");
      setPreflight(result);
    } catch {
      setPreflightError(true);
    } finally {
      setPreflightBusy(false);
    }
  }

  async function submitConfirmation(command: PendingConfirmation) {
    if (!preflight || confirmationInFlight.current) return;
    confirmationInFlight.current = true;
    setSaving(true);
    setConfirmationError("");
    try {
      const response = await fetch(
        `/api/core/requests/${encodeURIComponent(preflight.request_id)}/closure-confirmations`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": command.idempotencyKey,
            "X-Region-Id": regionId,
            "X-Correlation-Id": command.correlationId,
          },
          body: JSON.stringify(command.body),
        },
      );
      if (response.status === 409) {
        setConfirmationError(t.conflict);
        setPending(null);
        setPreflight(null);
        setHumanConfirmed(false);
        return;
      }
      if (
        response.status === 403 ||
        (response.status >= 400 &&
          response.status < 500 &&
          response.status !== 429)
      ) {
        setConfirmationError(t.error);
        setPending(null);
        return;
      }
      if (!response.ok) throw new Error("retryable");
      const result = (await response.json()) as ClosureReceipt;
      if (
        result.request_id !== preflight.request_id ||
        result.region_id !== regionId ||
        result.evidence_hash !== preflight.evidence_hash ||
        result.status !== "closed"
      )
        throw new Error("retryable");
      setReceipt(result);
      setPending(null);
    } catch {
      setPending(command);
      setConfirmationError(t.pending);
    } finally {
      confirmationInFlight.current = false;
      setSaving(false);
    }
  }

  function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !preflight ||
      pending ||
      saving ||
      confirmationInFlight.current ||
      !humanConfirmed ||
      !codePattern.test(reasonCode)
    )
      return;
    const command: PendingConfirmation = {
      body: {
        preflight_id: preflight.preflight_id,
        evidence_hash: preflight.evidence_hash,
        confirm: true,
        reason_code: reasonCode,
        expected_appeal_version: preflight.expected_appeal_version,
      },
      idempotencyKey: crypto.randomUUID(),
      correlationId: crypto.randomUUID(),
    };
    setPending(command);
    void submitConfirmation(command);
  }

  async function loadRecurrence() {
    if (
      !uuidPattern.test(canonicalRequestId) ||
      !Number.isInteger(version) ||
      version < 1 ||
      recurrenceBusy
    )
      return;
    setRecurrenceBusy(true);
    setRecurrenceError(false);
    setRecurrence(null);
    try {
      const response = await fetch(
        `/api/core/requests/${encodeURIComponent(canonicalRequestId)}/recurrence-assessment`,
        { headers: { "X-Region-Id": regionId }, cache: "no-store" },
      );
      if (!response.ok) throw new Error("recurrence");
      const result = (await response.json()) as Recurrence;
      if (
        result.request_id !== canonicalRequestId ||
        result.region_id !== regionId ||
        result.advisory_only !== true ||
        result.requires_human_confirmation !== true
      )
        throw new Error("recurrence");
      setRecurrence(result);
    } catch {
      setRecurrenceError(true);
    } finally {
      setRecurrenceBusy(false);
    }
  }

  const staleRecurrence = Boolean(
    recurrence && version >= 1 && recurrence.request_version !== version,
  );
  const noHistory =
    recurrence &&
    ["insufficient_context", "no_verified_history"].includes(recurrence.state);
  const inputsLocked = Boolean(pending) || preflightBusy || recurrenceBusy;

  return (
    <section className="closure-panel" aria-labelledby="closure-title">
      <header className="closure-heading">
        <div>
          <p className="eyebrow">
            {locale === "ru" ? "Проверка доказательств" : "Дәлелдерді тексеру"}
          </p>
          <h3 id="closure-title">{t.title}</h3>
          <p>{t.description}</p>
        </div>
      </header>

      <form className="closure-form" onSubmit={runPreflight}>
        <label>
          <span>{t.request}</span>
          <input
            value={requestId}
            disabled={inputsLocked}
            onChange={(event) => {
              setRequestId(event.target.value);
              resetPreflight();
              setRecurrence(null);
            }}
            autoComplete="off"
          />
        </label>
        <label>
          <span>{t.version}</span>
          <input
            type="number"
            min="1"
            step="1"
            required
            value={versionText}
            disabled={inputsLocked}
            onChange={(event) => {
              setVersionText(event.target.value);
              resetPreflight();
            }}
          />
        </label>
        <label>
          <span>{t.resolution}</span>
          <input
            value={resolutionCode}
            maxLength={64}
            pattern="[A-Z][A-Z0-9_]{0,63}"
            required
            disabled={inputsLocked}
            onChange={(event) => {
              setResolutionCode(event.target.value);
              resetPreflight();
            }}
          />
        </label>
        <label>
          <span>{t.evidenceType}</span>
          <input
            value={evidenceType}
            maxLength={64}
            pattern="[a-z][a-z0-9_]{0,63}"
            required
            disabled={inputsLocked}
            onChange={(event) => {
              setEvidenceType(event.target.value);
              resetPreflight();
            }}
          />
        </label>
        <label className="closure-wide">
          <span>{t.evidence}</span>
          <input
            value={evidenceHash}
            maxLength={71}
            pattern="sha256:[0-9a-f]{64}"
            required
            disabled={inputsLocked}
            onChange={(event) => {
              setEvidenceHash(event.target.value);
              resetPreflight();
            }}
          />
          <small>{t.evidenceHelp}</small>
        </label>
        <div className="closure-wide closure-actions">
          <button
            className="secondary-action"
            type="submit"
            disabled={!validInput || preflightBusy || Boolean(pending)}
          >
            {preflightBusy ? "…" : t.prepare}
          </button>
          <button
            className="secondary-action"
            type="button"
            onClick={() => void loadRecurrence()}
            disabled={
              !uuidPattern.test(canonicalRequestId) ||
              !Number.isInteger(version) ||
              version < 1 ||
              recurrenceBusy
            }
          >
            {recurrenceBusy ? "…" : t.assess}
          </button>
        </div>
        <p className="ownership-help closure-wide">{t.fields}</p>
        {preflightError && (
          <p className="ownership-error closure-wide" role="alert">
            {t.preflightError}
          </p>
        )}
      </form>

      {preflight && (
        <div className="closure-preflight" role="status">
          <strong>{t.preflight}</strong>
          <span>
            {t.request}: {preflight.request_id} · {t.version}:{" "}
            {preflight.expected_appeal_version}
          </span>
          <span>
            {t.evidence}: <code>{preflight.evidence_hash}</code>
          </span>
        </div>
      )}

      {preflight && !receipt && (
        <form className="closure-confirm-form" onSubmit={confirm}>
          <label>
            <span>{t.reason}</span>
            <input
              value={reasonCode}
              maxLength={64}
              pattern="[A-Z][A-Z0-9_]{0,63}"
              required
              disabled={Boolean(pending)}
              onChange={(event) => setReasonCode(event.target.value)}
            />
          </label>
          <label className="ownership-confirmation">
            <input
              type="checkbox"
              checked={humanConfirmed}
              disabled={Boolean(pending)}
              onChange={(event) => setHumanConfirmed(event.target.checked)}
            />
            <span>{t.human}</span>
          </label>
          {confirmationError && (
            <p className="ownership-error closure-wide" role="alert">
              {confirmationError}
            </p>
          )}
          <div className="closure-actions closure-wide">
            {!pending && (
              <button
                className="primary-action"
                type="submit"
                disabled={!humanConfirmed || !codePattern.test(reasonCode)}
              >
                {t.confirm}
              </button>
            )}
            {pending && (
              <button
                className="secondary-action"
                type="button"
                disabled={saving}
                onClick={() => void submitConfirmation(pending)}
              >
                {saving ? t.saving : t.retry}
              </button>
            )}
          </div>
        </form>
      )}

      {receipt && (
        <div className="closure-receipt" role="status">
          <strong>{t.success}</strong>
          {receipt.replayed && <span>{t.replayed}</span>}
          <small>
            {t.audit}: {receipt.audit_event_id}
          </small>
        </div>
      )}

      <section
        className="recurrence-panel"
        aria-labelledby="recurrence-title"
        aria-live="polite"
      >
        <h4 id="recurrence-title">{t.recurrence}</h4>
        <span className="advisory-chip">{t.advisory}</span>
        <p>{t.noAuto}</p>
        {recurrenceError && (
          <p className="ownership-error" role="alert">
            {t.loadError}
          </p>
        )}
        {recurrence && (
          <>
            {noHistory ? (
              <p className="recurrence-abstention" role="status">
                {t.abstention}
              </p>
            ) : (
              <p>
                <strong>{stateLabel(locale, recurrence.state)}</strong> ·{" "}
                {t.topic}: {recurrence.topic_id ?? "—"}
              </p>
            )}
            <p>
              {t.currentVersion}: {recurrence.request_version} · {t.counts}:{" "}
              {recurrence.verified_incident_count} /{" "}
              {recurrence.recent_closure_count} · {recurrence.window_days}{" "}
              {t.days}
            </p>
            {staleRecurrence && (
              <p className="ownership-error" role="alert">
                {t.stale}
              </p>
            )}
            {recurrence.reason_codes.length > 0 && (
              <p>
                {t.reasons}: {recurrence.reason_codes.join(" · ")}
              </p>
            )}
            {recurrence.incidents.length > 0 && (
              <div>
                <strong>{t.incidents}</strong>
                <ul>
                  {recurrence.incidents.map((incident) => (
                    <li key={incident.incident_id}>
                      {incident.incident_id} · {incident.first_reported_at} ·{" "}
                      {incident.supporting_appeal_count}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </section>
    </section>
  );
}
