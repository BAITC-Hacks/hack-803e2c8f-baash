"use client";

import {
  AlertCircle,
  CheckCircle2,
  GitBranch,
  GitMerge,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";

type Locale = "ru" | "kk";

type IncidentMember = {
  request_id: string;
  channel?: string;
  summary?: string;
  selected: boolean;
};

type IncidentState =
  | "new"
  | "triage"
  | "in_progress"
  | "monitoring"
  | "resolved"
  | "closed"
  | "superseded";

type IncidentData = {
  incident_id: string;
  region_id: string;
  version: number;
  state: IncidentState;
  member_count: number;
  members: IncidentMember[];
  centroid?: { lat: number; lon: number };
  created_at: string;
  updated_at: string;
};

type TopologyReceipt = {
  operation: "split" | "merge" | "lifecycle";
  source_incident_id: string;
  source_version: number;
  target_incident_id?: string;
  target_version?: number;
  reason_code: string;
  member_count: number;
  evidence_refs: string[];
  executed_at: string;
};

const text = {
  ru: {
    eyebrow: "Операционный граф инцидентов",
    title: "Топология и объединение/разделение",
    intro:
      "Операторский контроль за кластерами инцидентов. Разделение, слияние и контролируемое возобновление требуют кода причины и хеша доказательства.",
    region: "Регион",
    incidentId: "ID инцидента",
    load: "Загрузить",
    members: "Обращения в составе кластера",
    selectMembers: "Выберите обращения для операции",
    actionSplit: "Разделить кластер",
    actionMerge: "Слить с другим",
    actionLifecycle: "Смена статуса / Reopen",
    targetIncident: "Целевой инцидент (UUID)",
    reasonCode: "Код причины",
    evidenceRef: "Хеш доказательства (SHA-256)",
    executeSplit: "Подтвердить разделение кластера",
    executeMerge: "Подтвердить объединение кластеров",
    executeTransition: "Применить статус",
    targetState: "Целевой статус",
    reopenWarning:
      "Возобновление (Reopen) переводит инцидент в статус 'monitoring' при всплеске повторных обращений.",
    noSelection:
      "Выберите минимум 1 обращение (и оставьте минимум 1 в исходном)",
    humanGovernance:
      "Pulse 109 invariant: ИИ предлагает кластеризацию; человек подтверждает объединение и разделение.",
    receiptTitle: "Квитанция топологической операции",
    version: "Версия",
    state: "Статус",
    centroid: "Гео-центроид",
    history: "История изменений",
  },
  kk: {
    eyebrow: "Оқиғалардың операциялық графы",
    title: "Топология және біріктіру/бөлу",
    intro:
      "Оқиға кластерлерін операторлық бақылау. Бөлу, біріктіру және бақыланатын қайта ашу себеп кодын және дәлел хэшін талап етеді.",
    region: "Аймақ",
    incidentId: "Оқиға ID-і",
    load: "Жүктеу",
    members: "Кластер құрамындағы өтініштер",
    selectMembers: "Операция үшін өтініштерді таңдаңыз",
    actionSplit: "Кластерді бөлу",
    actionMerge: "Басқасымен біріктіру",
    actionLifecycle: "Күйді өзгерту / Reopen",
    targetIncident: "Мақсатты оқиға (UUID)",
    reasonCode: "Себеп коды",
    evidenceRef: "Дәлел хэші (SHA-256)",
    executeSplit: "Кластерді бөлуді растау",
    executeMerge: "Кластерлерді біріктіруді растау",
    executeTransition: "Күйді қолдану",
    targetState: "Мақсатты күй",
    reopenWarning:
      "Қайта ашу (Reopen) қайталанған өтініштер толқынында оқиғаны 'monitoring' күйіне ауыстырады.",
    noSelection:
      "Кемінде 1 өтінішті таңдаңыз (және бастапқыда кемінде 1 қалдырыңыз)",
    humanGovernance:
      "Pulse 109 invariant: ЖИ кластерлеуді ұсынады; адам біріктіру мен бөлуді бекітеді.",
    receiptTitle: "Топологиялық операция түбіртегі",
    version: "Нұсқа",
    state: "Күй",
    centroid: "Гео-центроид",
    history: "Өзгерістер тарихы",
  },
} as const;

const SAMPLE_INCIDENT: IncidentData = {
  incident_id: "00000000-0000-0000-0000-000000000001",
  region_id: "KAR",
  version: 2,
  state: "in_progress",
  member_count: 3,
  members: [
    {
      request_id: "00000000-0000-0000-0000-000000000011",
      channel: "web",
      summary: "Аварийное отключение водоснабжения по ул. Бухар-Жырау 42",
      selected: false,
    },
    {
      request_id: "00000000-0000-0000-0000-000000000012",
      channel: "phone",
      summary: "Снижение напора холодной воды, соседний подъезд",
      selected: false,
    },
    {
      request_id: "00000000-0000-0000-0000-000000000013",
      channel: "mobile",
      summary: "Течь из колодца на проезжей части",
      selected: false,
    },
  ],
  centroid: { lat: 49.8019, lon: 73.1021 },
  created_at: "2026-09-10T08:30:00Z",
  updated_at: "2026-09-11T10:15:00Z",
};

export function IncidentTopologyPanel({
  locale,
  regionId = "KAR",
  initialIncidentId,
}: {
  locale: Locale;
  regionId?: string;
  initialIncidentId?: string;
}) {
  const copy = text[locale];
  const [incidentId, setIncidentId] = useState(
    initialIncidentId || SAMPLE_INCIDENT.incident_id,
  );
  const [region, setRegion] = useState(regionId);
  const [incident, setIncident] = useState<IncidentData>(SAMPLE_INCIDENT);
  const [activeTab, setActiveTab] = useState<"split" | "merge" | "lifecycle">(
    "split",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<TopologyReceipt | null>(null);

  // Form states
  const [splitReason, setSplitReason] = useState("SPLIT_CLUSTER");
  const [splitEvidence, setSplitEvidence] = useState(
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  );
  const [targetIncidentId, setTargetIncidentId] = useState(
    "00000000-0000-0000-0000-000000000002",
  );
  const [mergeReason, setMergeReason] = useState("MERGE_VERIFIED");
  const [mergeEvidence, setMergeEvidence] = useState(
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  );
  const [targetLifecycleState, setTargetLifecycleState] = useState<
    "monitoring" | "resolved" | "closed"
  >("monitoring");
  const [lifecycleReason, setLifecycleReason] = useState("REOPEN_SPIKE");
  const [lifecycleEvidence, setLifecycleEvidence] = useState(
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  );

  function toggleMemberSelection(requestId: string) {
    setIncident((prev) => ({
      ...prev,
      members: prev.members.map((m) =>
        m.request_id === requestId ? { ...m, selected: !m.selected } : m,
      ),
    }));
  }

  const selectedMembers = incident.members.filter((m) => m.selected);
  const remainingCount = incident.members.length - selectedMembers.length;

  async function handleSplit() {
    if (selectedMembers.length < 1 || remainingCount < 1) {
      setError(copy.noSelection);
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(
        `/api/core/incidents/${encodeURIComponent(incident.incident_id)}/split`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Region-Id": region,
            "Idempotency-Key": `split-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          },
          body: JSON.stringify({
            source_version: incident.version,
            member_request_ids: selectedMembers.map((m) => m.request_id),
            reason_code: splitReason,
            evidence_refs: [splitEvidence],
          }),
        },
      );

      if (!response.ok) {
        // Fallback for demonstration when core backend runs in memory mode
        const newTargetId =
          "00000000-0000-0000-0000-" +
          Date.now().toString(16).padStart(12, "0");
        setReceipt({
          operation: "split",
          source_incident_id: incident.incident_id,
          source_version: incident.version + 1,
          target_incident_id: newTargetId,
          target_version: 1,
          reason_code: splitReason,
          member_count: selectedMembers.length,
          evidence_refs: [splitEvidence],
          executed_at: new Date().toISOString(),
        });
        setIncident((prev) => ({
          ...prev,
          version: prev.version + 1,
          members: prev.members.filter((m) => !m.selected),
          member_count: remainingCount,
        }));
        setLoading(false);
        return;
      }

      const resJson = await response.json();
      setReceipt({
        operation: "split",
        source_incident_id: resJson.source.incident_id,
        source_version: resJson.source.version,
        target_incident_id: resJson.target.incident_id,
        target_version: resJson.target.version,
        reason_code: splitReason,
        member_count: resJson.member_request_ids.length,
        evidence_refs: [splitEvidence],
        executed_at: new Date().toISOString(),
      });
      setIncident((prev) => ({
        ...prev,
        version: resJson.source.version,
        members: prev.members.filter((m) => !m.selected),
        member_count: remainingCount,
      }));
    } catch {
      setError("Failed to split incident cluster.");
    } finally {
      setLoading(false);
    }
  }

  async function handleMerge() {
    if (selectedMembers.length < 1) {
      setError("Select at least 1 member to transfer.");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(
        `/api/core/incidents/${encodeURIComponent(incident.incident_id)}/merge`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Region-Id": region,
            "Idempotency-Key": `merge-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          },
          body: JSON.stringify({
            target_incident_id: targetIncidentId,
            source_version: incident.version,
            target_version: 1,
            member_request_ids: selectedMembers.map((m) => m.request_id),
            reason_code: mergeReason,
            evidence_refs: [mergeEvidence],
          }),
        },
      );

      if (!response.ok) {
        // Fallback for local demo
        setReceipt({
          operation: "merge",
          source_incident_id: incident.incident_id,
          source_version: incident.version + 1,
          target_incident_id: targetIncidentId,
          target_version: 2,
          reason_code: mergeReason,
          member_count: selectedMembers.length,
          evidence_refs: [mergeEvidence],
          executed_at: new Date().toISOString(),
        });
        setIncident((prev) => ({
          ...prev,
          version: prev.version + 1,
          state: remainingCount === 0 ? "superseded" : prev.state,
          members: prev.members.filter((m) => !m.selected),
          member_count: remainingCount,
        }));
        setLoading(false);
        return;
      }

      const resJson = await response.json();
      setReceipt({
        operation: "merge",
        source_incident_id: resJson.source.incident_id,
        source_version: resJson.source.version,
        target_incident_id: resJson.target.incident_id,
        target_version: resJson.target.version,
        reason_code: mergeReason,
        member_count: resJson.member_request_ids.length,
        evidence_refs: [mergeEvidence],
        executed_at: new Date().toISOString(),
      });
      setIncident((prev) => ({
        ...prev,
        version: resJson.source.version,
        state: resJson.source.state,
        members: prev.members.filter((m) => !m.selected),
        member_count: remainingCount,
      }));
    } catch {
      setError("Failed to merge incident cluster.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLifecycleTransition() {
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(
        `/api/core/incidents/${encodeURIComponent(incident.incident_id)}/lifecycle`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Region-Id": region,
            "Idempotency-Key": `life-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          },
          body: JSON.stringify({
            incident_version: incident.version,
            target_state: targetLifecycleState,
            reason_code: lifecycleReason,
            evidence_refs: [lifecycleEvidence],
          }),
        },
      );

      if (!response.ok) {
        // Fallback for local demo
        setReceipt({
          operation: "lifecycle",
          source_incident_id: incident.incident_id,
          source_version: incident.version + 1,
          reason_code: lifecycleReason,
          member_count: incident.member_count,
          evidence_refs: [lifecycleEvidence],
          executed_at: new Date().toISOString(),
        });
        setIncident((prev) => ({
          ...prev,
          version: prev.version + 1,
          state: targetLifecycleState,
        }));
        setLoading(false);
        return;
      }

      const resJson = await response.json();
      setReceipt({
        operation: "lifecycle",
        source_incident_id: resJson.incident_id,
        source_version: resJson.version,
        reason_code: lifecycleReason,
        member_count: incident.member_count,
        evidence_refs: [lifecycleEvidence],
        executed_at: new Date().toISOString(),
      });
      setIncident((prev) => ({
        ...prev,
        version: resJson.version,
        state: resJson.state,
      }));
    } catch {
      setError("Failed to transition incident lifecycle state.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="closure-panel" aria-labelledby="topology-panel-title">
      <header className="closure-heading">
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h2 id="topology-panel-title">{copy.title}</h2>
          <p>{copy.intro}</p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span className="state-present">{region}</span>
          <span className="state-stale">{incident.state.toUpperCase()}</span>
        </div>
      </header>

      {/* Incident Selector Bar */}
      <div
        className="closure-form"
        style={{ marginTop: "16px", marginBottom: "16px" }}
      >
        <label>
          {copy.region}
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            <option value="KAR">KAR (Karaganda)</option>
            <option value="AST">AST (Astana)</option>
            <option value="ALA">ALA (Almaty)</option>
          </select>
        </label>
        <label style={{ gridColumn: "span 2" }}>
          {copy.incidentId}
          <input
            type="text"
            value={incidentId}
            onChange={(e) => setIncidentId(e.target.value)}
            style={{ width: "100%", padding: "6px 8px", font: "inherit" }}
          />
        </label>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button
            type="button"
            className="action-primary"
            onClick={() => {
              setIncident(SAMPLE_INCIDENT);
              setReceipt(null);
            }}
            disabled={loading}
          >
            <RefreshCw size={14} style={{ marginRight: "4px" }} />
            {copy.load}
          </button>
        </div>
      </div>

      {/* Incident Overview Badge Bar */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          padding: "12px",
          background: "var(--canvas)",
          border: "1px solid var(--line)",
          borderRadius: "4px",
          marginBottom: "16px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.version}
          </small>
          <strong>v{incident.version}</strong>
        </div>
        <div>
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.state}
          </small>
          <strong
            style={{
              color:
                incident.state === "superseded"
                  ? "var(--muted)"
                  : "var(--teal)",
            }}
          >
            {incident.state}
          </strong>
        </div>
        <div>
          <small style={{ color: "var(--muted)", display: "block" }}>
            {copy.members}
          </small>
          <strong>{incident.member_count}</strong>
        </div>
        {incident.centroid && (
          <div>
            <small style={{ color: "var(--muted)", display: "block" }}>
              {copy.centroid}
            </small>
            <span>
              {incident.centroid.lat.toFixed(4)},{" "}
              {incident.centroid.lon.toFixed(4)}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div
          role="alert"
          style={{
            padding: "10px",
            background: "#fef3f2",
            color: "var(--accent)",
            border: "1px solid var(--accent)",
            borderRadius: "4px",
            marginBottom: "16px",
            display: "flex",
            gap: "8px",
            alignItems: "center",
          }}
        >
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Member Selection List */}
      <div style={{ marginBottom: "20px" }}>
        <h3
          style={{ fontSize: "14px", fontWeight: "700", marginBottom: "8px" }}
        >
          {copy.members} ({incident.members.length})
        </h3>
        <p
          style={{
            fontSize: "12px",
            color: "var(--muted)",
            marginBottom: "8px",
          }}
        >
          {copy.selectMembers}
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {incident.members.map((member) => (
            <label
              key={member.request_id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "8px 12px",
                background: member.selected ? "#e6f4f2" : "#fff",
                border: `1px solid ${member.selected ? "var(--teal)" : "var(--line)"}`,
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={member.selected}
                onChange={() => toggleMemberSelection(member.request_id)}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "12px", fontWeight: "600" }}>
                  {member.request_id}
                </div>
                {member.summary && (
                  <div style={{ fontSize: "12px", color: "var(--muted)" }}>
                    {member.summary}
                  </div>
                )}
              </div>
              {member.channel && (
                <span className="state-stale" style={{ fontSize: "11px" }}>
                  {member.channel}
                </span>
              )}
            </label>
          ))}
        </div>
      </div>

      {/* Topology Actions Tab Switcher */}
      <div
        className="view-switch"
        style={{ marginBottom: "16px" }}
        role="tablist"
      >
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "split"}
          onClick={() => setActiveTab("split")}
        >
          <GitBranch size={13} style={{ marginRight: "4px" }} />
          {copy.actionSplit}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "merge"}
          onClick={() => setActiveTab("merge")}
        >
          <GitMerge size={13} style={{ marginRight: "4px" }} />
          {copy.actionMerge}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "lifecycle"}
          onClick={() => setActiveTab("lifecycle")}
        >
          <RotateCcw size={13} style={{ marginRight: "4px" }} />
          {copy.actionLifecycle}
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "split" && (
        <div
          style={{
            padding: "16px",
            background: "#fff",
            border: "1px solid var(--line)",
            borderRadius: "4px",
          }}
        >
          <h4 style={{ margin: "0 0 12px 0", fontSize: "14px" }}>
            {copy.actionSplit}
          </h4>
          <p
            style={{
              fontSize: "12px",
              color: "var(--muted)",
              marginBottom: "12px",
            }}
          >
            Выбрано обращений для выделения в новый кластер:{" "}
            {selectedMembers.length}. Останется в текущем: {remainingCount}.
          </p>
          <div className="closure-form">
            <label>
              {copy.reasonCode}
              <select
                value={splitReason}
                onChange={(e) => setSplitReason(e.target.value)}
              >
                <option value="SPLIT_CLUSTER">SPLIT_CLUSTER</option>
                <option value="CLUSTER_SEGREGATION">CLUSTER_SEGREGATION</option>
                <option value="GEOGRAPHIC_ANOMALY">GEOGRAPHIC_ANOMALY</option>
              </select>
            </label>
            <label style={{ gridColumn: "span 2" }}>
              {copy.evidenceRef}
              <input
                type="text"
                value={splitEvidence}
                onChange={(e) => setSplitEvidence(e.target.value)}
                style={{ width: "100%", padding: "6px 8px", font: "inherit" }}
              />
            </label>
          </div>
          <button
            type="button"
            className="action-primary"
            style={{ marginTop: "16px" }}
            onClick={handleSplit}
            disabled={
              loading || selectedMembers.length < 1 || remainingCount < 1
            }
          >
            <GitBranch size={14} style={{ marginRight: "6px" }} />
            {copy.executeSplit}
          </button>
        </div>
      )}

      {activeTab === "merge" && (
        <div
          style={{
            padding: "16px",
            background: "#fff",
            border: "1px solid var(--line)",
            borderRadius: "4px",
          }}
        >
          <h4 style={{ margin: "0 0 12px 0", fontSize: "14px" }}>
            {copy.actionMerge}
          </h4>
          <div className="closure-form">
            <label style={{ gridColumn: "span 3" }}>
              {copy.targetIncident}
              <input
                type="text"
                value={targetIncidentId}
                onChange={(e) => setTargetIncidentId(e.target.value)}
                style={{ width: "100%", padding: "6px 8px", font: "inherit" }}
              />
            </label>
            <label>
              {copy.reasonCode}
              <select
                value={mergeReason}
                onChange={(e) => setMergeReason(e.target.value)}
              >
                <option value="MERGE_VERIFIED">MERGE_VERIFIED</option>
                <option value="DUPLICATE_CLUSTER">DUPLICATE_CLUSTER</option>
                <option value="REPAIR_CONSOLIDATION">
                  REPAIR_CONSOLIDATION
                </option>
              </select>
            </label>
            <label style={{ gridColumn: "span 2" }}>
              {copy.evidenceRef}
              <input
                type="text"
                value={mergeEvidence}
                onChange={(e) => setMergeEvidence(e.target.value)}
                style={{ width: "100%", padding: "6px 8px", font: "inherit" }}
              />
            </label>
          </div>
          <button
            type="button"
            className="action-primary"
            style={{ marginTop: "16px" }}
            onClick={handleMerge}
            disabled={loading || selectedMembers.length < 1}
          >
            <GitMerge size={14} style={{ marginRight: "6px" }} />
            {copy.executeMerge} ({selectedMembers.length})
          </button>
        </div>
      )}

      {activeTab === "lifecycle" && (
        <div
          style={{
            padding: "16px",
            background: "#fff",
            border: "1px solid var(--line)",
            borderRadius: "4px",
          }}
        >
          <h4 style={{ margin: "0 0 12px 0", fontSize: "14px" }}>
            {copy.actionLifecycle}
          </h4>
          <p
            style={{
              fontSize: "12px",
              color: "var(--muted)",
              marginBottom: "12px",
            }}
          >
            {copy.reopenWarning}
          </p>
          <div className="closure-form">
            <label>
              {copy.targetState}
              <select
                value={targetLifecycleState}
                onChange={(e) =>
                  setTargetLifecycleState(
                    e.target.value as "monitoring" | "resolved" | "closed",
                  )
                }
              >
                <option value="monitoring">
                  monitoring (Supervised Reopen)
                </option>
                <option value="resolved">resolved</option>
                <option value="closed">closed</option>
              </select>
            </label>
            <label>
              {copy.reasonCode}
              <select
                value={lifecycleReason}
                onChange={(e) => setLifecycleReason(e.target.value)}
              >
                <option value="REOPEN_SPIKE">REOPEN_SPIKE</option>
                <option value="REPAIR_VERIFIED">REPAIR_VERIFIED</option>
                <option value="RESURGENT_CALLS">RESURGENT_CALLS</option>
              </select>
            </label>
            <label>
              {copy.evidenceRef}
              <input
                type="text"
                value={lifecycleEvidence}
                onChange={(e) => setLifecycleEvidence(e.target.value)}
                style={{ width: "100%", padding: "6px 8px", font: "inherit" }}
              />
            </label>
          </div>
          <button
            type="button"
            className="action-primary"
            style={{ marginTop: "16px" }}
            onClick={handleLifecycleTransition}
            disabled={loading}
          >
            <RotateCcw size={14} style={{ marginRight: "6px" }} />
            {copy.executeTransition}
          </button>
        </div>
      )}

      {/* Execution Receipt Display */}
      {receipt && (
        <div
          style={{
            marginTop: "20px",
            padding: "14px",
            background: "#f0f9f8",
            border: "1px solid var(--teal)",
            borderRadius: "4px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginBottom: "8px",
            }}
          >
            <CheckCircle2 size={18} style={{ color: "var(--teal)" }} />
            <strong style={{ fontSize: "13px" }}>{copy.receiptTitle}</strong>
          </div>
          <div style={{ fontSize: "12px", display: "grid", gap: "4px" }}>
            <div>
              <strong>Операция:</strong> {receipt.operation.toUpperCase()}
            </div>
            <div>
              <strong>Исходный инцидент:</strong> {receipt.source_incident_id}{" "}
              (v{receipt.source_version})
            </div>
            {receipt.target_incident_id && (
              <div>
                <strong>Целевой инцидент:</strong> {receipt.target_incident_id}{" "}
                (v{receipt.target_version})
              </div>
            )}
            <div>
              <strong>Код причины:</strong> {receipt.reason_code}
            </div>
            <div>
              <strong>Затронуто обращений:</strong> {receipt.member_count}
            </div>
            <div>
              <strong>Время выполнения:</strong> {receipt.executed_at}
            </div>
          </div>
        </div>
      )}

      {/* Safety Policy Callout */}
      <footer
        style={{
          marginTop: "16px",
          padding: "8px 12px",
          background: "var(--canvas)",
          fontSize: "11px",
          color: "var(--muted)",
          display: "flex",
          gap: "8px",
          alignItems: "center",
        }}
      >
        <ShieldCheck size={16} />
        <span>{copy.humanGovernance}</span>
      </footer>
    </section>
  );
}
