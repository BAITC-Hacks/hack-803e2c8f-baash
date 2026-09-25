# Pulse 109 Decision Log

Record implementation decisions here when the repository, contracts or available integrations require a concrete choice that is not already locked by `AGENTS.md`, the executable contracts or `DECISIONS_AND_BLOCKERS.md`.

## Initial accepted decisions

### D-001 — Modular core before service extraction

- **Status:** accepted
- **Decision:** implement a modular FastAPI core with separate processes for web, API, workers, inference and adapters.
- **Reason:** it gives production separation at runtime without creating a distributed ownership and deployment burden during the first month.
- **Revisit when:** a module has an independent owner, security boundary, scaling profile or measured reliability bottleneck.

### D-002 — PostgreSQL is authoritative

- **Status:** accepted
- **Decision:** PostgreSQL is the system of record; PostGIS and pgvector extend the same database. Redis, search indexes and caches are derived and optional.
- **Reason:** this keeps transactions, audit, recovery and local deployment manageable.
- **Revisit when:** measured load or retention requirements exceed the documented capacity plan.

### D-003 — Human confirmation for consequential AI actions

- **Status:** accepted
- **Decision:** models propose categories, routing, priority, duplicate links and reply drafts; authorized users confirm consequential actions.
- **Reason:** appeal history, SLA and accountability must remain explainable and reversible.
- **Revisit when:** a specific low-risk action has approved policy, calibrated quality, monitoring and a safe rollback path.

### D-004 — Stable canonical contract with isolated adapters

- **Status:** accepted
- **Decision:** every external CRM or government system integrates through its own adapter and the versioned canonical request/event contracts.
- **Reason:** integration-specific changes must not leak into domain logic.
- **Revisit when:** never for vendor-specific convenience; evolve only through a versioned contract change.

### D-005 — Pilot inference within two GPUs

- **Status:** accepted
- **Decision:** use the model stack documented in `contracts/model_stack.md`, with explicit batching, quantization where specified, CPU/lexical fallbacks and no hard dependency on a hosted LLM.
- **Reason:** the platform must fit the stated compute envelope and remain operable during model outages.
- **Revisit when:** benchmark evidence and an approved infrastructure budget justify a change.

## Entry template

### D-006 - Separate canonical import time from public intake time

- **Date:** 2026-09-11
- **Status:** accepted
- **Context:** the canonical adapter schema permits `received_at: null` with explicit `missing` or `date_only` quality, while the public `CreateRequest` schema requires a concrete date-time.
- **Decision:** M1 canonical import remains a separate application boundary and preserves null business time. It does not call or weaken the public M2 create DTO.
- **Alternatives:** fabricate a timestamp; loosen the public API; quarantine every missing date.
- **Consequences:** no contract drift or invented precision; M2 must map public intake and adapter import through one service after their separate validation steps.
- **Evidence:** canonical contract tests and `test_missing_and_date_only_time_do_not_invent_instants`.
- **Revisit when:** a versioned public bulk-import API is approved.

### D-007 - Deterministic synthetic M1 ingestion before source selection

- **Date:** 2026-09-11
- **Status:** accepted
- **Context:** the first regional system, authoritative source manifest, legal basis, and retention policy are external blockers.
- **Decision:** implement the M1 parser against an explicitly synthetic JSONL mapping and reject any manifest not marked synthetic. Keep source-specific transport and production persistence behind later adapter/repository work.
- **Alternatives:** invent a regional protocol; wait without implementing contract and DQ behavior.
- **Consequences:** provenance, quarantine, time quality, and idempotency are executable now without implying a live integration.
- **Evidence:** `data/manifests/synthetic-m1.json` and the reproducible DQ report.
- **Revisit when:** B07 and B10 are resolved in writing.

### D-008 - Synthetic-only M3 evidence before candidate training

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** B02, B03, B06 and B10 block representative labels, leakage-safe production features, the authoritative taxonomy and approved raw text.
- **Decision:** implement the versioned inference interface, deterministic mock/lexical CPU modes and a linear baseline evaluated only on an explicitly synthetic grouped temporal fixture. Require human confirmation for every output.
- **Alternatives:** train XLM-R on invented labels; expose uncalibrated scores as actionable quality; postpone all inference contracts.
- **Consequences:** M3 integration and evaluation mechanics are executable, while all metrics remain labelled fixture diagnostics and no autonomous routing is enabled.
- **Evidence:** `contracts/inference.schema.json`, `ml/datasets/synthetic_m3_manifest.json`, `ml/evaluation/synthetic_m3/` and `tests/model/`.
- **Revisit when:** approved pre-decision text, label policy, taxonomy and leakage documentation are supplied.

### D-009 - Manual in-memory vertical slice is not the production repository

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** M3 feedback needs an executable human-decision boundary, while completing the PostgreSQL M2 repository is outside this run's requested milestones.
- **Decision:** mount the contract-shaped manual API over an in-memory transactional repository for local/browser tests, and create forward database tables for the durable M2/M3 state without claiming they are wired at runtime.
- **Alternatives:** fake a human-correction test entirely inside the model package; silently present memory state as durable.
- **Consequences:** the no-ML operator path and feedback semantics are testable now; M2 remains the next milestone until the same transaction boundary is implemented in PostgreSQL.
- **Evidence:** `services/core/src/pulse109/manual_path/`, migrations `0003`/`0004`, API E2E and browser screenshots.
- **Revisit when:** the PostgreSQL repository and approved identity/authorization adapter are connected.

### D-010 - Deterministic hybrid fallback before representative M4 data

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** B02 and B04 block representative retrieval judgments, embeddings, and confirmed duplicate pairs.
- **Decision:** implement PostgreSQL FTS/pgvector storage and reciprocal-rank fusion, while using a deterministic lexical/hash-vector fallback for synthetic tests. Every duplicate remains a proposal with text, service, time, and geo evidence and requires a human decision.
- **Alternatives:** download unapproved embedding models; claim fixture scores as production quality; automatically merge high-scoring pairs.
- **Consequences:** storage and review contracts are executable offline without creating a quality claim or destroying appeal identity.
- **Evidence:** migration `0005`, `ml/datasets/synthetic_m4_manifest.json`, `ml/evaluation/synthetic_m4/`, and retrieval/E2E tests.
- **Revisit when:** approved raw text, representative judgments, confirmed pairs, and evaluation policy are available.

### D-011 - Replay adapter is the only M5 external transport

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** B07 leaves the first regional target, owner, API, sandbox, and status semantics unknown.
- **Decision:** ship a typed adapter SDK, deterministic replay adapter, bounded retries, dead-letter state, and reconciliation with unknown statuses routed to mapping review. Do not invent a live system protocol.
- **Alternatives:** bind domain code to an assumed CRM; omit delivery failure behavior until a target exists.
- **Consequences:** the delivery state machine and incident membership are testable, but no national or live integration is claimed.
- **Evidence:** migration `0006`, adapter contract/outage tests, and `data/reports/synthetic-m5-replay-trace.json`.
- **Revisit when:** B07 is resolved and the first adapter contract is approved.

### D-012 - Governed synthetic read model for M6

- **Date:** 2026-09-12
- **Status:** accepted
- **Context:** authoritative national coverage, SLA policy, production identity, and legal approval remain blocked by B01, B06, B08, and B10.
- **Decision:** expose an allowlisted metric catalog and governed intent parser over synthetic read results. Dashboard, PDF, and XLSX consume the same immutable metric result; missing and stale regions remain explicit and never become numeric zeros.
- **Alternatives:** allow arbitrary SQL; fabricate national values; encode an unapproved SLA threshold.
- **Consequences:** situation-center semantics and export reconciliation are executable without representing unavailable policy or data as fact.
- **Evidence:** migration `0007`, analytics/report tests, export comparison E2E, and browser evidence in `ml/evaluation/synthetic_m6/`.
- **Revisit when:** B01, B06, B08, and B10 are resolved.

### D-013 - Karaganda dates parse as M/D/Y

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** 87 709 Karaganda rows carry a second date field above 12 while the first field never exceeds 12, which fixes the order as month first.
- **Decision:** parse `created_date`, `updated_date` and `submission_date` with an explicit M/D/Y rule in the regional CSV adapter.
- **Alternatives:** default D/M/Y parsing, or per-row format inference.
- **Consequences:** two years of Karaganda history keep correct day and month. Inference was rejected because it is not deterministic across runs.
- **Evidence:** `adapters/regional_csv`, `data/reports/regional-csv-dq-report.json`.
- **Revisit when:** the source owner confirms or contradicts the export locale.

### D-014 - Turkestan collapses to one record per incident

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** the Turkestan export holds 98 876 rows over 52 050 distinct `incidentid` values. Repeats are lifecycle snapshots, not separate appeals.
- **Decision:** keep the row with the latest `updateddate` per `incidentid` and count the rest as deduplicated.
- **Alternatives:** treat every row as an appeal, or retain all versions as history.
- **Consequences:** any Turkestan metric computed without this step is inflated by roughly 47 percent. Version history is deferred until the source publishes a lifecycle contract.
- **Evidence:** 46 826 rows collapsed, recorded in `data/reports/regional-csv-dq-report.json`.
- **Revisit when:** B07 delivers a lifecycle event contract.

### D-015 - Pavlodar parts concatenate without deduplication

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** the two Pavlodar files share zero `id` values and both span 2020-02-09 to 2026-07-26, so the split is arbitrary rather than chronological.
- **Decision:** concatenate both parts into one regional stream.
- **Alternatives:** treat part 2 as a newer snapshot of part 1.
- **Consequences:** 666 634 Pavlodar records enter the canonical stream, which is 67.3 percent of the corpus. Region-weighted evaluation becomes mandatory.
- **Evidence:** identifier intersection of zero, verified over both files.
- **Revisit when:** the source explains the split.

### D-016 - Akmola column-shift rows are quarantined

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** the Akmola export has 180 lines with unescaped quotes. In 32 records the shift is visible because `creation_date` holds an organisation name fragment rather than a date.
- **Decision:** route those rows to quarantine with `SCHEMA_DRIFT_COLUMN_SHIFT` and never repair them heuristically.
- **Alternatives:** infer field boundaries and repair, or drop silently.
- **Consequences:** the canonical count is 990 000 rather than the 990 032 recorded in `DECISIONS_AND_BLOCKERS.md`. The difference is exactly these 32 rows.
- **Evidence:** `quarantine_reasons` in the data quality report.
- **Revisit when:** the source supplies a correctly escaped export.

### D-017 - Location normalization status is missing for nearly every record

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** coordinates are populated in 23 of 20 591 Kostanay rows and 264 of 98 876 Turkestan rows. The other five sources carry no coordinate columns.
- **Decision:** set `location.normalization_status` to `missing` unless a coordinate pair parses, and keep geocoding outside the ingest step.
- **Alternatives:** geocode addresses during ingest.
- **Consequences:** incident proposals rest on topic, service and time. Spatial clustering has no source and cannot be demonstrated as measured behaviour.
- **Evidence:** column fill rates in the data quality report.
- **Revisit when:** a geocoding service is approved or the source supplies coordinates.

### D-018 - Fine-tuning targets retrieval embeddings, not the intake classifier

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** a full pass over all eight exports confirms that no field holds citizen text. The only free text is written by the executor after closure, giving 14 397 unique documents, of which 72 percent exceed 40 characters and 3 150 exceed 150 characters.
- **Decision:** train embeddings for similar resolved case retrieval on that corpus. Keep the intake classifier on categorical features with a linear baseline until raw text arrives.
- **Alternatives:** wait for B02, train the classifier on weak service L1-L3 labels, or claim no fine-tuning at all.
- **Consequences:** the fine-tuning requirement is met on a corpus that actually exists. The absence of an intake classifier becomes a documented data request rather than an unexplained gap. This supersedes the routing model line in `DECISIONS_AND_BLOCKERS.md`.
- **Evidence:** corpus statistics in `data/reports/regional-csv-dq-report.json`, with a language split of 96.9 percent ru, 3.0 percent mixed and 0 percent kk.
- **Revisit when:** B02 delivers raw appeal text before 20 September.

### D-019 - Redacted corpus is versioned in the private repository

- **Date:** 2026-09-14
- **Status:** accepted
- **Context:** D-018 produced a 14 397 document corpus that every training and evaluation run depends on. Keeping it outside git made the retrieval results impossible to reproduce from a clone.
- **Decision:** version the redacted corpus, the 32 quarantine rows and the quality report. The repository is private and access stays limited to the team.
- **Alternatives:** keep the corpus out of git and distribute it by hand, or ship only hashes.
- **Consequences:** a clone reproduces retrieval evaluation without external files. The canonical stream stays ignored because 1.7 GB does not belong in git, which is a size decision and not a privacy one. B10 is still unresolved, so this data must not leave the private repository and must not appear in any public artifact.
- **Evidence:** residual PII scan over both files reports zero IIN, phone and email. Manifest at `ml/datasets/regional_retrieval_manifest.json`.
- **Revisit when:** B10 returns a legal basis and retention class, or the repository visibility changes.

### D-020 - Routing has no portable taxonomy across regions

- **Date:** 2026-09-14
- **Status:** accepted
- **Context:** leave-one-region-out over the seven regions shows that a model trained on six regions does not work on the seventh. Kostanay shares 94.4 percent of its topic names with the training regions yet scores 0.002 accuracy. Turkestan shares 82.9 percent and scores 0.005. Karaganda shares zero.
- **Decision:** treat the barrier to twenty regions as a taxonomy mapping problem, not a data volume problem. Report coverage per region and never present a single national routing number.
- **Alternatives:** train one national model and report its average, or wait for the remaining thirteen regions.
- **Consequences:** each region needs a versioned mapping from its own service catalogue onto a shared taxonomy before any cross-region claim holds. More data alone does not fix this.
- **Evidence:** `ml/evaluation/routing_v1/routing_report.json`, section `leave_one_region_out`.
- **Revisit when:** an authoritative shared service taxonomy arrives, or B01 delivers the remaining regions with their catalogues.

### D-021 - The routing ceiling without citizen text is measured, not assumed

- **Date:** 2026-09-14
- **Status:** accepted
- **Context:** a topic to service lookup reaches 0.573 accuracy on a temporal split inside each region. A logistic regression over topic, region, district, channel and time features reaches 0.588, which is 1.5 points better on accuracy and 0.02 points worse on macro F1.
- **Decision:** ship the lookup with backoff as the routing baseline and keep the linear model as the confidence source for the abstention threshold. Do not claim a modelling gain that the numbers do not support.
- **Alternatives:** present the model as the routing solution, or drop the model entirely.
- **Consequences:** the coverage curve becomes the product feature. At 30 percent coverage accuracy is 0.972, at 50 percent it is 0.809. The operator receives everything below the threshold, which makes human-in-the-loop a tunable setting rather than a slogan.
- **Evidence:** `ml/evaluation/routing_v1/routing_report.json`, sections `baselines`, `model` and `coverage_curve`.
- **Revisit when:** B02 delivers raw appeal text, which is the only input expected to move this ceiling.

### D-022 - Karaganda stays in the routing metrics with an explicit caveat

- **Date:** 2026-09-14
- **Status:** accepted
- **Context:** Karaganda is 99.9 percent deterministic from topic alone because the executor organisation is derived from the category. It contributes 14 percent of the test slice at 0.989 accuracy and lifts the aggregate by 6.7 points. Excluding it moves the model from 0.588 to 0.521.
- **Decision:** keep Karaganda in the reported metrics and publish both aggregates side by side, with and without it.
- **Alternatives:** exclude it from routing metrics, or report only the aggregate that includes it.
- **Consequences:** no number is hidden. A reader sees the inflated aggregate and the honest one in the same table, and can judge which applies to their region.
- **Evidence:** `per_region` in the routing report.
- **Revisit when:** new case data arrives and the region mix changes.

### D-023 - Fine-tuned retrieval embeddings beat both baselines by a measured margin

- **Date:** 2026-09-14
- **Status:** accepted
- **Context:** a frozen `multilingual-e5-small` loses to a character TF-IDF baseline on this corpus, scoring nDCG@10 of 0.3791 against 0.3932. Off-the-shelf multilingual semantics adds nothing to short clerical Russian text, which is what gives fine-tuning a measurable job.
- **Decision:** fine-tune the base model with MultipleNegativesRankingLoss on 7 466 pairs mined only from the training period, and report the gain against the lexical baseline rather than against the frozen model.
- **Alternatives:** ship the frozen model, ship lexical only, or claim the fine-tuning requirement without measuring it.
- **Consequences:** the ТЗ fine-tuning requirement is met with a number that survives scrutiny. nDCG@10 reaches 0.4086, which is 1.54 points above lexical and 2.95 above frozen. The honest headline is the smaller number, because the larger one compares the model to itself.
- **Evidence:** `ml/evaluation/retrieval_ft_v1/retrieval_finetune_report.json`, `ml/model_cards/retrieval_e5_small_ft_v1.json`.
- **Revisit when:** raw citizen text arrives, since queries in production are citizen texts while every query here is an executor text.

### D-024 - Retrieval stays hybrid because lexical wins the tail

- **Date:** 2026-09-14
- **Status:** accepted
- **Context:** the fine-tuned model leads on Recall@1 (0.4713 against 0.4625) and nDCG@10, yet trails marginally on Recall@10 (0.6925 against 0.6937). The gain is concentrated at the top of the ranking.
- **Decision:** keep lexical retrieval in the serving path permanently and fuse it with the dense ranking, rather than treating lexical as a fallback that a good enough model would retire.
- **Alternatives:** replace lexical with the dense model once it wins on the headline metric.
- **Consequences:** the operator sees a better first result from the dense side and keeps the recall of the lexical side. This confirms the existing locked decision that a lexical fallback always remains available, now with a measurement behind it.
- **Evidence:** per-system Recall@1 and Recall@10 in the fine-tune report.
- **Revisit when:** a reranker is added, which may change where each retriever contributes.

### D-025 - Trained weights are not versioned, the model card is

- **Date:** 2026-09-14
- **Status:** accepted
- **Context:** one checkpoint is 465 MB and is reproduced in about five minutes on CPU. The corpus, the pair mining and the split are all deterministic under a fixed seed.
- **Decision:** ignore `ml/evaluation/**/model/` in git and version a model card carrying the weight sha256, the training configuration, the split and every metric.
- **Alternatives:** commit the weights, or add Git LFS.
- **Consequences:** a clone reproduces the checkpoint from the corpus that is versioned. A reviewer can match any reported number to the exact weights that produced it without the repository carrying half a gigabyte per experiment.
- **Evidence:** `ml/model_cards/retrieval_e5_small_ft_v1.json`, field `weights.sha256`.
- **Revisit when:** a checkpoint has to be shipped to an environment that cannot retrain.

### D-026 - Load forecasting selects per region against a seasonal-naive baseline

- **Date:** 2026-09-15
- **Status:** accepted
- **Context:** rolling-origin backtest over the four regions with enough history. A ridge model on calendar and lag features beats seasonal naive on the two large high-variance regions (Pavlodar 19.9 percent lower MAE at a 7-day horizon, VKO 14.9 percent) and loses on the two smaller or shorter series (Karaganda, Turkestan), where seasonal naive is already strong.
- **Decision:** forecast each region with the method that wins its own backtest, and report both methods for every region. A model is used only where it beats the baseline it must beat.
- **Alternatives:** one national model, or the ridge model everywhere regardless of the backtest.
- **Consequences:** the situation centre reports a load forecast with a measured error against a reconstructible baseline, and never claims a modelling gain a region's data does not support. Three regions have too little history and are marked skipped rather than forecast weakly.
- **Evidence:** `ml/evaluation/forecast_v1/forecast_report.json`, sections `regions.*.backtest` and `summary`.
- **Revisit when:** new case data lengthens the short regions, or statsmodels ETS is added as a third candidate.

### D-027 - Surge detection is a robust residual, not a threshold on the count

- **Date:** 2026-09-15
- **Status:** accepted
- **Context:** raw daily counts have strong weekly rhythm, so a Monday is not a surge just because it exceeds a Sunday. The series is decomposed into a weekday-median seasonal, a centred rolling-median trend, and a residual.
- **Decision:** flag a surge when the residual exceeds k times the scaled median absolute deviation, with k of 4. This is the aggregate form of the incident concept, an emerging problem rather than a claim that two appeals are one event.
- **Alternatives:** a fixed daily threshold, or a mean-and-standard-deviation bound that outliers would inflate.
- **Consequences:** the manager view surfaces roughly 1 to 7 percent of days per region as surges, each with its residual size, and the top examples are real spikes such as Pavlodar on 2024-06-21 at 2355 appeals against a norm near 370. Detection quality is not yet validated against labelled incidents.
- **Evidence:** `regions.*.surges` in the forecast report.
- **Revisit when:** a labelled incident set exists to measure precision and recall.

### D-028 - The forecast is translated to operators per shift

- **Date:** 2026-09-15
- **Status:** accepted
- **Context:** a graph of appeals per day is not a decision. A supervisor needs a staffing number.
- **Decision:** convert the forecast to operators per shift using average handle time and a target occupancy, and mark both inputs as placeholders until the operator interview supplies real values.
- **Alternatives:** report only the appeal volume and leave staffing to the reader.
- **Consequences:** the number becomes actionable, for example Pavlodar's recent 339 appeals per day maps to about 5 operators per shift at a 6-minute handle time and 85 percent occupancy. The staffing figure is only as good as its two assumptions, which are stated in the report.
- **Evidence:** `regions.*.staffing_recent` and the `staffing` block in the forecast report.
- **Revisit when:** the operator interview returns a measured handle time and occupancy target.

### D-029 - One end-to-end scenario composes the three modules on real data

- **Date:** 2026-09-20
- **Status:** accepted
- **Context:** the three modules existed as separate scripts and reports. Judges reward one coherent working scenario over three separate metrics, and the product positioning is a single operational contour.
- **Decision:** ship `ml/training/demo_scenario.py`, which runs one appeal through routing, assist, surge and forecast, emitting a single trace where every downstream number comes from a real artifact. The intake free text is illustrative and labelled as such in the trace, because no citizen text exists (D-018). Everything after intake is real.
- **Alternatives:** keep the modules separate, or fake the whole flow with mock outputs for a smoother demo.
- **Consequences:** the demo has a spine. The default case is Pavlodar on 2024-06-21, a real surge day with 1819 water-supply appeals for a single topic. Routing returns 0.25 confidence and correctly sends the case to an operator, which demonstrates the abstention path rather than hiding it. The fine-tuned retriever returns three real resolved water-break cases. The manager view shows the surge and a 5-operators-per-shift staffing call.
- **Evidence:** `ml/evaluation/demo_v1/demo_trace.json`, reproducible from the canonical stream and the merged reports.
- **Revisit when:** raw citizen text arrives and the illustrative intake can be replaced by a real appeal.

### D-030 - Durable pilot path and verified identity boundary

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** M7 requires PostgreSQL durability and production access controls while B08 still blocks the selected identity provider and hosting profile.
- **Decision:** pilot/production profiles use PostgreSQL repositories for appeals and incidents, transactional audit/outbox writes, OIDC/JWKS validation, role and region scopes, and object-level report checks. Header identity is limited to local/development/test profiles.
- **Alternatives:** retain in-memory production state; trust identity headers at the reverse proxy; block all implementation pending provider selection.
- **Consequences:** the production boundary is fail-closed and Keycloak-compatible without selecting an unapproved provider. Local synthetic demos remain self-contained.
- **Evidence:** migrations `0008`-`0011`, `pulse109.security`, PostgreSQL integration tests, and security tests.
- **Revisit when:** B08 supplies the approved issuer, audience, claims, network and hosting profile.

### D-031 - Pre-submit duplicate evidence and reversible incident membership

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** the research requires duplicate warning before submission and reversible incident grouping without losing appeal identity.
- **Decision:** expose a non-mutating preflight endpoint with category, distance, time, lexical and semantic evidence; every membership decision is append-only and can explicitly remove then reconfirm a member. No candidate is merged automatically.
- **Alternatives:** search only after creating an appeal; hard-merge high-score pairs; mutate the prior membership row.
- **Consequences:** citizen/operator workflows can act on evidence while every appeal retains its identifier, history and SLA clock.
- **Evidence:** OpenAPI `preflightAppeal`, retrieval tests, incident event history, golden-flow E2E, and durable integration test.
- **Revisit when:** B04 provides approved pairs/groups and a production threshold policy.

### D-032 - Versioned policy records never invent an SLA

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** routing, confidence and SLA behavior need versioning, approval, effective dates and rollback, but B06 leaves the authoritative rules unavailable.
- **Decision:** persist immutable policy versions and review metadata; expose only active/effective versions. The synthetic routing/confidence policies are labelled local fixtures and SLA calculation remains disabled until an approved effective SLA policy exists.
- **Alternatives:** hard-code an assumed SLA; expose draft policy as active; omit policy provenance from assignment.
- **Consequences:** assignments retain policy provenance and missing policy remains visible rather than becoming a fabricated deadline.
- **Evidence:** migration `0009`, policy catalog API/tests, assignment validation, and rollback runbook.
- **Revisit when:** B06 is resolved by the policy owner.

### D-033 - Compatibility services and release evidence remain explicitly synthetic

- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** P1/P2 recommendations include Open311, Martin/MapLibre, MLOps tools and signed supply-chain evidence, while real source contracts, map hosting and signing authority are unavailable.
- **Decision:** provide an isolated Open311 sandbox, Martin-ready MapLibre source, tool-compatible offline exports, OTel instrumentation, dependency/SBOM CI gates and hash-indexed synthetic evidence. Do not claim a live adapter, production map, model promotion or signed release.
- **Alternatives:** invent regional credentials/endpoints; require external services for the offline demo; omit compatibility seams.
- **Consequences:** integration and operations mechanics are executable now and replaceable through stable boundaries; production claims stay gated by B01-B10.
- **Evidence:** `adapters/open311`, situation map, `synthetic_mlop`, security CI, runbooks and `release/evidence-index.md`.
- **Revisit when:** the first source, tile/geocoder infrastructure and release-signing owner are approved.

### D-034 - Preserve time provenance and scope idempotency to the region

- **Date:** 2026-09-23
- **Status:** superseded by D-036
- **Context:** M7 review found an invented received time in migration 0008, ambiguous status-event timestamps, and a global create idempotency receipt.
- **Decision:** received time and its quality are stored separately from observed time; missing or date-only time stays null. Status events state quality explicitly. Create receipts are region-scoped and transaction-locked; object access is checked before replay receipts are returned.
- **Alternatives:** backfill from observation time; infer exact quality from a timestamp; rely on unique-violation retry for concurrent requests.
- **Consequences:** SLA and analytics cannot mistake ingestion time for source time; concurrent retries get one response and cannot cross region boundaries.
- **Evidence:** OpenAPI and canonical schema changes, migration 0008, M7 durable-path and contract tests.
- **Revisit when:** source-specific time semantics are approved and integration tests run against the target PostgreSQL profile.

### D-035 - Fail closed for unapproved operational features and private data

- **Date:** 2026-09-23
- **Status:** accepted
- **Context:** the current retrieval, analytics and report providers are synthetic or process-local; the available regex does not safely remove names and addresses from arbitrary citizen text.
- **Decision:** pilot/production serves the durable manual path but returns `read_model_unavailable` for those demo endpoints. Operational intake requires an immutable source reference and configured legal basis and retention class; free text is not stored as a feature or passed to inference until an approved privacy gateway exists.
- **Alternatives:** present synthetic metrics as live data; treat regex masking as complete PII redaction; invent legal defaults.
- **Consequences:** several assistive features remain unavailable in the operational profile while the manual critical path can proceed with approved private storage and policy configuration.
- **Evidence:** profile gating tests, operational-intake tests, security review and `IMPLEMENTATION_STATUS.md`.
- **Revisit when:** B01, B02, B08 and B10 supply approved data, identity, redaction, storage and policies.

### D-036 - Withhold unapproved regional prose and historical model claims

- **Date:** 2026-09-23
- **Status:** accepted
- **Context:** review of the merged regional research artifacts found street addresses in the versioned retrieval corpus, raw source values in quarantine, timezone assumptions for naive dates, and `Recall@k` labels for query hit rates. B10 does not approve private-text processing or model quality claims.
- **Decision:** replace the corpus prose with a fixed withheld marker, remove source row values from quarantine, preserve naive and date-only time as non-instants, disable new corpus export and fail training/evaluation loaders on withheld text. Mark historical reports and the model card unverified, with query metrics labelled hit rate. Preserve existing Git history pending the repository owner's retention decision; this change does not rewrite published commits.
- **Alternatives:** rely on expanded regex masking; continue model training from the existing corpus; rewrite published Git history without a retention plan.
- **Consequences:** regional ML scripts no longer yield quality numbers from these artifacts. The manual operational path is unaffected. Historical blobs remain reachable in Git until a separate retention and history-remediation decision is executed.
- **Evidence:** `scripts/withhold_unapproved_corpus.py`, regional ingest and research-artifact gate tests, manifest/model-card status, and CI security scan.
- **Revisit when:** B10 approves a private source store, redaction process, legal basis, retention class, and independently reviewed evaluation split.

### D-037 — Governed ownership facts remain advisory

- **Date:** 2026-09-24
- **Status:** accepted
- **Context:** the supplied M8 Handoff Guard design requires ownership evidence without silently replacing regional systems or allowing an AI to assign a service.
- **Decision:** store regional organization, jurisdiction, asset and responsibility-rule facts as append-only effective versions with source and approval references. The assessment reads only approved, effective records for the appeal region and last human-confirmed service. It returns explicit ambiguity, time provenance and prior rejection evidence; only a human may execute a handoff.
- **Alternatives:** infer current ownership from free text; auto-assign the highest-ranked candidate; overwrite a rule in place.
- **Consequences:** operators can review candidate evidence even when ML and adapters are unavailable. Unapproved or absent catalog facts yield no candidate. A later command path must separately validate a confirmed handoff and record an idempotent receipt.
- **Evidence:** migration `0012_m8_ownership_catalog`, ownership engine and tests, OpenAPI assessment contract.
- **Revisit when:** approved regional ownership sources and handoff protocols are available.

### D-038 — Isolate inference behind a typed provider

- **Date:** 2026-09-24
- **Status:** accepted
- **Context:** the core imported the lexical model implementation directly although inference runs as a separate deployment boundary.
- **Decision:** manual-path classification calls an injected `InferenceProvider`; a named local lexical implementation preserves offline/test fallback. Pilot/production still fail closed before inference until an approved de-identified feature snapshot and remote provider are configured.
- **Alternatives:** keep model imports in both manual services; auto-fallback to local inference after remote failures.
- **Consequences:** model transport can change without changing appeal transactions. The provider boundary alone is not a complete Decision Gateway or an operational remote inference client.
- **Evidence:** `services/core/src/pulse109/decisions/inference_provider.py`, provider-injection test and existing manual-path E2E flow.
- **Revisit when:** B02/B08/B10 approve real features, privacy handling and operational inference.

### D-039 — Bind handoff outcomes to a durable assignment

- **Date:** 2026-09-24
- **Status:** accepted
- **Context:** handoff loop evidence must refer to a particular appeal assignment and cannot be inferred from free text or a model proposal.
- **Decision:** only an operator, supervisor or administrator can record accepted/rejected outcomes through an idempotent, region-scoped command. The assignment unit identifier must match the organization identifier until a governed organization/unit crosswalk exists. The outcome, timeline, audit, outbox and receipt commit together; evidence references are content addressed.
- **Alternatives:** infer rejection from status transitions; accept an unbound organization; record outcome without a timeline or audit event.
- **Consequences:** replayed commands return the same receipt and wrong-region requests cannot expose a receipt. Assignments without an organization-bound unit cannot yet record an outcome.
- **Evidence:** ownership outcome repository and API, contract/event catalog and PostgreSQL integration test.
- **Revisit when:** approved organization/unit mapping and regional handoff protocol are available.

### D-040 — Ask only policy-required intake questions

- **Date:** 2026-09-24
- **Status:** accepted
- **Context:** service-specific appeals need different evidence, while raw values and citizen text must stay outside a public planning seam.
- **Decision:** resolve one approved, effective regional service/topic policy and return kk/ru authored questions based only on known/missing/unknown field states. Missing states remain unknown; no inference fills them. The plan is advisory, versioned and bounded, with no raw values in its request or response.
- **Alternatives:** fixed universal form; LLM-generated questions; infer missing values from free text.
- **Consequences:** absent or conflicting policies yield an explicit unavailable state. Policy publication and conditional fields remain subsequent M8 work.
- **Evidence:** migration `0013_m8_intake_policy`, intake component, route, OpenAPI and integration tests.
- **Revisit when:** approved regional intake requirements, localized wording and evidence classes are supplied.

### D-041 — Decision Gateway needs explicit approved inputs

- **Date:** 2026-09-24
- **Status:** accepted
- **Context:** inference confidence and ownership suggestions must never become an autonomous routing decision. A missing required-field policy or ownership evidence from another appeal cannot be treated as valid evidence.
- **Decision:** keep the gateway a pure advisory evaluator. It accepts an approved effective confidence policy, explicit required-field states, and ownership evidence bound to the same appeal and version. Missing field policy yields `INSUFFICIENT_DATA`; mismatched ownership is discarded. All outcomes require human confirmation and never set an assignee.
- **Alternatives:** use model confidence as an assignment threshold; infer a complete field policy from an empty input; reuse ownership evidence by service alone.
- **Consequences:** the evaluator can be tested with synthetic evidence, but operational use awaits governed policy publication and approved feature snapshots.
- **Evidence:** `services/core/src/pulse109/decisions/gateway.py` and focused gateway tests.
- **Revisit when:** approved regional confidence thresholds, intake requirements and model validation evidence are available.

### D-042 — Jurisdiction evidence must agree at stated precision

- **Date:** 2026-09-24
- **Status:** accepted
- **Context:** an appeal may contain an exact jurisdiction ID, coordinates, asset reference, or a mixture. Boundary overlaps and coordinate uncertainty can make an apparently exact lookup unsafe.
- **Decision:** resolve only approved effective jurisdiction versions in the appeal region. Coordinate evidence needs complete coordinates and a bounded precision radius; one boundary must cover the full uncertainty shape. Supplied ID and coordinates must agree. Unknown, partial and conflicting evidence is flagged for human review and never causes assignment.
- **Alternatives:** use the point center alone; choose the first matching polygon; trust a source ID despite contradictory coordinates.
- **Consequences:** borderline appeals may need manual review. PostGIS tests exercise overlap and boundary behavior with synthetic geometries.
- **Evidence:** ownership repository/service and `tests/integration/test_m8_ownership_catalog.py`.
- **Revisit when:** approved regional geometry and precision conventions are supplied.

### D-043 — Bind confidence thresholds to the exact model artifact

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** a region-wide confidence threshold could be applied to an unrelated model or taxonomy and misrepresent its calibration.
- **Decision:** store append-only, approved and effective confidence policies keyed by region, model artifact SHA-256, taxonomy version and preprocessing version. The reader permits only one matching version and excludes synthetic policies in operational mode. The gateway verifies the same binding before using thresholds and withholds its confidence band when the policy is absent or mismatched. The catalog API shows confidence policies only from this typed table; older unbound `catalog.policy_version` confidence rows cannot drive runtime decisions or appear as current policy.
- **Alternatives:** one threshold for all models in a region; trust the model-supplied confidence band without a policy binding.
- **Consequences:** a new artifact or taxonomy requires its own reviewed policy. Operational use remains unavailable until a policy is approved and the feature snapshot is authorized.
- **Evidence:** migration `0014_m8_confidence_policy`, policy repository and gateway tests.
- **Revisit when:** approved model calibration evidence and regional publication workflow are available.

### D-044 — Publish confidence thresholds through independent review

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** artifact-bound confidence thresholds need a controlled path from proposal to effective use, with evidence that a second person reviewed the exact values.
- **Decision:** record immutable, region-scoped proposals with a canonical command digest and SHA-256 source reference. A different authenticated administrator or supervisor approves or rejects the digest. Approval atomically writes the immutable policy, review, audit and outbox; overlapping approved intervals are prohibited in PostgreSQL. Synthetic policies are rejected in operational profiles.
- **Alternatives:** direct edits to the confidence policy table; in-place approval flag; optimistic review without database constraints.
- **Consequences:** approval requires a future effective start and cannot silently replace an active policy. The regional taxonomy and real calibration evidence remain external inputs.
- **Evidence:** migration `0015_m8_confidence_publication`, publication API and PostgreSQL integration test.
- **Revisit when:** regional policy authority and production artifact registry are available.

### D-045 — Close only with appeal-bound evidence and a human command

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** an imported or regional status alone cannot prove that an appeal was resolved, and a closure must preserve every appeal's own history.
- **Decision:** preflight requires a recorded `resolved` state and validates content-addressed attachment references against the same appeal, region and current version without changing its status. A separate explicit operator confirmation atomically changes status, consumes the preflight, records the timeline and audit events, queues outbox delivery and stores an idempotent receipt. Any intervening appeal version invalidates the preflight. Resolved status alone never proves closure.
- **Alternatives:** close from source status; accept a free-form evidence URI; update status before recording audit.
- **Consequences:** closure requires an existing durable attachment reference and operator review. Evidence existence does not by itself attest to substantive resolution; the reason and decision remain accountable to the operator.
- **Evidence:** migration `0016_m9_closure_integrity`, closure API and PostgreSQL integration test.
- **Revisit when:** regional evidence classes and legally approved closure criteria are supplied.

### D-046 — Resolve the handoff assignment from the durable appeal

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** operators must not guess or manually enter an opaque assignment UUID before confirming a handoff outcome.
- **Decision:** expose the latest persisted assignment through a region-scoped, authenticated read route and feed that ID into the handoff panel. The panel disables outcome recording when no assignment exists and preserves the same idempotency key for a retry after an uncertain network result.
- **Alternatives:** UUID entry field; derive assignment ID from the appeal ID; submit outcome without assignment binding.
- **Consequences:** outcomes remain tied to a real assignment. A completed regional organization/unit crosswalk is still needed for broader operational handoff coverage.
- **Evidence:** latest-assignment API, operator panel, and manual-path integration assertion.
- **Revisit when:** a governed organization/unit crosswalk is approved.

### D-047 — Count recurrence only after verified closure

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** repeated reports at one infrastructure object can indicate failed resolution, but similar unclosed appeals may belong to one ongoing incident rather than recurrence.
- **Decision:** the read-only recurrence assessment requires a stable object ID, an exact business event time and a human-selected topic for the new appeal. It counts distinct prior confirmed incidents only when their current membership is confirmed, a matching appeal has an operator-confirmed closure preflight, and that closure precedes the new event within a bounded window. A closure within seven days signals possible failed resolution; three distinct verified incidents signal a recurring pattern. The result is advisory and requires human confirmation.
- **Alternatives:** count all related appeals; infer event time from row order; treat imported `closed` status as proof of resolution.
- **Consequences:** uncertain time, missing object or topic, and unverified closures produce abstention or no verified history. The assessment may undercount until regional asset IDs and evidence are reliable.
- **Evidence:** `pulse109.recurrence` read model and service, focused tests and PostgreSQL integration scenario.
- **Revisit when:** regional asset identity quality, incident closure semantics and approved recurrence thresholds are available.

### D-048 — Keep Replay Lab historical and non-promoting

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** rule and model changes need evidence before rollout, but historical observations cannot prove a counterfactual outcome and synthetic fixtures cannot establish model quality.
- **Decision:** replay only immutable, content-addressed, region-scoped snapshots with a small approved input-feature allowlist. Reject post-decision fields, non-finite values and cross-region cases. Exclude synthetic cases from all reported quality metrics. Keep labels outside predictor inputs, report descriptive baseline/candidate comparisons and prohibit promotion in the persistence schema.
- **Alternatives:** run candidate policies against live appeals; use outcome fields as inputs; include synthetic fixtures in accuracy; promote automatically on a better historical score.
- **Consequences:** the current engine is an offline comparison component, not a release controller. Production datasets, approved policy artifacts and representative labels are still needed.
- **Evidence:** `pulse109.replay`, migration `0017_m11_replay_lab` and focused deterministic tests.
- **Revisit when:** B02/B04/B05 provide approved snapshots and labels, and signed model artifacts exist.

### D-049 — Treat outcome memory as verified retrieval only

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** prior resolutions can help operators, but imported `closed` status, unowned evidence or post-decision fields would contaminate advice and intake training.
- **Decision:** eligible outcome records require a human-confirmed closure chain, appeal-owned content-addressed evidence, source provenance and a redacted classification. Retrieval is region/service/topic scoped, excludes the source appeal, uses controlled terms, labels synthetic data and abstains when no verified match exists. Outcome records are explicitly blocked from becoming intake features or autonomous replies.
- **Alternatives:** RAG over raw appeal text; direct use of status `closed`; treat prior resolutions as training input for the current intake decision.
- **Consequences:** this is a validated component boundary. A PostgreSQL reader must still assemble and verify the proof chain before operational retrieval is exposed.
- **Evidence:** `pulse109.outcome_memory` and focused eligibility tests.
- **Revisit when:** approved source corpus, redaction, taxonomy and legal retention rules are available.

### D-050 — Resolve regional unit IDs through approved organization mappings

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** regional assignments may carry a unit ID that is different from the canonical organization ID used by Handoff Guard. Treating them as equal blocks valid outcomes or invites arbitrary operator input.
- **Decision:** keep direct identity matching for existing assignments. Otherwise require one append-only, independently reviewed, effective regional mapping for the exact service and unit at assignment time, linked to an approved organization version. Synthetic mappings are excluded in operational profiles. Store the mapping ID with the outcome and its audit/event payload.
- **Alternatives:** trust an organization ID supplied with the outcome; fuzzy name matching; accept a mapping published after the assignment as retroactive proof.
- **Consequences:** unmatched units remain unavailable for outcome recording, and real crosswalk entries need approval before assignments use them. Existing direct-ID assignments remain compatible.
- **Evidence:** migration `0018_m8_unit_organization_crosswalk`, handoff repository and PostgreSQL integration scenario.
- **Revisit when:** the first regional unit directory and publication authority are supplied.

### D-051 — Select conditional evidence without intake values

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** different issue types need different evidence, and an approved policy may require a later field only after a prerequisite is known.
- **Decision:** extend the immutable intake policy payload with optional `when_states` predicates referencing earlier unconditional fields and a controlled `evidence_type`. Evaluate only trusted `known`/`missing`/`unknown` states. Inactive conditional fields are omitted from the question plan; an active missing field produces its authored question and evidence type. Reject unknown, forward or cyclic dependencies.
- **Alternatives:** inspect raw citizen answers to choose evidence; use arbitrary policy expressions; ask every possible field up front.
- **Consequences:** policies can adapt without backend code changes or PII in the planning seam. Conditions on categorical answer values and final attachment validation still require approved regional schema and storage rules.
- **Evidence:** adaptive intake service, PostgreSQL reader, OpenAPI response and focused tests.
- **Revisit when:** approved regional field taxonomy and evidence classes are provided.

### D-052 — Require supervised review of a repeated rejected handoff

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** the ownership assessment warned about prior rejection, but a manual assignment could still repeat the same organization without a reviewed reason.
- **Decision:** while locking the appeal for assignment, check recorded rejection for the proposed organization ID or one currently approved unit-to-organization mapping. Refuse the repeat with a conflict until a supervisor or administrator supplies a controlled override reason. Store the override in the appeal event, audit and outbox payload. Keep manual routing available when no organization identity can be established.
- **Alternatives:** silently permit repeated rejected routes; prohibit all reassignment; infer a target organization from a service name.
- **Consequences:** a rejected organization's repeat route becomes reviewable and idempotent. Unknown unit identity cannot be guarded until the regional directory is approved; role enforcement depends on the authenticated API boundary.
- **Evidence:** assignment service, OpenAPI command, route authorization test and PostgreSQL handoff integration scenario.
- **Revisit when:** an approved regional unit directory and supervisor escalation policy are supplied.

### D-053 — Bind offline replay receipts to immutable snapshot content

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** the replay schema stores manifest and report metadata, but a report ID alone cannot prove that the compared cases match the saved object.
- **Decision:** canonicalize pseudonymous snapshot bytes, verify their SHA-256 before storing them through an injected immutable object store, and persist the content address with the manifest. Report writes require the original typed dataset and verify its region, ID, cutoff, engine digest and content hash against the stored manifest. Reports remain descriptive and cannot be promoted.
- **Alternatives:** trust caller-supplied snapshot hashes; persist reports without checking dataset binding; store raw case snapshots in PostgreSQL.
- **Consequences:** a failed database write may leave an unreferenced immutable object for lifecycle cleanup. No operational run endpoint exists until approved datasets and policies are available.
- **Evidence:** Replay Lab persistence repository, focused tests and PostgreSQL integration smoke scenario.
- **Revisit when:** B02/B04/B05 provide approved representative snapshots and policy artifacts.

### D-XXX — Short title

- **Date:** YYYY-MM-DD
- **Status:** proposed | accepted | superseded
- **Context:** what forced the choice
- **Decision:** the selected behavior or design
- **Alternatives:** serious options considered
- **Consequences:** performance, security, migration and operations impact
- **Evidence:** benchmark, test, issue or contract reference
- **Revisit when:** explicit trigger, if any
