# Implementation Plan: Pulse 109 Hex Visual Style Landing Page Rework

## Goal
Refactor the Pulse 109 landing page (`apps/web/app/landing.tsx` and `apps/web/app/landing.module.css`) to embody the visual style of **Hex** (AI Analytics Platform for Your Whole Team) extracted via InspoMCP: Bento Grid macrostructure, light editorial aesthetic, precise Hex color palette (#d49e46, #ecc484, #080720, #5c9c4c, #bcb4d4), type weight + scale driven hierarchy, sharp 1px border radii, subtle technical grids, and delightful micro-interactions.

## Tasks
- [ ] Task 1: Initialize Project DESIGN.md from InspoMCP Hex extracted tokens → Verify: `DESIGN.md` exists with exact Hex palette, type ramp, and bento specifications.
- [ ] Task 2: Configure Hex typography, font faces (IBM Plex Sans & Mono with Formula / Cinetype geometric styling) in `apps/web/app/globals.css` and layout → Verify: CSS variables and Google Fonts/IBM Plex loaded.
- [ ] Task 3: Redesign `landing.module.css` with Hex design tokens, surface system (`#080720` ink, `#ecc484` / `#d49e46` support/accents, `#5c9c4c` live/status green, `#bcb4d4` muted violet), Bento Grid layouts (irregular spans, 1px borders, subtle paper/technical grid texture, sharp 1px/2px radius) → Verify: CSS compiles cleanly.
- [ ] Task 4: Refactor Hero into an asymmetric Hex-style Bento Hero: Headline in expanded display scale, Live Municipal Stage with interactive arrival chart, Real-time Operations Pulse, and Ask Pulse inspector card → Verify: Hero displays in modular bento cells with responsive desktop and mobile layouts.
- [ ] Task 5: Refactor Feature & Operational Architecture sections into Hex Bento Grid cards with technical micro-interactions, guardrail badges, and inspection states → Verify: Bento modules render cleanly without layout shifts.
- [ ] Task 6: Refactor Ask Pulse analytical exploration and Incident Aggregation into Hex notebook/studio bento cards with verified provenance tags and drilldown paths → Verify: Interactive toggles and synthetic data disclaimers function properly.
- [ ] Task 7: Refactor Navigation, Language Switcher (RU/KK), Facts Ticker, and Footer to match Hex high-craft minimalism and 1440px container discipline → Verify: Sticky nav and accessibility skip links work across viewports.
- [ ] Task 8: Add Design Spells micro-interactions: subtle hover coordinate glows, bento tile corner markers (`+` grid crosses), interactive metric inspection, and smooth transitions → Verify: 60fps micro-animations without layout shifting.
- [ ] Task 9: Run TypeScript validation, linting, and Next.js verification → Verify: `node node_modules/.pnpm/typescript@5.9.2/node_modules/typescript/lib/tsc.js --project apps/web/tsconfig.json --noEmit` exits with 0 and zero errors.

## Done When
- [ ] The landing page adheres strictly to the Hex design system: Bento Grid macrostructure, specified palette, dominant ink/surfaces, type weight hierarchy, sharp geometry, and responsive 1440px max-width container.
- [ ] All Pulse 109 domain invariants, bilingual RU/KK support, synthetic data labels, and demo links remain completely intact.
- [ ] TypeScript check passes cleanly with zero errors.
