[Русский](DEVELOPMENT_HISTORY.md) · [English](DEVELOPMENT_HISTORY.en.md) · [Қазақша](DEVELOPMENT_HISTORY.kk.md)

# Pulse 109 development history

Timeline of the complete retained `main` history, checked on October 1, 2026 through `e494390`. This is change history; [FEATURE_STATUS](../submission/FEATURE_STATUS.en.md) defines the current state. Work before September 12 is described in the [Camp journal](../submission/PROJECT_JOURNAL.en.md); no Git commits are claimed for September 3–11.

| Dates | Direction change and reason | Representative commits / authors |
| --- | --- | --- |
| Before September 12 | Original-case analysis and data audit: seven regions, missing citizen text, and incompatible reference catalogs | Documented in the original journal, without Git verification for the week |
| September 12 | Contracts and the first executable foundation instead of independent mockups | `d199e16`, `9e3d86e` — Baktiyar |
| September 13–15 | Canonical ingest and routing/retrieval/forecast experiments; measuring data limits and portability | `666f369`, `d004b71`, `0ef5c50`, `0196030` — Arsen |
| September 20 | Shared offline research scenario | `85216b4` — Arsen |
| September 23–25 | Durable PostgreSQL, outbox/restore, and human governance: decisions must survive independently of ML/external systems | `7534a5b`, `833c412`, `9bbc61b`, `23f87c2`, `a31c8a9`, `cb10f3e` — Baktiyar |
| September 26–27 | Incident/control plane/privacy, real PostgreSQL demo; moving from one appeal to a shared city problem | `c82dcde`, `26b9243` — Baktiyar; `9106efd`, `69b5883`, `c87dc6b`, `98793e4` — Arsen |
| September 28 | Product shell, incident list, outcomes, policy replay diff, storage runtime/public overlays; Ask Pulse with calculated answers | `c61b322`, `8eba430`, `5c9d044`, `bf83bb8` — Arsen; `b3b4440` — Shyngyskhan; `ac21689`, `344ac69`, `5e3b8fa` — Baktiyar |
| September 29–30 | Hex UI, Golden World, maps, and presenter flow; browser recording helper and web image publishing to avoid Next.js builds on the VPS | `4559a7d` — Shyngyskhan; `ca4c2dd` — Arsen; `d613a6b`, `b255bb6`, `c2effc5`, `766bd46`, `1c8ab77`, `22d89e7` — Baktiyar |
| October 1 | Judge-facing README and captures, followed by reconciliation of languages, history, CI, and deployment | `41b6a1f`, `e494390` — Shyngyskhan; this documentation pass continues that stage |

Authorship and the captain's role are documented in [PROJECT_JOURNAL](../submission/PROJECT_JOURNAL.en.md). Commit count does not measure total team effort. Inspect a commit with `git show <hash>`; chronology with `git log --reverse --date=short --format='%h %ad %an %s' main`. Architecture decisions and revisions: [DECISION_LOG](../governance/DECISION_LOG.en.md).
