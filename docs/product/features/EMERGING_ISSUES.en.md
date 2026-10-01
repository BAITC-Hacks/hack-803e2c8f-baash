[Русский](EMERGING_ISSUES.md) · [English](EMERGING_ISSUES.en.md) · [Қазақша](EMERGING_ISSUES.kk.md)

# Emerging Issues Radar

## The problem it solves

A hotline routes against a taxonomy that already exists. A city problem can
appear before a category for it does. Reports arrive saying the water smells
odd, tastes metallic, looks cloudy after repairs, and a classifier scatters them
across water quality, water supply, other and manual review. Nobody sees that
they are one thing.

## What it reports

That a group of reports arrived close together and fits the existing taxonomy
poorly. Not what caused it. The radar has no way to know that, and a system that
says "the water is contaminated" on this evidence is guessing with the city's
trust.

## How it works

`POST /v1/discovery/scans` reads a recent window for one region and links
reports that are close in three measured ways:

| Signal   | Weight | Source                                     |
| -------- | ------ | ------------------------------------------ |
| geo      | 0.45   | recorded coordinates, great-circle metres  |
| time     | 0.30   | business time, only when it exists         |
| taxonomy | 0.25   | operator decision topic, when one was made |

Linking uses single link agglomeration. A developing city problem spreads along
a street or a pipe, so its reports form a chain rather than a ball, and single
link follows a chain. It is deterministic and needs no numerical library, so the
radar stays available on the CPU-only fallback path.

A signal that cannot be measured for a pair is removed from the denominator
rather than scored as zero, so an unmeasurable signal never masquerades as a
measured mismatch.

## What novelty is, and what it is not

Novelty measures how poorly one report fits what the taxonomy already knows: a
report sent to manual review, or routed with low confidence, or carrying no
topic at all. It gates whether a cluster is worth an alert.

It takes no part in linking. Scoring novelty between two reports made any two
unusual reports look related, and a lighting report duly joined a water cluster
a kilometre away. That defect was found by looking at a cluster on screen and is
covered by a regression test.

## Thresholds are policy

`DiscoveryPolicy` carries the window, the distances, the minimum cluster size
and the minimum cohesion and novelty. A supervisor has to be able to make the
radar quieter or louder without a release, and every stored cluster keeps the
policy snapshot that produced it, so a reviewer can reconstruct an alert months
later.

## Identity

A cluster id is derived from its member set, so rescanning the same reports
returns the same cluster rather than renaming it underneath a reviewer.

## What a human does

Promotion to an incident happens on the incident endpoint. The radar records
that it happened. It cannot open work by itself, and the review endpoint refuses
a promotion that does not name an incident a human already created.

## Blocked

The semantic signal is designed and not connected. No regional export carries
the citizen's own words (blocker B02), so a scan reports
`semantic_status: unavailable, CITIZEN_TEXT_ABSENT`. When text arrives, the
embedding term plugs into the same weighted affinity.
