"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { PresenterPreset } from "./presenter-panel";

type Locale = "ru" | "kk";
type IntakeDraft = {
  description: string;
  location: string;
  contact: "none" | "phone";
};
type DuplicateCandidate = {
  candidate_id: string;
  score: number;
  reasons: string[];
  distance_m?: number | null;
};
type IntakeQuestionItem = {
  field_id: string;
  prompt: string;
  evidence_type: string | null;
};
type IntakePlan = {
  question_items?: IntakeQuestionItem[];
  required_evidence_types?: string[];
  policy_version?: string;
};
type SubmissionAttempt = {
  idempotencyKey: string;
  body: string;
};

const labels = {
  ru: {
    eyebrow: "Гражданский канал",
    title: "Подать обращение",
    intro:
      "Ответьте на несколько коротких вопросов. Ответы остаются только на этой странице до отправки.",
    question: [
      "Что произошло?",
      "Где это произошло?",
      "Как с вами связаться?",
      "Уточните детали обращения",
      "Проверьте возможные дубликаты",
    ],
    adaptiveTitle: "Вопросы для уточнения",
    adaptiveIntro:
      "Оператор может задать эти вопросы, чтобы собрать недостающие сведения. Ответы здесь не записываются.",
    evidence: "Что может подтвердить ответ",
    planUnavailable: "Дополнительные вопросы сейчас недоступны.",
    noQuestions: "Дополнительные вопросы не требуются.",
    description: "Опишите проблему",
    location: "Адрес или ориентир",
    contact: "Предпочтительный канал",
    noContact: "Не связываться",
    phone: "Телефон будет добавлен оператором",
    next: "Далее",
    back: "Назад",
    sending: "Отправляем…",
    retry: "Повторить отправку",
    unconfirmed:
      "Не удалось подтвердить отправку. Ответы сохранены на странице. Повторите попытку: будет использован тот же номер запроса.",
    rejected: "Сервис отклонил обращение. Проверьте данные и попробуйте снова.",
    demoOnly:
      "Подача через сайт пока доступна только для синтетических испытаний. Рабочий приём откроется после подключения защищённого хранения исходных данных.",
    demoNotice:
      "Демонстрационный режим: используйте только вымышленные данные.",
    required: "Заполните это поле, чтобы продолжить.",
    duplicates: "Похожие открытые проблемы",
    duplicateHint:
      "Это только предложение. Ваше обращение не будет объединено автоматически.",
    checking: "Проверяем похожие обращения…",
    noDuplicates: "Похожих обращений не найдено.",
    preflightUnavailable:
      "Проверка сейчас недоступна. Обращение всё равно можно отправить.",
    same: "Это та же проблема",
    none: "Нет, создать новое обращение",
    review: "Подтвердить обращение",
    reviewText:
      "После подтверждения оператор проверит данные и присвоит номер обращения.",
    submit: "Подтвердить и отправить",
    submitted: "Обращение принято",
    number: "Номер обращения",
    newAppeal: "Подать ещё одно обращение",
    openInQueue: "Открыть в очереди оператора",
  },
  kk: {
    eyebrow: "Азамат арнасы",
    title: "Өтініш беру",
    intro:
      "Бірнеше қысқа сұраққа жауап беріңіз. Жауаптар жіберілгенше тек осы бетте қалады.",
    question: [
      "Не болды?",
      "Бұл қай жерде болды?",
      "Сізбен қалай байланысуға болады?",
      "Өтініш туралы мәліметтерді нақтылаңыз",
      "Ықтимал дубликаттарды тексеріңіз",
    ],
    adaptiveTitle: "Нақтылау сұрақтары",
    adaptiveIntro:
      "Оператор жетіспейтін мәліметтерді жинау үшін осы сұрақтарды қоя алады. Жауаптар мұнда жазылмайды.",
    evidence: "Жауапты растайтын мәліметтер",
    planUnavailable: "Қосымша сұрақтар қазір қолжетімсіз.",
    noQuestions: "Қосымша сұрақтар қажет емес.",
    description: "Мәселені сипаттаңыз",
    location: "Мекенжай немесе бағдар",
    contact: "Қалаулы байланыс арнасы",
    noContact: "Байланыспау",
    phone: "Телефонды оператор қосады",
    next: "Келесі",
    back: "Артқа",
    sending: "Жіберілуде…",
    retry: "Қайта жіберу",
    unconfirmed:
      "Өтініштің жіберілгенін растау мүмкін болмады. Жауаптар осы бетте қалды. Қайта жіберіңіз: сол сұрау нөмірі қолданылады.",
    rejected:
      "Қызмет өтінішті қабылдамады. Деректерді тексеріп, қайта көріңіз.",
    demoOnly:
      "Сайт арқылы жіберу әзірге тек синтетикалық сынақтар үшін қолжетімді. Нақты қабылдау бастапқы деректердің қорғалған сақтау орны қосылғаннан кейін ашылады.",
    demoNotice:
      "Демонстрациялық режим: тек ойдан шығарылған деректерді қолданыңыз.",
    required: "Жалғастыру үшін бұл жолды толтырыңыз.",
    duplicates: "Ұқсас ашық мәселелер",
    duplicateHint: "Бұл тек ұсыныс. Өтініш автоматты түрде біріктірілмейді.",
    checking: "Ұқсас өтініштер тексерілуде…",
    noDuplicates: "Ұқсас өтініштер табылмады.",
    preflightUnavailable:
      "Тексеру қазір қолжетімсіз. Өтінішті бәрібір жіберуге болады.",
    same: "Бұл сол мәселе",
    none: "Жоқ, жаңа өтініш жасау",
    review: "Өтінішті растау",
    reviewText:
      "Растағаннан кейін оператор деректерді тексеріп, өтініш нөмірін береді.",
    submit: "Растау және жіберу",
    submitted: "Өтініш қабылданды",
    number: "Өтініш нөмірі",
    newAppeal: "Тағы өтініш беру",
    openInQueue: "Оператор кезегінде ашу",
  },
} as const;

const initialDraft: IntakeDraft = {
  description: "",
  location: "",
  contact: "none",
};
export function Intake({
  locale,
  regionId,
  demoEnabled,
  presenterPreset,
  onOpenSubmitted,
}: {
  locale: Locale;
  regionId: string;
  demoEnabled: boolean;
  presenterPreset?: PresenterPreset | null;
  onOpenSubmitted?: (requestId: string) => void;
}) {
  const syntheticAssistEnabled = demoEnabled;
  const copy = labels[locale];
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<IntakeDraft>(
    presenterPreset
      ? {
          description: presenterPreset.description,
          location: presenterPreset.location,
          contact: "none",
        }
      : initialDraft,
  );
  const [error, setError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submissionLocked, setSubmissionLocked] = useState(false);
  const attemptRef = useRef<SubmissionAttempt | null>(null);
  const [duplicateChoice, setDuplicateChoice] = useState("none");
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([]);
  const [preflightState, setPreflightState] = useState<
    "idle" | "loading" | "ready" | "unavailable"
  >("idle");
  const [intakePlan, setIntakePlan] = useState<IntakePlan | null>(null);
  const [intakePlanUnavailable, setIntakePlanUnavailable] = useState(false);
  const [submittedNumber, setSubmittedNumber] = useState("");

  useEffect(() => {
    if (presenterPreset) return;
    const oldDraft = window.localStorage.getItem(
      "pulse109-guided-intake-draft",
    );
    window.localStorage.removeItem("pulse109-guided-intake-draft");
    if (!oldDraft) return;
    try {
      const parsed: unknown = JSON.parse(oldDraft);
      if (!parsed || typeof parsed !== "object") return;
      const values = parsed as Record<string, unknown>;
      const restored = {
        description:
          typeof values.description === "string" ? values.description : "",
        location: typeof values.location === "string" ? values.location : "",
        contact: values.contact === "phone" ? "phone" : "none",
      } as const;
      const timer = window.setTimeout(() => setDraft(restored), 0);
      return () => window.clearTimeout(timer);
    } catch {
      // An unreadable legacy draft is removed without exposing its contents.
    }
  }, [presenterPreset]);

  const progress = useMemo(() => `${step + 1} / 5`, [step]);

  function updateDraft<K extends keyof IntakeDraft>(
    key: K,
    value: IntakeDraft[K],
  ) {
    setDraft((current) => {
      return { ...current, [key]: value };
    });
    setError("");
    setSubmitError("");
  }

  async function goNext() {
    if (step === 0 && !draft.description.trim()) {
      setError(copy.required);
      return;
    }
    if (step === 1 && !draft.location.trim()) {
      setError(copy.required);
      return;
    }
    if (step === 2) {
      setIntakePlan(null);
      setIntakePlanUnavailable(!syntheticAssistEnabled);
      if (syntheticAssistEnabled) {
        const category = inferSyntheticCategory(draft.description);
        try {
          const response = await fetch("/api/core/intake/plans", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Region-Id": regionId,
            },
            body: JSON.stringify({
              service_id: `service:${category}`,
              topic_id: `topic:${category}`,
              locale,
              field_states: { description: "known", location: "known" },
              max_questions: 5,
            }),
          });
          if (!response.ok) throw new Error("intake_plan_failed");
          setIntakePlan((await response.json()) as IntakePlan);
        } catch {
          setIntakePlanUnavailable(true);
        }
      }
    }
    if (step === 3) {
      if (!syntheticAssistEnabled) {
        setPreflightState("unavailable");
      } else {
        setPreflightState("loading");
        const category = inferSyntheticCategory(draft.description);
        try {
          const response = await fetch("/api/core/appeals/preflight", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Region-Id": regionId,
            },
            body: JSON.stringify({
              region_id: regionId,
              service_id: `service:${category}`,
              topic_id: `topic:${category}`,
              text: draft.description,
              occurred_at: null,
              occurred_at_quality: "missing",
            }),
          });
          if (!response.ok) throw new Error("preflight_failed");
          const result = (await response.json()) as {
            candidates?: DuplicateCandidate[];
          };
          setDuplicates(result.candidates ?? []);
          setPreflightState("ready");
        } catch {
          setDuplicates([]);
          setPreflightState("unavailable");
        }
      }
    }
    setError("");
    setStep((current) => Math.min(4, current + 1));
  }

  async function submit() {
    if (!syntheticAssistEnabled) {
      setSubmitError(copy.demoOnly);
      return;
    }
    if (submitting) return;
    setSubmitting(true);
    setSubmitError("");
    if (!attemptRef.current) {
      const sourceRequestId = `web-${crypto.randomUUID()}`;
      const presetLocation =
        presenterPreset &&
        regionId === "ALA" &&
        draft.location === presenterPreset.location;
      attemptRef.current = {
        idempotencyKey: crypto.randomUUID(),
        body: JSON.stringify({
          source_system: presenterPreset
            ? "pulse109-demo-synthetic"
            : "pulse109-web-synthetic",
          source_request_id: sourceRequestId,
          region_id: regionId,
          received_at: presenterPreset ? new Date().toISOString() : null,
          received_at_quality: presenterPreset ? "exact" : "missing",
          channel: "web",
          language: locale,
          text: `${draft.description}\n${draft.location}`,
          consent_or_legal_basis: "SYNTHETIC_TEST_ONLY",
          ...(presetLocation
            ? {
                location: {
                  latitude: presenterPreset.latitude,
                  longitude: presenterPreset.longitude,
                  precision_m: 40,
                  geo_id: "ALA-SYNTHETIC-DISTRICT-4",
                },
              }
            : {}),
        }),
      };
    }
    setSubmissionLocked(true);
    const attempt = attemptRef.current;
    try {
      const response = await fetch("/api/core/requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": attempt.idempotencyKey,
          "X-Region-Id": regionId,
        },
        body: attempt.body,
      });
      if (!response.ok) {
        if (
          response.status >= 400 &&
          response.status < 500 &&
          ![408, 409, 429].includes(response.status)
        ) {
          attemptRef.current = null;
          setSubmissionLocked(false);
          setSubmitError(copy.rejected);
          return;
        }
        throw new Error("request_unconfirmed");
      }
      const result = (await response.json()) as { request_id?: string };
      if (!result.request_id || !isUuid(result.request_id)) {
        throw new Error("request_id_missing");
      }
      setSubmittedNumber(result.request_id);
      attemptRef.current = null;
    } catch {
      setSubmitError(copy.unconfirmed);
    } finally {
      setSubmitting(false);
    }
  }

  if (submittedNumber) {
    return (
      <section className="intake-shell" aria-labelledby="intake-complete-title">
        <section className="intake-card confirmation-card">
          <p className="eyebrow">{copy.submitted}</p>
          <h1 id="intake-complete-title">{copy.submitted}</h1>
          <p>{copy.number}</p>
          <strong className="appeal-number">{submittedNumber}</strong>
          {onOpenSubmitted ? (
            <button
              className="secondary-action"
              type="button"
              onClick={() => onOpenSubmitted(submittedNumber)}
            >
              {copy.openInQueue}
            </button>
          ) : null}
          <button
            className="primary-action"
            type="button"
            onClick={() => {
              setSubmittedNumber("");
              setStep(0);
              setDraft(initialDraft);
              setSubmissionLocked(false);
              setSubmitError("");
              attemptRef.current = null;
            }}
          >
            {copy.newAppeal}
          </button>
        </section>
      </section>
    );
  }

  return (
    <section className="intake-shell" aria-labelledby="intake-title">
      <section className="intake-card">
        <div className="intake-heading">
          <div>
            <p className="eyebrow">{copy.eyebrow}</p>
            <h1 id="intake-title">{copy.title}</h1>
            <p>{copy.intro}</p>
          </div>
          <span className="step-count" aria-label={`Step ${progress}`}>
            {progress}
          </span>
        </div>
        {!syntheticAssistEnabled ? (
          <p className="form-error" role="status">
            {copy.demoOnly}
          </p>
        ) : null}
        <div className="progress-track" aria-hidden="true">
          <span style={{ width: `${((step + 1) / 5) * 100}%` }} />
        </div>
        <p className="step-label">{copy.question[step]}</p>

        {step === 0 && (
          <div className="form-field">
            <label htmlFor="description">
              {copy.description} <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="description"
              rows={6}
              value={draft.description}
              disabled={submissionLocked}
              onChange={(event) =>
                updateDraft("description", event.target.value)
              }
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "description-error" : undefined}
            />
          </div>
        )}
        {step === 1 && (
          <div className="form-field">
            <label htmlFor="location">
              {copy.location} <span aria-hidden="true">*</span>
            </label>
            <input
              id="location"
              value={draft.location}
              disabled={submissionLocked}
              onChange={(event) => updateDraft("location", event.target.value)}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "location-error" : undefined}
            />
          </div>
        )}
        {step === 2 && (
          <fieldset className="form-field">
            <legend>{copy.contact}</legend>
            <label className="radio-row">
              <input
                type="radio"
                name="contact"
                checked={draft.contact === "none"}
                disabled={submissionLocked}
                onChange={() => updateDraft("contact", "none")}
              />{" "}
              {copy.noContact}
            </label>
            <label className="radio-row">
              <input
                type="radio"
                name="contact"
                checked={draft.contact === "phone"}
                disabled={submissionLocked}
                onChange={() => updateDraft("contact", "phone")}
              />{" "}
              {copy.phone}
            </label>
          </fieldset>
        )}
        {step === 3 && (
          <div
            className="adaptive-intake"
            aria-labelledby="adaptive-intake-title"
          >
            <h2 id="adaptive-intake-title">{copy.adaptiveTitle}</h2>
            <p>{copy.adaptiveIntro}</p>
            {intakePlanUnavailable ? (
              <p role="status">{copy.planUnavailable}</p>
            ) : (intakePlan?.question_items?.length ?? 0) > 0 ? (
              <ol className="adaptive-question-list">
                {intakePlan?.question_items?.map((item) => (
                  <li key={item.field_id}>
                    <strong>{item.prompt}</strong>
                    {item.evidence_type && (
                      <span className="evidence-tag">{item.evidence_type}</span>
                    )}
                  </li>
                ))}
              </ol>
            ) : (
              <p role="status">{copy.noQuestions}</p>
            )}
            {(intakePlan?.required_evidence_types?.length ?? 0) > 0 && (
              <div className="required-evidence">
                <span>{copy.evidence}</span>
                <ul>
                  {intakePlan?.required_evidence_types?.map((evidenceType) => (
                    <li key={evidenceType}>{evidenceType}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {step === 4 && (
          <div className="duplicate-review" aria-labelledby="duplicate-title">
            <h2 id="duplicate-title">{copy.duplicates}</h2>
            <p>{copy.duplicateHint}</p>
            <p role="status" aria-live="polite">
              {preflightState === "loading"
                ? copy.checking
                : preflightState === "unavailable"
                  ? copy.preflightUnavailable
                  : preflightState === "ready" && duplicates.length === 0
                    ? copy.noDuplicates
                    : ""}
            </p>
            {duplicates.map((candidate) => (
              <div className="duplicate-option" key={candidate.candidate_id}>
                <strong>
                  {candidate.candidate_id} · {Math.round(candidate.score * 100)}
                  %
                </strong>
                <span>{candidate.reasons.join(" · ")}</span>
                <label className="radio-row">
                  <input
                    type="radio"
                    name="duplicate"
                    value={candidate.candidate_id}
                    checked={duplicateChoice === candidate.candidate_id}
                    onChange={(event) => setDuplicateChoice(event.target.value)}
                  />{" "}
                  {copy.same}
                </label>
              </div>
            ))}
            <label className="radio-row">
              <input
                type="radio"
                name="duplicate"
                value="none"
                checked={duplicateChoice === "none"}
                onChange={(event) => setDuplicateChoice(event.target.value)}
              />{" "}
              {copy.none}
            </label>
            <div className="review-summary">
              <strong>{copy.review}</strong>
              <span>{copy.reviewText}</span>
            </div>
          </div>
        )}

        {error && (
          <p
            id={step === 0 ? "description-error" : "location-error"}
            className="form-error"
            role="alert"
          >
            {error}
          </p>
        )}
        {submitError && (
          <p className="form-error" role="alert">
            {submitError}
          </p>
        )}
        <div className="intake-actions">
          <button
            className="secondary-action"
            type="button"
            onClick={() => setStep((current) => Math.max(0, current - 1))}
            disabled={step === 0 || submissionLocked || submitting}
          >
            {copy.back}
          </button>
          {step < 4 ? (
            <button
              className="primary-action"
              type="button"
              onClick={goNext}
              disabled={submitting}
            >
              {copy.next}
            </button>
          ) : (
            <button
              className="primary-action"
              type="button"
              onClick={submit}
              disabled={submitting || !syntheticAssistEnabled}
            >
              {submitting
                ? copy.sending
                : submitError && submissionLocked
                  ? copy.retry
                  : copy.submit}
            </button>
          )}
        </div>
      </section>
    </section>
  );
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    value,
  );
}

function inferSyntheticCategory(description: string): string {
  const normalized = description.toLocaleLowerCase();
  if (/water|pipe|leak|вод|су|құбыр/.test(normalized)) return "water";
  if (/road|pothole|дорог|жол|шұңқыр/.test(normalized)) return "roads";
  if (/waste|trash|мусор|қоқыс/.test(normalized)) return "waste";
  return "utilities";
}
