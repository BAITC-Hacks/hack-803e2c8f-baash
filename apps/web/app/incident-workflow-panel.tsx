"use client";

import { useRef, useState } from "react";

type Locale = "ru" | "kk";
type AppealChoice = { request_id: string; source_request_id: string };
type Incident = {
  incident_id: string;
  region_id: string;
  state: string;
  version: number;
  member_count: number;
  candidate_member_request_ids: string[];
  confirmed_member_request_ids: string[];
};

const copy = {
  ru: {
    title: "Инцидент: решение человека",
    intro:
      "Предложите два связанных обращения, подтвердите состав и затем подтвердите инцидент. Каждое обращение сохраняет свой ID и историю.",
    second: "Второе обращение",
    create: "Предложить инцидент",
    id: "ID инцидента",
    load: "Загрузить сохранённый инцидент",
    confirmMember: "Подтвердить участие",
    confirmIncident: "Подтвердить инцидент (руководитель)",
    confirmed: "Подтверждено",
    candidate: "Кандидаты",
    state: "Состояние",
    version: "Версия",
  },
  kk: {
    title: "Оқиға: адам шешімі",
    intro:
      "Екі байланысты өтінішті ұсыныңыз, құрамын, содан кейін оқиғаны растаңыз. Әр өтініштің ID-і мен тарихы сақталады.",
    second: "Екінші өтініш",
    create: "Оқиғаны ұсыну",
    id: "Оқиға ID-і",
    load: "Сақталған оқиғаны жүктеу",
    confirmMember: "Қатысуды растау",
    confirmIncident: "Оқиғаны растау (басшы)",
    confirmed: "Расталды",
    candidate: "Үміткерлер",
    state: "Күйі",
    version: "Нұсқа",
  },
} as const;

// A server answer, whatever its status. Anything else leaves the outcome unknown,
// which is the case where a retry has to reuse its idempotency key.
class ApiError extends Error {
  readonly status: number;

  constructor(code: string, status: number) {
    super(code);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  regionId: string,
  body?: object,
  idempotencyKey?: string,
): Promise<T> {
  const response = await fetch(`/api/core${path}`, {
    method: body ? "POST" : "GET",
    headers: {
      "X-Region-Id": regionId,
      ...(body
        ? {
            "Content-Type": "application/json",
            "Idempotency-Key": idempotencyKey ?? crypto.randomUUID(),
          }
        : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(
      payload?.detail?.code ?? `HTTP ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export function IncidentWorkflowPanel({
  locale,
  regionId,
  requestId,
  choices,
  topicId,
  serviceId,
}: {
  locale: Locale;
  regionId: string;
  requestId: string;
  choices: AppealChoice[];
  topicId: string | null;
  serviceId: string | null;
}) {
  const t = copy[locale];
  const otherAppeals = choices.filter((item) => item.request_id !== requestId);
  const [secondId, setSecondId] = useState(otherAppeals[0]?.request_id ?? "");
  const [incidentId, setIncidentId] = useState("");
  const [incident, setIncident] = useState<Incident | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Incident commands are versioned writes. A retry after a lost response must
  // carry the key of the attempt that may already have committed.
  const commandKeys = useRef(new Map<string, string>());

  function commandKey(operation: string): string {
    const existing = commandKeys.current.get(operation);
    if (existing) return existing;
    const created = crypto.randomUUID();
    commandKeys.current.set(operation, created);
    return created;
  }

  async function load(id: string) {
    const result = await request<Incident>(
      `/incidents/${encodeURIComponent(id)}`,
      regionId,
    );
    setIncident(result);
    setIncidentId(result.incident_id);
  }

  async function run(action: () => Promise<void>, operation?: string) {
    setBusy(true);
    setError(null);
    try {
      await action();
      if (operation) commandKeys.current.delete(operation);
    } catch (failure) {
      if (operation && failure instanceof ApiError) {
        commandKeys.current.delete(operation);
      }
      setError(
        failure instanceof Error ? failure.message : "operation_unconfirmed",
      );
    } finally {
      setBusy(false);
    }
  }

  function create() {
    if (!secondId || !topicId) return;
    const operation = `incident-create:${requestId}:${secondId}`;
    void run(async () => {
      const result = await request<Incident>(
        "/incidents",
        regionId,
        {
          region_id: regionId,
          topic_id: topicId,
          service_id: serviceId,
          member_request_ids: [requestId, secondId],
          proposal_source: "operator",
          rationale: ["OPERATOR_REVIEW"],
        },
        commandKey(operation),
      );
      await load(result.incident_id);
    }, operation);
  }

  function confirmMember(memberId: string) {
    if (!incident) return;
    const operation = `member-confirm:${incident.incident_id}:${memberId}:${incident.version}`;
    void run(async () => {
      await request(
        `/incidents/${incident.incident_id}/members`,
        regionId,
        {
          request_id: memberId,
          incident_version: incident.version,
          decision: "confirm",
          reason_code: "OPERATOR_VERIFIED",
          evidence_refs: [],
        },
        commandKey(operation),
      );
      await load(incident.incident_id);
    }, operation);
  }

  function confirmIncident() {
    if (!incident) return;
    const operation = `incident-confirm:${incident.incident_id}:${incident.version}`;
    void run(async () => {
      await request(
        `/incidents/${incident.incident_id}/confirm`,
        regionId,
        {
          incident_version: incident.version,
          decision: "confirm",
          reason_code: "TWO_MEMBERS_VERIFIED",
        },
        commandKey(operation),
      );
      await load(incident.incident_id);
    }, operation);
  }

  return (
    <section
      className="incident-workflow"
      aria-labelledby="incident-workflow-title"
    >
      <h3 id="incident-workflow-title">{t.title}</h3>
      <p>{t.intro}</p>
      {error ? (
        <p role="alert" className="attention">
          {error}
        </p>
      ) : null}
      <div className="manual-fields">
        <label>
          {t.second}
          <select
            value={secondId}
            onChange={(event) => setSecondId(event.target.value)}
          >
            {otherAppeals.map((item) => (
              <option key={item.request_id} value={item.request_id}>
                {item.source_request_id}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="secondary-action"
          disabled={busy || !secondId || !topicId}
          onClick={create}
        >
          {t.create}
        </button>
      </div>
      <div className="manual-fields">
        <label>
          {t.id}
          <input
            value={incidentId}
            onChange={(event) => setIncidentId(event.target.value)}
          />
        </label>
        <button
          type="button"
          className="secondary-action"
          disabled={busy || !incidentId.trim()}
          onClick={() => void run(() => load(incidentId.trim()))}
        >
          {t.load}
        </button>
      </div>
      {incident ? (
        <div>
          <p>
            {t.state}: <strong>{incident.state}</strong> · {t.version}:{" "}
            {incident.version} · {t.confirmed}: {incident.member_count}
          </p>
          <h4>{t.candidate}</h4>
          <ol>
            {incident.candidate_member_request_ids.map((memberId) => {
              const confirmed =
                incident.confirmed_member_request_ids.includes(memberId);
              return (
                <li key={memberId}>
                  {choices.find((item) => item.request_id === memberId)
                    ?.source_request_id ?? memberId}
                  {confirmed ? (
                    ` · ${t.confirmed}`
                  ) : (
                    <button
                      type="button"
                      className="secondary-action"
                      disabled={busy || incident.state !== "proposed"}
                      onClick={() => confirmMember(memberId)}
                    >
                      {t.confirmMember}
                    </button>
                  )}
                </li>
              );
            })}
          </ol>
          {incident.state === "proposed" ? (
            <button
              type="button"
              className="primary-action"
              disabled={busy || incident.member_count < 2}
              onClick={confirmIncident}
            >
              {t.confirmIncident}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
