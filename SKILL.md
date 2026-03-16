---
name: create-diagram
description: Create Excalidraw diagram JSON files that make visual arguments. Use when the user wants to visualize workflows, architectures, pipelines, or concepts. Generates .excalidraw JSON, renders to PNG for validation, iterates until correct.
argument-hint: <topic or path to source file>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Excalidraw Diagram Creator

Generate `.excalidraw` JSON files that **argue visually**, not just display information.

**Before starting any diagram**, read these two files:
- `references/color-palette.md` -- single source of truth for all colors
- `references/visual-references.md` -- quality bar. Look at the example PNGs. Your diagram must match that level.

**Setup:** If renderer is not installed, see Setup at the bottom.

---

## Core Philosophy

**Diagrams should ARGUE, not DISPLAY.** A diagram is a visual argument showing relationships, causality, and flow that words alone cannot express. The shape should BE the meaning.

**The Isomorphism Test**: Remove all text -- does the structure alone communicate the concept? If not, redesign.

**The Education Test**: Does this diagram teach something concrete (real system names, actual numbers, specific outcomes), or just label boxes?

### The Action Title Pattern

The headline IS the takeaway, not a label.

| Bad (Label) | Good (Action Title) |
|-------------|---------------------|
| "Enrichment Pipeline" | "Pipeline processes 500 records while you sleep" |
| "System Architecture" | "6 services work together so nothing falls through the cracks" |

---

## Use Case Profiles (Do This First)

Before designing, declare the use case. It sets canvas size, typography, roughness, and element count.

### Client Deliverable
For non-technical stakeholders seeing your work for the first time.
- **Canvas:** 1800x1200 (landscape) or 1200x1600 (portrait)
- **Typography:** titles 28-32px, body 18-20px
- **Roughness:** 0
- **Elements:** 5-20 max. Business language only.
- **Action Title:** Required

### Internal Documentation
For developers and team members.
- **Canvas:** 1800x1400 (landscape)
- **Typography:** titles 24-28px, body 16-18px
- **Roughness:** 0
- **Elements:** 15-40. Real file names, technical names OK.
- **Action Title:** Optional

### LinkedIn Post
For tech-savvy professionals scrolling their feed. Must stop the scroll.
- **Canvas:** 1080x1080 (square) or 1080x1350 (portrait 4:5)
- **Typography:** titles 28-36px, body 20-24px (mobile-readable)
- **Roughness:** 1 (hand-drawn feel -- only works on simple diagrams)
- **Elements:** 5-7 max. One clear visual path.
- **Action Title:** Required -- this IS the hook

**Default:** If the use case isn't clear, use Internal Documentation settings and ask.

---

## Typography (Four-Font System)

Diagrams use four fonts with distinct roles. The three-tier hierarchy uses font WEIGHT as the primary differentiator: Lilita One (heavy) > Liberation Sans (medium) > Nunito (light).

| Font | fontFamily | Role | Where |
|------|-----------|------|-------|
| Lilita One | 7 | Titles (ALL CAPS) | Diagram title, section headers -- always uppercase |
| Liberation Sans | 9 | Subtitles | Diagram subtitle, secondary headings -- medium weight bridge |
| Nunito | 6 | All body text | Node labels, annotations, callouts, sidebar titles, descriptions |
| Cascadia | 3 | Step numbers only | Circle numbers in numbered sequences |

**Char width multipliers** (calibrated):
- Nunito (6): 0.60
- Lilita One (7): 0.58
- Liberation Sans (9): 0.53
- Cascadia (3): 0.60

---

## Design Process

1. **Declare use case** -- Client, internal, or LinkedIn
2. **Understand deeply** -- What does each concept DO? What are the relationships?
3. **Pick a pattern** -- See Visual Pattern Library below
4. **Sketch the flow** -- Trace how the eye moves. Clear visual story.
5. **Generate JSON** -- See large diagram strategy below
6. **Render & validate** -- Mandatory. Keep iterating until it looks right.

---

## Visual Pattern Library

Each pattern has a proven builder script in `patterns/`. **Before building a diagram, read the builder for your chosen pattern.** The builders show exact layout math, color usage, binding patterns, and element construction that produce professional output.

### Side-by-Side (Comparison)
Two large bordered rectangles side by side, each with title + bullet-point text. Shared elements in the gap between them with arrows to both sides.
- **Builder:** `patterns/side-by-side.py`

### Layered Stack
Horizontal layers stacked vertically with color gradient. Description column to the right. Inner boxes use colored border + fill.
- **Builder:** `patterns/layered-stack.py`

### Complex Vertical Workflow
Top-to-bottom flow with convergence, processing stage, fan-out, and persistence layer below a dashed divider.
- **Builder:** `patterns/complex-workflow.py`

### Numbered Sequence Trail (LinkedIn)
Numbered circles connected by arrows in portrait format. Side annotations LEFT for insights, loop-back arrow RIGHT for iteration.
- **Builder:** `patterns/linkedin-portrait.py`

### Fan-Out (One-to-Many)
Central element with arrows radiating to multiple targets.

### Convergence (Many-to-One)
Multiple inputs merging through arrows to single output. See `references/arrow-patterns.md`.

---

## Hard Rules

1. **No arrows crossing through elements.** If the layout forces it, redesign element positions.
2. **No code snippets.** No JSON, Python, or API responses in diagrams. Plain English only.
3. **All text readable and fits its container.** Min body text 16px, min annotations 13px.
4. **Grid-aligned layout.** Same-level elements share the same Y or X. Consistent spacing.
5. **Arrows bind to shapes, never to text.** Wrap text in a rectangle if needed.

---

## Arrows

### Style (Non-Negotiable)
All arrows use elbow style with open triangle arrowheads:
```json
{
  "endArrowhead": "triangle_outline",
  "startArrowhead": null,
  "roundness": {"type": 2},
  "elbowed": true,
  "roughness": 0,
  "strokeWidth": 1.5
}
```

### Binding
Use `focus/gap` binding. Both source and target elements must list the arrow in their `boundElements` array.

### Waypoints
`elbowed: true` with only 2 points renders as a straight line. Add intermediate waypoints for visible elbow bends.

---

## Large Diagram Strategy

### Section-by-Section (15+ Elements)
Build JSON one section at a time, not in a single pass.

### Python Builder (30+ Elements)
Write a builder script with helpers: `T()` for text, `R()` for rectangle, `A()` for arrow, `LINE()` for lines. Define layout constants at top, compute coordinates programmatically, write via `json.dump()`.

---

## Render & Validate (MANDATORY)

A diagram is NOT complete until rendered and validated.

### How to Validate

**Step 1: Render.** Run the section inspector:
```bash
python engine/section_inspector.py <path-to-file.excalidraw> <output_prefix>
```

**Step 2: Inspect EVERY section screenshot.** The full overview always looks fine. The bugs hide in the zoomed sections.

**Step 3: Produce a Validation Report.** For each section, check:
- Text fits containers
- Arrows clear of elements
- Arrow endpoints bound
- Annotations visible
- Spacing consistent

If issues found: fix the GENERATOR (engine or builder), not the output file.

---

## JSON Structure

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [...],
  "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
  "files": {}
}
```

---

## Setup

```bash
pip install playwright
playwright install chromium
```

Requires: Python 3.10+, Chromium (installed by Playwright).
