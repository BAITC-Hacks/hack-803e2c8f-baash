# Presenter card

One scenario, four to five minutes, plus a minute of Data Lab. Hold this open on
a second screen. Everything in bold is a click. Everything in quotes is what to
say, shortened to what fits in one breath.

Before you start: `uv run python scripts/demo_runtime.py verify`. It checks the
environment, runs the whole API path and leaves a clean city behind.

---

## 0. Opening, 20 seconds

The **Operations center** is already on screen.

> "Pulse 109 turns scattered citizen appeals into detected city problems,
> coordinates who resolves them, checks the result and learns from confirmed
> outcomes."

Point at the badge, top right.

> "The municipal records here are synthetic. The application, PostgreSQL, the
> outbox, the worker and the audit trail are real. Everything you are about to
> see goes through them."

---

## 1. The city right now, 30 seconds

Point at the counters, then at the chart.

> "Open appeals, active incidents, emerging patterns. These are counts of
> records, not estimates."

Hover the red point on the activity chart.

> "That is the busiest hour, with its topic breakdown. The chart counts only
> appeals whose business time we can trust, and it says underneath how many it
> left out. We do not put a date-only record into an hour bucket."

---

## 2. Detect, 60 seconds

Press **Run scan**.

> "The radar looks for reports that arrived close together in space and time and
> fit the existing taxonomy poorly."

When the result appears, read the line above the counters.

> "It reports its own state. It also says the semantic signal is not running,
> because no regional export contains the citizen's own words. We are not
> pretending a category code is what somebody wrote."

Open the emerging pattern. **Кластер**.

> "Six reports, about two hundred metres apart, over forty minutes. Here is how
> the arrivals built up, the signals that linked them, and the languages they
> came in."

The sentence that matters here:

> "The radar says a group of similar reports appeared. It does not say what
> caused it. Naming a cause is a human act."

---

## 3. Coordinate, 60 seconds

Press **Создать инцидент из кластера**.

> "A human promotes it. Nothing merges automatically, and every appeal keeps its
> own identifier, timeline and clock."

The war room opens.

> "One incident as one city problem: where the reports fall, who owns it, what
> was done about comparable problems, and what can be done next."

Point at the footprint.

> "This is the spread of the reports we received. Calling it an impact area
> would claim something about people who never reported anything."

Point at **Подтверждённые похожие случаи**.

> "Six comparable outcomes, human-confirmed closures with evidence. Marked
> synthetic in their own provenance, so nobody can quote them as model quality."

Point at one suggestion and read its reason codes aloud.

> "Every suggestion names the rules that fired and the artefacts behind them.
> It recommends. The operator decides."

---

## 4. Act and verify, 60 seconds

Confirm the assignment, then let the delivery state update.

> "The command is durable. It enters a transactional outbox, a worker claims it
> with a database lease, and the adapter returns a receipt. In this environment
> that adapter is a deterministic replay, not a live municipal system, and the
> external identifier says so."

Attach evidence and close.

> "Closure checks the evidence before it accepts the close. That is what makes
> the outcome usable later."

---

## 5. Understand, 45 seconds

Open **Лаборатория данных**.

> "Six quality dimensions, not one score. A single number does not tell anyone
> what to fix."

Point at the funnel and the largest drop.

> "That is where work stalls."

Press **Обращения за этой цифрой** on any figure.

> "And this is the part that matters. Every aggregate opens into the appeals it
> was computed from. It is not a dashboard you read and trust. It is analytics
> you can walk into."

---

## If somebody asks about models

Open **Replay Lab**.

> "Before a routing change ships, we replay it against approved history and
> compare it with what the human actually decided. Look at this report: forty
> eight cases present, zero evaluated, because every one of them is synthetic
> and synthetic traffic never contributes to a model quality claim. Real numbers
> need an approved historical sample, which we do not have yet."

That is the answer. Do not try to make Replay Lab the centre of the demo: the
persisted report keeps aggregate metrics only, and the interface says so.

---

## If somebody asks what happens without AI

Stop the inference container.

```bash
docker compose -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.demo.yml stop inference
```

> "The recommendation goes unavailable and says so. Creating an appeal, routing
> it by hand, assigning it, changing status and closing it all keep working.
> The critical path never depends on a model."

---

## Answers to keep short

**"Is this real data?"**
No. The records are synthetic and labelled. The workflows are real.

**"Does it detect contamination?"**
No. It detects that an unusual group of reports appeared. A person decides what
it is.

**"Is the AI accurate?"**
We have not validated any model. What runs in the demo is a lexical baseline,
and it says so on screen with its confidence. Routing quality needs the raw
appeal text, which no export we were given contains.

**"Is it scanned for malware?"**
The scanner is a mock. Calling it antivirus would be false. Production needs an
approved scanner.

**"Why are the CI checks red on this repository?"**
The mirror cannot start Actions because of an organization billing lock. The
same four jobs pass on the development repository, and the README links a run.
