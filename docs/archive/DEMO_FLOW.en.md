[Русский](DEMO_FLOW.md) · [English](DEMO_FLOW.en.md) · [Қазақша](DEMO_FLOW.kk.md)

> Historical document. This is not a source of truth for the current project state.

# Demo flow, Mock Demo Day #2

> **Superseded planning draft — not a runnable walkthrough.** This document
> describes proposed panels, a demo-state selector and regional-data claims that
> are not present in the current running application. Use the verified
> [demo runbook](../DEMO_RUNBOOK.en.md) and [feature-status matrix](../FEATURE_STATUS.en.md)
> for Mock Demo Day. Do not present this draft's claims as live behavior.

Format requested by the organisers: no slides. Show the working MVP live, say
what runs today, what is still being built, and what comes next.

Slot: 28 or 29 September, 17:00 for Gov cases. Online.

The whole walkthrough is one page. Every panel below exists in
`apps/web/app/page.tsx` and is served by the live stack, not by a mockup.

---

## 0. Pre-flight, 20 minutes before the call

```bash
make up          # Compose profile from infra/compose
make migrate     # forward-only Alembic chain
```

Then open the web app and confirm three things before anyone joins:

1. The page renders and the language switch toggles **ru / kk**.
2. The demo-state selector is visible and set to `ready`.
3. `make dq-report` prints without error, so the data path is alive.

If Compose does not come up, go straight to the fallback in section 5. Do not
debug Docker while the jury watches.

---

## 1. What runs today, said in one sentence

> Обращение проходит весь контур: приём, определение владельца, решение с
> порогом уверенности, инцидент, закрытие с проверкой доказательств. Всё, что
> вы увидите, работает на реальных выгрузках семи регионов.

Then stop talking and start clicking.

---

## 2. The walkthrough, panel by panel

The panels appear on the page in this order. Follow it top to bottom.

### 2.1 Intake

Submit an appeal. Show the bilingual form and the adaptive questions: the form
asks only what changes the routing decision, not a fixed questionnaire.

Say out loud, once: **the citizen free text is illustrative, because the
supplied exports contain no citizen text.** Everything after intake is real.
This is the first line of our data request to the organisers.

### 2.2 Situation centre

Regional service overview. Show the surge and the load forecast.

Concrete number to name: Pavlodar, 21 June 2024, **2355 appeals in one day
against a norm near 370**, of which **1819 were a single water-supply topic**.
That is a real infrastructure event found in the data, not a synthetic example.

Say that the forecast method is chosen per region by backtest, and that the
model wins two regions while seasonal naive wins two. We do not claim a model
gain a region's data does not support.

### 2.3 Ownership and handoff

Show owner recommendation and the Handoff Guard. The point: the system proposes
an owner, a human confirms, and the handoff is guarded so an appeal cannot fall
between two organisations.

### 2.4 Incident topology

Show how separate appeals become one municipal incident, and that every citizen
keeps an individual request id and SLA. This is the product differentiator:
ten calls about one burst pipe become one job for the service, not ten.

### 2.5 Replay Lab

Show a replay inspection. This is how a policy or model change is checked
before it reaches production: old versus new decisions on the same appeals.

### 2.6 Closure integrity

Show that a closure requires clean evidence. A case cannot be closed by
assertion.

---

## 3. Show it breaking, on purpose

This is the strongest part of the demo and most teams will not have it. Use the
demo-state selector to switch states live:

| State              | What the jury sees                              | What to say                                                                |
| ------------------ | ----------------------------------------------- | -------------------------------------------------------------------------- |
| `low_confidence`   | routing hands the case to an operator           | the abstention path, human-in-the-loop as a threshold rather than a slogan |
| `ml_unavailable`   | the contour keeps working without ML            | no requirement depends on the model being healthy                          |
| `stale_catalog`    | stale service catalogue is surfaced, not hidden | the system refuses to route on data it knows is old                        |
| `sync_retry`       | outbox retry after an external system fails     | an appeal is not lost when the regional system is down                     |
| `forbidden_region` | access denied across a region boundary          | region scoping is enforced, not decorative                                 |

Pick two. `low_confidence` and `sync_retry` are the most legible in a short
slot.

---

## 4. What is honestly not finished

State this before the jury asks. It reads as maturity, and every item is an
open external dependency rather than a gap we hid.

- **No citizen text in the data.** The routing ceiling without it is measured:
  a lookup table reaches 0.573 accuracy, a model 0.588. The gap closes only
  with raw appeal text, which is our first request to the organisers.
- **No portable taxonomy across regions.** Leave-one-region-out: a model
  trained on six regions scores 0.002 on Kostanay even though 94.4 percent of
  topic names match. The barrier to twenty regions is service-catalogue
  mapping, not data volume.
- **No Kazakh in the corpus.** 96.9 percent ru, 3.0 percent mixed, zero pure
  kk. Bilingual evaluation needs a frozen test set from the organisers.
- **No coordinates.** Filled in 0.1 to 0.3 percent of rows, so incident
  grouping runs on topic, service and time. Geo clustering waits on real
  address or coordinate data.
- **No live regional integration.** The adapter contract is implemented and
  exercised by a replay adapter. A real sandbox is request number four.

---

## 5. Fallback if the stack does not start

Do not debug live. In order of preference:

1. **Recorded walkthrough.** Record the full flow the evening before and keep
   the file locally, not in cloud storage.
2. **Evidence run.** `make release-evidence` and `make dq-report` produce real
   output in the terminal. Showing the pipeline produce numbers live is still a
   live demo.
3. **Say it plainly.** "The environment is not starting on this machine, here
   is the recorded run and here is the repository." A stack that fails with a
   recorded backup costs nothing. A stack that fails while you debug it on
   camera costs the slot.

---

## 6. Timing

A short slot is enough for six panels if nobody narrates architecture.

| Minutes     | Section                                 |
| ----------- | --------------------------------------- |
| 0:00 – 0:30 | one sentence on what runs               |
| 0:30 – 3:30 | panels 2.1 to 2.6                       |
| 3:30 – 4:30 | two failure states                      |
| 4:30 – 5:30 | what is not finished, and the four asks |
| rest        | questions                               |

The four asks, in priority order: raw appeal text, the remaining thirteen
regions **with their service catalogues**, a frozen kk/ru test set, and one
regional sandbox with an architect contact.
