# Visual Reference Guide

Before creating any diagram, look at the example PNGs in the `examples/` directory. They represent the quality bar.

## How to Use This File

Browse the `examples/` directory for rendered PNG outputs from each pattern builder. Study them for 10 seconds each. Then create your diagram to match this quality level.

---

## Pattern 1: Side-by-Side Comparison
**Example:** `examples/side-by-side.png`
**Use case:** Comparing two approaches, architectures, or options

What makes it work:
- Two large bordered areas side by side
- Each area has: bold title, subtitle, bullet-point list as free-floating text
- Shared service badges sit in the GAP between sides -- dark rounded rectangles with white text
- Horizontal arrows connect the center badges to both sides
- Dashed annotation boxes at bottom with muted summary text
- Three-level title hierarchy: main title (centered), section titles (left-aligned), body text

## Pattern 2: Layered Stack
**Example:** `examples/layered-stack.png`
**Use case:** Layered architectures, memory systems, abstraction stacks

What makes it work:
- Each layer is a colored rectangle with title + inner service boxes
- Description text uses a SEPARATE column to the right (light background box with "what it does")
- Arrows pointing between layers with transition labels
- Distinct color per layer creates visual gradient from top to bottom
- Inner boxes use colored border + parent fill (not dark solid fill) so they belong visually

## Pattern 3: Complex Vertical Workflow
**Example:** `examples/complex-workflow.png`
**Use case:** Multi-stage pipelines, systems with convergence/fan-out

What makes it work:
- Clean vertical top-to-bottom flow
- Three-column layout at top (parallel sources) converging to a single processing stage
- Fan-out at bottom showing multiple output types
- Dashed divider separates pipeline from persistence layer
- Timeline at top gives temporal context in one line
- Annotations positioned close to their elements

## Pattern 4: LinkedIn Portrait (Numbered Sequence)
**Example:** `examples/linkedin-portrait.png`
**Use case:** LinkedIn posts, step-by-step methodologies, iteration loops

What makes it work:
- Portrait 1080x1350 (4:5 ratio) -- optimized for LinkedIn feed
- Roughness 1 -- hand-drawn feel that works because element count is low (6 main boxes)
- Clear vertical flow with numbered circles (1-6) as visual anchors
- Side annotations on the LEFT add insight without cluttering the flow
- Dashed loop-back arrow on the RIGHT shows the iteration cycle
- Contrast "wrong way" box (red dashed, top-left) sets up the argument
- Bottom insight box (dashed, centered) delivers the punchline
- BALANCED: annotations on left, loop on right, steps in center -- nothing dominates
- Each step has its own color from the palette -- visual variety without chaos
- Mobile-readable: 22px body text, 36px title

**This is the quality bar for LinkedIn diagrams.** Clear separation, balanced sides, clean vertical flow.

---

## Common Patterns Across All References

1. **Roughness 0 always** (except LinkedIn which uses roughness 1 for hand-drawn feel)
2. **Tight boxes** -- text fits with minimal padding, boxes are NOT oversized
3. **Text alignment depends on content length:**
   - Short labels (1-3 words): CENTER horizontally and vertically
   - Multi-line text, bullet points, descriptions: LEFT-ALIGN (`textAlign: "left"`) with `verticalAlign: "middle"`
4. **Data stores below** -- dark navy boxes positioned below the main flow, not inline
5. **Short arrows** -- connected elements are placed adjacent to each other
6. **Left-to-right or top-to-bottom** -- never diagonal, never random
7. **Section titles** -- simple, top-left, one line
8. **No code** -- everything described in plain English
9. **No decoration** -- every visual element carries information
10. **Color gradient for layers** -- when showing hierarchy/progression, each level gets a distinct color
11. **Pattern diversity** -- no two pages in a presentation use the same layout
12. **Arrows bind to shapes** -- wrap text in a minimal rectangle if arrows need to connect to it
