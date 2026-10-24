---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: []
---

# Surface: MuleNetX investigator dashboard (frontend/)

Mode: Operate. Audience: investigators, analysts and administrators (PRODUCT.md). Job: move from a ranked, flagged account to an evidenced case and see where every number came from. Constraints: real API data only, the evidence labels of SRS §20.5, the states of §20.4, no client-side scoring, no geography (PaySim has none).

Owner brief: use MULENETX_REDESIGNED.jsx as inspiration, including its heatmap and graph visualization; improve it or redesign it. The direction below is an improvement that keeps its world (black ground, serif italic entity names, mono data, risk ramp). It fixes the template's illegible 7–9 px type, its grey-on-black contrast failures, its emoji/glyph icons and its mock geography.

Unattended run: the owner asked for no questions. The surface roll (seed 225223ad) dealt structures 3, 6 and 2. The lead (3, graph-first triage) was taken without a user lock.

## Direction contract

THESIS: Triage is spatial. A ranked queue sits beside the selected account's live money graph and its score decomposition, so cause and structure are read together. This refuses the category default of a KPI-card grid above a flat table.

OWN-WORLD: Ink-black ground (#07090c) with a cool second neutral for rails and panels. One risk ramp (deep green → chartreuse → amber → vermilion → oxblood) is the only saturated colour and carries heatmap cells, graph node fills and score bars. Source Serif 4 italic is used for entity identifiers (accounts, cases). Inter is the UI face, and JetBrains Mono is used for amounts, IDs and timestamps only. Hairline 1 px rules, square corners and no shadows except on overlays.

STORY: The investigator sees the active context and its freshness. They read why the top accounts score high from the signal-matrix rows, open one account, follow its money in the graph, and open a case with it as a subject.

FIRST VIEWPORT: There is a left nav rail (56 px icons with labels on hover) and a context banner across the top (dataset, snapshot, model, stale state). Below it are three columns. The left column (360 px) is a signal-matrix queue: the top accounts by final score, one row per account, with six ramp cells (ML, graph, behavioural, rules, propagation, final) and a serif italic ID. The centre column is a D3 neighbourhood graph of the selected row: hop rings, nodes filled by the ramp and edges weighted by amount. The right column (340 px) is the decomposition: final score, tier, coverage, components, the top SHAP bars, and "Open workspace" and "Open case" as the primary actions.

FORM: Graph-first triage (structure 3 of 7), seed key 225223ad. The signature move is the signal-matrix heatmap rows, whose ramp continues into the graph's node fills.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
