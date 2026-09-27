# Start Here

> Historical bootstrap guide. Its milestone instructions are superseded by the
> [current documentation index](../README.md) and [feature matrix](../FEATURE_STATUS.md).

## Is the original specification enough

It is strong architecture documentation, but it should not be used as one giant implementation prompt. It describes both the first pilot and the national target state, contains dependencies that only the organizers can resolve and leaves implementation sequencing to the reader.

This kit converts it into an executable workflow for Codex.

## How to use the kit

1. Put the contents of this kit in the root of a new or existing Git repository.
2. Keep `AGENTS.md` in the repository root so Codex loads the durable project rules automatically.
3. Start Codex from the repository root and give it the text in `START_CODEX_PROMPT.md`.
4. Let the first run complete M0 and produce a reviewable plan and scaffold.
5. Continue milestone by milestone. A separate chat or worktree per milestone is preferable once the repository exists.
6. Add real datasets only under an access-controlled path outside Git. Commit manifests, schemas and anonymized fixtures, never production PII.

## Files to give Codex

- `AGENTS.md`: short durable repository rules.
- `CODEX_IMPLEMENTATION_HANDOFF.md`: implementation order and engineering decisions.
- `DECISIONS_AND_BLOCKERS.md`: what is fixed, unknown and safe to assume.
- `ACCEPTANCE_MATRIX.md`: evidence required to finish each milestone.
- `contracts/`: executable OpenAPI, JSON Schema, events and ADRs.
- `docs/`: the complete technical specification and rendered architecture.

## What not to do

- Do not paste only the 40-page PDF into an empty chat and ask to build everything.
- Do not ask for all modules in one unreviewed diff.
- Do not claim model quality before raw text, labels and a frozen test set exist.
- Do not let a mocked regional integration silently become the production integration.
- Do not store real appeal payloads in Git, prompts, logs or screenshots.
