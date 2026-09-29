# Ask Pulse

Ask Pulse is the natural-language analytics surface inside the Operations Center.
An RU or KK question becomes a strict, versioned intent and an allowlisted metric
query. Core computes the numbers; the web renders the returned chart specification.
Neither a parser nor an optional LLM may generate SQL, calculate the displayed
answer, change an appeal or decide its routing.

## Runtime and data boundary

The demo runs the real API, PostgreSQL analytics read model, migrations and
append-only query audit. Its municipal records, identities and catalog are
explicitly synthetic. The existing in-memory fixture is available for local/test
contract checks; it is not a substitute for the PostgreSQL demo or production.
An unavailable database or audit store produces an explicit failure state.

Region coverage comes from registered sources and their freshness assessments.
Missing or stale sources remain visible in every result. This does not claim a
complete twenty-region dataset: the authoritative manifest and remaining sources
are still blocker B01. Topic and service aliases come from the active catalog;
synthetic catalog entries are excluded from operational profiles. B06 remains
open for the approved taxonomy and SLA policy.

Ask Pulse uses `appeals_volume/2.0.0`; the existing `/analytics/query` default
continues to use `appeals_volume/1.0.0` and its observed-time meaning. Version
2.0 adds trusted business time, human-confirmed topic/service dimensions and
time-quality exclusions without silently changing existing consumers.

Trusted business time is required for aggregation. Missing or ambiguous time is
excluded, with a count and limitations in provenance. An observation/import time
is never silently presented as the business event time.

Question calendar periods use Kazakhstan's +05:00 boundary; chart buckets use
UTC, as the metric definition states. The cutoff is the latest observed source
record in the read snapshot, independently of the requested business period.
Late imports can therefore contribute to a historical business-time query.
Excluded undated records are counted in the selected scope; their missing dates
cannot be assigned to the requested period.

Reviewed, effective-dated aliases live in `analytics.intent_alias` and must
reference an already registered region or active topic/service. Production
aliases require an approval reference; demo aliases remain synthetic. Adding
aliases never creates regional coverage. Forecasts require contiguous measured
daily history and decline when gaps cannot be distinguished from missing data.
Unobserved region and time buckets stay absent. A lack of rows is not rendered
as zero unless an approved freshness policy can establish completeness for the
whole requested interval.

## Supported questions and honest limits

- Volume and time trends, region comparisons and topic structure.
- A comparison with the preceding period of equal duration. A missing, stale or
  partial comparison cannot produce a confident growth percentage; division by
  a zero baseline leaves the percentage undefined.
- Active persisted Radar alerts. Growth alone is not an anomaly, and an empty
  alert list is not proof that no anomaly exists.
- Handoffs through existing Data Lab analytics where the repository supplies it.
- Seasonal-naive volume forecasts for one, two or three months where sufficient
  trusted history exists. Insufficient history is explicit; no calibrated
  prediction interval, learned quality number or staffing estimate is invented.

An ambiguous region or period returns `clarification_required` and selectable
options. Unsupported, unsafe, causal or unapproved-policy questions return
`abstained` with a controlled reason. Unavailable storage or capabilities return
`unavailable`. These are separate from a successful result containing zero.

## UI and reproducibility

The panel contains localized questions, suggested prompts and follow-ups,
context chips, numbers and deterministic SVG line/bar charts. It preserves a
normalized context through a signed, actor- and region-bound token. A new question
clears context; changing the region remounts the panel. The browser does not save
conversation text in local storage.

Each result shows its synthetic flag, coverage and cutoff. **Как рассчитано** /
**Қалай есептелді** opens the metric version and definition, period, sources,
excluded records and limitations. A chart has a table alternative. Forecast
bounds are rendered only when returned explicitly.

**Показать обращения** calls the authenticated drill-down endpoint for the same
validated intent. It shows metadata, preserving unknown business time; it does
not retrieve citizen text or private references. PDF and Excel actions send the
signed result snapshot to the server renderer, so the file uses the displayed
rows and cutoff even if the underlying database changes. Download and drill-down
repeat identity/region checks; exports also require an allowed export purpose.
Configure `NEXT_PUBLIC_PULSE109_EXPORT_PURPOSE` to the deployment's approved
purpose claim. Its development default is `analytics-review`; this does not
approve a legal basis or bypass the server's verified-identity purpose check.

## Interfaces

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/analytics/ask` | Question, locale and optional signed context; returns `ask-pulse-v1` |
| `POST /v1/analytics/ask/drilldown` | Signed context and bounded limit; appeal metadata |
| `POST /v1/analytics/ask/export` | Signed result token and PDF/XLSX format; binary attachment |
| `POST /v1/inference/analytics-intent` | Optional private inference gateway; strict intent only |

The application uses the deterministic CPU parser when no local LLM is configured
or when the gateway fails. A local model is optional and replaceable through the
versioned inference boundary and model aliases. No Qwen/Gemma weights or model
quality are implied by the interface. Model approval, RU/KK evaluation and GPU
capacity remain separate deployment work; B09 is still open. The ordinary
operator panel does not select model candidates.
When the gateway reports parser metadata, the result identifies the model alias,
runtime and fallback reason. Evaluation candidates remain explicitly unvalidated.

Only the question, scoped catalog and normalized context may cross the private
intent gateway. Citizen records, PII and aggregates remain in Core. Questions are
transient and may themselves contain sensitive input; they are not written to
logs, metric labels or query audit. The audit stores a question hash, parser
version, validated structured intent/query, scope, result state and cutoff.

## Demo click path

See [the demo runbook](../DEMO_RUNBOOK.md#ask-pulse-about-30-seconds). The normal
manual appeal path stays available with inference stopped. The feature does not
close B01–B10 or certify production identity, legal basis, retention or a live
regional integration.

## Verification note

The migration chain through `0024_ask_analytics_read_model` was applied from an
empty database in two independent PostgreSQL integration passes; all 23 tests
passed in both disposable databases. The Docker demo verification also rebuilt
the images, migrated and seeded the real PostgreSQL topology, completed the
end-to-end API walkthrough and restored a clean 134-appeal synthetic world.
Re-running the seed was verified to be idempotent, including the immutable
Replay Lab snapshot.
