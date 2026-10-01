[Русский](DESIGN.md) · [English](DESIGN.en.md) · [Қазақша](DESIGN.kk.md)

# Hex visual reference for Pulse 109

This is a reference palette and layout vocabulary, not a claim that Pulse 109
copies or fully implements Hex. The current landing blends a dark editorial
hero with light technical sections and uses static captures of the actual
synthetic demo rather than independent marketing UI.

> Extracted by [Inspo](https://github.com/Nutlope/inspo) from https://www.hex.tech / https://inspomcp.dev/api/design/hex-tech

## 1. Visual Theme & Atmosphere
- **Aesthetic:** Swiss-inspired Brutalism meets High-Craft AI Analytics Platform.
- **Mode:** Light mode with `#080720` ink, warm paper/linen surface nuances, and high-density technical cards.
- **Macrostructure:** Bento Grid. Asymmetric spans, modular interlocking cells, sharp geometry.
- **Atmosphere:** Rigorous, editorial, data-dense, developer-grade. Minimalist restraint with tactical bursts of warm gold/amber support accents.
- **Depth & Elevation:** Flat surfaces partitioned by crisp 1px borders (`rgba(8, 7, 32, 0.08)` to `rgba(8, 7, 32, 0.15)`), delicate corner registration marks (`+`), and whisper-soft ambient glow rather than blurry diffuse shadows.

## 2. Color Palette & Roles
- **Ink / Deep Void (`#080720`):** Dominant ink for text, primary navigation, technical headings, and high-contrast structural accents.
- **Gold Support / Accent (`#d49e46`):** Focused highlight color for key metrics, focal indicators, and selected states. Used sparingly.
- **Warm Champagne / Gold Soft (`#ecc484`):** Soft luminous support for badge backgrounds, subtle callout halos, and active metric chips.
- **Terminal Green / Operational Status (`#5c9c4c`):** Live indicators, verified provenance badges, healthy pipeline states.
- **Muted Lavender / Violet Gray (`#bcb4d4`):** Technical captions, schema labels, secondary metadata, grid borders.
- **Surface Linen / Off-White (`#fbf9f9` / `#ffffff`):** Dominant surface background for bento cells.
- **Canvas Base (`#f4f1ea` / `#f7f5f0`):** Outer page canvas giving a warm, editorial paper tone.

## 3. Typography Rules
Hierarchy is driven primarily by **type weight + scale** rather than arbitrary colors:
- **Display / h1:** `PP Formula SemiExtended`, 51px, weight 700, line-height 1.15, letter-spacing -1.58px. Expanded, authoritative stance. Fallback: `Space Grotesk`, `Cabinet Grotesk`, system extended grotesque.
- **Headings / h2:** `IBM Plex Sans`, 16px - 24px, weight 600 - 700, line-height 1.3, letter-spacing -0.4px.
- **Subheadings / h3:** `PP Formula` / `IBM Plex Sans`, 20px - 28px, weight 800, line-height 1.3, letter-spacing -0.7px.
- **Body & Buttons:** `Cinetype` / `IBM Plex Sans`, 14px - 15px, weight 400 - 500, line-height 1.55, letter-spacing 0.
- **Monospace & Metadata:** `IBM Plex Mono`, 11px - 13px, uppercase tracking +0.05em, precise tabular numbers.

## 4. Geometry & Components
- **Border Radius:** `1px` (strictly sharp, precision-machined corners).
- **Max Container Width:** `1440px`.
- **Bento Grid Architecture:**
  - Standard 12-column desktop grid with irregular spans (col-span-7 / col-span-5, col-span-4 / col-span-4 / col-span-4, col-span-8 / col-span-4).
  - 1px gap or 1px overlapping borders for true tabular bento framing.
- **Buttons:**
  - Primary: `#080720` background, white text, 1px radius, sharp uppercase or sentence case, smooth hover state with subtle golden outline or arrow nudge.
  - Secondary: 1px border `#080720`, transparent background, sharp hover fill.
- **Micro-Interactions (Design Spells):**
  - Corner registration crosses (`+`) at bento grid intersections.
  - Live pulse indicators on municipal signal streams.
  - Interactive arrival chart hover inspection with instant tooltip readouts.
  - Provenance inspection drawer / tabs showing exact calculation origin.
