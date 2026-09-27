# Outcome Memory

## What it stores

Not that a case was closed, but how it was resolved and whether the resolution
held: the taxonomy codes, the actions taken, the evidence, the time to
resolution, the closure verification, and whether it was reopened or recurred.

## What qualifies

Only a human-confirmed closure with valid evidence. A status arriving from a CRM
does not qualify, because it records that somebody marked a ticket closed, not
that the problem was fixed. The provenance chain is enforced in the model: a
closure id, a preflight id, a confirming actor digest, at least one piece of
content-addressed evidence, and a confirmation that cannot precede the operator
decision.

## What it shows

When a comparable problem appears, the war room shows how many verified
outcomes exist, what was done in them, the median time to resolution and how
many went thirty days without recurrence.

It never says "do X". It shows the record and lets an operator draw the
conclusion.

## No text crosses this boundary

Retrieval uses controlled taxonomy terms only. Free text, names, locations and
identifiers are rejected by the model validators, so the memory cannot become a
back door around the privacy boundary.

## Current state

Wired into the war room and answering.

Production retrieval still refuses to yield candidates, correctly. It needs an
approved corpus, a verified evidence timestamp, a controlled retrieval-term
mapping and a retention approval, none of which exist. Waiting for those would
leave the capability invisible, and a capability nobody can see is one nobody
can judge.

The demo profile therefore mounts a separate reader over the closures the demo
itself produced through the real closure workflow, human-confirmed and
evidence-backed. They pass the same model validators production retrieval would
face, and every record carries `data_classification: synthetic` with an explicit
`DEMO_SYNTHETIC_OUTCOME_CORPUS` label in its own provenance. The reader refuses a
caller that has not accepted synthetic data.

These records are a demonstration corpus. They must never appear in a production
model-quality claim.

## One number the demo cannot show

Resolution time. The seeding script records the decision and the confirmed
closure within the same second, so the duration is an artefact of how the demo
was built rather than a fact about resolving anything. Any gap under a minute is
reported as unknown instead of zero, because a median of zero hours would be a
lie dressed as a metric.
