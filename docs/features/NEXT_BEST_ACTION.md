# Next Best Action

## What it is

Deterministic rules over one war room snapshot. Each suggestion names the codes
that fired and the artefacts a reviewer can open.

## Why rules and not a model

Every suggestion has to survive the question "why did you propose that", asked
months later by somebody auditing a decision. A rule answers with the codes that
fired and the evidence behind them. A learned scorer, on this data volume and
with no labelled corpus of good operator moves, answers with a number nobody can
check. When such a corpus exists, the rules become its baseline.

## The proposals it may make

| Action              | Fires when                                                 |
| ------------------- | ---------------------------------------------------------- |
| `review_owner`      | the resolver has a candidate                               |
| `resolve_ambiguity` | ownership is ambiguous                                     |
| `avoid_handoff`     | the record shows loop risk                                 |
| `expand_incident`   | candidate members are pending                              |
| `request_evidence`  | a confirmed incident has nothing attached                  |
| `escalate_unowned`  | it has been active past the policy threshold with no owner |

The set is closed. A suggestion outside it cannot be produced.

## Confidence

A band, not a probability, derived from how many independent supports the record
holds. Three or more is high, two is medium, one is low. A band says how much
the record backs the proposal, which is what it can honestly say.

## Decision preview

Before a handoff, the preview compares candidate targets on recorded facts: the
ownership rules that matched, rejections that already happened, comparable
verified outcomes that exist. Its `basis` field is literally
`recorded_facts_only`, because calling it a forecast would claim knowledge
nobody has.

## The boundary

This module recommends. The Decision Gateway and the human authorize. Every
suggestion carries `advisory_only: true`, and nothing here can issue a command.
