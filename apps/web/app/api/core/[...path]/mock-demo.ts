/*
 * Self-contained presenter runtime. Every record and every side effect here is
 * synthetic and process-local. It is selected only by the explicit launcher
 * and only for browser pages under /demo.
 */
type Appeal = {
  request_id: string;
  source_request_id: string;
  region_id: string;
  status: string;
  received_at: string | null;
  received_at_quality: string;
  language: string;
  channel: string;
  text: string;
  topic_id: string;
  service_id: string;
  synthetic: true;
  version: number;
  current_decision?: { topic_id: string; service_id: string; priority: string };
  point?: { latitude: number; longitude: number };
};
type Incident = {
  incident_id: string;
  region_id: string;
  state: string;
  topic_id: string;
  service_id: string;
  member_request_ids: string[];
  confirmed: boolean;
  created_at: string;
};
type Cluster = {
  cluster_id: string;
  region_id: string;
  topic_id: string;
  service_id: string;
  member_request_ids: string[];
  status: string;
  confidence: number;
  rationale: string;
};
type State = {
  appeals: Appeal[];
  incidents: Incident[];
  clusters: Cluster[];
  exports: Map<string, unknown>;
};
type Input = Record<string, unknown>;
const root = globalThis as typeof globalThis & { __pulseMockDemo?: State };
const uid = () => crypto.randomUUID();
const now = () => new Date().toISOString();
const fixedIds = [
  "01909109-0000-7000-8000-000000000001",
  "01909109-0000-7000-8000-000000000002",
  "01909109-0000-7000-8000-000000000003",
  "01909109-0000-7000-8000-000000000004",
  "01909109-0000-7000-8000-000000000005",
  "01909109-0000-7000-8000-000000000006",
];
function state(): State {
  if (!root.__pulseMockDemo) {
    const water = [
      "После ремонта вода стала мутной и пахнет металлом.",
      "Вода из крана коричневая, неприятный запах.",
      "После работ на улице вода с осадком.",
      "В нескольких домах мутная вода после ремонта труб.",
      "Появился металлический запах у водопроводной воды.",
      "Соседи тоже жалуются на мутную воду после ремонта.",
    ];
    const appeals = water.map(
      (text, i): Appeal => ({
        request_id: fixedIds[i],
        source_request_id: `demo-emerging-water-0${i + 1}`,
        region_id: "ALA",
        status: "received",
        received_at: new Date(Date.now() - (i + 1) * 8 * 60_000).toISOString(),
        received_at_quality: "exact",
        language: "ru",
        channel: "web",
        text,
        topic_id: "topic:water_quality",
        service_id: "service:water",
        synthetic: true,
        version: 1,
        point: {
          latitude: 43.2414 + i * 0.002,
          longitude: 76.8951 + i * 0.001,
        },
      }),
    );
    for (let i = 1; i <= 120; i++)
      appeals.push({
        request_id: `01909109-1000-7000-8000-${String(i).padStart(12, "0")}`,
        source_request_id: `DEMO-HISTORY-${new Date(Date.now() - i * 86400000).toISOString().slice(0, 10).replaceAll("-", "")}`,
        region_id: "ALA",
        status: i % 7 === 0 ? "closed" : "received",
        received_at: new Date(Date.now() - i * 86400000).toISOString(),
        received_at_quality: "exact",
        language: "ru",
        channel: ["web", "phone", "mobile"][i % 3],
        text: `Условное синтетическое обращение ${i}: требуется проверить городской сервис.`,
        topic_id: [
          "topic:water_quality",
          "topic:road",
          "topic:lighting",
          "topic:waste",
        ][i % 4],
        service_id: [
          "service:water",
          "service:roads",
          "service:lighting",
          "service:waste",
        ][i % 4],
        synthetic: true,
        version: 1,
      });
    root.__pulseMockDemo = {
      appeals,
      incidents: [],
      clusters: [],
      exports: new Map(),
    };
  }
  return root.__pulseMockDemo;
}
function json(data: unknown, status = 200) {
  return Response.json(data, {
    status,
    headers: { "X-Pulse109-Mode": "mock", "Cache-Control": "no-store" },
  });
}
async function body(req: Request): Promise<Input> {
  try {
    return (await req.json()) as Input;
  } catch {
    return {};
  }
}
function publicAppeal(a: Appeal) {
  return Object.fromEntries(
    Object.entries(a).filter(([key]) => key !== "text"),
  ) as Omit<Appeal, "text">;
}
function attachment(a: Appeal) {
  return {
    request_id: a.request_id,
    created_at: a.received_at ?? now(),
    region_id: a.region_id,
    status: a.status,
    source_request_id: a.source_request_id,
    received_at: a.received_at,
    received_at_quality: a.received_at_quality,
    language: a.language,
    channel: a.channel,
    text: a.text,
    version: a.version,
    synthetic: true,
    current_decision: a.current_decision ?? null,
    attachments: [],
    audit: [],
    timeline: [],
  };
}
function makeCluster(s: State): Cluster | null {
  const members = s.appeals.filter((a) =>
    a.source_request_id.startsWith("demo-emerging-water-"),
  );
  return members.length >= 3
    ? {
        cluster_id: "01909109-2000-7000-8000-000000000001",
        region_id: "ALA",
        topic_id: "topic:water_quality",
        service_id: "service:water",
        member_request_ids: members.map((m) => m.request_id),
        status: "candidate",
        confidence: 0.91,
        rationale:
          "Синтетические обращения о мутной воде после ремонта; оператор проверяет сигнал.",
      }
    : null;
}
function workspace(s: State, inc: Incident) {
  const members = inc.member_request_ids
    .map((id) => s.appeals.find((a) => a.request_id === id))
    .filter((a): a is Appeal => !!a);
  const receivedTimes = members
    .map((member) => member.received_at)
    .filter((value): value is string => value !== null)
    .sort();
  return {
    incident_id: inc.incident_id,
    region_id: inc.region_id,
    state: inc.state,
    topic_id: inc.topic_id,
    service_id: inc.service_id,
    version: 1,
    member_count: members.length,
    confirmed_count: inc.confirmed ? members.length : 0,
    candidate_count: inc.confirmed ? 0 : members.length,
    created_at: inc.created_at,
    updated_at: inc.created_at,
    first_reported_at: receivedTimes[0] ?? null,
    last_reported_at: receivedTimes[receivedTimes.length - 1] ?? null,
    active_minutes: inc.confirmed ? 1 : null,
    members: members.map((a) => ({
      request_id: a.request_id,
      source_request_id: a.source_request_id,
      membership: inc.confirmed ? "confirmed" : "candidate",
      status: a.status,
      received_at: a.received_at,
      received_at_quality: a.received_at_quality,
      language: a.language,
      channel: a.channel,
      point: a.point ?? null,
    })),
    geo: {
      status: { state: "available", reason_code: null },
      located_member_count: members.filter((a) => a.point).length,
      total_member_count: members.length,
      centroid: { latitude: 43.245, longitude: 76.897 },
      report_spread_m: 1200,
    },
    ownership: {
      status: { state: "available", reason_code: null },
      candidates: [],
      ambiguous: false,
      loop_risk: false,
      reason_codes: ["mock_only"],
    },
    similar_outcomes: {
      status: { state: "abstained", reason_code: "INSUFFICIENT_HISTORY" },
      comparable_count: 0,
      median_resolution_hours: null,
      without_recurrence_30d: null,
    },
    next_actions: {
      status: { state: "abstained", reason_code: "NO_SUPPORTED_ACTION" },
      items: [],
    },
    synchronization: {
      status: { state: "abstained", reason_code: "LOCAL_MOCK_ONLY" },
      queued: 0,
      delivered: 0,
      retrying: 0,
      failed_permanent: 0,
    },
    timeline: [
      {
        occurred_at: inc.created_at,
        event_type: "incident_created",
        actor_type: "operator",
        synthetic: true,
      },
    ],
    evidence: [],
    synthetic: true,
  };
}
function csvRows(s: State) {
  return s.appeals.filter((a) => a.region_id === "ALA");
}
function clusterDetail(s: State, c: Cluster) {
  return {
    cluster_id: c.cluster_id,
    state: "open",
    appeal_count: c.member_request_ids.length,
    first_seen_at: now(),
    last_seen_at: now(),
    radius_m: 1200,
    centroid_longitude: 76.897,
    centroid_latitude: 43.245,
    cohesion_score: 0.84,
    novelty_score: 0.76,
    cluster_score: c.confidence,
    signals_used: ["shared_topic", "time_window", "location"],
    top_topics: [[c.topic_id, 0.91]],
    languages: { ru: c.member_request_ids.length },
    algorithm_version: "mock-rules-v1",
    members: c.member_request_ids.map((id, index) => {
      const a = s.appeals.find((x) => x.request_id === id)!;
      return {
        request_id: id,
        source_request_id: a.source_request_id,
        score: 0.91 - index * 0.01,
        membership_reasons: ["similar_topic", "nearby_time"],
        received_at: a.received_at,
        language: a.language,
        longitude: a.point?.longitude ?? null,
        latitude: a.point?.latitude ?? null,
      };
    }),
    synthetic: true,
  };
}

export async function handleMockDemo(req: Request, path: string[]) {
  const s = state();
  const p = path.join("/");
  const url = new URL(req.url);
  const input = req.method === "GET" ? {} : await body(req);
  if (p === "demo/reset" && req.method === "POST") {
    root.__pulseMockDemo = undefined;
    return json({ reset: true, synthetic: true });
  }
  if (p === "health/ready")
    return json({
      profile: "demo-mock",
      mock: true,
      checks: {
        application: "ready",
        database: "simulated",
        worker: "simulated",
        external_delivery: "simulated",
      },
    });
  if (p === "session/context")
    return json({ regions: ["ALA"], authentication_source: "demo-synthetic" });
  if (p === "requests" && req.method === "GET") {
    const offset = Number(url.searchParams.get("offset") ?? 0),
      limit = Math.min(100, Number(url.searchParams.get("limit") ?? 50));
    return json(
      csvRows(s)
        .slice(offset, offset + limit)
        .map((a) => ({
          ...publicAppeal(a),
          source_system: "pulse109-demo-synthetic",
          created_at: a.received_at,
        })),
    );
  }
  if (p === "requests" && req.method === "POST") {
    const id = uid(),
      location = input.location as
        | { latitude?: number; longitude?: number }
        | undefined;
    const a: Appeal = {
      request_id: id,
      source_request_id: String(input.source_request_id ?? `mock-${id}`),
      region_id: String(input.region_id ?? "ALA"),
      status: "received",
      received_at:
        typeof input.received_at === "string" ? input.received_at : now(),
      received_at_quality: String(input.received_at_quality ?? "exact"),
      language: String(input.language ?? "ru"),
      channel: String(input.channel ?? "web"),
      text: String(input.text ?? "Синтетическое обращение"),
      topic_id: "topic:unclassified",
      service_id: "service:unclassified",
      synthetic: true,
      version: 1,
      point: location
        ? {
            latitude: Number(location.latitude),
            longitude: Number(location.longitude),
          }
        : undefined,
    };
    s.appeals.unshift(a);
    return json({ request_id: id, synthetic: true }, 201);
  }
  if (p === "intake/plans")
    return json({
      status: "available",
      questions: [],
      suggested_fields: [],
      synthetic: true,
    });
  if (p === "appeals/preflight" && req.method === "POST") {
    const regionId = String(input.region_id ?? "ALA");
    const requestedTopic = String(input.topic_id ?? "");
    const topicId =
      requestedTopic === "topic:water" ? "topic:water_quality" : requestedTopic;
    const incomingWords = new Set(
      String(input.text ?? "")
        .toLocaleLowerCase("ru")
        .match(/[\p{L}\p{N}]{4,}/gu) ?? [],
    );
    const candidates = s.appeals
      .filter(
        (appeal) =>
          appeal.region_id === regionId &&
          appeal.topic_id === topicId &&
          !["closed", "resolved", "cancelled"].includes(appeal.status),
      )
      .map((appeal) => {
        const words = new Set(
          appeal.text.toLocaleLowerCase("ru").match(/[\p{L}\p{N}]{4,}/gu) ?? [],
        );
        const shared = [...incomingWords].filter((word) => words.has(word));
        return { appeal, shared };
      })
      .filter(({ shared }) => shared.length > 0)
      .sort((left, right) => right.shared.length - left.shared.length)
      .slice(0, 3)
      .map(({ appeal, shared }, index) => ({
        candidate_type: "request",
        candidate_id: appeal.request_id,
        score: Math.min(0.96, 0.79 + shared.length * 0.035 - index * 0.015),
        reasons: [
          "Совпадает тема обращения",
          `Похожие слова: ${shared.slice(0, 3).join(", ")}`,
        ],
        distance_m: null,
        time_delta_minutes: null,
        needs_human_confirmation: true,
      }));
    return json({
      candidates,
      evaluated_factors: ["category", "lexical"],
      needs_human_confirmation: true,
      automatic_merge: false,
      synthetic_only: true,
    });
  }
  if (p.startsWith("requests/")) {
    const parts = p.split("/"),
      id = decodeURIComponent(parts[1] ?? ""),
      a = s.appeals.find((row) => row.request_id === id);
    if (!a)
      return json(
        { code: "not_found", message: "Synthetic appeal not found" },
        404,
      );
    const action = parts.slice(2).join("/");
    if (!action && req.method === "GET") return json(attachment(a));
    if (action === "attachments") return json([]);
    if (action === "classifications")
      return json({
        recommendation_id: uid(),
        top_topics: [
          {
            id:
              a.topic_id === "topic:unclassified"
                ? "topic:water_quality"
                : a.topic_id,
            score: 0.91,
          },
        ],
        top_services: [
          {
            id:
              a.service_id === "service:unclassified"
                ? "service:water"
                : a.service_id,
            score: 0.87,
          },
        ],
        priority: "normal",
        model_version: "mock-rules-v1",
        confidence_band: "medium",
        synthetic: true,
      });
    if (action === "decisions") {
      a.current_decision = {
        topic_id: String(input.topic_id ?? a.topic_id),
        service_id: String(input.service_id ?? a.service_id),
        priority: String(input.priority ?? "normal"),
      };
      a.topic_id = a.current_decision.topic_id;
      a.service_id = a.current_decision.service_id;
      a.version++;
      return json({ decision_id: uid(), synthetic: true });
    }
    if (action === "assignments" || action === "status-events") {
      a.status = String(
        input.status ??
          input.target_status ??
          (action === "assignments" ? "assigned" : "in_progress"),
      );
      a.version++;
      return json({ status: a.status, event_id: uid(), synthetic: true });
    }
    if (action === "ownership-assessment")
      return json({
        request_id: id,
        request_version: a.version,
        region_id: a.region_id,
        service_id: a.service_id,
        policy_time: a.received_at,
        policy_time_source: a.received_at ? "received_at" : null,
        candidates: [
          {
            organization_id: "org:district-service",
            specificity: 0.88,
            evidence: [
              {
                rule_id: "synthetic-service-match",
                version: "mock-v1",
                reason_code: "service_match",
                source_ref: null,
                reason_codes: ["synthetic_demo"],
              },
            ],
            previously_rejected: false,
            previously_accepted: false,
          },
        ],
        ambiguous: false,
        loop_risk: false,
        reason_codes: ["synthetic_demo"],
        requires_human_confirmation: true,
        advisory_only: true,
        assigned_organization_id: null,
      });
    if (action === "assignments/latest")
      return json({
        assignment_id: uid(),
        status: "simulated",
        target_organization_id: "org:district-service",
      });
    if (action.includes("handoff-outcomes"))
      return json({
        status: "simulated",
        outcome: "accepted",
        synthetic: true,
      });
    if (action === "closure-preflight")
      return json({
        request_id: id,
        region_id: a.region_id,
        expected_appeal_version: input.expected_appeal_version ?? a.version,
        requires_human_confirmation: true,
        source_status_sufficient: false,
        evidence_hash: input.evidence_hash,
        status: "ready",
      });
    if (action === "closure-confirmations") {
      a.status = "closed";
      a.version++;
      return json({
        request_id: id,
        region_id: a.region_id,
        evidence_hash: input.evidence_hash,
        status: "closed",
        confirmation_id: uid(),
        synthetic: true,
      });
    }
    if (action === "recurrence-assessment")
      return json({
        request_id: id,
        region_id: a.region_id,
        request_version: input.request_version ?? a.version,
        advisory_only: true,
        requires_human_confirmation: true,
        status: "insufficient_evidence",
        matches: [],
      });
  }
  if (p === "discovery/scans") {
    const c = makeCluster(s);
    if (c && !s.clusters.some((row) => row.cluster_id === c.cluster_id))
      s.clusters.push(c);
    return json({
      status: { state: "available", reason_code: null },
      semantic_status: {
        state: "unavailable",
        reason_code: "mock_lexical_only",
      },
      scanned_appeals: s.appeals.length,
      clusters: c
        ? [
            {
              cluster_id: c.cluster_id,
              state: "open",
              appeal_count: c.member_request_ids.length,
              first_seen_at: now(),
              last_seen_at: now(),
              radius_m: 1200,
              centroid_longitude: 76.897,
              centroid_latitude: 43.245,
              cohesion_score: 0.84,
              novelty_score: 0.76,
              cluster_score: c.confidence,
              signals_used: ["shared_topic", "time_window", "location"],
              top_topics: [[c.topic_id, 0.91]],
              languages: { ru: c.member_request_ids.length },
              algorithm_version: "mock-rules-v1",
              members: c.member_request_ids.map((id, index) => {
                const a = s.appeals.find((x) => x.request_id === id)!;
                return {
                  request_id: id,
                  source_request_id: a.source_request_id,
                  score: 0.91 - index * 0.01,
                  membership_reasons: ["similar_topic", "nearby_time"],
                  received_at: a.received_at,
                  language: a.language,
                  longitude: a.point?.longitude ?? null,
                  latitude: a.point?.latitude ?? null,
                };
              }),
            },
          ]
        : [],
      synthetic: true,
    });
  }
  if (p === "operations/attention-feed") {
    const cluster = makeCluster(s);
    return json({
      status: { state: "available", reason_code: null },
      region_id: "ALA",
      generated_at: now(),
      pulse: {
        open_appeals: s.appeals.filter((a) => a.status !== "closed").length,
        active_incidents: s.incidents.length,
        emerging_patterns: cluster ? 1 : 0,
        unowned_incidents: 0,
        queued_deliveries: 0,
        failed_deliveries: 0,
      },
      items: cluster
        ? [
            {
              kind: "emerging_cluster",
              severity: "elevated",
              region_id: "ALA",
              detected_at: now(),
              summary_code: "EMERGING_CLUSTER",
              count: cluster.member_request_ids.length,
              target_kind: "cluster",
              target_id: cluster.cluster_id,
              detail: { radius_m: 1200 },
            },
          ]
        : [],
      synthetic: true,
    });
  }
  if (p === "datalab/arrivals") {
    const buckets = Array.from({ length: 24 }, (_, i) => ({
      start: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
      count: [
        2, 3, 4, 5, 3, 8, 11, 12, 7, 5, 4, 6, 8, 9, 5, 3, 4, 7, 10, 8, 6, 4, 3,
        2,
      ][i],
      by_topic: { water_quality: (i % 3) + 1, roads: i % 2 },
      synthetic: true,
    }));
    return json({
      status: { state: "available", reason_code: null },
      buckets,
      peak: buckets[7],
      baseline_per_bucket: 5,
      excluded_untrusted_time: 0,
    });
  }
  if (p === "incidents" && req.method === "GET")
    return json(
      s.incidents
        .filter(
          (i) =>
            !url.searchParams.has("state") ||
            i.state === url.searchParams.get("state"),
        )
        .map((i) => ({
          ...i,
          member_count: i.member_request_ids.length,
          confirmed_member_count: i.confirmed ? i.member_request_ids.length : 0,
          synthetic: true,
        })),
    );
  if (p === "incidents" && req.method === "POST") {
    const ids = (input.member_request_ids ?? []) as string[];
    const inc: Incident = {
      incident_id: uid(),
      region_id: String(input.region_id ?? "ALA"),
      state: "open",
      topic_id: String(input.topic_id ?? "topic:water_quality"),
      service_id: String(input.service_id ?? "service:water"),
      member_request_ids: ids,
      confirmed: false,
      created_at: now(),
    };
    s.incidents.unshift(inc);
    return json(
      {
        incident_id: inc.incident_id,
        candidate_member_request_ids: ids,
        confirmed_member_request_ids: [],
        synthetic: true,
      },
      201,
    );
  }
  if (p.startsWith("incidents/")) {
    const parts = p.split("/"),
      inc = s.incidents.find((i) => i.incident_id === parts[1]);
    if (!inc) return json({ code: "not_found" }, 404);
    const action = parts.slice(2).join("/");
    if (action === "workspace") return json(workspace(s, inc));
    if (!action)
      return json({
        ...inc,
        member_count: inc.member_request_ids.length,
        synthetic: true,
      });
    if (action === "confirm") {
      inc.confirmed = true;
      inc.state = "active";
      return json({
        ...inc,
        confirmed_member_request_ids: inc.member_request_ids,
        synthetic: true,
      });
    }
    if (action === "members") {
      const id = String(input.request_id ?? input.member_request_id ?? "");
      if (id && !inc.member_request_ids.includes(id))
        inc.member_request_ids.push(id);
      return json({
        candidate_member_request_ids: inc.member_request_ids,
        confirmed_member_request_ids: inc.confirmed
          ? inc.member_request_ids
          : [],
        synthetic: true,
      });
    }
    if (action === "merge")
      return json({ ...inc, state: "merged", synthetic: true });
    if (action === "split")
      return json({ ...inc, state: "split", synthetic: true });
  }
  if (p.startsWith("discovery/clusters/")) {
    const parts = p.split("/"),
      c = s.clusters.find((x) => x.cluster_id === parts[2]) ?? makeCluster(s);
    if (!c) return json({ code: "not_found" }, 404);
    if (parts[3] === "reviews") {
      c.status = "promoted";
      return json({
        status: c.status,
        promoted_incident_id: url.searchParams.get("promoted_incident_id"),
        synthetic: true,
      });
    }
    return json(clusterDetail(s, c));
  }
  if (p === "analytics/ask") return ask(s, input);
  if (p === "analytics/query") return query(s, input);
  if (p === "analytics/ask/drilldown")
    return json({
      appeals: csvRows(s).slice(0, 25).map(attachment),
      total: csvRows(s).length,
      synthetic: true,
    });
  if (p === "analytics/ask/export") return exportFile(s, input);
  if (p.startsWith("datalab/")) return dataLab(s, p, url);
  if (p === "replay/reports")
    return json([
      {
        report_id: "mock-replay-synthetic",
        dataset_id: "demo-synthetic-ala",
        region_id: "ALA",
        cutoff_at: now(),
        baseline_policy_id: "synthetic-baseline",
        baseline_version: "mock-v1",
        candidate_policy_id: "synthetic-candidate",
        candidate_version: "mock-v1",
        created_at: now(),
        decision: null,
        status: "completed",
        evaluated_count: 0,
        synthetic_count: 126,
        accuracy: null,
        summary: "Синтетические данные исключены из оценки качества.",
        synthetic: true,
      },
    ]);
  if (p.startsWith("replay/reports/"))
    return json({
      report_id: p.split("/")[2],
      dataset_id: "demo-synthetic-ala",
      region_id: "ALA",
      cutoff_at: now(),
      baseline_policy_id: "synthetic-baseline",
      baseline_version: "mock-v1",
      candidate_policy_id: "synthetic-candidate",
      candidate_version: "mock-v1",
      created_at: now(),
      decision: null,
      dataset_digest: "synthetic-data-excluded-from-quality-evaluation",
      status: "completed",
      baseline: {
        evaluated_count: 0,
        synthetic_count: 126,
        route_change_count: 0,
        labeled_count: 0,
        confirmed_route_agreement: null,
        route_matched_case_count: 0,
        historical_handoff_rate_on_route_matched_cases: null,
        operator_override_rate: null,
        first_pass_acceptance_rate: null,
        language_slice_agreement: {},
      },
      candidate: {
        evaluated_count: 0,
        synthetic_count: 126,
        route_change_count: 0,
        labeled_count: 0,
        confirmed_route_agreement: null,
        route_matched_case_count: 0,
        historical_handoff_rate_on_route_matched_cases: null,
        operator_override_rate: null,
        first_pass_acceptance_rate: null,
        language_slice_agreement: {},
      },
      promoted: false,
      reason: "synthetic_data_excluded",
      synthetic: true,
    });
  return json(
    {
      code: "mock_route_not_implemented",
      path: p,
      message: "This action is not available in the local mock demo.",
    },
    501,
  );
}

function query(s: State, input: Input) {
  const total = csvRows(s).length;
  return json({
    metric_id: String(input.metric_id ?? "appeal_volume"),
    metric_version: "mock-v1",
    columns: [
      { name: "region_id", type: "string" },
      { name: "count", type: "integer" },
    ],
    rows: [["ALA", total]],
    computed_at: now(),
    data_cutoff: now(),
    quality: "complete",
    coverage: { ALA: "present" },
    missing_regions: [],
    provenance: ["local synthetic mock"],
  });
}
function ask(s: State, input: Input) {
  const question = String(input.question ?? "").toLowerCase();
  const forecast = /прогноз|forecast|алдағы|болжам/.test(question);
  const horizon = /90|3 месяц|үш ай/.test(question)
    ? 90
    : /60|2 месяц|екі ай/.test(question)
      ? 60
      : 30;
  const trend = /динамик|тренд|trend|измен|өсім/.test(question);
  const todayOnly = /сегодня|today|бүгін/.test(question);
  const periodMs = (todayOnly ? 1 : 7) * 86400000;
  const total = csvRows(s).filter(
    (a) => a.received_at && Date.now() - Date.parse(a.received_at) < periodMs,
  ).length;
  const columns = [
    { name: "period", type: "string" },
    { name: "value", type: "integer" },
    ...(forecast
      ? [
          { name: "observed", type: "boolean" },
          { name: "baseline", type: "integer" },
          { name: "lower_bound", type: "integer" },
          { name: "upper_bound", type: "integer" },
        ]
      : []),
  ];
  const rows: unknown[][] = forecast
    ? Array.from({ length: 30 + horizon }, (_, i) => {
        const value =
          i < 30 ? 8 + (i % 7) * 2 : 13 + Math.round((i - 29) * 0.13);
        return [
          new Date(Date.now() + (i - 29) * 86400000).toISOString().slice(0, 10),
          value,
          i < 30,
          12,
          Math.max(0, value - 4),
          value + 5,
        ];
      })
    : Array.from({ length: 7 }, (_, i) => [
        new Date(Date.now() - (6 - i) * 86400000).toISOString().slice(0, 10),
        Math.max(2, total + i - 5),
      ]);
  const forecastTotal = rows
    .slice(30)
    .reduce((sum, row) => sum + Number(row[1]), 0);
  const answerTotal = forecast ? forecastTotal : total;
  const previousTotal = forecast ? horizon * 12 : Math.max(0, total - 3);
  const metric = "appeals_volume";
  const qr = {
    metric_id: metric,
    metric_version: "mock-v1",
    dimensions: ["region_id"],
    filters: [],
    time_from: new Date(Date.now() - periodMs).toISOString(),
    time_to: forecast
      ? new Date(Date.now() + horizon * 86400000).toISOString()
      : now(),
    granularity: "day",
    limit: 500,
  };
  const result = {
    metric_id: metric,
    metric_version: "mock-v1",
    columns,
    rows,
    computed_at: now(),
    data_cutoff: now(),
    quality: "complete",
    coverage: { ALA: "present" },
    missing_regions: [],
    provenance: ["synthetic local demo data"],
  };
  const token = uid();
  s.exports.set(token, { question, rows, total });
  return json({
    schema_version: "ask-pulse-v1",
    status: "available",
    answer: {
      text: forecast
        ? `Симуляция прогноза на ${horizon} дней: около ${answerTotal} обращений по условной истории Алматы.`
        : `В синтетической выборке за ${todayOnly ? "сегодня" : "7 дней"} найдено ${total} обращений.`,
      total: answerTotal,
      previous_total: previousTotal,
      change_pct:
        previousTotal === 0
          ? null
          : Number(
              (((answerTotal - previousTotal) / previousTotal) * 100).toFixed(
                1,
              ),
            ),
      peak: {
        period: rows[rows.length - 1][0],
        value: Number(rows[rows.length - 1][1]),
      },
    },
    query: qr,
    result,
    previous_result: result,
    chart: {
      type: forecast ? "forecast" : trend ? "line" : "bar",
      x: "period",
      y: "value",
      series: null,
      columns,
      rows,
    },
    forecast: forecast
      ? {
          baseline: 12,
          lower_bound: 8,
          upper_bound: 19,
          method: "Линейный сценарий (демо)",
          version: "mock-v1",
        }
      : null,
    alerts: [],
    provenance: {
      metric_id: metric,
      metric_version: "mock-v1",
      definition: "Synthetic local sample only",
      time_from: qr.time_from,
      time_to: qr.time_to,
      data_cutoff: now(),
      computed_at: now(),
      coverage: { ALA: "present" },
      missing_regions: [],
      source_refs: ["mock-process-memory"],
      excluded_records: 0,
      limitations: [
        "All records and analytics are synthetic; not model quality or operational evidence.",
      ],
    },
    clarification: null,
    reason_code: null,
    context_token: token,
    synthetic: true,
    inference: null,
    intent: {
      schema_version: "analytics-intent-v1",
      intent_type: forecast ? "forecast" : trend ? "trend" : "volume",
      metric_id: metric,
      region_ids: ["ALA"],
      topic_id: null,
      service_id: null,
      time_from: qr.time_from,
      time_to: qr.time_to,
      granularity: "day",
      comparison: "previous_period",
      horizon_days: forecast ? horizon : null,
      visualization: forecast ? "forecast" : trend ? "line" : "bar",
    },
    actions: {
      drilldown_url: "/v1/analytics/ask/drilldown",
      export_token: token,
      export_query: qr,
      export_formats: ["pdf", "xlsx"],
    },
  });
}
function dataLab(s: State, p: string, url: URL) {
  const n = csvRows(s).length,
    status = { state: "available", reason_code: null };
  if (p === "datalab/quality")
    return json({
      status,
      dimensions: [
        {
          name: "Время поступления",
          numerator: n,
          denominator: n,
          ratio: 1,
          definition: "Synthetic timestamps",
          drilldown: "received_at",
        },
        {
          name: "Геолокация",
          numerator: 6,
          denominator: n,
          ratio: 6 / n,
          definition: "Synthetic mapped points",
          drilldown: "location",
        },
      ],
      provenance: {
        dataset: "demo-synthetic-ala",
        region_id: "ALA",
        generated_at: now(),
        rows_considered: n,
        synthetic: true,
        metric_version: "mock-v1",
      },
    });
  if (p === "datalab/process")
    return json({
      status,
      stages: ["received", "classified", "assigned", "closed"].map(
        (stage, i) => ({
          stage,
          definition: "Mock workflow stage",
          count: Math.max(0, n - i * 12),
          share_of_previous: i ? 0.9 : 1,
          drilldown: stage,
        }),
      ),
      largest_drop: "closed",
    });
  if (p === "datalab/timings")
    return json({
      status,
      timings: ["intake", "classification", "assignment", "resolution"].map(
        (stage) => ({
          stage,
          definition: "Simulated duration",
          overall: { count: n, p50: 2.4, p75: 5.1, p90: 9, p95: 12 },
        }),
      ),
    });
  if (p === "datalab/handoffs")
    return json({
      status,
      handoff_rate: 0.12,
      appeals_with_handoff: 4,
      appeals_total: n,
      edges: [
        {
          from_service: "service:district",
          to_service: "service:water",
          count: 4,
          drilldown: "handoffs",
        },
      ],
      loops: [],
    });
  if (p === "datalab/definitions")
    return json({
      definitions: ["appeal_volume", "resolution_time", "handoff_rate"].map(
        (key) => ({
          key,
          title: key,
          numerator: "Synthetic count",
          denominator: "Synthetic total",
          time_basis: "received_at",
          included: ["synthetic demo records"],
          excluded: ["real data"],
          metric_version: "mock-v1",
        }),
      ),
    });
  if (p === "datalab/drilldown")
    return json({
      key: url.searchParams.get("key"),
      total: n,
      appeals: csvRows(s).slice(0, 25).map(publicAppeal),
    });
  return json({ status, rows: [] });
}
async function exportFile(s: State, input: Input) {
  const token = input.result_token ?? input.export_token ?? input.token;
  const data = s.exports.get(String(token)) as
    | { question: string; rows: unknown[][]; total: number }
    | undefined;
  const format = String(
    input.format ?? input.export_format ?? "pdf",
  ).toLowerCase();
  const label = data?.question ?? "Синтетическая аналитика Pulse 109";
  if (format === "xlsx") {
    const bytes = makeXlsx(label, data?.rows ?? []);
    return new Response(bytes, {
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": 'attachment; filename="pulse109-analytics.xlsx"',
        "X-Pulse109-Mode": "mock",
      },
    });
  }
  const bytes = makePdf(
    `${label}\n${data?.total ?? 0} synthetic records\nLocal mock demo; not operational evidence.`,
  );
  return new Response(bytes, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": 'attachment; filename="pulse109-analytics.pdf"',
      "X-Pulse109-Mode": "mock",
    },
  });
}
function makePdf(text: string) {
  const safe = text.replace(/[()\\]/g, "\\$&").replace(/[^\x20-\x7e]/g, "?");
  const stream = `BT /F1 12 Tf 50 760 Td (${safe}) Tj ET`;
  const objs = [
    `1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj`,
    `2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj`,
    `3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>endobj`,
    `4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj`,
    `5 0 obj<< /Length ${stream.length} >>stream\n${stream}\nendstream endobj`,
  ];
  let out = "%PDF-1.4\n";
  const offsets = [0];
  for (const obj of objs) {
    offsets.push(out.length);
    out += `${obj}\n`;
  }
  const xref = out.length;
  out += `xref\n0 ${offsets.length}\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((o) => `${String(o).padStart(10, "0")} 00000 n \n`)
    .join(
      "",
    )}trailer<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return new TextEncoder().encode(out);
}
function makeXlsx(title: string, rows: unknown[][]) {
  // A small valid SpreadsheetML package without runtime dependencies.
  const entries = [
    [
      "[Content_Types].xml",
      `<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`,
    ],
    [
      "_rels/.rels",
      `<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
    ],
    [
      "xl/workbook.xml",
      `<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Mock analytics" sheetId="1" r:id="rId1"/></sheets></workbook>`,
    ],
    [
      "xl/_rels/workbook.xml.rels",
      `<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>`,
    ],
    [
      "xl/worksheets/sheet1.xml",
      `<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${[title, ...rows.map((r) => r.join(" | "))].map((v, i) => `<row r="${i + 1}"><c r="A${i + 1}" t="inlineStr"><is><t>${xml(String(v))}</t></is></c></row>`).join("")}</sheetData></worksheet>`,
    ],
  ] as const;
  return zip(entries);
}
function xml(v: string) {
  return v
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}
function zip(files: readonly (readonly [string, string])[]) {
  const enc = new TextEncoder(),
    parts: Uint8Array[] = [];
  const u16 = (n: number) => [n & 255, (n >> 8) & 255],
    u32 = (n: number) => [...u16(n & 65535), ...u16(n >>> 16)];
  let size = 0;
  const central: Uint8Array[] = [];
  const crc32 = (data: Uint8Array) => {
    let c = -1;
    for (const b of data) {
      c ^= b;
      for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (c & 1 ? 0xedb88320 : 0);
    }
    return (c ^ -1) >>> 0;
  };
  for (const [name, content] of files) {
    const n = enc.encode(name),
      d = enc.encode(content),
      crc = crc32(d),
      off = size;
    const local = new Uint8Array([
      0x50,
      0x4b,
      3,
      4,
      ...u16(20),
      ...u16(0),
      ...u16(0),
      ...u16(0),
      ...u16(0),
      ...u32(crc),
      ...u32(d.length),
      ...u32(d.length),
      ...u16(n.length),
      ...u16(0),
      ...n,
      ...d,
    ]);
    parts.push(local);
    size += local.length;
    central.push(
      new Uint8Array([
        0x50,
        0x4b,
        1,
        2,
        ...u16(20),
        ...u16(20),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u32(crc),
        ...u32(d.length),
        ...u32(d.length),
        ...u16(n.length),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u16(0),
        ...u32(0),
        ...u32(off),
        ...n,
      ]),
    );
  }
  const csize = central.reduce((a, b) => a + b.length, 0),
    end = new Uint8Array([
      0x50,
      0x4b,
      5,
      6,
      ...u16(0),
      ...u16(0),
      ...u16(files.length),
      ...u16(files.length),
      ...u32(csize),
      ...u32(size),
      ...u16(0),
    ]);
  const out = new Uint8Array(size + csize + end.length);
  let at = 0;
  for (const part of [...parts, ...central, end]) {
    out.set(part, at);
    at += part.length;
  }
  return out;
}
