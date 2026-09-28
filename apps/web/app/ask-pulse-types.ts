/** Mirrors the versioned Ask Pulse contract; values are computed in Core. */
export type Locale = "ru" | "kk";
export type MetricColumn = {
  name: string;
  type: "string" | "integer" | "number" | "datetime" | "boolean";
};
export type AnalyticsQuery = {
  metric_id: string;
  metric_version: string;
  dimensions: string[];
  filters: {
    field: string;
    operator: "eq" | "in" | "gte" | "lte";
    value: string | number | string[];
  }[];
  time_from: string;
  time_to: string;
  granularity: "hour" | "day" | "week" | "month";
  limit: number;
};
export type ChartSpec = {
  type: "kpi" | "line" | "bar" | "forecast" | "surge" | "ranked_edges";
  x: string;
  y: string;
  series: string | null;
  columns: MetricColumn[];
  rows: unknown[][];
};
export type AnalyticsResult = {
  metric_id: string;
  metric_version: string;
  columns: MetricColumn[];
  rows: unknown[][];
  computed_at: string;
  data_cutoff: string;
  quality: "complete" | "partial" | "stale" | "missing";
  coverage: Record<string, "present" | "missing" | "stale">;
  missing_regions: string[];
  provenance: string[];
};
export type AskResponse = {
  schema_version: "ask-pulse-v1";
  status: "available" | "clarification_required" | "abstained" | "unavailable";
  answer: {
    text: string;
    total: number | null;
    previous_total: number | null;
    change_pct: number | null;
    peak: { period: string; value: number } | null;
  };
  query: AnalyticsQuery | null;
  result: AnalyticsResult | null;
  previous_result: AnalyticsResult | null;
  chart: ChartSpec | null;
  forecast: {
    baseline: number | null;
    lower_bound: number | null;
    upper_bound: number | null;
    method: string;
    version: string;
  } | null;
  alerts: {
    alert_id: string;
    region_id: string;
    type: string;
    severity: string;
    detected_at: string;
    baseline: number | null;
    observed_value: number | null;
  }[];
  provenance: {
    metric_id: string;
    metric_version: string;
    definition: string;
    time_from: string;
    time_to: string;
    data_cutoff: string;
    computed_at: string;
    coverage: Record<string, "present" | "missing" | "stale">;
    missing_regions: string[];
    source_refs: string[];
    excluded_records: number | null;
    limitations: string[];
  } | null;
  clarification: { field: string; prompt: string; options: string[] } | null;
  reason_code: string | null;
  context_token: string | null;
  synthetic: boolean;
  inference?: {
    requested_alias: "champion" | "challenger" | "baseline";
    model_alias: "champion" | "challenger" | "baseline";
    model_name: string;
    model_revision: string | null;
    artifact_sha256: string | null;
    runtime: string;
    runtime_version: string | null;
    quantization: string | null;
    prompt_version: string;
    schema_version: string;
    fallback_used: boolean;
    fallback_reason: string | null;
    latency_ms: number;
    approval_state: "deterministic_baseline" | "evaluation" | "approved";
  } | null;
  intent: {
    schema_version: "analytics-intent-v1";
    intent_type:
      | "volume"
      | "trend"
      | "region_comparison"
      | "topic_structure"
      | "surge"
      | "forecast"
      | "bottlenecks";
    metric_id: string;
    region_ids: string[];
    topic_id: string | null;
    service_id: string | null;
    time_from: string;
    time_to: string;
    granularity: "hour" | "day" | "week" | "month";
    comparison: "none" | "previous_period";
    horizon_days: number | null;
    visualization: string;
  } | null;
  actions: {
    drilldown_url: string | null;
    export_token: string | null;
    export_query: AnalyticsQuery | null;
    export_formats: ("pdf" | "xlsx")[];
  };
};
