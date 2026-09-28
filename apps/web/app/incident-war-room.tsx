"use client";

/**
 * One incident as one city problem.
 *
 * Every algorithmic section renders its own state. A section that did not run
 * says so instead of showing an empty list, because "nothing found" and "nothing
 * ran" lead an operator to opposite conclusions.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ReportMap, type ReportPoint } from "./report-map";

type Locale = "ru" | "kk";

type CapabilityStatus = {
  state: "available" | "abstained" | "unavailable";
  reason_code: string | null;
};

type Member = {
  request_id: string;
  source_request_id: string;
  membership: "confirmed" | "candidate";
  status: string;
  received_at: string | null;
  received_at_quality: string;
  language: string;
  channel: string;
  point: { longitude: number; latitude: number } | null;
};

type SuggestedAction = {
  action: string;
  candidate_target: string | null;
  confidence: "high" | "medium" | "low";
  reason_codes: string[];
  evidence_refs: string[];
  summary_code: string;
};

type Workspace = {
  incident_id: string;
  region_id: string;
  state: string;
  topic_id: string;
  service_id: string | null;
  version: number;
  member_count: number;
  confirmed_count: number;
  candidate_count: number;
  first_reported_at: string | null;
  last_reported_at: string | null;
  active_minutes: number | null;
  members: Member[];
  geo: {
    status: CapabilityStatus;
    located_member_count: number;
    total_member_count: number;
    centroid: { longitude: number; latitude: number } | null;
    report_spread_m: number | null;
  };
  ownership: {
    status: CapabilityStatus;
    candidates: Record<string, unknown>[];
    ambiguous: boolean | null;
    loop_risk: boolean | null;
    reason_codes: string[];
  };
  similar_outcomes: {
    status: CapabilityStatus;
    comparable_count: number;
    median_resolution_hours: number | null;
    without_recurrence_30d: number | null;
  };
  next_actions: { status: CapabilityStatus; items: SuggestedAction[] };
  synchronization: {
    status: CapabilityStatus;
    queued: number;
    delivered: number;
    retrying: number;
    failed_permanent: number;
  };
  timeline: { occurred_at: string; event_type: string; actor_type: string }[];
  evidence: { evidence_ref: string; evidence_type: string }[];
  synthetic: boolean;
};

type IncidentDetail = {
  incident_id: string;
  region_id: string;
  state: string;
  version: number;
  confirmed_member_request_ids: string[];
};

type IncidentTopologyResponse = {
  operation: "merge" | "split";
  source: IncidentDetail;
  target: IncidentDetail;
  member_request_ids: string[];
};

const copy = {
  ru: {
    title: "Ситуационная карточка инцидента",
    intro:
      "Одна городская проблема целиком: кто сообщил, где, кто отвечает, что делали в похожих случаях и что можно сделать дальше. Все действия остаются за человеком.",
    situation: "Ситуация",
    members: "Обращения",
    map: "Где поступили сообщения",
    mapNote: "Это охват поступивших сообщений, а не зона, где пострадали люди.",
    noGeo: "Координат нет ни у одного обращения",
    ownership: "Ответственный",
    outcomes: "Подтверждённые похожие случаи",
    actions: "Что можно сделать дальше",
    timeline: "Хронология",
    evidence: "Доказательства",
    sync: "Внешняя доставка",
    confirmed: "подтверждено",
    candidates: "кандидаты",
    active: "в работе",
    minutes: "мин",
    spread: "разброс",
    advisory: "Только рекомендация. Решение принимает человек.",
    unavailableLabel: "Не выполнялось",
    abstainedLabel: "Воздержалось",
    loading: "Загрузка карточки…",
    refresh: "Обновить",
    noEvidence: "Доказательства не приложены",
    median: "медиана решения",
    hours: "ч",
    withoutRecurrence: "без повтора за 30 дней",
  },
  kk: {
    title: "Оқиғаның ситуациялық картасы",
    intro:
      "Бір қалалық мәселе толығымен: кім хабарлады, қайда, кім жауапты, ұқсас жағдайларда не істелді және әрі қарай не істеуге болады. Барлық шешімді адам қабылдайды.",
    situation: "Жағдай",
    members: "Өтініштер",
    map: "Хабарламалар қайдан түсті",
    mapNote: "Бұл түскен хабарламалардың ауқымы, зардап шеккен аймақ емес.",
    noGeo: "Бірде-бір өтініште координат жоқ",
    ownership: "Жауапты",
    outcomes: "Расталған ұқсас жағдайлар",
    actions: "Әрі қарай не істеуге болады",
    timeline: "Хронология",
    evidence: "Дәлелдер",
    sync: "Сыртқы жеткізу",
    confirmed: "расталды",
    candidates: "үміткерлер",
    active: "жұмыста",
    minutes: "мин",
    spread: "таралу",
    advisory: "Тек ұсыныс. Шешімді адам қабылдайды.",
    unavailableLabel: "Орындалмады",
    abstainedLabel: "Ұстанды",
    loading: "Карта жүктелуде…",
    refresh: "Жаңарту",
    noEvidence: "Дәлелдер тіркелмеген",
    median: "шешім медианасы",
    hours: "сағ",
    withoutRecurrence: "30 күнде қайталанбаған",
  },
} as const;

function StateBadge({
  status,
  locale,
}: {
  status: CapabilityStatus;
  locale: Locale;
}) {
  if (status.state === "available") return null;
  const t = copy[locale];
  const label =
    status.state === "unavailable" ? t.unavailableLabel : t.abstainedLabel;
  return (
    <span
      className={`capability capability-${status.state}`}
      title={status.reason_code ?? undefined}
    >
      {label}
      {status.reason_code ? ` · ${status.reason_code}` : ""}
    </span>
  );
}

function IncidentTopologyControls({
  incident,
  members,
  regionId,
  onChanged,
}: {
  incident: Pick<Workspace, "incident_id" | "state" | "version">;
  members: Member[];
  regionId: string;
  onChanged: () => Promise<void>;
}) {
  const confirmedMembers = members.filter(
    (member) => member.membership === "confirmed",
  );
  const [operation, setOperation] = useState<"merge" | "split">("split");
  const [targetId, setTargetId] = useState("");
  const [target, setTarget] = useState<IncidentDetail | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [reasonCode, setReasonCode] = useState("");
  const [evidenceRef, setEvidenceRef] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IncidentTopologyResponse | null>(null);
  const commandKeys = useRef(new Map<string, string>());

  function commandKey(key: string): string {
    const current = commandKeys.current.get(key);
    if (current) return current;
    const created = crypto.randomUUID();
    commandKeys.current.set(key, created);
    return created;
  }

  async function loadTarget() {
    if (!targetId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/core/incidents/${encodeURIComponent(targetId.trim())}`,
        {
          headers: { "X-Region-Id": regionId },
          cache: "no-store",
        },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail?.code ?? `HTTP ${response.status}`);
      }
      const detail = (await response.json()) as IncidentDetail;
      if (detail.region_id !== regionId)
        throw new Error("incident_region_mismatch");
      setTarget(detail);
    } catch (failure) {
      setTarget(null);
      setError(
        failure instanceof Error ? failure.message : "incident_unavailable",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (selected.length < 2 || !confirmed || !reasonCode || !evidenceRef)
      return;
    if (operation === "merge" && (!target || target.state !== "confirmed"))
      return;
    const operationId = `${operation}:${incident.incident_id}:${incident.version}:${target?.incident_id ?? "new"}:${selected.join(",")}`;
    setBusy(true);
    setError(null);
    try {
      const body =
        operation === "merge"
          ? {
              target_incident_id: target!.incident_id,
              source_version: incident.version,
              target_version: target!.version,
              member_request_ids: selected,
              reason_code: reasonCode,
              evidence_refs: [evidenceRef],
            }
          : {
              source_version: incident.version,
              member_request_ids: selected,
              reason_code: reasonCode,
              evidence_refs: [evidenceRef],
            };
      const response = await fetch(
        `/api/core/incidents/${encodeURIComponent(incident.incident_id)}/${operation}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Region-Id": regionId,
            "Idempotency-Key": commandKey(operationId),
          },
          body: JSON.stringify(body),
        },
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail?.code ?? `HTTP ${response.status}`);
      }
      const responseBody = (await response.json()) as IncidentTopologyResponse;
      commandKeys.current.delete(operationId);
      setResult(responseBody);
      setSelected([]);
      setConfirmed(false);
      await onChanged();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "incident_topology_unconfirmed",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="war-room-card war-room-wide topology-controls">
      <h3>Incident membership topology</h3>
      <p className="war-room-note">
        Human-confirmed only. Appeals keep their own IDs, timelines, and SLA
        clocks. This control never publishes a policy or merges automatically.
      </p>
      <div className="topology-form">
        <label>
          Operation
          <select
            value={operation}
            disabled={busy}
            onChange={(event) => {
              setOperation(event.target.value as "merge" | "split");
              setResult(null);
            }}
          >
            <option value="split">
              Split selected members into proposed incident
            </option>
            <option value="merge">
              Merge selected members into confirmed incident
            </option>
          </select>
        </label>
        {operation === "merge" ? (
          <label>
            Confirmed target incident UUID
            <input
              value={targetId}
              disabled={busy}
              onChange={(event) => {
                setTargetId(event.target.value);
                setTarget(null);
              }}
            />
            <button
              type="button"
              className="secondary-action"
              disabled={busy || !targetId.trim()}
              onClick={() => void loadTarget()}
            >
              Check target
            </button>
          </label>
        ) : null}
        <label>
          Reason code
          <input
            value={reasonCode}
            disabled={busy}
            pattern="[A-Z][A-Z0-9_]{0,63}"
            onChange={(event) =>
              setReasonCode(event.target.value.toUpperCase())
            }
            placeholder="MERGE_INCIDENT_AREAS"
          />
        </label>
        <label>
          Evidence SHA-256
          <input
            value={evidenceRef}
            disabled={busy}
            pattern="[0-9a-f]{64}"
            onChange={(event) => setEvidenceRef(event.target.value)}
            placeholder="64 lowercase hexadecimal characters"
          />
        </label>
      </div>
      {operation === "merge" && target ? (
        <p
          className={target.state === "confirmed" ? "topology-ok" : "attention"}
        >
          Target {target.incident_id} · {target.state} · v{target.version}
        </p>
      ) : null}
      <fieldset className="topology-members" disabled={busy}>
        <legend>Select at least two confirmed appeal memberships</legend>
        {confirmedMembers.length === 0 ? (
          <p className="war-room-note">No confirmed members can be moved.</p>
        ) : (
          confirmedMembers.map((member) => (
            <label key={member.request_id}>
              <input
                type="checkbox"
                checked={selected.includes(member.request_id)}
                onChange={(event) =>
                  setSelected((current) =>
                    event.target.checked
                      ? [...current, member.request_id]
                      : current.filter((id) => id !== member.request_id),
                  )
                }
              />
              {member.source_request_id} <code>{member.request_id}</code>
            </label>
          ))
        )}
      </fieldset>
      <label className="topology-confirmation">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={busy}
          onChange={(event) => setConfirmed(event.target.checked)}
        />{" "}
        I reviewed membership, target, reason and evidence. Submit this human
        decision.
      </label>
      <button
        type="button"
        className="primary-action"
        disabled={
          busy ||
          selected.length < 2 ||
          !confirmed ||
          !reasonCode ||
          !evidenceRef ||
          (operation === "merge" && target?.state !== "confirmed")
        }
        onClick={() => void submit()}
      >
        {operation === "merge" ? "Confirm merge" : "Confirm split"}
      </button>
      {error ? (
        <p role="alert" className="attention">
          {error}
        </p>
      ) : null}
      {result ? (
        <p role="status" className="topology-ok">
          {result.operation} committed · source v{result.source.version} ·
          target v{result.target.version} · {result.member_request_ids.length}{" "}
          memberships. War Room refreshed; audit timeline and outbox state
          remain server records.
        </p>
      ) : null}
    </article>
  );
}

export function IncidentWarRoom({
  locale,
  regionId,
  incidentId,
  onClose,
}: {
  locale: Locale;
  regionId: string;
  incidentId: string;
  onClose?: () => void;
}) {
  const t = copy[locale];
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/core/incidents/${encodeURIComponent(incidentId)}/workspace`,
        { headers: { "X-Region-Id": regionId }, cache: "no-store" },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail?.code ?? `HTTP ${response.status}`);
      }
      setWorkspace((await response.json()) as Workspace);
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "workspace_unavailable",
      );
    }
  }, [incidentId, regionId]);

  useEffect(() => {
    // Deferred so the first paint is not a cascading render, matching how the
    // operator queue loads its own data.
    void Promise.resolve().then(load);
  }, [load]);

  if (error) {
    return (
      <section className="war-room">
        <p role="alert" className="attention">
          {error}
        </p>
      </section>
    );
  }
  if (!workspace) {
    return (
      <section className="war-room">
        <p role="status">{t.loading}</p>
      </section>
    );
  }

  const points: ReportPoint[] = workspace.members
    .filter((member) => member.point !== null)
    .map((member) => ({
      longitude: member.point!.longitude,
      latitude: member.point!.latitude,
      label: member.source_request_id,
      kind: member.membership,
    }));

  return (
    <section className="war-room" aria-labelledby="war-room-title">
      <div className="war-room-head">
        <div>
          <p className="eyebrow">
            {workspace.region_id} · {workspace.state} · v{workspace.version}
            {workspace.synthetic ? " · SYNTHETIC" : ""}
          </p>
          <h2 id="war-room-title">{t.title}</h2>
          <p>{t.intro}</p>
        </div>
        <div className="war-room-head-actions">
          <button
            type="button"
            className="secondary-action"
            onClick={() => void load()}
          >
            {t.refresh}
          </button>
          {onClose ? (
            <button
              type="button"
              className="secondary-action"
              onClick={onClose}
            >
              ✕
            </button>
          ) : null}
        </div>
      </div>

      <div className="war-room-grid">
        <article className="war-room-card">
          <h3>{t.situation}</h3>
          <dl className="war-room-stats">
            <div>
              <dt>{t.members}</dt>
              {/* Total on the card, because member_count counts confirmed
                  members only and reading "0" beside six candidates looks
                  like the incident is empty. */}
              <dd>{workspace.members.length}</dd>
            </div>
            <div>
              <dt>{t.confirmed}</dt>
              <dd>{workspace.confirmed_count}</dd>
            </div>
            <div>
              <dt>{t.candidates}</dt>
              <dd>{workspace.candidate_count}</dd>
            </div>
            <div>
              <dt>{t.active}</dt>
              <dd>
                {workspace.active_minutes === null
                  ? "—"
                  : `${workspace.active_minutes} ${t.minutes}`}
              </dd>
            </div>
          </dl>
          <p className="war-room-topic">
            {workspace.topic_id}
            {workspace.service_id ? ` → ${workspace.service_id}` : ""}
          </p>
        </article>

        <article className="war-room-card">
          <h3>
            {t.map} <StateBadge status={workspace.geo.status} locale={locale} />
          </h3>
          <ReportMap
            points={points}
            centroid={workspace.geo.centroid}
            spreadMetres={workspace.geo.report_spread_m}
            emptyLabel={t.noGeo}
          />
          {workspace.geo.report_spread_m !== null ? (
            <p className="war-room-note">
              {t.spread}: {Math.round(workspace.geo.report_spread_m)} m ·{" "}
              {workspace.geo.located_member_count}/
              {workspace.geo.total_member_count}
            </p>
          ) : null}
          <p className="war-room-note">{t.mapNote}</p>
        </article>

        <article className="war-room-card">
          <h3>
            {t.ownership}{" "}
            <StateBadge status={workspace.ownership.status} locale={locale} />
          </h3>
          {workspace.ownership.candidates.length > 0 ? (
            <ul className="war-room-list">
              {workspace.ownership.candidates
                .slice(0, 3)
                .map((candidate, index) => (
                  <li key={index}>
                    <strong>
                      {String(candidate.organization_id ?? candidate.id ?? "—")}
                    </strong>
                    <span className="codes">
                      {(candidate.reason_codes as string[] | undefined)
                        ?.slice(0, 4)
                        .join(" · ")}
                    </span>
                  </li>
                ))}
            </ul>
          ) : null}
          {workspace.ownership.loop_risk ? (
            <p className="attention">HANDOFF_LOOP_RISK</p>
          ) : null}
        </article>

        <article className="war-room-card">
          <h3>
            {t.outcomes}{" "}
            <StateBadge
              status={workspace.similar_outcomes.status}
              locale={locale}
            />
          </h3>
          {workspace.similar_outcomes.status.state === "available" ? (
            <dl className="war-room-stats">
              <div>
                <dt>{t.outcomes}</dt>
                <dd>{workspace.similar_outcomes.comparable_count}</dd>
              </div>
              <div>
                <dt>{t.median}</dt>
                <dd>
                  {workspace.similar_outcomes.median_resolution_hours ?? "—"}{" "}
                  {t.hours}
                </dd>
              </div>
              <div>
                <dt>{t.withoutRecurrence}</dt>
                <dd>
                  {workspace.similar_outcomes.without_recurrence_30d ?? "—"}
                </dd>
              </div>
            </dl>
          ) : null}
        </article>

        <article className="war-room-card war-room-wide">
          <h3>
            {t.actions}{" "}
            <StateBadge
              status={workspace.next_actions.status}
              locale={locale}
            />
          </h3>
          {workspace.next_actions.items.length > 0 ? (
            <ol className="war-room-actions">
              {workspace.next_actions.items.map((action) => (
                <li key={action.summary_code}>
                  <div className="action-head">
                    <strong>{action.summary_code}</strong>
                    <span
                      className={`confidence confidence-${action.confidence}`}
                    >
                      {action.confidence}
                    </span>
                  </div>
                  {action.candidate_target ? (
                    <p className="action-target">{action.candidate_target}</p>
                  ) : null}
                  <ul className="codes-list">
                    {action.reason_codes.map((code) => (
                      <li key={code}>{code}</li>
                    ))}
                  </ul>
                  {action.evidence_refs.length > 0 ? (
                    <p className="codes">{action.evidence_refs.join(" · ")}</p>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : null}
          <p className="war-room-note">{t.advisory}</p>
        </article>

        <IncidentTopologyControls
          incident={workspace}
          members={workspace.members}
          regionId={regionId}
          onChanged={load}
        />

        <article className="war-room-card">
          <h3>{t.sync}</h3>
          <dl className="war-room-stats">
            <div>
              <dt>queued</dt>
              <dd>{workspace.synchronization.queued}</dd>
            </div>
            <div>
              <dt>delivered</dt>
              <dd>{workspace.synchronization.delivered}</dd>
            </div>
            <div>
              <dt>retrying</dt>
              <dd>{workspace.synchronization.retrying}</dd>
            </div>
            <div>
              <dt>failed</dt>
              <dd>{workspace.synchronization.failed_permanent}</dd>
            </div>
          </dl>
        </article>

        <article className="war-room-card">
          <h3>{t.evidence}</h3>
          {workspace.evidence.length === 0 ? (
            <p className="war-room-note">{t.noEvidence}</p>
          ) : (
            <ul className="war-room-list">
              {workspace.evidence.map((item) => (
                <li key={item.evidence_ref}>
                  <strong>{item.evidence_type}</strong>
                  <span className="codes">
                    {item.evidence_ref.slice(0, 22)}…
                  </span>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="war-room-card war-room-wide">
          <h3>{t.timeline}</h3>
          <ol className="war-room-timeline">
            {workspace.timeline.map((entry, index) => (
              <li key={`${entry.event_type}-${index}`}>
                <span className="time">{entry.occurred_at.slice(11, 16)}</span>
                <span className="event">{entry.event_type}</span>
                <span className="codes">{entry.actor_type}</span>
              </li>
            ))}
          </ol>
        </article>
      </div>
    </section>
  );
}
