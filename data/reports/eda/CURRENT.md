# Canonical dataset exploration

Dataset `synthetic-m1-accepted`, 3 records.
Content hash `f1b73dd22f6ca957…`, generated 2026-09-27T12:45:12.887293+00:00.

**This dataset is synthetic.** No figure here describes a real city.

## Provenance

| Field | Value |
| --- | --- |
| Rows | 3 |
| Schema versions | 1.0.0 |
| Mapping versions | synthetic-source/1.0.0 |
| Adapters | synthetic-crm |
| Regions | ALA, AST |
| Earliest received | 2026-09-10T10:00:00+05:00 |
| Latest received | 2026-09-10T10:00:00+05:00 |

> Regions in this dataset cover different periods. Comparing raw volume between them is not meaningful without the per-region coverage below.

## Data quality by region

Six dimensions rather than one score, because a single number does not
tell anyone what to fix.

| Region | Rows | Coverage | completeness | timeliness | uniqueness | schema_conformity | consistency | provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALA | 1 | 2026-09-10 … 2026-09-10 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| AST | 2 | — … — | 0.0% | 0.0% | 100.0% | 100.0% | 0.0% | 100.0% |

### Look here first

Dimensions below 95 percent, weakest first.

- `AST` · completeness · 0.0%
- `AST` · timeliness · 0.0%
- `AST` · consistency · 0.0%

## Arrival patterns

Hour and weekday counts use only records whose business time can be
trusted. The trusted share is stated so a reader knows how much of the
region these charts actually describe.

| Region | Trusted rows | Trusted share | Observed days | Mean per day | Busiest hours |
| --- | --- | --- | --- | --- | --- |
| ALA | 1 | 100.0% | 1 | 1.0 | 10 |
| AST | 0 | 0.0% | 0 | — | — |

## Distributions

### Received time quality

- `exact` · 1 · 33.3%
- `date_only` · 1 · 33.3%
- `missing` · 1 · 33.3%

### Channels

- `web` · 1 · 33.3%
- `import` · 1 · 33.3%
- `phone` · 1 · 33.3%

### Languages

- `kk` · 1 · 33.3%
- `mixed` · 1 · 33.3%
- `ru` · 1 · 33.3%

### Statuses

- `new` · 1 · 100.0%

## Limits

- This is observational exploration of historical exports. Nothing here establishes cause. A difference between two regions is a difference in what was recorded, which may be a difference in the city, in the process or in the export.
- Regions cover different periods. Raw volume must never be compared between them without reading the coverage column beside it.
- Counts that depend on the hour or the weekday use only records whose business time is trustworthy. The trusted share is stated per region.
- No citizen text exists in these exports (B02), so nothing here describes what people actually wrote.
