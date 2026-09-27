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

Wired into the war room and abstaining, because the demo has no verified
closures yet. The section reports `abstained, NO_COMPARABLE_VERIFIED_OUTCOME`
rather than an empty list, so an operator can tell an empty corpus from a
retrieval that never ran.
