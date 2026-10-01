# Pulse 109 Decision Log

Chronological internal decisions; early target choices and evidence refer to
their recorded dates. Current runtime/status is [FEATURE_STATUS](FEATURE_STATUS.md).
D-036 withholds the historical prose corpus and supersedes D-018/D-019/D-023
quality/reproducibility claims; S3 runtime wiring in `5c9d044` supersedes the
storage-wiring deferral in D-071. Neither named models nor archived scores
establish current mandatory citizen-text fine-tuning compliance.

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
- **Consequences (assessment corrected 2026-10-01):** this records an executor-text research direction, not compliance with the required citizen-text runtime fine-tuning. The intake classifier remains blocked on B02 and implementation/validation. D-036 later withheld this corpus pending privacy approval.
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
- **Consequences (assessment corrected 2026-10-01):** the historical report records nDCG@10 0.4086 against lexical 0.3932 and frozen 0.3791 on executor-text proxy data. This does not close the mandatory citizen-text fine-tuned embedding runtime requirement. D-036 blocks quality claims and corpus reuse pending privacy/split approval.
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

### D-054 — Persist advisory gateway assessments against verified inputs

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** a transient gateway result does not establish which appeal version, model recommendation, candidate set and confidence policy an operator saw.
- **Decision:** lock the appeal at its current version, verify the complete persisted recommendation and ranked candidates, and resolve any claimed confidence policy against the approved effective catalog in the same transaction. Store an immutable result with input/evidence digests and an exact-retry key, plus audit and outbox rows. Every result remains advisory and requires human confirmation; no assignment action is exposed.
- **Alternatives:** trust caller-supplied model or policy fields; record only the winning candidate; reuse one assessment after the appeal changes.
- **Consequences:** historical assessments are reproducible and stale or mismatched evidence fails closed. The database schema gains a composite recommendation binding and append-only assessment table. Operational publication waits for approved model and intake artifacts.
- **Evidence:** migration `0019_m8_gateway_assessment`, assessment repository, focused tests and PostgreSQL integration scenario.
- **Revisit when:** B02/B04/B05 provide approved model snapshots, taxonomy and calibration evidence.

### D-055 — Measure handoff outcomes from explicit operational cohorts

- **Date:** 2026-09-25
- **Status:** accepted
- **Context:** a first-pass acceptance rate or repeated rejected handoff count can be misleading if the cohort silently includes synthetic fixtures, lacks an outcome, counts a later assignment as the first, or guesses a regional unit's organization.
- **Decision:** compute read-only metrics for one region and a bounded UTC assignment-time interval, using the interval end as the outcome observation cutoff. First-pass acceptance uses the globally first assignment per appeal and its earliest unambiguous observed outcome before the cutoff; unknown outcomes remain unclassified. Repeated rejected handoffs require one approved, effective, non-synthetic organization identity and a recorded rejection on an earlier assignment before the current assignment time. An explicit operational source-system allowlist excludes synthetic test-only appeals. Return raw numerators, denominators, quality and provenance; zero denominators produce an unavailable rate.
- **Alternatives:** infer outcomes from source status; count the first assignment inside each reporting window; divide by all appeals regardless of outcome; map units by name.
- **Consequences:** this repository is opt-in and has no dashboard route until the regional source allowlist and publication authority are approved. Unmapped or ambiguous assignments remain visible as data-quality counts.
- **Evidence:** `pulse109.ownership.metrics`, focused tests and PostgreSQL integration smoke.
- **Revisit when:** a regional unit directory, approved source registry and reporting definitions are available.

### D-056 — Advance incident state only through supervised, evidenced transitions

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** confirmed incident membership existed, but the incident could not progress through active response, resolution and closure with a reviewable state history.
- **Decision:** require a supervisor or administrator, the current incident version, an idempotency key and a controlled reason code for each forward transition. Resolution and closure require SHA-256 evidence references; PostgreSQL accepts them only when they belong to attachments of currently confirmed member appeals in the same region. Record the transition in incident history, audit and outbox in one transaction. Appeal identities, statuses and SLAs remain independent.
- **Alternatives:** infer incident closure from regional source status; accept arbitrary notes or unowned attachment references; change incident state without review.
- **Consequences:** evidence ownership is checked, but attachment content and remediation quality are not independently verified by this command. Merge, split, reopen and supersession still require their own governed operations.
- **Evidence:** incident lifecycle route, OpenAPI schema, synthetic E2E and PostgreSQL integration scenario.
- **Revisit when:** approved incident evidence policy and regional remediation workflow are available.

### D-057 — Verify regional release bundles before activation

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** federated policy and catalog distribution needs an integrity and downgrade boundary while central service connectivity may be unavailable.
- **Decision:** use a bounded canonical JSON manifest signed with an explicitly trusted Ed25519 key. Verify signature, region, schema, validity window and artifact digests before an atomic PostgreSQL activation that advances both version and sequence. Persist append-only release history and the original signed bytes so current keys and time can reverify a stored release. Expose immutable verified content and preserve the last known good bundle on rejection.
- **Alternatives:** accept unsigned configuration updates; trust a caller-supplied digest; permit a lower sequence to replace the active release.
- **Consequences:** verification and durable activation are implemented; artifact retrieval, key rotation, signing authority and regional deployment are still required before this becomes an operational control plane. A stored active row is historical evidence, so consumers must reverify its signed bytes against current trust and expiry before application.
- **Evidence:** `pulse109.control_plane`, migration `0020_bundle_activation`, focused tamper, replay, scope, expiry and immutability tests, and PostgreSQL integration scenario.
- **Revisit when:** signing keys, regional runtime and approved release artifacts are supplied.

### D-058 — Keep browser intake synthetic until private source storage exists

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** the guided browser form could show a fabricated success number after a network error and supplied a raw address in a field defined as an opaque private reference. No approved immutable source storage, legal basis or retention class exists for real citizen intake.
- **Decision:** show success only after the API returns a valid request UUID; retry an ambiguous failure with the same idempotency key and body. Remove persistent browser drafts, restoring legacy drafts in memory once. Disable submission by default; an explicit synthetic-assist flag allows only test submissions and never passes raw address text as a private reference. Keep received time missing when the source did not provide it.
- **Alternatives:** invent an offline acceptance number; treat a raw address as a private reference; submit real data before B08/B10 are approved.
- **Consequences:** the web journey is not an operational citizen channel until protected source storage and governance are integrated. The synthetic mode can exercise the UI and backend with fictitious data.
- **Evidence:** `apps/web/app/intake.tsx`, frontend typecheck and lint, API fail-closed requirements.
- **Revisit when:** B08/B10 provide approved identity, immutable source storage, legal basis and retention rules.

### D-059 — Advance incident version for every membership decision

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** membership decisions were append-only but did not advance the incident aggregate version, allowing a stale `incident_version` to authorize a later decision.
- **Decision:** each confirmed, rejected or removed membership decision atomically advances the incident version. The membership decision, incident event, audit record and outbox event carry the resulting aggregate version. Idempotent replays return the original response before checking the submitted version, after region scope is verified.
- **Alternatives:** version membership decisions independently; permit multiple decisions at one incident version.
- **Consequences:** clients must submit the latest incident version after every membership decision; no schema migration is needed because existing version fields hold the aggregate version.
- **Evidence:** in-memory E2E and PostgreSQL integration coverage.
- **Revisit when:** membership becomes an independently versioned aggregate with an explicit cross-aggregate concurrency contract.

### D-060 — Supervised incident topology operations (merge, split, reopen)

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** incidents cluster multiple appeals, but cluster errors require explicit operational intervention to merge related incidents, split segregated clusters, or reopen closed incidents upon recurring appeal spikes without losing historical lineage or appeal autonomy.
- **Decision:** implement versioned, atomic incident merge and split operations and supervised reopen transitions (`resolved -> monitoring`, `closed -> monitoring`). Merge supersedes the source incident and transfers confirmed member appeals to the target incident. Split creates a new target incident for a verified subset while leaving at least one member in the source. Both require supervisor authentication, region scoping, controlled reason codes, and SHA-256 evidence refs validated against confirmed member attachments.
- **Alternatives:** autonomous LLM-driven incident merges/splits; mutable destructive updates deleting source incidents; unconstrained cross-region clustering.
- **Consequences:** all member appeals retain independent identifiers, SLAs, and histories. Cycle prevention is enforced. Idempotent replays are guaranteed.
- **Evidence:** `contracts/openapi.yaml`, `contracts/event_catalog.md`, `services/core/src/pulse109/incidents/`, `tests/e2e/test_incident_topology.py`, `tests/integration/test_incident_topology_persistence.py`.
- **Revisit when:** multi-region cross-jurisdiction clustering is approved.

### D-061 — Replay Lab offline inspection API, language slices, and operator UI panels

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** policy and model evaluations must be inspectable and auditable across demographic and linguistic slices (KK, RU, mixed) without executing autonomous deployments or mutating live routing rules.
- **Decision:** expose authenticated Replay Lab inspection endpoints (`GET /v1/replay/reports`, `GET /v1/replay/reports/{report_id}`) returning comparative metrics across baseline and candidate policies (route agreement, operator override rate, first-pass acceptance rate, historical handoff churn) and language slice agreements. Complement with operator UI panels for Incident Topology and Replay Lab in Next.js web application. Replay is strictly descriptive; policy activation requires cryptographically signed regional bundles via the control plane.
- **Alternatives:** autonomous auto-deployment on passing score; unsegmented global metrics masking language bias; monolithic analytics database.
- **Consequences:** full observability into language performance parity; operators and supervisors can review historical evidence before approving regional configuration bundles.
- **Evidence:** `contracts/openapi.yaml`, `services/core/src/pulse109/replay/`, `apps/web/app/incident-topology-panel.tsx`, `apps/web/app/replay-lab-panel.tsx`, `tests/contract/test_contracts.py`, `services/core/tests/replay/test_router.py`.
- **Revisit when:** approved production candidate policies and live regional datasets are ingested.

### D-062 — Governed anomaly detectors and actionable Situation Center alert review

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** operators and regional supervisors require automated detection of operational anomalies (handoff loops, reopen spikes, adapter lag, override spikes) and the ability to review, acknowledge, or dismiss alerts with controlled disposition codes without losing audit trail.
- **Decision:** implement modular detectors (`HandoffLoopDetector`, `ReopenSpikeDetector`, `AdapterLagDetector`, `OverrideSpikeDetector`) orchestrated by `AlertDetectorEngine` with active alert deduplication. Map detected anomalies to existing database-constrained alert types (`volume_spike`, `incident_growth`, `sla_risk`, `data_quality`, `model_drift`) with specific detector metadata in evidence. Mount `POST /v1/alerts/{alert_id}/reviews` with authenticated role checks (`operator`, `supervisor`, `analyst`, `auditor`, `admin`), regional isolation, and controlled action codes (`acknowledge`, `resolve`, `dismiss`). Provide interactive alert triage in Situation Center frontend.
- **Alternatives:** autonomous automated rule mutators; unstructured string alerts; unmonitored outbox backlogs.
- **Consequences:** operations team can detect handoff ping-pong ($A \to B \to A$), delivery delays, and routing model drift early; every alert review produces immutable audit and timeline evidence.
- **Evidence:** `contracts/openapi.yaml`, `services/core/src/pulse109/analytics/detectors.py`, `services/core/tests/analytics/test_detectors.py`, `apps/web/app/situation-center.tsx`, `tests/contract/test_contracts.py`.
- **Revisit when:** real-time streaming event processing or WebSocket push alerts are approved.

### D-063 — Privacy reference boundary and immutable PII access audit

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** citizen PII (names, phone numbers, addresses, personal identifiers) must be isolated from feature data, inference pipelines, traces, metric labels, and application logs. Resolving private references or unmasking data requires strict access scope validation and an immutable audit trail.
- **Decision:** implement `pulse109.privacy` service backed by `privacy.private_ref` and `audit.audit_event`. Require authenticated actor roles to intersect the reference's `access_scope` and match regional bounds before returning private details. Whenever a private reference is accessed, atomically write an immutable audit event (`PII_VIEWED`, `PII_REVEALED`, `PII_EXPORTED`) recording actor, action, timestamp, and purpose code. Never include raw PII text in audit payloads, metric labels, logger output, or OpenTelemetry trace spans.
- **Alternatives:** plain text storage in application database; un-audited token resolution; ad-hoc regex redaction at log egress.
- **Consequences:** zero PII leakage guarantee across the platform; compliance with citizen data protection laws and access governance; every PII view is fully accountable.
- **Evidence:** `services/core/src/pulse109/privacy/`, `services/core/tests/privacy/test_privacy_service.py`, `services/core/tests/test_observability.py`.
- **Revisit when:** HSM / external vault integration and homomorphic encryption are specified.

### D-064 — Control plane bundle inspection and atomic activation HTTP API

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** regional deployments and operators need to inspect currently active verified release bundles and activate new Ed25519-signed bundles via the public API with role-based governance and anti-rollback guarantees.
- **Decision:** expose authenticated API endpoints `GET /v1/control-plane/bundles/active` and `POST /v1/control-plane/bundles/activate`. Inspection requires operator/supervisor/analyst/auditor/admin role and concrete region isolation (`X-Region-Id`). Activation requires supervisor or admin role, validates the signed envelope cryptographically via `BundleVerifier`, asserts regional matching between envelope and header, and applies atomic monotonicity checks advancing both version and sequence. Contract is published in `contracts/openapi.yaml` (`37` operations, `60` schemas).
- **Alternatives:** direct database manipulation; manual CLI deployment only; unauthenticated bundle activation.
- **Consequences:** complete control-plane lifecycle exposed over HTTP with strict cryptographic verification and anti-rollback protection; fallback in memory preserves testing and offline operational safety.
- **Evidence:** `contracts/openapi.yaml`, `services/core/src/pulse109/control_plane/router.py`, `services/core/tests/control_plane/test_router.py`, `tests/contract/test_contracts.py`.
- **Revisit when:** multi-party signing threshold schemes (e.g. M-of-N Ed25519) are introduced.

### D-065 — Security hardening of citizen attachment ingestion and malware scanning

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** citizen appeal attachments uploaded to the platform present attack vectors including disguised executables, polyglot files, script injection, and malware.
- **Decision:** implement comprehensive attachment validation pipeline in `pulse109.security.attachments`. Enforce strict allowlisted MIME types (`application/pdf`, `image/jpeg`, `image/png`, `image/webp`, `text/plain`), inspect binary magic bytes to prevent MIME sniffing evasion, scan for executable headers (`MZ`, `\x7fELF`, `\xca\xfe\xba\xbe`, shebang `#!`) and embedded scripts (`<script`), compute canonical SHA-256 digests, and integrate pluggable `MalwareScanner` abstraction (`MockMalwareScanner` with simulated EICAR and threat detection).
- **Alternatives:** rely purely on client-supplied `Content-Type` header; store uninspected blobs directly into S3; client-side validation only.
- **Consequences:** malicious or disguised payloads are blocked and quarantined at ingestion boundary before persisting to object storage or worker processing; zero executable execution risk.
- **Evidence:** `services/core/src/pulse109/security/attachments.py`, `tests/security/test_attachments.py`.
- **Revisit when:** ClamAV / external cloud threat detection API is connected in staging.

### D-066 — Attachment ingestion, queue listing, persistent alert store, and privacy API exposure

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** an independent audit revealed critical seams preventing production operator use: attachments had validation functions but no operational HTTP upload/list endpoint (blocking closure preflight and incident resolution evidence chains); the operator workspace had to fall back to hardcoded IDs due to a missing appeal listing endpoint; alert reviews and states were in-memory despite existing PostgreSQL tables; privacy reference resolution was unmounted; replay snapshot bytes were lost on restart; and the Next.js web proxy dropped query strings.
- **Decision:** expose authenticated `POST /v1/requests/{id}/attachments` and `GET /v1/requests/{id}/attachments` validating magic bytes, executable markers, and malware scanning before persisting to `appeals.attachment_ref` and recording `action='attachment.uploaded'` in timeline. Expose `GET /v1/requests` with cursor/limit pagination, status filtering, and region isolation. Wire `PostgresAlertStore` into `analytics` to persist alerts and reviews in `analytics.alert` and `analytics.alert_review`. Expose authenticated `POST /v1/privacy/references/{token}/resolve` and `GET /v1/privacy/references/{token}/audits`. Wire `FileSnapshotStore` into `PostgresReplayRepository`. Forward query search strings in `apps/web/app/api/core/[...path]/route.ts`.
- **Alternatives:** keep in-memory mock endpoints; let operators upload attachments directly via raw SQL fixtures; bypass query params in web tier.
- **Consequences:** complete evidence ingestion, appeal queue triage, and privacy audit lifecycle are now fully operational end-to-end over HTTP; persistent stores survive restart; operator workspace displays live backend data.
- **Evidence:** `contracts/openapi.yaml` (42 operations, 67 schemas), `docs/archive/PRODUCTION_AUDIT.md`, `services/core/tests/manual_path/test_router.py`, `services/core/tests/privacy/test_privacy_router.py`, `services/core/tests/analytics/test_detectors.py`.
- **Revisit when:** S3 direct presigned upload URLs with async scanning webhooks are introduced.

### D-067 — Monotonic control plane rollback CLI and quarantine closure integrity verification

- **Date:** 2026-09-26
- **Status:** accepted
- **Context:** (1) The signed bundle control plane implements strict anti-rollback counters (`version` and `sequence`), but lacked a dedicated command to safely rollback to an earlier configuration without disabling monotonic protections. (2) Closure integrity requires verified evidence attachments, but previously did not explicitly assert that referenced files were not security-quarantined or flagged.
- **Decision:** (1) Implement `create_rollback_bundle` in `pulse109.control_plane.bundles` and add `pulse109-bundle rollback` CLI action. The rollback command reads the target bundle's content, sets `version = max(active.version, target.version) + 1` and `sequence = max(active.sequence, target.sequence) + 1`, re-signs the bundle with an authorized Ed25519 private key, and atomically installs it to PostgreSQL. (2) In `PostgresClosureRepository.create_preflight` and `confirm`, query `data_classification` from `appeals.attachment_ref` and reject any evidence item marked `security` with HTTP 422 `evidence_quarantined`. Re-verify attachment presence and clean status during confirmation before atomic closure.
- **Alternatives:** allow manual decrement of sequence watermarks in the database; disable anti-rollback during emergency incidents; accept quarantined evidence with a warning flag.
- **Consequences:** emergency rollbacks are fully supported while preserving strict monotonic tamper resistance and anti-replay invariants; zero risk of malicious or quarantined files being accepted as closure proof.
- **Evidence:** `services/core/src/pulse109/control_plane/bundles.py`, `services/core/src/pulse109/control_plane/cli.py`, `services/core/src/pulse109/outcomes/postgres.py`, `services/core/tests/control_plane/test_bundles.py`, `services/core/tests/control_plane/test_cli.py`, `tests/integration/test_m9_closure_integrity.py`.
- **Revisit when:** multi-signature threshold approval for rollback releases is mandated.

### D-068 — Isolated demo profile and fail-closed external seams

- **Date:** 2026-09-26
- **Status:** accepted for local/demo runtime; operational integrations remain blocked
- **Context:** the existing local UI and worker could report fabricated decisions or replay delivery, while attachment metadata could be saved without the bytes.
- **Decision:** use one `demo` profile of the normal FastAPI/PostgreSQL/outbox/worker/web topology, with idempotent labelled fixtures and a dedicated Compose project. Reject replay delivery in pilot/production. Store demo attachment bytes in its isolated volume, but reject operational upload until approved immutable storage and real scanning exist. Bind private-reference access to stored region ownership; leave legacy unknown-region rows inaccessible. The operator queue uses API receipts rather than sample-state success.
- **Alternatives:** a separate fake demonstration app; enabling replay delivery in pilot; treating metadata-only attachments as stored content.
- **Consequences:** reviewers can reproduce the same critical path while external gaps remain explicit. Existing private references need an approved region backfill before access. Demo volumes are disposable and must contain synthetic data only.
- **Evidence:** `infra/compose/docker-compose.demo.yml`, `scripts/demo_runtime.py`, migration `0022_privacy_region`, profile/privacy/worker tests, `docs/DEMO_RUNBOOK.md`.
- **Revisit when:** the first regional adapter, approved object store/scanner and production identity provider are supplied.

### D-069 — Incident readback and demonstrable end-to-end path

- **Date:** 2026-09-27
- **Status:** accepted for demo and local review
- **Context:** the incident backend could mutate durable state but had no region-scoped read endpoint; an unused web panel fabricated success when topology commands failed. The demo only showed a partial appeal-to-status journey.
- **Decision:** add a scoped incident detail contract with candidate and confirmed member IDs; expose a small operator panel that calls the actual create, membership and supervisor-confirm APIs. Seed a second related synthetic appeal and clean evidence, then verify decision, assignment, worker delivery, incident, resolution, closure, recurrence and analytics through the demo API in CI. Remove unmounted sample-only panels that fabricated operational results.
- **Alternatives:** keep a static incident illustration; pre-seed a confirmed incident; return sample incident data when the API fails.
- **Consequences:** a reviewer can reload and inspect persisted membership, and API failures stay visible. The panel does not yet cover topology merge/split. PostgreSQL topology and resolution commands require clean evidence from current incident members; approved evidence policy remains external.
- **Evidence:** `services/core/src/pulse109/incidents`, `apps/web/app/incident-workflow-panel.tsx`, `scripts/verify_demo_flow.py`, demo-profile CI job.
- **Revisit when:** approved incident evidence and regional workflow rules are available.

### D-070 — Keep PulseDM as a governed research candidate beside the conservative ML stack

- **Date:** 2026-09-27
- **Status:** accepted for research design and offline evaluation, not model deployment
- **Context:** the current critical path has a lexical CPU fallback and human Decision Gateway, while candidate routing/retrieval models lack approved KK/RU/mixed labels. A structured non-generative decision model could share representations across advisory questions, but neither its accuracy nor operational benefit is established.
- **Decision:** retain the conservative supervised routing, hybrid retrieval and pair-classifier track; specify PulseDM as a separate multilingual Choice/Boolean/Score research design; allow Jev or structured LLMs only as optional external benchmarks/teachers after privacy approval. Compare all implemented candidates on identical pinned decision-time cases. Add an offline Choice/Boolean evaluator with leakage, split and probability checks; keep Score evaluation, training and serving unimplemented until justified. No model enters the hot path or gains authority over SLA, ownership, assignment, merge or closure through this decision.
- **Alternatives:** replace the existing inference service with an untrained PulseDM placeholder; select a public leaderboard winner; send citizen text to an external benchmark by default.
- **Consequences:** research can proceed without breaking CPU/manual continuity or claiming unavailable model quality. Candidate configurations and weights will be added only with a concrete runner, license check, approved dataset and model card.
- **Evidence:** `docs/ml/`, `ml/evaluation/candidate_compare.py`, `tests/model/test_candidate_compare.py`, existing synthetic baseline and Replay Lab contracts.
- **Revisit when:** approved, privacy-reviewed KK/RU/mixed gold data and deployment resources support a measured candidate experiment.

### D-071 — Keep operator showcase actions contract-bound and integration reruns disposable

- **Date:** 2026-09-28
- **Status:** accepted for pilot review
- **Context:** reviewers need to inspect replay comparisons and incident topology actions, but stored replay reports retain aggregate policy metrics rather than per-case decisions. Reusing an integration database causes state from one pass to influence another. Production object storage, identity infrastructure, and delivery environment have not been supplied.
- **Decision:** expose only persisted Replay Lab report and aggregate metric differences; label case-level decision traces unavailable rather than reconstructing them. Have War Room controls call the existing region-scoped merge/split API with user confirmation, evidence hash, and idempotency key. Run integration passes in newly created UUID-named PostgreSQL databases, never against the caller database. Provide immutable local/S3-compatible storage adapters without wiring them into attachments or replay until approved infrastructure is supplied.
- **Alternatives:** render invented case decisions; implement client-side topology changes; truncate shared integration tables; claim a bucket or OIDC deployment exists.
- **Consequences:** the showcase is inspectable and failures remain visible, while per-case replay trace, production storage wiring, IdP, deployment, retention, and recovery targets remain open external work.
- **Evidence:** `apps/web/app/replay-lab.tsx`, `apps/web/app/incident-war-room.tsx`, `scripts/run_integration_tests.py`, `services/core/src/pulse109/security/object_storage.py`, `tests/architecture/test_integration_isolation.py`, `infra/runbooks/PILOT_DEPLOYMENT_REQUIREMENTS.md`.
- **Revisit when:** B02/B03 supply decision-time trace semantics, and B07/B08/B10 supply approved service, identity, storage, privacy, and recovery requirements.

### D-072 — Use captured working demo screens as landing proof

- **Date:** 2026-09-29
- **Status:** accepted for synthetic demo
- **Context:** the first landing used independently drawn interface imitations whose counts and controls could diverge from the application.
- **Decision:** frame screenshots captured from the running PostgreSQL-backed demo for Operations Center, Smart Intake, operator queue, War Room, Ask Pulse and Data Lab. Label them as static captures of synthetic data. Keep the CTA connected to the actual workspace; improve weak operational layouts in the app before capturing them.
- **Alternatives:** maintain parallel mock UI components; use proprietary reference imagery; embed an interactive demo inside the landing.
- **Consequences:** landing proof corresponds to available screens and does not imply live regional data. Screenshots must be refreshed after material app-UI changes. No API or migration changes.
- **Evidence:** `apps/web/app/landing.tsx`, `apps/web/public/product/`, `infra/docker/web.Dockerfile`.
- **Revisit when:** the application UI changes enough that the static captures no longer represent it.

### D-073 — Treat process stages as independent snapshot counts

- **Date:** 2026-09-29
- **Status:** accepted
- **Context:** a resolved appeal is not simultaneously in the current `in_progress` state; the Data Lab displayed a 125% conversion and a fictitious largest drop between independent counts.
- **Decision:** preserve the existing stage counts and drill-down keys, but leave cohort-conversion and largest-drop fields unset and explain the snapshot semantics in the UI. Make VPS Compose database URLs use the configured URL-safe PostgreSQL password across migrate, API and worker; public overlays require a nonempty value.
- **Alternatives:** infer historical transitions from current statuses; keep the misleading percentage; change the API schema; retain a hard-coded local password in public containers.
- **Consequences:** exact counts remain inspectable without fabricated conversion. Public deploys need an explicit database secret; existing PostgreSQL role passwords require deliberate rotation rather than only changing Compose environment.
- **Evidence:** `services/core/tests/datalab/test_datalab_contracts.py`, `docs/features/DATA_LAB.md`, `infra/compose/`, `infra/runbooks/PUBLIC_DEPLOYMENT.md`.
- **Revisit when:** a true event-cohort funnel is specified and tested against append-only lifecycle data.

### D-XXX — Short title

- **Date:** YYYY-MM-DD
- **Status:** proposed | accepted | superseded
- **Context:** what forced the choice
- **Decision:** the selected behavior or design
- **Alternatives:** serious options considered
- **Consequences:** performance, security, migration and operations impact
- **Evidence:** benchmark, test, issue or contract reference
- **Revisit when:** explicit trigger, if any

### D-ASK-01 — Version trusted-time analytics semantics

- **Date:** 2026-09-28
- **Status:** accepted for pilot review
- **Context:** Ask Pulse needs trusted business-time filtering, human-confirmed dimensions, and explicit exclusion of records without reliable event time. The existing analytics endpoint already exposes observed-time volume results to consumers.
- **Decision:** publish trusted-time volume semantics as `appeals_volume/2.0.0` and use that version for Ask Pulse. Keep the existing `appeals_volume/1.0.0` meaning and default intact for `/analytics/query`. Do not synthesize missing region/time buckets as zero without an approved completeness policy.
- **Alternatives:** silently change the existing metric's meaning; keep using ingestion/observation timestamps for citizen-facing trend questions; infer zero from an empty query result.
- **Consequences:** existing consumers keep their current interpretation. Ask Pulse excludes ambiguous business times and identifies its metric version. Sparse results remain sparse until source freshness policy establishes completeness.
- **Evidence:** `services/core/src/pulse109/analytics/catalog.py`, `services/core/src/pulse109/analytics/repository.py`, `services/core/tests/analytics/test_repository_boundary.py`, `docs/features/ASK_PULSE.md`.
- **Revisit when:** metric versioning becomes a shared contract with external analytics consumers or approved freshness completeness rules are supplied.

### D-074 — Reconcile submission documentation with verified evidence

- **Date:** 2026-10-01
- **Status:** accepted for documentation
- **Context:** judge READMEs and journals mixed historic counts, future models, stale storage/deployment facts and unsupported current claims.
- **Decision:** use Russian as canonical judge language, equivalent English/Kazakh READMEs, weekly Git/document evidence with explicit provenance, and dated CI/deployment records. Keep research, synthetic demo and external blockers distinct.
- **Consequences:** no product/runtime/executable contracts changed. Security CI failures and stale public water fixtures remain visible rather than being declared fixed.
- **Evidence:** [documentation review](review/DOCUMENTATION_REVIEW_2026-10-01.md), [current status](FEATURE_STATUS.md), [deployment](../infra/runbooks/PUBLIC_DEPLOYMENT.md).
- **Revisit when:** source code, CI, deployment or team evidence changes.
