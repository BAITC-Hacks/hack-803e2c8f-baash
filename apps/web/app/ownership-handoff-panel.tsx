"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

type Locale = "ru" | "kk";
type Evidence = {
  rule_id: string;
  version: string;
  reason_code: string;
  source_ref: string | null;
  reason_codes: string[];
};
type Candidate = {
  organization_id: string;
  specificity: number;
  evidence: Evidence[];
  previously_rejected: boolean;
  previously_accepted: boolean;
};
type Assessment = {
  request_id: string;
  request_version: number;
  region_id: string;
  service_id: string | null;
  policy_time: string | null;
  policy_time_source: "received_at" | "observed_at_fallback" | null;
  candidates: Candidate[];
  reason_codes: string[];
  ambiguous: boolean;
  loop_risk: boolean;
  requires_human_confirmation: true;
  advisory_only: true;
  assigned_organization_id: null;
};
type Receipt = {
  outcome_id: string;
  request_id: string;
  assignment_id: string;
  region_id: string;
  disposition: "accepted" | "rejected";
  audit_event_id: string;
  outbox_event_id: string;
  replayed: boolean;
};
type Assignment = {
  assignment_id: string;
  request_id: string;
  request_version: number;
  new_version: number;
  service_id: string;
  assignee_unit_id: string | null;
  assigned_at: string;
};
type PendingCommand = {
  assignment_id: string;
  organization_id: string;
  disposition: "accepted" | "rejected";
  reason_code: string;
  source_event_id: string;
  evidence_refs: string[];
  idempotency_key: string;
};

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const translations = {
  ru: {
    title: "Ответственность и передача",
    description:
      "Оценка только для проверки оператором. Назначение не создаётся автоматически.",
    requestId: "UUID обращения",
    load: "Загрузить оценку",
    assignment: "UUID существующего назначения",
    assignmentUnavailable:
      "Для этой карточки API не вернуло существующее назначение. Результат нельзя записать без его идентификатора.",
    assignmentLoading: "Загружаем существующее назначение…",
    assignmentMissing:
      "Для обращения нет сохранённого назначения. Сначала подтвердите назначение в карточке.",
    service: "Служба",
    unit: "Подразделение",
    candidate: "Организация из кандидатов",
    disposition: "Результат передачи",
    accepted: "Принято организацией",
    rejected: "Отклонено организацией",
    reason: "Код причины",
    evidenceRefs: "Ссылки на подтверждения (sha256:…; необязательно)",
    submit: "Записать подтверждённый результат",
    retry: "Повторить ту же отправку",
    assessmentLoading: "Загружаем региональную оценку…",
    submitting: "Сохраняем результат и аудит…",
    none: "Для этого обращения пока нет кандидатов ответственности.",
    ambiguous: "Неоднозначность: требуется ручная проверка.",
    loop: "Риск цикла: эта организация ранее отклоняла передачу.",
    acceptedBefore: "Ранее принимала передачу",
    rejectedBefore: "Ранее отклоняла передачу",
    noAuto:
      "Оценка носит рекомендательный характер; назначенная организация отсутствует.",
    success:
      "Результат записан. Созданы аудиторское событие и событие синхронизации.",
    replayed: "Сервер подтвердил повтор уже сохранённой операции.",
    pending:
      "Ответ сервера не получен. Повтор сохранит тот же ключ идемпотентности.",
    auth: "Доступ запрещён для выбранного региона или роли.",
    unavailable:
      "Оценка сейчас недоступна. Проверьте соединение и повторите запрос.",
    noUuid: "Введите UUID реального обращения, чтобы загрузить оценку из API.",
    specificity: "Специфичность",
    policyTime: "Время политики",
    policySource: "Источник времени",
    errors: "Проверьте UUID назначения, код причины и ссылки sha256.",
    confirmLabel:
      "Я проверил оценку и подтверждаю этот результат для указанной организации.",
  },
  kk: {
    title: "Жауапкершілік және беру",
    description:
      "Тек оператор тексеретін бағалау. Тағайындау автоматты түрде жасалмайды.",
    requestId: "Өтініш UUID-і",
    load: "Бағалауды жүктеу",
    assignment: "Бар тағайындаудың UUID-і",
    assignmentUnavailable:
      "Бұл карточка үшін API бар тағайындауды қайтармады. Идентификаторсыз нәтиже жазылмайды.",
    assignmentLoading: "Бар тағайындау жүктелуде…",
    assignmentMissing:
      "Өтініште сақталған тағайындау жоқ. Алдымен карточкада тағайындауды растаңыз.",
    service: "Қызмет",
    unit: "Бөлімше",
    candidate: "Үміткерлердегі ұйым",
    disposition: "Берудің нәтижесі",
    accepted: "Ұйым қабылдады",
    rejected: "Ұйым қабылдамады",
    reason: "Себеп коды",
    evidenceRefs: "Растау сілтемелері (sha256:…; міндетті емес)",
    submit: "Расталған нәтижені жазу",
    retry: "Сол жіберілімді қайталау",
    assessmentLoading: "Өңірлік бағалау жүктелуде…",
    submitting: "Нәтиже мен аудит сақталуда…",
    none: "Бұл өтініште жауапкершілік үміткерлері әзірге жоқ.",
    ambiguous: "Екіұштылық: қолмен тексеру қажет.",
    loop: "Цикл қаупі: бұл ұйым беруді бұрын қабылдамаған.",
    acceptedBefore: "Бұрын беруді қабылдаған",
    rejectedBefore: "Бұрын беруді қабылдамаған",
    noAuto: "Бағалау ұсыныс ретінде беріледі; ұйым автоматты тағайындалмайды.",
    success: "Нәтиже жазылды. Аудит және синхрондау оқиғалары жасалды.",
    replayed: "Сервер бұрын сақталған операцияның қайталанғанын растады.",
    pending:
      "Сервер жауабы алынбады. Қайталау сол идемпотенттік кілтті қолданады.",
    auth: "Таңдалған өңірге немесе рөлге кіруге рұқсат жоқ.",
    unavailable: "Бағалау қазір қолжетімсіз. Байланысты тексеріп, қайталаңыз.",
    noUuid: "API бағалауын алу үшін нақты өтініштің UUID-ін енгізіңіз.",
    specificity: "Нақтылық деңгейі",
    policyTime: "Саясат уақыты",
    policySource: "Уақыт көзі",
    errors:
      "Тағайындау UUID-ін, себеп кодын және sha256 сілтемелерін тексеріңіз.",
    confirmLabel:
      "Бағалауды тексеріп, көрсетілген ұйым үшін осы нәтижені растаймын.",
  },
} as const;

export function OwnershipHandoffPanel({
  locale,
  regionId,
  initialRequestId,
  assignmentId,
  assignmentServiceId,
  assignmentUnitId,
}: {
  locale: Locale;
  regionId: string;
  initialRequestId: string;
  assignmentId?: string;
  assignmentServiceId?: string;
  assignmentUnitId?: string | null;
}) {
  const t = translations[locale];
  const [requestId, setRequestId] = useState(initialRequestId);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [assignmentState, setAssignmentState] = useState<
    "idle" | "loading" | "ready" | "missing" | "unavailable"
  >(assignmentId ? "ready" : "idle");
  const [loading, setLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState<
    "forbidden" | "unavailable" | ""
  >("");
  const [organizationId, setOrganizationId] = useState("");
  const [disposition, setDisposition] = useState<"accepted" | "rejected">(
    "accepted",
  );
  const [reasonCode, setReasonCode] = useState("");
  const [evidenceText, setEvidenceText] = useState("");
  const [pending, setPending] = useState<PendingCommand | null>(null);
  const [saving, setSaving] = useState(false);
  const [outcomeError, setOutcomeError] = useState("");
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [humanConfirmed, setHumanConfirmed] = useState(false);
  const effectiveAssignmentId =
    requestId.trim() === initialRequestId
      ? (assignmentId ?? assignment?.assignment_id)
      : assignment?.assignment_id;

  const validRequestId = uuidPattern.test(requestId.trim());
  const selectedCandidate = useMemo(
    () =>
      assessment?.candidates.find(
        (item) => item.organization_id === organizationId,
      ),
    [assessment, organizationId],
  );

  async function loadAssessment() {
    if (!validRequestId) return;
    setLoading(true);
    setAssessmentError("");
    setAssessment(null);
    setAssignment(null);
    setAssignmentState(
      assignmentId && requestId.trim() === initialRequestId ? "ready" : "idle",
    );
    setReceipt(null);
    setPending(null);
    try {
      const response = await fetch(
        `/api/core/requests/${encodeURIComponent(requestId.trim())}/ownership-assessment`,
        {
          headers: { "X-Region-Id": regionId },
          cache: "no-store",
        },
      );
      if (response.status === 403) throw new Error("forbidden");
      if (!response.ok) throw new Error("unavailable");
      const result = (await response.json()) as Assessment;
      setAssessment(result);
      setOrganizationId(result.candidates[0]?.organization_id ?? "");
      await loadLatestAssignment(result.request_id);
    } catch (error) {
      setAssessmentError(
        error instanceof Error && error.message === "forbidden"
          ? "forbidden"
          : "unavailable",
      );
    } finally {
      setLoading(false);
    }
  }

  const loadLatestAssignment = useCallback(
    async (id: string, showLoading = true) => {
      if (assignmentId && id === initialRequestId) return;
      if (showLoading) setAssignmentState("loading");
      try {
        const response = await fetch(
          `/api/core/requests/${encodeURIComponent(id)}/assignments/latest`,
          {
            headers: { "X-Region-Id": regionId },
            cache: "no-store",
          },
        );
        if (response.status === 404) {
          setAssignmentState("missing");
          return;
        }
        if (!response.ok) throw new Error("unavailable");
        setAssignment((await response.json()) as Assignment);
        setAssignmentState("ready");
      } catch {
        setAssignmentState("unavailable");
      }
    },
    [assignmentId, initialRequestId, regionId],
  );

  useEffect(() => {
    if (!uuidPattern.test(initialRequestId)) return;
    let cancelled = false;
    fetch(
      `/api/core/requests/${encodeURIComponent(initialRequestId)}/ownership-assessment`,
      {
        headers: { "X-Region-Id": regionId },
        cache: "no-store",
      },
    )
      .then(async (response) => {
        if (response.status === 403) throw new Error("forbidden");
        if (!response.ok) throw new Error("unavailable");
        return (await response.json()) as Assessment;
      })
      .then((result) => {
        if (cancelled) return;
        setAssessment(result);
        setOrganizationId(result.candidates[0]?.organization_id ?? "");
        void loadLatestAssignment(result.request_id, false);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setAssessmentError(
          error instanceof Error && error.message === "forbidden"
            ? "forbidden"
            : "unavailable",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [initialRequestId, loadLatestAssignment, regionId]);

  function makeCommand(): PendingCommand | null {
    const refs = evidenceText
      .split(/[\s,;]+/)
      .map((value) => value.trim())
      .filter(Boolean);
    if (
      !assessment ||
      !selectedCandidate ||
      !effectiveAssignmentId ||
      !humanConfirmed ||
      !reasonCode.trim() ||
      refs.some((ref) => !/^sha256:[0-9a-f]{64}$/.test(ref))
    )
      return null;
    return {
      assignment_id: effectiveAssignmentId,
      organization_id: selectedCandidate.organization_id,
      disposition,
      reason_code: reasonCode.trim(),
      source_event_id: `operator-${crypto.randomUUID()}`,
      evidence_refs: refs,
      idempotency_key: crypto.randomUUID(),
    };
  }

  async function submitOutcome(command: PendingCommand) {
    setSaving(true);
    setOutcomeError("");
    try {
      const response = await fetch(
        `/api/core/requests/${encodeURIComponent(assessment!.request_id)}/assignments/${encodeURIComponent(command.assignment_id)}/handoff-outcomes`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": command.idempotency_key,
            "X-Region-Id": regionId,
            "X-Correlation-Id": crypto.randomUUID(),
          },
          body: JSON.stringify({
            organization_id: command.organization_id,
            disposition: command.disposition,
            reason_code: command.reason_code,
            source_event_id: command.source_event_id,
            evidence_refs: command.evidence_refs,
          }),
        },
      );
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as {
          detail?: { message?: string };
          message?: string;
        };
        if (response.status === 403) {
          setOutcomeError(t.auth);
          setPending(null);
          return;
        }
        if (response.status < 500 && response.status !== 429) {
          setOutcomeError(
            body.detail?.message ??
              body.message ??
              `Request rejected (${response.status}).`,
          );
          setPending(null);
          return;
        }
        throw new Error("retryable");
      }
      setReceipt((await response.json()) as Receipt);
      setPending(null);
    } catch {
      setPending(command);
      setOutcomeError(t.pending);
    } finally {
      setSaving(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitAttempted(true);
    setReceipt(null);
    const command = makeCommand();
    if (command) void submitOutcome(command);
  }

  return (
    <section className="ownership-panel" aria-labelledby="ownership-title">
      <div className="ownership-heading">
        <div>
          <p className="eyebrow">M8 · human review</p>
          <h3 id="ownership-title">{t.title}</h3>
          <p>{t.description}</p>
        </div>
        <span className="advisory-chip">Advisory only</span>
      </div>

      <div className="ownership-load">
        <label>
          <span>{t.requestId}</span>
          <input
            value={requestId}
            onChange={(event) => {
              setRequestId(event.target.value);
              setAssessment(null);
              setAssignment(null);
              setAssignmentState("idle");
              setAssessmentError("");
              setPending(null);
              setReceipt(null);
              setHumanConfirmed(false);
            }}
            inputMode="text"
            autoComplete="off"
          />
        </label>
        <button
          type="button"
          className="secondary-action"
          onClick={() => void loadAssessment()}
          disabled={!validRequestId || loading}
        >
          {loading ? t.assessmentLoading : t.load}
        </button>
      </div>
      {!validRequestId && <p className="ownership-help">{t.noUuid}</p>}
      {assessmentError && (
        <p role="alert" className="ownership-error">
          {assessmentError === "forbidden" ? t.auth : t.unavailable}
        </p>
      )}
      {assessment && (
        <>
          <div className="ownership-facts">
            <span>
              {t.policyTime}: <strong>{assessment.policy_time ?? "—"}</strong>
            </span>
            <span>
              {t.policySource}:{" "}
              <strong>{assessment.policy_time_source ?? "—"}</strong>
            </span>
          </div>
          <div className="ownership-alerts" aria-live="polite">
            {assessment.ambiguous && <p role="status">{t.ambiguous}</p>}
            {assessment.loop_risk && <p role="alert">{t.loop}</p>}
            <p>{t.noAuto}</p>
          </div>
          {assessment.reason_codes.length > 0 && (
            <p className="ownership-reasons">
              {assessment.reason_codes.join(" · ")}
            </p>
          )}
          {assessment.candidates.length === 0 ? (
            <p>{t.none}</p>
          ) : (
            <div className="ownership-candidates" aria-label={t.title}>
              {assessment.candidates.map((candidate) => (
                <article
                  className="ownership-candidate"
                  key={candidate.organization_id}
                >
                  <div className="ownership-candidate-title">
                    <strong>{candidate.organization_id}</strong>
                    <span>
                      {t.specificity}: {candidate.specificity}
                    </span>
                  </div>
                  {(candidate.previously_rejected ||
                    candidate.previously_accepted) && (
                    <div className="ownership-history">
                      {candidate.previously_rejected && (
                        <span className="attention">{t.rejectedBefore}</span>
                      )}
                      {candidate.previously_accepted && (
                        <span>{t.acceptedBefore}</span>
                      )}
                    </div>
                  )}
                  {candidate.evidence.length === 0 ? (
                    <p>—</p>
                  ) : (
                    <ul>
                      {candidate.evidence.map((evidence, index) => (
                        <li
                          key={`${evidence.rule_id}:${evidence.version}:${index}`}
                        >
                          <strong>{evidence.reason_code}</strong> ·{" "}
                          {evidence.rule_id} v{evidence.version}
                          {evidence.reason_codes.length > 0 && (
                            <span> · {evidence.reason_codes.join(", ")}</span>
                          )}
                          {evidence.source_ref && (
                            <span> · {evidence.source_ref}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          )}
          <form className="ownership-outcome-form" onSubmit={onSubmit}>
            {effectiveAssignmentId ? (
              <p className="ownership-assignment">
                {t.assignment}: <strong>{effectiveAssignmentId}</strong>
                {(assignment?.service_id ?? assignmentServiceId) && (
                  <span>
                    {" "}
                    · {t.service}:{" "}
                    {assignment?.service_id ?? assignmentServiceId}
                  </span>
                )}
                {(assignment?.assignee_unit_id ?? assignmentUnitId) && (
                  <span>
                    {" "}
                    · {t.unit}:{" "}
                    {assignment?.assignee_unit_id ?? assignmentUnitId}
                  </span>
                )}
              </p>
            ) : (
              <p className="ownership-error" role="status">
                {assignmentState === "loading"
                  ? t.assignmentLoading
                  : assignmentState === "missing"
                    ? t.assignmentMissing
                    : t.assignmentUnavailable}
              </p>
            )}
            <label>
              <span>{t.candidate}</span>
              <select
                value={organizationId}
                onChange={(event) => setOrganizationId(event.target.value)}
                disabled={assessment.candidates.length === 0}
              >
                {assessment.candidates.map((candidate) => (
                  <option
                    key={candidate.organization_id}
                    value={candidate.organization_id}
                  >
                    {candidate.organization_id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{t.disposition}</span>
              <select
                value={disposition}
                onChange={(event) =>
                  setDisposition(event.target.value as "accepted" | "rejected")
                }
              >
                <option value="accepted">{t.accepted}</option>
                <option value="rejected">{t.rejected}</option>
              </select>
            </label>
            <label>
              <span>{t.reason}</span>
              <input
                value={reasonCode}
                onChange={(event) => setReasonCode(event.target.value)}
                pattern="[A-Za-z][A-Za-z0-9_:-]*"
                maxLength={128}
                required
              />
            </label>
            <label className="ownership-evidence-input">
              <span>{t.evidenceRefs}</span>
              <textarea
                value={evidenceText}
                onChange={(event) => setEvidenceText(event.target.value)}
                rows={2}
              />
            </label>
            <label className="ownership-confirmation">
              <input
                type="checkbox"
                checked={humanConfirmed}
                onChange={(event) => setHumanConfirmed(event.target.checked)}
              />
              <span>{t.confirmLabel}</span>
            </label>
            {submitAttempted && !pending && !receipt && !makeCommand() && (
              <p role="alert" className="ownership-error">
                {t.errors}
              </p>
            )}
            {outcomeError && (
              <p role="alert" className="ownership-error">
                {outcomeError}
              </p>
            )}
            {receipt && (
              <div className="ownership-receipt" role="status">
                <strong>{t.success}</strong>
                {receipt.replayed && <span>{t.replayed}</span>}
                <small>
                  Audit: {receipt.audit_event_id} · Outbox:{" "}
                  {receipt.outbox_event_id}
                </small>
              </div>
            )}
            <div className="ownership-actions">
              <button
                className="primary-action"
                type="submit"
                disabled={
                  saving ||
                  !!pending ||
                  !selectedCandidate ||
                  !effectiveAssignmentId
                }
              >
                {saving ? t.submitting : t.submit}
              </button>
              {pending && (
                <button
                  className="secondary-action"
                  type="button"
                  onClick={() => void submitOutcome(pending)}
                  disabled={saving}
                >
                  {saving ? t.submitting : t.retry}
                </button>
              )}
            </div>
          </form>
        </>
      )}
    </section>
  );
}
