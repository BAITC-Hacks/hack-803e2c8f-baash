"use client";

import { useMemo, useState } from "react";

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

const labels = {
  ru: {
    eyebrow: "Гражданский канал",
    title: "Подать обращение",
    intro:
      "Ответьте на несколько коротких вопросов. Черновик сохраняется на этом устройстве.",
    question: [
      "Что произошло?",
      "Где это произошло?",
      "Как с вами связаться?",
      "Проверьте возможные дубликаты",
    ],
    description: "Опишите проблему",
    location: "Адрес или ориентир",
    contact: "Предпочтительный канал",
    noContact: "Не связываться",
    phone: "Телефон будет добавлен оператором",
    next: "Далее",
    back: "Назад",
    save: "Черновик сохранён",
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
    offline:
      "Онлайн-сервис недоступен. Черновик сохранён; показан демонстрационный номер.",
  },
  kk: {
    eyebrow: "Азамат арнасы",
    title: "Өтініш беру",
    intro: "Бірнеше қысқа сұраққа жауап беріңіз. Жоба осы құрылғыда сақталады.",
    question: [
      "Не болды?",
      "Бұл қай жерде болды?",
      "Сізбен қалай байланысуға болады?",
      "Ықтимал дубликаттарды тексеріңіз",
    ],
    description: "Мәселені сипаттаңыз",
    location: "Мекенжай немесе бағдар",
    contact: "Қалаулы байланыс арнасы",
    noContact: "Байланыспау",
    phone: "Телефонды оператор қосады",
    next: "Келесі",
    back: "Артқа",
    save: "Жоба сақталды",
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
    offline:
      "Онлайн қызмет қолжетімсіз. Жоба сақталды; демонстрациялық нөмір көрсетілді.",
  },
} as const;

const initialDraft: IntakeDraft = {
  description: "",
  location: "",
  contact: "none",
};
const draftKey = "pulse109-guided-intake-draft";

export function Intake({ locale }: { locale: Locale }) {
  const copy = labels[locale];
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<IntakeDraft>(() => readDraft());
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(() => hasDraft());
  const [duplicateChoice, setDuplicateChoice] = useState("none");
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([]);
  const [preflightState, setPreflightState] = useState<
    "idle" | "loading" | "ready" | "unavailable"
  >("idle");
  const [submittedNumber, setSubmittedNumber] = useState("");
  const [offline, setOffline] = useState(false);

  const progress = useMemo(() => `${step + 1} / 4`, [step]);

  function updateDraft<K extends keyof IntakeDraft>(
    key: K,
    value: IntakeDraft[K],
  ) {
    setDraft((current) => {
      const next = { ...current, [key]: value };
      window.localStorage.setItem(draftKey, JSON.stringify(next));
      return next;
    });
    setSaved(true);
    setError("");
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
      setPreflightState("loading");
      const category = inferSyntheticCategory(draft.description);
      try {
        const response = await fetch("/api/core/appeals/preflight", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Region-Id": "ALA",
          },
          body: JSON.stringify({
            region_id: "ALA",
            service_id: `service:${category}`,
            topic_id: `topic:${category}`,
            text: draft.description,
            occurred_at: new Date().toISOString(),
            occurred_at_quality: "exact",
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
    setError("");
    setStep((current) => Math.min(3, current + 1));
  }

  async function submit() {
    const sourceRequestId = `web-${crypto.randomUUID()}`;
    const idempotencyKey = crypto.randomUUID();
    try {
      const response = await fetch("/api/core/requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
          "X-Region-Id": "ALA",
        },
        body: JSON.stringify({
          source_system: "pulse109-web",
          source_request_id: sourceRequestId,
          region_id: "ALA",
          received_at: new Date().toISOString(),
          channel: "web",
          language: locale,
          text: draft.description,
          location: { address_text_private_ref: draft.location },
        }),
      });
      if (!response.ok) throw new Error("request_failed");
      const result = (await response.json()) as { request_id?: string };
      setSubmittedNumber(
        result.request_id ?? `SYN-109-${sourceRequestId.slice(-6)}`,
      );
    } catch {
      setOffline(true);
      setSubmittedNumber(`SYN-109-${sourceRequestId.slice(-6)}`);
    }
    window.localStorage.removeItem(draftKey);
  }

  if (submittedNumber) {
    return (
      <section className="intake-shell" aria-labelledby="intake-complete-title">
        <section className="intake-card confirmation-card">
          <p className="eyebrow">{copy.submitted}</p>
          <h1 id="intake-complete-title">{copy.submitted}</h1>
          <p>{copy.number}</p>
          <strong className="appeal-number">{submittedNumber}</strong>
          {offline && (
            <p className="form-error" role="alert">
              {copy.offline}
            </p>
          )}
          <button
            className="primary-action"
            type="button"
            onClick={() => {
              setSubmittedNumber("");
              setStep(0);
              setDraft(initialDraft);
              setOffline(false);
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
        <div className="progress-track" aria-hidden="true">
          <span style={{ width: `${((step + 1) / 4) * 100}%` }} />
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
                onChange={() => updateDraft("contact", "none")}
              />{" "}
              {copy.noContact}
            </label>
            <label className="radio-row">
              <input
                type="radio"
                name="contact"
                checked={draft.contact === "phone"}
                onChange={() => updateDraft("contact", "phone")}
              />{" "}
              {copy.phone}
            </label>
          </fieldset>
        )}
        {step === 3 && (
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
        <p className="draft-status" role="status" aria-live="polite">
          {saved ? copy.save : ""}
        </p>
        <div className="intake-actions">
          <button
            className="secondary-action"
            type="button"
            onClick={() => setStep((current) => Math.max(0, current - 1))}
            disabled={step === 0}
          >
            {copy.back}
          </button>
          {step < 3 ? (
            <button className="primary-action" type="button" onClick={goNext}>
              {copy.next}
            </button>
          ) : (
            <button className="primary-action" type="button" onClick={submit}>
              {copy.submit}
            </button>
          )}
        </div>
      </section>
    </section>
  );
}

function readDraft(): IntakeDraft {
  if (typeof window === "undefined") return initialDraft;
  const stored = window.localStorage.getItem(draftKey);
  if (!stored) return initialDraft;
  try {
    return { ...initialDraft, ...JSON.parse(stored) } as IntakeDraft;
  } catch {
    window.localStorage.removeItem(draftKey);
    return initialDraft;
  }
}

function hasDraft(): boolean {
  return (
    typeof window !== "undefined" &&
    Boolean(window.localStorage.getItem(draftKey))
  );
}

function inferSyntheticCategory(description: string): string {
  const normalized = description.toLocaleLowerCase();
  if (/water|pipe|leak|вод|су|құбыр/.test(normalized)) return "water";
  if (/road|pothole|дорог|жол|шұңқыр/.test(normalized)) return "roads";
  if (/waste|trash|мусор|қоқыс/.test(normalized)) return "waste";
  return "utilities";
}
