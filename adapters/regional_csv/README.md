# Regional CSV ingest adapter

Maps the seven provided regional exports onto
`contracts/canonical_request.schema.json` v1.0.0.

Standard library only. No pandas, no added dependency in `pyproject.toml`.

## Run

```bash
python adapters/regional_csv/src/pulse109_regional_csv/ingest.py \
  --src /path/to/exports \
  --out build/ingest
```

A full pass takes about 24 seconds on 1 036 858 input rows and produces:

| Output                   | Versioned | Note                                                |
| ------------------------ | --------- | --------------------------------------------------- |
| `canonical.jsonl`        | no        | 990 000 records, about 1.7 GB, regenerate on demand |
| `retrieval_corpus.jsonl` | yes       | 14 397 redacted executor texts, see D-019           |
| `quarantine.jsonl`       | yes       | 32 column-shift rows, scanned clean of PII          |
| `dq_report.json`         | yes       | aggregate counters only, no row content, no PII     |

The redacted corpus, the quarantine rows and the aggregate report are
versioned under `ml/datasets` and `data/reports`. Only the 1.7 GB canonical
stream stays out of git, for size rather than privacy. See D-019.

## Observed result

```
input 1 036 858  ->  canonical 990 000
  Turkestan lifecycle snapshots collapsed   46 826
  Akmola column-shift rows quarantined          32
```

The independent count of 990 000 differs from the 990 032 recorded in
`DECISIONS_AND_BLOCKERS.md` by exactly the 32 quarantined Akmola rows.

## Source families

| Region     | Family       | Rows in | Identifier           | Free text |
| ---------- | ------------ | ------- | -------------------- | --------- |
| Pavlodar   | appeals      | 666 634 | `id`                 | none      |
| Karaganda  | karaganda    | 143 954 | absent, synthesized  | none      |
| Turkestan  | incidents    | 98 876  | `incidentid`         | none      |
| VKO        | applications | 83 385  | `application_number` | `com_exp` |
| Kostanay   | incidents    | 20 591  | `incidentid`         | `result`  |
| Almaty obl | applications | 19 912  | `application_number` | `com_exp` |
| Akmola     | akmola       | 3 506   | `request_number`     | none      |

Karaganda carries no request identifier at all. Every Karaganda record receives
a synthetic id derived from the row content and is flagged
`SYNTHETIC_SOURCE_ID`. Deduplication and joins inside that region are not
possible until the source supplies a key.

## Encoded decisions

See `docs/DECISION_LOG.md` entries D-013 through D-018. In short:

- Karaganda dates parse as M/D/Y. 87 709 rows prove the American order.
- Turkestan collapses by `incidentid` to the latest `updateddate`.
- Pavlodar parts concatenate. They share zero identifiers.
- Akmola column-shift rows are quarantined, never repaired by heuristic.
- `location.normalization_status` is `missing` for nearly every record.
  Coordinates exist in 23 of 20 591 Kostanay rows and 264 of 98 876 Turkestan rows.

## What the data does not contain

No citizen text in any of the eight files. The only free text is written by the
executor after closure. Pure Kazakh is absent: 96.9 percent of records are
Russian, 3.0 percent mixed, 0.1 percent unknown, and zero are `kk`.

This is the evidence behind the request to the data owner for raw appeal text
and a frozen Kazakh test set.

## PII handling

Redaction runs before anything is written, not after. The pass over the real
exports flagged 10 IIN and 93 phone numbers inside executor free text, plus
22 347 street values and 6 499 name values in VKO columns.

Direct identifiers never reach the canonical record. Addresses become opaque
tokens salted from `PULSE109_TOKEN_SALT`, which must come from the secret store
in any environment other than local development.
