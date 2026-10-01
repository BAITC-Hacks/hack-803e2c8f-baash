[Русский](OPERATIONS_CENTER.md) · [English](OPERATIONS_CENTER.en.md) · [Қазақша](OPERATIONS_CENTER.kk.md)

# Operations Center

## The question it answers

Not "how much work is there", which a dashboard of totals answers, but "where
does the city need attention right now", which is what a supervisor actually
has to decide.

## Shape

`GET /v1/operations/attention-feed` returns two things.

**City pulse**: counters of records. Open appeals, active incidents, emerging
patterns, incidents without an owner, queued and failed deliveries. Each is a
count, never an estimate.

**Attention feed**: a ranked list where every item names a target that can be
opened. A signal with nowhere to go is noise, and noise trains people to stop
reading the screen.

| Kind               | Raised by                                      |
| ------------------ | ---------------------------------------------- |
| `emerging_cluster` | an open or under-review cluster from the radar |
| `unowned_incident` | active past the threshold with no service      |
| `adapter_lag`      | the oldest undelivered outbox entry            |
| `closure_review`   | closed appeals carrying no evidence            |

## Severity is reproducible

Derived from counts and age, never from a model. A supervisor can reproduce the
ordering by hand, which is the property that makes a triage screen trustworthy.

## Counters and feed say different things

A counter reports state. The feed reports what crossed a threshold. One unowned
incident can therefore show in the counter while the feed stays quiet, and the
empty-feed text says exactly that rather than claiming nothing is happening.

## Nothing here detects anything new

Clusters come from the radar, stuck deliveries from the outbox, unowned
incidents from the incident table. The value is ranking and routing.
