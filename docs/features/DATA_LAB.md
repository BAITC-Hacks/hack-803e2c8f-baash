# Urban Intelligence / Data Lab

## The problem it solves

A dashboard tells a supervisor a number. It does not tell them whether to
believe it, what it leaves out, or which cases produced it. On a service that
routes citizen reports, a figure nobody can trace is a figure that will be
misused.

## Three levels

```
Data Lab              offline exploration of approved historical datasets
Operations analytics  what the live platform looks like right now
Drill-down            from any figure to the appeals behind it
```

## Offline exploration

`make eda` runs `analytics.offline.report` over a canonical dataset and writes
`CURRENT.md` and `CURRENT.json`. It is reproducible by construction: the same
file produces the same report, and the report records the content hash of what
it read, so two runs can be compared honestly.

Real records never enter the repository. The default target is the committed
synthetic fixture. Point `INPUT` at an approved dataset outside the repo for the
real thing.

```bash
make eda INPUT=/secure/data/canonical.jsonl OUTPUT=/secure/reports/eda
```

Every report opens with its provenance: rows, schema versions, mapping versions,
adapters, regions and the period each one covers. Two notes are generated rather
than written by hand, when the data warrants them: that the regions cover
different periods, and that no record carries citizen text.

## Data quality as dimensions

Six ratios per region, each with its numerator, denominator and definition:
completeness, timeliness, uniqueness, schema conformity, consistency and
provenance.

Not one score. A region at 72 percent could be missing addresses, carrying
unmapped statuses, or reporting times nobody can trust, and those are three
different problems with three different owners.

"Look here first" lists only dimensions below 95 percent. A section with that
heading which opens at a hundred percent has already taught the reader to skim
past it.

## Trust travels with the chart

Any count that depends on the hour or the weekday uses only records whose
business time is trustworthy, and the trusted share is stated beside it. Putting
a date-only record in an hour bucket places it in a moment nobody observed,
which is how a plausible chart becomes a false one.

## Percentiles, not averages

`time_to_first_decision` and `time_to_first_assignment` report P50, P75, P90 and
P95 over appeals with a trustworthy received time. An average is dominated by
the easy cases and hides exactly the ones an operations manager is judged on.

Percentiles are nearest-rank, so every value reported is a value some case
actually had.

## Drill-down is the point

Every aggregate carries a key. `GET /v1/datalab/drilldown?key=...` returns the
appeals behind it.

```
timeliness 90%
      ↓
quality:timeliness
      ↓
demo-109-light-002 · received_at_quality = missing
```

The key is matched against a closed mapping in the service and never reaches SQL
as text. An analytics filter is exactly where somebody would try to reach the
database, and there is a test for each hostile key shape.

## Explain this metric

`GET /v1/datalab/definitions` states, for each metric, its numerator,
denominator, time basis, what is included and what is excluded. Every definition
must say what it leaves out, and a test enforces that.

## Data quality reaches the attention feed

When the share of trustworthy business times in a region falls below the floor,
the operations center raises `BUSINESS_TIME_QUALITY_LOW` with a drill-down key.
A feed that reports on incidents while the records underneath them decay gives a
supervisor confidence they have not earned.

## What this does not claim

Nothing here establishes cause. A difference between two regions is a difference
in what was recorded, which may be a difference in the city, in the process or in
the export. The reports say so in their own limits section.
