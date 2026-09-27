# Replay Lab

## The problem it solves

Changing a routing model or a policy normally means train, deploy and hope. On a
service that routes citizen appeals, hope is not an acceptable release process.

## The loop

```
candidate
   ↓ replay approved historical traffic
compare against the current baseline
   ↓ inspect the decisions that changed
slice by region and language
   ↓ shadow
canary proposal
   ↓ authorized human approval
signed control plane activates the artefact
```

There is no "deploy automatically" anywhere in it.

## Decision diff

The unit a reviewer reads is one changed case: what the current system
recommended, what the candidate recommends, and what the human actually decided.
That third column is what turns a difference into an improvement or a
regression, and it is why replay runs against approved historical cases rather
than synthetic traffic.

## Honest metrics only

Report what can be computed from the replayed set: human agreement, abstention
rate, and the slices where the candidate is worse. A candidate that improves
overall while getting worse on short Kazakh texts has to show that, because the
aggregate would hide it.

## Current state

The backend, snapshots and persistence are implemented, and CI reconciles a
replay report against its snapshot. The decision diff review screen is the
outstanding piece, and `docs/FEATURE_STATUS.md` is the authority on that line.
