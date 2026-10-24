---
name: MuleNetX
description: Graph-based money-mule triage on an ink-black ground, where one risk ramp is the only colour.
colors:
  ink-0: "#07090c"
  ink-1: "#0c1015"
  ink-2: "#121821"
  ink-3: "#18202b"
  line: "#1c2430"
  line-strong: "#2b3644"
  text-1: "#e6ebf0"
  text-2: "#aab5c1"
  text-3: "#808d9b"
  text-inverse: "#07090c"
  ramp-0: "#123524"
  ramp-1: "#1f6b45"
  ramp-2: "#3f9a5c"
  ramp-3: "#9bb83a"
  ramp-4: "#e0a52a"
  ramp-5: "#e3692f"
  ramp-6: "#d43c2f"
  ramp-7: "#a3172b"
  no-signal: "#151b23"
  tier-low: "#63c283"
  tier-medium: "#e9b64d"
  tier-high: "#f2814f"
  tier-critical: "#ff6474"
  warn: "#f4f6f8"
  warn-line: "#8a96a3"
  danger: "#ff6474"
  focus: "#f4f6f8"
typography:
  score:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "1.75rem"
    fontWeight: 600
    letterSpacing: "-0.03em"
    fontFeature: "\"tnum\""
  entity-display:
    fontFamily: "Source Serif 4 Variable, Source Serif 4, Georgia, serif"
    fontSize: "2.25rem"
    fontWeight: 560
    letterSpacing: "0"
  headline:
    fontFamily: "Inter Variable, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.4375rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Inter Variable, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Inter Variable, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "\"cv11\", \"ss01\""
  label:
    fontFamily: "Inter Variable, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
  evidence-label:
    fontFamily: "Inter Variable, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    letterSpacing: "0.04em"
  entity:
    fontFamily: "Source Serif 4 Variable, Source Serif 4, Georgia, serif"
    fontWeight: 560
    letterSpacing: "0"
  data:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "0.95em"
    letterSpacing: "-0.01em"
    fontFeature: "\"tnum\""
rounded:
  square: "2px"
spacing:
  sp-1: "4px"
  sp-2: "8px"
  sp-3: "12px"
  sp-4: "16px"
  sp-5: "24px"
  sp-6: "32px"
  sp-7: "48px"
components:
  button:
    backgroundColor: "{colors.ink-2}"
    textColor: "{colors.text-1}"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "32px"
  button-hover:
    backgroundColor: "{colors.ink-3}"
  button-primary:
    backgroundColor: "{colors.text-1}"
    textColor: "{colors.text-inverse}"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "32px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-2}"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "32px"
  button-small:
    padding: "0 8px"
    height: "26px"
    typography: "{typography.label}"
  input:
    backgroundColor: "{colors.ink-0}"
    textColor: "{colors.text-1}"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "32px"
  chip:
    textColor: "{colors.text-1}"
    rounded: "{rounded.square}"
    padding: "0 8px"
    height: "22px"
    typography: "{typography.label}"
  evidence-label:
    textColor: "{colors.text-1}"
    rounded: "{rounded.square}"
    padding: "0 7px"
    height: "20px"
    typography: "{typography.evidence-label}"
  evidence-label-synthetic:
    textColor: "{colors.danger}"
  panel:
    backgroundColor: "{colors.ink-1}"
    padding: "16px"
  nav-item:
    textColor: "{colors.text-3}"
    rounded: "{rounded.square}"
    width: "44px"
    height: "40px"
  nav-item-active:
    backgroundColor: "{colors.ink-3}"
    textColor: "{colors.text-1}"
  signal-cell:
    typography: "{typography.data}"
    width: "44px"
    height: "34px"
---

# Design System: MuleNetX

## Overview

**Creative North Star: "The Night Ledger"**

MuleNetX is an instrument read for hours in a dim operations room. The ground is ink-black and every neutral is tinted cool, so the screen recedes and only the evidence glows. A single risk ramp (deep green through chartreuse, amber and vermilion to oxblood) is the one saturated colour in the system. It runs continuously from the signal-matrix heatmap cells into the graph's node fills and the score bars, so the eye can follow one account's risk across every view without a legend.

Everything else is told by treatment rather than hue: border style, fill, weight and typeface. Entities (accounts, cases) are named in Source Serif 4 italic, like names in a ledger. Interface text is Inter, and machine facts (amounts, IDs, timestamps, scores) are JetBrains Mono with tabular figures. The density is high and the forms are square, ruled with 1px hairlines and flat at rest. Shadows appear only on things that float above the page.

Motion is spent once. When a neighbourhood graph loads, the money spreads outward from the focus account ring by ring. Everything else changes state in 150 to 220ms without choreography.

**Key Characteristics:**
- Ink-black, cool-tinted ground; no pure greys.
- One saturated colour system: the risk ramp, used only to mean risk.
- Status and evidence distinguished by border, fill and weight, never by a new hue.
- Three typefaces with strict jobs: serif italic for entities, sans for interface, mono for data.
- Square 2px corners, 1px hairline rules, flat surfaces, shadows on overlays only.
- One authored motion: the graph reveal, 110ms per hop.

## Colors

A near-monochrome cool-ink palette with one continuous risk ramp as the only voice of colour.

### Primary
- **The Risk Ramp** (ramp-0 to ramp-7): an eight-stop scale from Deep Pine through Moss, Field Green, Chartreuse, Amber, Vermilion and Signal Red to Oxblood. It is interpolated in Lab space across the stops 0, 0.15, 0.30, 0.45, 0.60, 0.75, 0.88 and 1.0 and clamped at both ends. It fills heatmap cells, graph node fills, risk-tinted edges, score-bar fills and the low-to-high legend. Text on a ramp fill is ink (#07090c) between 0.38 and 0.80 and near-white (#eef2f5) outside that band.
- **No Signal** (no-signal): a slate one step off the ground for a cell or node with a null score. A cell that does not apply carries a faint 135° hatch instead of a colour.
- **Tier text** (tier-low, tier-medium, tier-high, tier-critical): brightened ramp hues that hold 4.5:1 on ink-0. They are used only for the tier word and its square tier dot. A missing tier falls back to text-3.

### Neutral
- **Ink Black** (ink-0): the page ground, input fields and the stroke that separates graph nodes.
- **Rail Ink** (ink-1): the nav rail, context banner, panels and sticky table heads.
- **Raised Ink** (ink-2): default button fill, hover rows, popovers and the mobile sheet.
- **Selected Ink** (ink-3): selected rows, active nav items, the MODEL OUTPUT label fill and score-bar tracks.
- **Hairline** (line) and **Strong Hairline** (line-strong): every rule, panel border and control stroke. The strong line is used for control borders and table-head underlines.
- **Paper White** (text-1), **Mist** (text-2), **Slate** (text-3): primary text, secondary text and labels, and tertiary text, metadata and placeholders. Text-1 is also the fill of the primary button and the INVESTIGATOR FINDING label.
- **Warn** (warn, warn-line, warn-ground): a near-white text on a grey line over a 6% white wash. Staleness is shown by the dashed grey rule and the wording, not by amber.
- **Danger** (danger): the single hazard hue. It is used for destructive button text, invalid-field borders, error text and the SYNTHETIC DATA label.
- **Focus** (focus): a near-white 2px outline at a 2px offset.

### Named Rules
**The One Ramp Rule.** The risk ramp is the only saturated colour system, and it means risk and nothing else. Never borrow a ramp hue for status, navigation, branding or emphasis.

**The Treatment, Not Hue Rule.** Status, staleness and evidence class are told apart by border style, fill and weight. Danger red is the one hazard exception, reserved for destruction, errors and synthetic data.

**The Continuous Signal Rule.** Any new view that shows a risk value colours it through the shared ramp function, so a value reads the same in a cell, a node and a bar.

## Typography

**Display / Entity Font:** Source Serif 4 (with Georgia, serif), italic
**Body Font:** Inter (with system-ui, sans-serif)
**Label/Mono Font:** JetBrains Mono (with ui-monospace, Menlo)

**Character:** A ledger hand set against a precise grotesque. The serif italic makes every account and case read as a named subject. Inter carries the interface without comment, and the mono face makes every number auditable.

### Hierarchy
- **Entity display** (Source Serif 4 italic 560, 2.25rem): the account title in the workspace. Cases use 1.75rem, and the graph inspector uses 1.1875rem.
- **Score** (JetBrains Mono 600, 1.75rem, -0.03em, tabular): the headline final score beside its tier.
- **Headline** (Inter 600, 1.4375rem, line-height 1.15, -0.01em): page headers. The text is balanced, and supporting copy under it is capped at 72ch.
- **Title** (Inter 600, 0.875rem): panel titles in 44px-high panel heads.
- **Body** (Inter 400, 0.875rem, line-height 1.45, cv11 and ss01 on): default interface text. Tables and controls drop to 0.8125rem.
- **Label** (Inter 500, 0.75rem): field labels, table heads, hints, the banner and legends.
- **Evidence label** (Inter 600, 0.6875rem, +0.04em): the mandated evidence classes and the role tag. The tier word uses 600 weight at +0.03em.
- **Entity inline** (Source Serif 4 italic 560, 1.05em of its context): account and case IDs inside tables, the matrix and graph labels. The brand wordmark uses the same face at 600.
- **Data inline** (JetBrains Mono, 0.95em, -0.01em, tabular): amounts, hashes, snapshot and model IDs, timestamps and lineage values.

### Named Rules
**The Three Jobs Rule.** Serif italic names entities, Inter runs the interface, and mono shows data. A typeface never does another face's job. Mono is for amounts, IDs, timestamps and scores only, never for prose or headings.

**The Named Subject Rule.** Every account or case identifier, wherever it appears, is set in Source Serif 4 italic.

## Layout

The app shell is a fixed grid: a 64px nav rail spanning both rows, a 44px context banner across the top (brand, dataset, snapshot, model, activation age and user), and a scrolling main area. The banner drops its optional items below 900px. Below 640px the rail disappears and the shell becomes banner, content and a 60px bottom bar with five items, where "More" opens a two-column sheet.

Triage is three columns at 372px, fluid and 360px: the signal-matrix queue, the neighbourhood graph and the decomposition. At 1280px it falls to two columns (340px and fluid), and at 820px it becomes one. The graph explorer pairs a fluid canvas with a 340px inspector and stacks at 1100px. Case detail uses a 1 : 1.2 split that also stacks at 1100px.

Spacing is a 4px-based scale (4, 8, 12, 16, 24, 32 and 48). Panels pad 16px. Page headers pad 24px on the sides and 16px below. Controls are 32px high, 26px for the small size. Table rows are 40px high with 34px heads, and matrix rows are 34px high with a 2px gap between them. The density is deliberate: a long queue should fit above the fold.

## Elevation & Depth

The system is flat. Depth comes from tonal steps of ink (0 for the page, 1 for rails and panels, 2 for raised and hover surfaces, 3 for selected surfaces) and from 1px hairlines. Shadows exist only for elements that float over content.

### Shadow Vocabulary
- **Overlay** (`box-shadow: 0 12px 32px rgba(0,0,0,0.55), 0 2px 6px rgba(0,0,0,0.4)`): lineage popovers, rail tooltips, the mobile sheet and graph overlays. Nothing else uses it.

### Named Rules
**The Overlay-Only Shadow Rule.** A surface casts a shadow only when it floats above the page. Panels, cards, buttons and rows stay flat, and selection is a tonal step plus a 2px text-1 bar on the leading edge.

## Shapes

Corners are square: a single 2px radius on buttons, inputs, chips, labels and nav items, and 0 on panels, tracks and matrix cells. The only round shapes are the 7px status dot, the running pulse and the graph nodes. Tier dots are square 8px swatches. All rules are 1px hairlines. The double, dashed and dotted border styles are vocabulary and carry meaning on evidence labels and the stale banner. Score bars are 6px tracks with a 1px tick at the attainable maximum. SHAP bars diverge from a centre hairline, vermilion (ramp-5) upward and field green (ramp-2) downward.

## Components

### Buttons
Quiet and solid, square and compact.
- **Shape:** squared (2px), 32px high and 12px side padding, with an 8px icon gap and 0.8125rem Inter at 500.
- **Default:** raised ink (ink-2) with a strong-hairline border. On hover it steps to ink-3 with a slate border, and on press it goes to the line tone.
- **Primary:** paper white (text-1) fill with ink text. Hover goes to pure white and press to mist. It is used for the one forward action in a region, such as "Open workspace".
- **Ghost:** transparent and borderless with mist text. Hover gives it raised ink and a hairline.
- **Danger:** the default button with danger-red text. It is never filled red.
- **Small:** 26px high, 8px padding and 0.75rem type. Disabled buttons drop to 45% opacity.

### Chips and Evidence Labels
- **Chip:** 22px high with a square 2px corner, a strong-hairline border and 0.75rem/500 type, with an optional 7px round dot in the current colour.
- **Evidence labels:** 20px high, 0.6875rem/600 at +0.04em, using the mandated label text verbatim. They are told apart by treatment alone:
  - FACT is solid with a mist border.
  - ANALYTICAL SIGNAL is muted (mist text on a strong hairline).
  - MODEL OUTPUT is filled with ink-3.
  - ANALYTICAL CANDIDATE has a 3px double border.
  - HYPOTHETICAL SIMULATION is dashed and italic.
  - INVESTIGATOR FINDING is inverse (paper-white fill, ink text).
  - AI INTERPRETATION is dotted and italic.
  - SYNTHETIC DATA is the only one in danger red.
- **Lineage badge:** a 22px hairline chip that opens a 380px popover on ink-2 with the overlay shadow. The popover is a mono definition list. A stale lineage takes the warn line and text.

### Cards / Containers
- **Corner Style:** square (0).
- **Background:** rail ink (ink-1).
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1px hairline. The 44px head is ruled off with a hairline.
- **Internal Padding:** 16px, with 8px × 16px in the head.

### Inputs / Fields
- **Style:** ink-0 field, 1px strong hairline, 2px corner, 32px high and 12px padding. The label sits 6px above in 0.75rem mist. Selects use a drawn two-triangle chevron.
- **Focus:** the border and a 1px ring both turn to near-white focus. There is no glow.
- **Error / Disabled:** the invalid state has a danger border with 0.75rem danger error text. Hints are 0.75rem slate.

### Navigation
- **Rail:** 64px wide on rail ink, with icon-only 44 × 40px items in slate grouped by hairline rules. Hover gives raised ink and paper text. The active item gets selected ink and a 2px paper-white bar on the rail's left edge. A fixed tooltip with the overlay shadow names each item.
- **Tabs:** 40px high in mist 0.8125rem/500. The selected tab turns paper white with a 2px paper underline sitting on the hairline.
- **Mobile:** a 60px bottom bar of five icon-and-label items on rail ink. "More" opens a two-column sheet of 44px rows with the overlay shadow.

### Signal Matrix (signature)
Each account in the ranked queue is one row. The row shows a serif italic account ID with its tier word underneath, then six 44 × 34px ramp cells (ML, graph, behavioural, rules, propagation and final). The final cell is 52px wide and bold. Cell values are 0.6875rem mono, cells are separated by a 2px ink-1 column rule, and rows are separated by a 2px gap. Hovering brightens the cells by 12%. The selected row gets ink-3 behind the ID and a 2px paper-white inset bar. Null cells are no-signal slate, and cells that do not apply are hatched.

### Neighbourhood Graph (signature)
A D3 canvas around the focus account. Hop rings are dashed hairlines (3 6). Nodes are filled with the risk ramp and stroked 2px in ink-0. Edges are a muted slate at 40% opacity and grow thicker with the amount transferred. Edges touching a risky counterparty are tinted with its ramp hue. Labels are serif italic with an ink halo. On load, nodes fade in over 420ms and edges over 520ms, delayed 110ms per hop (plus 60ms for edges), so the money visibly spreads outward from the focus. This is the system's one authored motion.

### Decomposition and Score Bars
The final score is set in mono at 1.75rem beside the tier word and a square tier dot. Component rows pair an Inter label with a 6px ramp-filled track and a mono value. A 1px mist tick marks the maximum attainable score.

### State Views
Empty and error states are left-aligned, at most 60ch wide and padded 32px × 24px, with a 1rem paper title and a mono meta line. Loading uses 12px shimmer bars stepping between ink-2 and ink-3 over 1.4s. A running job uses an 8px pulsing paper dot. The stale banner is a dashed warn-line underline on a 6% white wash.

## Do's and Don'ts

### Do:
- **Do** colour every risk value through the shared ramp (ramp-0 to ramp-7, Lab-interpolated), and use ink or near-white text on it according to the 0.38 to 0.80 band.
- **Do** set every account and case ID in Source Serif 4 italic at weight 560.
- **Do** set amounts, IDs, timestamps and scores in JetBrains Mono with tabular figures.
- **Do** separate surfaces with ink steps and 1px hairlines (line or line-strong), and keep corners at 2px.
- **Do** distinguish evidence classes and status by border style, fill and weight, and render every mandated evidence label verbatim.
- **Do** mark selection with a tonal step and a 2px paper-white leading bar.
- **Do** keep state transitions at 150ms (fast) or 220ms (medium) on cubic-bezier(0.16, 1, 0.3, 1), and honour reduced motion.

### Don't:
- **Don't** use a ramp hue, or any new saturated hue, for status, staleness, navigation or decoration.
- **Don't** use danger red for anything except destructive actions, errors and SYNTHETIC DATA.
- **Don't** put shadows on panels, cards, buttons or rows. The overlay shadow belongs to floating elements only.
- **Don't** round corners beyond 2px, except for status dots, the pulse and graph nodes.
- **Don't** set prose, headings or labels in the mono face, or entity names in Inter.
- **Don't** add a second choreographed motion. The ring-by-ring graph reveal is the only one.
