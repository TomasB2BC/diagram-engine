"""Excalidraw Diagram Layout Engine -- section-based declarative API.

Accepts declarative topology (sections, nodes, connections) and computes
all pixel coordinates, box sizing, and arrow waypoints. Produces valid
Excalidraw JSON files.

Usage:
    from layout_engine import Diagram

    d = Diagram(profile="internal", title="My Pipeline")
    with d.section("inputs", layout="row"):
        d.node("slack", "SLACK\\n6-8hr window", style="trigger")
        d.node("notion", "NOTION\\nClient record", style="secondary")
    with d.section("processing", layout="row"):
        d.node("llm", "LLM EXTRACTION", style="ai")
    d.connect("slack", "llm")
    d.connect("notion", "llm")
    d.render("output.excalidraw")
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Seed generator -- deterministic, sequential, no collisions
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Font metrics -- from Excalidraw packages/common/src/font-metadata.ts
# ---------------------------------------------------------------------------
FONT_METRICS: dict[int, dict[str, float | int]] = {
    5:  {"lineHeight": 1.25, "unitsPerEm": 1000, "ascender": 886,  "descender": -374},  # Excalifont (current Excalidraw default)
    6:  {"lineHeight": 1.25, "unitsPerEm": 1000, "ascender": 1011, "descender": -353},  # Nunito
    7:  {"lineHeight": 1.15, "unitsPerEm": 1000, "ascender": 923,  "descender": -220},  # Lilita One
    8:  {"lineHeight": 1.25, "unitsPerEm": 1000, "ascender": 750,  "descender": -250},  # Comic Shanns
    3:  {"lineHeight": 1.2,  "unitsPerEm": 2048, "ascender": 1900, "descender": -480},  # Cascadia (our default, deprecated in Excalidraw)
    9:  {"lineHeight": 1.15, "unitsPerEm": 2048, "ascender": 1854, "descender": -434},  # Liberation Sans
    10: {"lineHeight": 1.25, "unitsPerEm": 2048, "ascender": 1021, "descender": -287},  # Assistant
    1:  {"lineHeight": 1.25, "unitsPerEm": 1000, "ascender": 886,  "descender": -374},  # Virgil (deprecated)
    2:  {"lineHeight": 1.15, "unitsPerEm": 2048, "ascender": 1577, "descender": -471},  # Helvetica (deprecated)
}
DEFAULT_FONT_FAMILY = 3  # Cascadia -- keep for now, switch to Excalifont (5) is a separate phase
LINE_HEIGHT = FONT_METRICS[DEFAULT_FONT_FAMILY]["lineHeight"]

# Average character width as fraction of fontSize. Monospace fonts have consistent
# width; proportional fonts vary but average works for layout estimation.
# Cascadia (0.60) is proven. Others are approximate starting points from
# Excalidraw source analysis -- validate empirically if switching fonts.
CHAR_WIDTH_MULTIPLIER: dict[int, float] = {
    3:  0.60,   # Cascadia (monospace -- very consistent, proven value)
    5:  0.55,   # Excalifont (hand-drawn, slightly narrower)
    6:  0.60,   # Nunito (proportional, calibrated via Playwright 2026-03-15)
    7:  0.58,   # Lilita One (display font, wider)
    8:  0.55,   # Comic Shanns (monospace)
    9:  0.53,   # Liberation Sans (proportional)
    10: 0.50,   # Assistant (proportional, narrow)
    1:  0.55,   # Virgil (deprecated)
    2:  0.53,   # Helvetica (deprecated)
}

# Roundness types -- from Excalidraw packages/common/src/constants.ts
ROUNDNESS_ADAPTIVE = {"type": 3}      # Rectangles: fixed 32px radius
ROUNDNESS_PROPORTIONAL = {"type": 2}  # Lines/arrows: 25% of largest side

H_PAD = 20          # Engine horizontal padding (Excalidraw adds ~10px more internally)
V_PAD = 16          # Engine vertical padding (Excalidraw adds ~10px more internally)

_seed_counter = 100000


def next_seed() -> int:
    global _seed_counter
    _seed_counter += 1
    return _seed_counter


def reset_seeds(start: int = 100000) -> None:
    """Reset seed counter (useful for deterministic tests)."""
    global _seed_counter
    _seed_counter = start


# ---------------------------------------------------------------------------
# PROFILES -- canvas size, font sizes, roughness, element limits
# ---------------------------------------------------------------------------
PROFILES: dict[str, dict[str, Any]] = {
    "client": {
        "canvas": (1800, 1200),
        "title_size": 30,
        "body_size": 18,
        "roughness": 0,
        "max_elements": 20,
        "title_gap": 24,
        "subtitle_gap": 20,
        "header_gap": 30,
        "callout_gap": 24,
        "min_annotation_size": 14,
        "stack_gap": 80,
        "node_gap": 56,
        "section_padding": 100,
        "row_padding": 140,
        "title_font": 7,   # Lilita One
        "subtitle_font": 9,  # Liberation Sans
        "body_font": 6,    # Nunito
        "number_font": 3,  # Cascadia
        "title_transform": "uppercase",
        "subtitle_size": 20,
        "title_max_lines": 1,
        "min_title_subtitle_gap": 20,
        "min_subtitle_content_gap": 30,
    },
    "internal": {
        "canvas": (1800, 1400),
        "title_size": 26,
        "body_size": 16,
        "roughness": 0,
        "max_elements": 40,
        "title_gap": 36,
        "subtitle_gap": 28,
        "header_gap": 44,
        "callout_gap": 32,
        "min_annotation_size": 13,
        "stack_gap": 72,
        "node_gap": 56,
        "section_padding": 112,
        "row_padding": 168,
        "title_font": 7,   # Lilita One
        "subtitle_font": 9,  # Liberation Sans
        "body_font": 6,    # Nunito
        "number_font": 3,  # Cascadia
        "title_transform": "uppercase",
        "subtitle_size": 20,
        "title_max_lines": 1,
        "min_title_subtitle_gap": 20,
        "min_subtitle_content_gap": 30,
    },
    "linkedin": {
        "canvas": (1080, 1350),
        "title_size": 32,
        "body_size": 22,
        "roughness": 1,
        "max_elements": 7,
        "title_gap": 40,
        "subtitle_gap": 32,
        "header_gap": 44,
        "callout_gap": 36,
        "min_annotation_size": 18,
        "stack_gap": 90,
        "node_gap": 78,
        "section_padding": 80,
        "row_padding": 120,
        "title_font": 7,   # Lilita One
        "subtitle_font": 9,  # Liberation Sans
        "body_font": 6,    # Nunito
        "number_font": 3,  # Cascadia
        "title_transform": "uppercase",
        "subtitle_size": 20,
        "title_max_lines": 1,
        "min_title_subtitle_gap": 20,
        "min_subtitle_content_gap": 30,
    },
}

# ---------------------------------------------------------------------------
# Semantic styles -- Tailwind CSS palette
# Cross-reference with Excalidraw's Open Color (packages/common/src/colors.ts):
#   primary/secondary/tertiary/inactive ~ blue family (OC blue[0-2], blue[4])
#   trigger ~ orange family (OC orange[1], orange[4])
#   success ~ teal family (OC teal[1], teal[4])
#   warning/error ~ red family (OC red[0-1], red[3-4])
#   decision ~ yellow family (OC yellow[0-1], yellow[4])
#   ai ~ violet family (OC violet[1], violet[4])
#   dark ~ gray family (OC gray[4])
# Our hex values are Tailwind, not exact OC. Colors render fine in Excalidraw
# but won't snap to palette positions in the color picker. Cosmetic only.
# ---------------------------------------------------------------------------
STYLES: dict[str, dict[str, str]] = {
    "primary":   {"fill": "#3b82f6", "stroke": "#1e3a5f"},
    "secondary": {"fill": "#60a5fa", "stroke": "#1e3a5f"},
    "tertiary":  {"fill": "#93c5fd", "stroke": "#1e3a5f"},
    "trigger":   {"fill": "#fed7aa", "stroke": "#c2410c"},
    "success":   {"fill": "#a7f3d0", "stroke": "#047857"},
    "warning":   {"fill": "#fee2e2", "stroke": "#dc2626"},
    "decision":  {"fill": "#fef3c7", "stroke": "#b45309"},
    "ai":        {"fill": "#ddd6fe", "stroke": "#6d28d9"},
    "inactive":  {"fill": "#dbeafe", "stroke": "#1e40af"},
    "error":     {"fill": "#fecaca", "stroke": "#b91c1c"},
    "dark":      {"fill": "#1e293b", "stroke": "#1e293b"},
}

TEXT_COLORS: dict[str, str] = {
    "title": "#1e40af",
    "subtitle": "#3b82f6",
    "body": "#64748b",
    "on_light": "#374151",
    "on_dark": "#ffffff",
}


# ---------------------------------------------------------------------------
# WCAG 2.1 relative luminance -- text contrast detection
# ---------------------------------------------------------------------------
def _relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance (0.0 = black, 1.0 = white).

    Uses sRGB linearization per https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return 0.5
    channels = []
    for i in range(3):
        c = int(hex_color[i * 2 : i * 2 + 2], 16) / 255.0
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _is_dark_fill(hex_color: str) -> bool:
    """Check if a fill color needs white/light text for readability.

    Uses WCAG relative luminance with threshold 0.179 (the geometric mean
    of black and white luminance at 4.5:1 contrast ratio).
    """
    return _relative_luminance(hex_color) < 0.179


# ---------------------------------------------------------------------------
# FIXED_POINTS -- normalized anchor positions on each side of a rectangle.
# Used for fixedPoint/orbit binding mode (loop arrows, forced side exits).
# Values are [normalizedX, normalizedY] where 0..1 maps to element bounds.
# ---------------------------------------------------------------------------
FIXED_POINTS: dict[str, list[float]] = {
    "top":    [0.5, 0.0],
    "bottom": [0.5, 1.0],
    "left":   [0.0, 0.5],
    "right":  [1.0, 0.5],
    "top_left":     [0.25, 0.0],
    "top_right":    [0.75, 0.0],
    "bottom_left":  [0.25, 1.0],
    "bottom_right": [0.75, 1.0],
    "left_top":     [0.0, 0.25],
    "left_bottom":  [0.0, 0.75],
    "right_top":    [1.0, 0.25],
    "right_bottom": [1.0, 0.75],
}

# ---------------------------------------------------------------------------
# Font metrics -- estimate pixel size from text content
# Proven formula from 4 existing builder scripts (fontFamily 3 / Cascadia)
# ---------------------------------------------------------------------------
def estimate_text_size(
    text: str, font_size: int, font_family: int = DEFAULT_FONT_FAMILY
) -> tuple[int, int]:
    """Estimate RAW pixel width and height for text content.

    Returns raw text dimensions. Caller applies padding.
    Uses per-font character width multiplier and line height from FONT_METRICS.
    """
    lines = text.split("\n")
    max_chars = max(len(line) for line in lines)
    multiplier = CHAR_WIDTH_MULTIPLIER.get(font_family, 0.58)
    line_height = FONT_METRICS.get(font_family, {}).get("lineHeight", 1.2)
    width = int(max_chars * font_size * multiplier)
    height = int(len(lines) * font_size * line_height)
    return width, height


# ---------------------------------------------------------------------------
# Element dataclasses
# ---------------------------------------------------------------------------
@dataclass
class Node:
    """A rectangle + contained text element."""
    id: str
    text: str
    style: str = "primary"
    section_id: str = ""
    layout_type: str = ""        # "row", "stack", "timeline", "funnel", "sidebar"
    spine_x: int | None = None   # timeline only: x position of spine/dot
    fixed_width: int | None = None  # step_marker width override (minimum)
    inner_of: str | None = None     # breadcrumb: fill from this style, stroke from own
    # Computed by layout
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


@dataclass
class Connection:
    """A deferred arrow connection between two nodes."""
    src_id: str
    dst_id: str
    label: str | None = None
    exit_side: str | None = None
    enter_side: str | None = None
    dashed: bool = False


@dataclass
class Annotation:
    """A text note positioned relative to a node."""
    target_id: str
    text: str
    side: str = "right"  # right, left, below
    color: str | None = None  # override color; auto-derives from target stroke if None


@dataclass
class Callout:
    """A floating callout box not part of section flow."""
    text: str
    position: str = "bottom"  # "top" or "bottom"
    style: str = "decision"   # semantic style for fill/stroke
    width: int | None = None  # auto-computed if None
    font_size: int | None = None  # None = use profile body_size


@dataclass
class Section:
    """A group of nodes with a layout mode."""
    id: str
    layout: str  # "row", "stack", "funnel", "timeline", or "sidebar"
    nodes: list[Node] = field(default_factory=list)
    start_width: int | None = None  # funnel mode: width of first stage
    end_width: int | None = None    # funnel mode: width of last stage
    x_bias: str = "right"           # timeline mode: which side content branches to
    entry_gap: int = 80             # timeline mode: vertical spacing between entries
    position: str = "right"         # sidebar mode: "left" or "right"
    sidebar_width: int = 260        # sidebar mode: width of the sidebar panel


# ---------------------------------------------------------------------------
# JSON helpers: T, R, A -- ported from example-builders/complex-workflow.py
# These produce valid Excalidraw JSON element dicts.
# ---------------------------------------------------------------------------
def _T(
    id: str,
    x: int,
    y: int,
    text: str,
    size: int = 16,
    color: str = "#64748b",
    align: str = "left",
    container: str | None = None,
    w: int | None = None,
    h: int | None = None,
    cw: int | None = None,
    ch: int | None = None,
    roughness: int = 0,
    font_family: int = DEFAULT_FONT_FAMILY,
) -> dict:
    """Create a text element dict.

    When container is set with cw/ch (container width/height), the text x,y
    are manually centered within the container. Excalidraw's verticalAlign/
    textAlign don't apply on JSON file load -- only on interactive editing.
    """
    # Always compute text dimensions from content (per-font metrics)
    char_w = CHAR_WIDTH_MULTIPLIER.get(font_family, 0.58)
    line_height = FONT_METRICS.get(font_family, {}).get("lineHeight", 1.2)
    text_w = int(max(len(line) for line in text.split("\n")) * size * char_w)
    lines = text.count("\n") + 1
    text_h = int(lines * size * line_height)
    # Use explicit w/h if provided, otherwise auto-calculated
    if w is None:
        w = text_w
    if h is None:
        h = text_h
    # Manual centering when container dimensions are provided
    # (Excalidraw's verticalAlign:"middle" doesn't work from JSON load)
    if container and cw is not None and ch is not None:
        x = x + (cw - text_w) // 2
        y = y + (ch - text_h) // 2
        w = text_w
        h = text_h
    return {
        "type": "text",
        "id": id,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": text,
        "originalText": text,
        "fontSize": size,
        "fontFamily": font_family,
        "textAlign": align if not container else "center",
        "verticalAlign": "top" if not container else "middle",
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": roughness,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "groupIds": [],
        "boundElements": None,
        "link": None,
        "locked": False,
        "containerId": container,
        "lineHeight": line_height,
    }


def _R(
    id: str,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str,
    stroke: str,
    sw: int = 2,
    bound_text: str | None = None,
    bound_arrows: list[str] | None = None,
    dashed: bool = False,
    roughness: int = 0,
) -> dict:
    """Create a rectangle element dict."""
    be: list[dict] = []
    if bound_text:
        be.append({"id": bound_text, "type": "text"})
    if bound_arrows:
        for aid in bound_arrows:
            be.append({"id": aid, "type": "arrow"})
    return {
        "type": "rectangle",
        "id": id,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": sw,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": roughness,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "groupIds": [],
        "boundElements": be if be else None,
        "link": None,
        "locked": False,
        "roundness": ROUNDNESS_ADAPTIVE,
    }


def _ELLIPSE(
    id: str,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str,
    stroke: str,
    sw: int = 2,
    bound_text: str | None = None,
    bound_arrows: list[str] | None = None,
    roughness: int = 0,
) -> dict:
    """Create an ellipse element dict. Mirrors _R() parameter convention."""
    be: list[dict] = []
    if bound_text:
        be.append({"id": bound_text, "type": "text"})
    if bound_arrows:
        for aid in bound_arrows:
            be.append({"id": aid, "type": "arrow"})
    return {
        "type": "ellipse",
        "id": id,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": sw,
        "strokeStyle": "solid",
        "roughness": roughness,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "groupIds": [],
        "boundElements": be if be else None,
        "link": None,
        "locked": False,
    }


def _A(
    id: str,
    x: int,
    y: int,
    pts: list[list[int]],
    stroke: str,
    sw: float = 1.5,
    start_id: str | None = None,
    end_id: str | None = None,
    start_binding: dict | None = None,
    end_binding: dict | None = None,
    style: str = "solid",
    roughness: int = 0,
) -> dict:
    """Create an arrow element dict."""
    # Use explicit binding dicts if provided, otherwise build orbit binding
    if start_binding is None and start_id:
        start_binding = {"elementId": start_id, "mode": "orbit", "fixedPoint": [0.5, 1.0]}
    if end_binding is None and end_id:
        end_binding = {"elementId": end_id, "mode": "orbit", "fixedPoint": [0.5, 0.0]}
    return {
        "type": "arrow",
        "id": id,
        "x": x,
        "y": y,
        "width": abs(pts[-1][0] - pts[0][0]) if len(pts) > 1 else 0,
        "height": abs(pts[-1][1] - pts[0][1]) if len(pts) > 1 else 0,
        "strokeColor": stroke,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": sw,
        "strokeStyle": style,
        "roughness": roughness,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "groupIds": [],
        "boundElements": None,
        "link": None,
        "locked": False,
        "points": pts,
        "startBinding": start_binding,
        "endBinding": end_binding,
        "startArrowhead": None,
        "endArrowhead": "triangle_outline",
        "roundness": ROUNDNESS_PROPORTIONAL,
        "elbowed": True,
        "fixedSegments": None,
        "startIsSpecial": None,
        "endIsSpecial": None,
    }


def _LINE(
    id: str,
    x: int,
    y: int,
    pts: list[list[int]],
    stroke: str = "#64748b",
    sw: int = 2,
    dashed: bool = False,
    roughness: int = 0,
) -> dict:
    """Create a line element dict."""
    return {
        "type": "line",
        "id": id,
        "x": x,
        "y": y,
        "width": abs(pts[-1][0]) if pts else 0,
        "height": abs(pts[-1][1]) if pts else 0,
        "strokeColor": stroke,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": sw,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": roughness,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "groupIds": [],
        "boundElements": None,
        "link": None,
        "locked": False,
        "points": pts,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": None,
        "polygon": False,
    }


# ---------------------------------------------------------------------------
# Section layout computation
# ---------------------------------------------------------------------------
def _compute_funnel_widths(
    count: int, start_width: int, end_width: int
) -> list[int]:
    """Linearly interpolate widths from start_width to end_width."""
    if count <= 1:
        return [start_width]
    step = (start_width - end_width) / (count - 1)
    return [int(start_width - i * step) for i in range(count)]


def layout_section(
    nodes: list[Node],
    layout: str,
    canvas_width: int,
    start_y: int,
    profile: dict[str, Any],
    gap: int = 56,
    start_width: int | None = None,
    end_width: int | None = None,
    x_bias: str = "right",
    entry_gap: int = 80,
    position: str = "right",
    sidebar_width: int = 260,
) -> int:
    """Position nodes within a section. Mutates node x/y/w/h. Returns next_y.

    Row layout: elements spread horizontally, centered on canvas.
    Stack layout: elements stacked vertically, centered on canvas.
    Funnel layout: elements stacked vertically with decreasing widths, centered.
    Timeline layout: vertical spine with dots and content branching to one side.
    """
    body_size = profile["body_size"]
    body_font = profile.get("body_font", DEFAULT_FONT_FAMILY)
    node_gap = profile.get("node_gap", gap)
    section_padding = profile.get("section_padding", gap * 2)
    row_padding = profile.get("row_padding", gap * 3)  # noqa: F841 -- available for multi-row sections

    # Compute content-driven sizes (raw text + proportional padding)
    # Gap 7: Proportional padding gives ~80% text fill in wide boxes.
    # h_pad_total scales with text width (20% of raw_w) but never less than
    # the fixed H_PAD. v_pad_total similarly scales with text height.
    for node in nodes:
        raw_w, raw_h = estimate_text_size(node.text, body_size, font_family=body_font)
        h_pad_total = max(H_PAD, int(raw_w * 0.20))
        v_pad_total = max(V_PAD, int(raw_h * 0.15))
        node.w = max(raw_w + h_pad_total, 120)
        node.h = max(raw_h + v_pad_total, 50)
        # Fixed width override (minimum width from step_marker width param)
        if node.fixed_width is not None:
            node.w = max(node.fixed_width, node.w)

    if layout == "row":
        total_w = sum(n.w for n in nodes) + node_gap * max(len(nodes) - 1, 0)
        x = (canvas_width - total_w) // 2
        for node in nodes:
            node.x = x
            node.y = start_y
            x += node.w + node_gap
        max_h = max(n.h for n in nodes) if nodes else 0
        # Equalize heights in a row for visual consistency
        for node in nodes:
            node.h = max_h
        return start_y + max_h + section_padding

    elif layout == "funnel":
        # Funnel: linearly decreasing widths, tight vertical stacking
        sw = start_width or 400
        ew = end_width or 120
        widths = _compute_funnel_widths(len(nodes), sw, ew)
        funnel_gap = 8  # tight stacking for funnel visual
        center_x = canvas_width // 2
        # Equalize heights for uniform funnel stages
        max_h = max(n.h for n in nodes) if nodes else 50
        for i, node in enumerate(nodes):
            tapered_w = widths[i]
            # Enforce minimum width so text remains readable
            if tapered_w < node.w:
                import sys
                print(
                    f"[!] Funnel stage '{node.id}': tapered width {tapered_w}px "
                    f"< text width {node.w}px, expanding to fit text",
                    file=sys.stderr,
                )
                stage_w = node.w
            else:
                stage_w = tapered_w
            node.w = stage_w
            node.h = max_h
            node.x = center_x - stage_w // 2
            node.y = start_y
            start_y += max_h + funnel_gap
        return start_y + section_padding

    elif layout == "timeline":
        # Timeline: vertical spine line with dots at each entry and content
        # branching to the specified side (x_bias). Nodes are positioned as
        # dot+content pairs rather than rectangles. The spine x is placed
        # at 1/4 canvas width (right bias) or 3/4 (left bias) to leave room
        # for branching content.
        # NOTE: Timeline dots can be arrow DESTINATIONS but should NOT be
        # arrow SOURCES (connecting FROM a dot is visually unclear).
        content_offset = 40  # horizontal distance from spine to content
        spine_x = canvas_width // 4 if x_bias == "right" else (canvas_width * 3) // 4

        for i, node in enumerate(nodes):
            node.layout_type = "timeline"
            node.spine_x = spine_x
            # Position node as the content area (used for arrow binding)
            raw_w, raw_h = estimate_text_size(node.text, body_size, font_family=body_font)
            tl_h_pad = max(H_PAD, int(raw_w * 0.20))
            tl_v_pad = max(V_PAD, int(raw_h * 0.15))
            node.w = max(raw_w + tl_h_pad, 120)
            node.h = max(raw_h + tl_v_pad, 40)
            node.y = start_y + i * entry_gap
            if x_bias == "right":
                node.x = spine_x + content_offset
            else:
                node.x = spine_x - content_offset - node.w

        # Return next_y past the last entry
        if nodes:
            last = nodes[-1]
            return last.y + last.h + section_padding
        return start_y + section_padding

    elif layout == "sidebar":
        # Sidebar: nodes stacked vertically at the left or right edge.
        # Sidebar sections don't advance vertical flow (they're positioned
        # absolutely at the side). Returns start_y unchanged so content
        # sections continue from where they were.
        margin = 30
        inner_pad = 16  # padding inside sidebar container
        if position == "right":
            sidebar_x = canvas_width - sidebar_width - margin
        else:
            sidebar_x = margin

        # Stack nodes vertically within the sidebar bounds
        node_y = start_y + 40  # leave room for sidebar title
        for node in nodes:
            node.w = min(node.w, sidebar_width - inner_pad * 2)
            node.x = sidebar_x + inner_pad
            node.y = node_y
            node_y += node.h + 12  # tight spacing in sidebar
        # Sidebar does NOT advance the main vertical flow
        return start_y

    else:  # stack
        stack_gap = profile.get("stack_gap", gap)
        for node in nodes:
            node.x = (canvas_width - node.w) // 2
            node.y = start_y
            start_y += node.h + stack_gap
        return start_y + section_padding


# ---------------------------------------------------------------------------
# Arrow routing -- compute waypoints and bindings for connections
# ---------------------------------------------------------------------------
def _anchor_point(
    node: Node, side: str
) -> tuple[int, int]:
    """Get the pixel coordinate for a specific side of a node.

    Timeline nodes use spine/dot position for top/bottom/left sides
    and text box edge for right side.
    """
    if node.layout_type == "timeline" and node.spine_x is not None:
        dot_y = node.y + node.h // 2
        if side == "top":
            return node.spine_x, node.y
        elif side == "bottom":
            return node.spine_x, node.y + node.h
        elif side == "left":
            return node.spine_x - 6, dot_y  # dot left edge (dot_size/2)
        elif side == "right":
            return node.x + node.w, dot_y   # text box right edge
        return node.spine_x, node.y + node.h

    if side == "top":
        return node.x + node.w // 2, node.y
    elif side == "bottom":
        return node.x + node.w // 2, node.y + node.h
    elif side == "left":
        return node.x, node.y + node.h // 2
    elif side == "right":
        return node.x + node.w, node.y + node.h // 2
    # Default to bottom
    return node.x + node.w // 2, node.y + node.h


def _effective_center(node: Node) -> tuple[int, int]:
    """Get routing-effective center. Timeline nodes use dot/spine position."""
    if node.layout_type == "timeline" and node.spine_x is not None:
        return node.spine_x, node.y + node.h // 2
    return node.x + node.w // 2, node.y + node.h // 2


def _infer_exit_side(
    src: Node, dst: Node, all_nodes: list[Node] | None = None
) -> str:
    """Infer the best exit side from src to dst based on relative positions.

    Default: exit toward the destination (bottom if dst is below, etc.).
    When all_nodes is provided, checks whether a bottom-exit elbow would
    cross an intermediate box and switches to a side exit if so.
    """
    src_cx, src_cy = _effective_center(src)
    dst_cx, dst_cy = _effective_center(dst)

    dx = dst_cx - src_cx
    dy = dst_cy - src_cy

    # When exiting bottom toward a destination below, check if the
    # elbow junction would cross an intermediate node. If so, prefer
    # a side exit to route around it cleanly.
    if dy > 0 and all_nodes:
        for n in all_nodes:
            if n.id in (src.id, dst.id):
                continue
            # Skip nodes in the same row as src (similar y)
            if abs(n.y - src.y) < 20:
                continue
            # Node is between src and dst vertically
            # (obstacle top is above dst, obstacle bottom is below src)
            if n.y + n.h > src.y + src.h and n.y < dst.y:
                # And the horizontal junction would cross it
                min_x = min(src_cx, dst_cx) - 10
                max_x = max(src_cx, dst_cx) + 10
                if n.x < max_x and n.x + n.w > min_x:
                    return "right" if dx > 0 else "left"

    # Vertical-flow bias: if destination is clearly in a different row
    # (dy > half the source height), prefer bottom/top exit. This avoids
    # side exits for convergence arrows where elbow routing handles the
    # horizontal offset cleanly.
    if abs(dy) > src.h * 0.5:
        return "bottom" if dy > 0 else "top"

    # Same-row or nearly same-row: use horizontal direction
    if abs(dx) > 0:
        return "right" if dx > 0 else "left"
    return "bottom" if dy > 0 else "top"


def _infer_enter_side(
    src: Node, dst: Node, all_nodes: list[Node] | None = None
) -> str:
    """Infer the best entry side on dst from src."""
    src_cx, src_cy = _effective_center(src)
    dst_cx, dst_cy = _effective_center(dst)

    dx = dst_cx - src_cx
    dy = dst_cy - src_cy

    # Mirror the vertical-flow bias from exit side
    if abs(dy) > dst.h * 0.5:
        return "top" if dy > 0 else "bottom"

    if abs(dx) > 0:
        return "left" if dx > 0 else "right"
    return "top" if dy > 0 else "bottom"


def _opposite_side(side: str) -> str:
    """Return the opposite side."""
    return {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}[side]


def _make_binding(
    element_id: str,
    fixed_point: str,
) -> dict:
    """Create an orbit-mode binding dict for an arrow endpoint.

    All bindings use mode:orbit with fixedPoint overshoot values, matching
    the proven pattern from reference builders (linkedin-portrait.py, etc.).

    Args:
        element_id: The element to bind to.
        fixed_point: Name from FIXED_POINTS (e.g. "top", "bottom_left").
    """
    fp = FIXED_POINTS.get(fixed_point, [0.5, 0.5])
    return {
        "elementId": element_id,
        "mode": "orbit",
        "fixedPoint": fp,
    }


def _segment_hits_box(
    ax: int, ay: int, bx: int, by: int,
    box_x: int, box_y: int, box_w: int, box_h: int,
    margin: int = 15,
) -> bool:
    """Check if a line segment (ax,ay)-(bx,by) passes through a box with margin.

    Only checks axis-aligned segments (the only kind we produce).
    """
    # Expand box by margin
    bx1 = box_x - margin
    by1 = box_y - margin
    bx2 = box_x + box_w + margin
    by2 = box_y + box_h + margin

    if ax == bx:
        # Vertical segment
        if not (bx1 <= ax <= bx2):
            return False
        seg_y1, seg_y2 = min(ay, by), max(ay, by)
        return seg_y1 < by2 and seg_y2 > by1
    elif ay == by:
        # Horizontal segment
        if not (by1 <= ay <= by2):
            return False
        seg_x1, seg_x2 = min(ax, bx), max(ax, bx)
        return seg_x1 < bx2 and seg_x2 > bx1
    return False


def _path_hits_obstacle(
    origin_x: int, origin_y: int, pts: list[list[int]],
    obstacle: Node, margin: int = 15,
) -> bool:
    """Check if any segment of an arrow path passes through an obstacle.

    Scales collision margin for small elements (Pitfall 6): a 12px dot
    should not get a 42x42px collision zone. For elements <= 20px in
    either dimension, margin is scaled to max(element_size * 0.5, 8).
    """
    # Scale margin for small elements (timeline dots, step marker circles)
    min_dim = min(obstacle.w, obstacle.h)
    if min_dim <= 20:
        margin = max(int(min_dim * 0.5), 8)
    for i in range(len(pts) - 1):
        ax = origin_x + pts[i][0]
        ay = origin_y + pts[i][1]
        bx = origin_x + pts[i + 1][0]
        by = origin_y + pts[i + 1][1]
        if _segment_hits_box(ax, ay, bx, by,
                             obstacle.x, obstacle.y, obstacle.w, obstacle.h,
                             margin):
            return True
    return False


def compute_waypoints(
    src: Node,
    dst: Node,
    exit_side: str,
    enter_side: str,
    stagger_offset: int = 0,
    junction_offset: int = 50,
    loop_out: int = 120,
    obstacles: list[Node] | None = None,
    junction_override: int | None = None,
) -> tuple[int, int, list[list[int]], str | None, str | None]:
    """Compute arrow origin and waypoints for a connection.

    Returns (origin_x, origin_y, points_list, actual_exit, actual_enter)
    where points are relative to origin. actual_exit/actual_enter are non-None
    when the routing pattern overrides the requested exit/enter sides (e.g.,
    feedback arrows that reroute along the canvas margin).

    Four routing patterns:
        STRAIGHT: src and dst roughly aligned on the connection axis.
        ELBOW: src and dst offset, needs 90-degree bends.
        LOOP: exit_side == enter_side (feedback arrow).
        FEEDBACK: long-distance upward connection routed along canvas margin.

    If obstacles are provided, ELBOW and STRAIGHT patterns check for collisions
    and reroute around intermediate boxes when necessary.
    """
    # For loop arrows (same side exit/enter), use separated anchor points
    # to create visible vertical/horizontal offset
    is_loop = exit_side == enter_side
    if is_loop and src.id == dst.id:
        # Self-referencing loop: separate the exit and enter points
        sep = max(src.h // 3, 20)  # separation in pixels
        if exit_side in ("right", "left"):
            ox, oy = _anchor_point(src, exit_side)
            oy -= sep // 2  # exit from upper part
            ex, ey = ox, oy + sep  # enter at lower part
        else:
            ox, oy = _anchor_point(src, exit_side)
            ox -= sep // 2
            ex, ey = ox + sep, oy
    else:
        ox, oy = _anchor_point(src, exit_side)
        ex, ey = _anchor_point(dst, enter_side)

    # Apply stagger offset to origin position (for fan-out/convergence)
    if exit_side in ("top", "bottom"):
        ox += stagger_offset
    else:
        oy += stagger_offset

    dx = ex - ox
    dy = ey - oy

    # Pattern 3: LOOP -- exit_side == enter_side (feedback arrow)
    if is_loop:
        if exit_side in ("right", "left"):
            out_dir = loop_out if exit_side == "right" else -loop_out
            return ox, oy, [[0, 0], [out_dir, 0], [out_dir, dy], [0, dy]], None, None
        else:  # top or bottom
            out_dir = loop_out if exit_side == "bottom" else -loop_out
            return ox, oy, [[0, 0], [0, out_dir], [dx, out_dir], [dx, dy]], None, None

    # Pattern 4: FEEDBACK -- long-distance upward connection with intermediates
    # Route along the canvas margin to avoid cutting through intermediate sections.
    if obstacles and dy < 0:
        intermediates = [n for n in obstacles
                         if n.y + n.h > dst.y + dst.h and n.y < src.y]
        if intermediates:
            # Find the rightmost content edge across ALL nodes to set margin
            all_x_edges = [n.x + n.w for n in obstacles]
            all_x_edges.extend([src.x + src.w, dst.x + dst.w])
            margin_x = max(all_x_edges) + 60  # 60px clear of content

            # Path: exit right from src -> up along margin -> enter from right at dst
            # Recompute anchor points for side exit/entry
            sox, soy = _anchor_point(src, "right")
            dex, dey = _anchor_point(dst, "right")

            # Waypoints relative to sox, soy
            pts = [
                [0, 0],                              # start at src right edge
                [margin_x - sox, 0],                  # horizontal to margin
                [margin_x - sox, dey - soy],          # vertical along margin
                [dex - sox, dey - soy],               # horizontal to dst right edge
            ]
            # Return actual sides so bindings match the routed path
            return sox, soy, pts, "right", "right"

    # Adaptive junction depth: scale with section gap instead of fixed constant.
    # junction_override (from cross-pattern detection) takes precedence.
    if junction_override is not None:
        junction_offset = junction_override
    else:
        section_gap = dst.y - (src.y + src.h)
        if section_gap > 0:
            junction_offset = max(min(int(section_gap * 0.4), 80), 30)

    # Pattern 1: STRAIGHT -- aligned on the perpendicular axis
    align_threshold = 15
    if exit_side in ("top", "bottom") and abs(dx) < align_threshold:
        pts = [[0, 0], [0, dy]]
        # Check for collisions on straight vertical path
        if obstacles:
            for obs in obstacles:
                if _path_hits_obstacle(ox, oy, pts, obs):
                    # Reroute: pick the side of the obstacle that's closer
                    obs_cx = obs.x + obs.w // 2
                    if ox <= obs_cx:
                        detour_x = obs.x - 30 - ox  # go left of obstacle
                    else:
                        detour_x = obs.x + obs.w + 30 - ox  # go right
                    mid_y = (obs.y - oy) if exit_side == "bottom" else (obs.y + obs.h - oy)
                    pts = [[0, 0], [0, mid_y], [detour_x, mid_y],
                           [detour_x, dy - junction_offset], [0, dy - junction_offset], [0, dy]]
                    break
        return ox, oy, pts, None, None
    if exit_side in ("left", "right") and abs(dy) < align_threshold:
        return ox, oy, [[0, 0], [dx, 0]], None, None

    # Pattern 2: ELBOW -- offset elements, needs bends
    #
    # Perpendicular case (e.g. exit=left, enter=top): use a clean 3-point
    # L-path that goes horizontal to align with the target, then straight
    # down (or vice versa). This avoids the 4-point zigzag.
    exit_is_horizontal = exit_side in ("left", "right")
    enter_is_vertical = enter_side in ("top", "bottom")
    exit_is_vertical = exit_side in ("top", "bottom")
    enter_is_horizontal = enter_side in ("left", "right")

    if exit_is_horizontal and enter_is_vertical:
        # L-path: go horizontal to align with target center, then vertical
        return ox, oy, [[0, 0], [dx, 0], [dx, dy]], None, None
    if exit_is_vertical and enter_is_horizontal:
        # L-path: go vertical to align with target center, then horizontal
        return ox, oy, [[0, 0], [0, dy], [dx, dy]], None, None

    # Same-axis elbow (exit and enter are both vertical or both horizontal)
    if exit_is_vertical:
        # Vertical-first: down/up to junction, then horizontal, then to target
        jy = junction_offset if exit_side == "bottom" else -junction_offset
        pts = [[0, 0], [0, jy], [dx, jy], [dx, dy]]
        # Check for collisions and reroute if needed
        if obstacles:
            for obs in obstacles:
                if _path_hits_obstacle(ox, oy, pts, obs):
                    # Route around: offset the horizontal junction to clear obstacle
                    obs_bottom = obs.y + obs.h
                    obs_top = obs.y
                    if exit_side == "bottom":
                        # Go further down past the obstacle before turning horizontal
                        clear_y = obs_bottom + 30 - oy
                        pts = [[0, 0], [0, clear_y], [dx, clear_y], [dx, dy]]
                    else:
                        clear_y = obs_top - 30 - oy
                        pts = [[0, 0], [0, clear_y], [dx, clear_y], [dx, dy]]
                    break
        return ox, oy, pts, None, None
    else:
        # Horizontal-first: right/left to junction, then vertical, then to target
        jx = junction_offset if exit_side == "right" else -junction_offset
        return ox, oy, [[0, 0], [jx, 0], [jx, dy], [dx, dy]], None, None


def _compute_stagger_offsets(
    count: int, spacing: int = 20
) -> list[int]:
    """Compute stagger offsets for fan-out/convergence arrows.

    Centers the group: for count=3, returns [-20, 0, 20].
    For count=1, returns [0].
    """
    if count <= 1:
        return [0]
    half = (count - 1) / 2
    return [int((i - half) * spacing) for i in range(count)]


def _detect_cross_patterns(
    conv_groups: dict[tuple[str, str], list[int]],
    connections: list[Connection],
    default_junction: int = 50,
) -> dict[int, int]:
    """Detect 2-to-2 cross-patterns via shared destinations.

    When two sources each connect to the same two destinations, the arrows
    cross. This function assigns staggered junction depths so the crossing
    arrows don't overlap at the junction point.

    Uses proven junction ratios from manual calibration:
    - Inner arrows: junction_offset * 0.4 (~19px at default 50)
    - Outer arrows: junction_offset * 0.7 (~31.5px at default 50)

    Returns a dict mapping connection index to custom junction offset.
    """
    junction_overrides: dict[int, int] = {}
    seen_pairs: set[tuple[str, str]] = set()

    for (dst_id, enter_side), indices in conv_groups.items():
        if len(indices) < 2:
            continue
        sources = {connections[j].src_id for j in indices}
        if len(sources) < 2:
            continue
        # Check if these sources also share another destination
        for (dst_id2, _), indices2 in conv_groups.items():
            if dst_id2 == dst_id:
                continue
            sources2 = {connections[j].src_id for j in indices2}
            shared = sources & sources2
            if len(shared) >= 2:
                # Avoid processing the same pair twice
                pair_key = tuple(sorted([dst_id, dst_id2]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                # 2-to-2 pattern found -- assign staggered junctions
                inner_junction = int(default_junction * 0.4)
                outer_junction = int(default_junction * 0.7)
                for j in indices:
                    junction_overrides[j] = inner_junction
                for j in indices2:
                    junction_overrides[j] = outer_junction
    return junction_overrides


# ---------------------------------------------------------------------------
# Diagram class -- the public API
# ---------------------------------------------------------------------------
class Diagram:
    """Declarative diagram builder with section-based layout.

    Usage:
        d = Diagram(profile="internal", title="Pipeline")
        with d.section("inputs", layout="row"):
            d.node("a", "Node A", style="trigger")
            d.node("b", "Node B", style="primary")
        d.connect("a", "b")
        d.render("output.excalidraw")
    """

    def __init__(self, profile: str = "internal", title: str = "",
                 subtitle: str = ""):
        if profile not in PROFILES:
            raise ValueError(
                f"Unknown profile '{profile}'. Choose from: {list(PROFILES.keys())}"
            )
        self.profile_name = profile
        self.profile = PROFILES[profile]
        self.title = title
        self.subtitle = subtitle
        self.sections: list[Section] = []
        self.nodes_by_id: dict[str, Node] = {}
        self.connections: list[Connection] = []
        self.annotations: list[Annotation] = []
        self._callouts: list[Callout] = []
        self._current_section: Section | None = None
        self._last_step_marker_id: str | None = None
        # Track step markers for special rendering (circle + label box)
        # Maps node_id -> (number, circle_id)
        self._step_markers: dict[str, tuple[int, str]] = {}
        # Track sidebar widths for reducing content usable_width
        # Maps "left"/"right" to sidebar_width (px)
        self._sidebar_widths: dict[str, int] = {}
        # Track sidebar sections for special rendering (dashed container)
        self._sidebar_sections: dict[str, Section] = {}
        # Timeline header data (set by timeline_header())
        self._timeline_header_data: dict | None = None

    @contextmanager
    def section(
        self,
        id: str,
        layout: str = "row",
        start_width: int | None = None,
        end_width: int | None = None,
        x_bias: str = "right",
        entry_gap: int = 80,
        position: str = "right",
        sidebar_width: int = 260,
    ):
        """Context manager for declaring a section of nodes.

        Args:
            id: Unique section identifier.
            layout: "row" (horizontal), "stack" (vertical), "funnel" (tapered),
                    "timeline" (vertical spine with dots and branching content),
                    or "sidebar" (side panel for legends/stats).
            start_width: Funnel mode -- width of first (widest) stage in pixels.
            end_width: Funnel mode -- width of last (narrowest) stage in pixels.
            x_bias: Timeline mode -- "left" or "right", which side content branches to.
            entry_gap: Timeline mode -- vertical spacing between entries in pixels.
            position: Sidebar mode -- "left" or "right" (default "right").
            sidebar_width: Sidebar mode -- width of the sidebar panel in pixels.
        """
        if layout not in ("row", "stack", "funnel", "timeline", "sidebar"):
            raise ValueError(f"Layout must be 'row', 'stack', 'funnel', 'timeline', or 'sidebar', got '{layout}'")
        sec = Section(
            id=id, layout=layout,
            start_width=start_width, end_width=end_width,
            x_bias=x_bias, entry_gap=entry_gap,
            position=position, sidebar_width=sidebar_width,
        )
        self.sections.append(sec)
        self._current_section = sec
        self._last_step_marker_id = None  # reset per-section step chaining
        try:
            yield sec
        finally:
            self._current_section = None
            # Track sidebar width for content width reduction
            if layout == "sidebar":
                self._sidebar_widths[position] = sidebar_width
                self._sidebar_sections[sec.id] = sec

    def node(self, id: str, text: str, style: str = "primary",
             inner_of: str | None = None) -> None:
        """Declare a node in the current section.

        Args:
            id: Unique node identifier (used in connect()).
            text: Display text (use \\n for line breaks).
            style: Semantic style name from STYLES dict. Unknown falls back to 'primary'.
            inner_of: Optional style name for breadcrumb rendering -- fill comes from
                       this style, stroke from the node's own style.
        """
        if self._current_section is None:
            raise RuntimeError(
                "node() must be called inside a section() context manager"
            )
        if id in self.nodes_by_id:
            raise ValueError(f"Duplicate node id: '{id}'")
        # Validate style -- fall back to primary silently
        if style not in STYLES:
            style = "primary"
        n = Node(id=id, text=text, style=style, section_id=self._current_section.id,
                 inner_of=inner_of)
        self._current_section.nodes.append(n)
        self.nodes_by_id[id] = n

    def connect(
        self,
        src: str,
        dst: str,
        label: str | None = None,
        exit: str | None = None,
        enter: str | None = None,
        dashed: bool = False,
    ) -> None:
        """Declare a connection between two nodes.

        Arrow routing is computed at render() time (Plan 02 implements full routing).

        Args:
            src: Source node id.
            dst: Destination node id.
            label: Optional arrow label text (deferred to v2).
            exit: Exit side ("top", "bottom", "left", "right") or None for auto.
            enter: Entry side or None for auto.
            dashed: If True, render arrow with dashed stroke style.
        """
        self.connections.append(
            Connection(src_id=src, dst_id=dst, label=label,
                       exit_side=exit, enter_side=enter, dashed=dashed)
        )

    def annotate(
        self, target: str, text: str, side: str = "right",
        color: str | None = None,
    ) -> None:
        """Add a text annotation positioned relative to a node.

        Args:
            target: Node id to annotate.
            text: Annotation text.
            side: Position relative to target: "right", "left", or "below".
            color: Text color override. If None, auto-derives from target node's
                   stroke color for semantic consistency.
        """
        self.annotations.append(Annotation(target_id=target, text=text, side=side,
                                            color=color))

    def callout(self, text: str, position: str = "bottom",
                style: str = "decision", width: int | None = None) -> None:
        """Add a floating callout box (not part of section flow).

        Args:
            text: Callout body text.
            position: "top" (above sections) or "bottom" (below sections).
            style: Semantic style name for fill/stroke colors.
            width: Box width in px; auto-computed from text if None.
        """
        if style not in STYLES:
            style = "decision"
        self._callouts.append(Callout(text=text, position=position,
                                       style=style, width=width))

    def timeline_header(
        self, labels: list[str], y_offset: int = 0
    ) -> None:
        """Add a horizontal timeline header with dots and labels above sections.

        Renders a horizontal line spanning the usable content width, with
        evenly-spaced filled circles (12px diameter, primary blue) and labels
        below each dot. Call BEFORE section definitions -- reserves vertical
        space automatically.

        Args:
            labels: List of label strings (e.g. ["Q1", "Q2", "Q3", "Q4"]).
            y_offset: Additional vertical offset from top in pixels.
        """
        self._timeline_header_data = {
            "labels": labels,
            "y_offset": y_offset,
        }

    def step_marker(
        self, id: str, number: int, text: str, style: str = "primary",
        width: int | None = None,
    ) -> None:
        """Create a numbered step marker (circle with number + label box).

        Creates a composite element: 36px number circle + label box to the right.
        If this is not the first step marker in the section, auto-connects from
        the previous step marker's label box to this one's circle.

        The label box is registered as a regular node (using 'id'), so external
        connect() calls can link to/from step markers.

        Args:
            id: Unique identifier for this step marker (used as the label box ID).
            number: Step number displayed inside the circle.
            text: Label text displayed in the box to the right of the circle.
            style: Semantic style name from STYLES dict.
            width: Optional minimum width for the label box in pixels.
        """
        if self._current_section is None:
            raise RuntimeError(
                "step_marker() must be called inside a section() context manager"
            )
        if id in self.nodes_by_id:
            raise ValueError(f"Duplicate node id: '{id}'")
        if style not in STYLES:
            style = "primary"

        circle_id = f"__step_circle_{id}__"
        self._step_markers[id] = (number, circle_id)

        # Register as a regular node so layout_section positions it
        n = Node(id=id, text=text, style=style, section_id=self._current_section.id,
                 fixed_width=width)
        self._current_section.nodes.append(n)
        self.nodes_by_id[id] = n

        # Auto-connect from previous step marker to this one
        if self._last_step_marker_id is not None:
            self.connections.append(
                Connection(
                    src_id=self._last_step_marker_id,
                    dst_id=id,
                    label=None,
                    exit_side=None,
                    enter_side=None,
                )
            )
        self._last_step_marker_id = id

    def render(self, output_path: str) -> None:
        """Compute layout and write the .excalidraw JSON file.

        Raises:
            ValueError: If LinkedIn profile constraints are violated.
        """
        reset_seeds()
        canvas_w, canvas_h = self.profile["canvas"]
        roughness = self.profile["roughness"]
        elements: list[dict] = []

        # -- Font assignments from profile --
        title_font = self.profile.get("title_font", DEFAULT_FONT_FAMILY)
        body_font = self.profile.get("body_font", DEFAULT_FONT_FAMILY)
        subtitle_font = self.profile.get("subtitle_font", body_font)
        number_font = self.profile.get("number_font", DEFAULT_FONT_FAMILY)
        title_line_height = FONT_METRICS.get(title_font, {}).get("lineHeight", 1.2)
        body_line_height = FONT_METRICS.get(body_font, {}).get("lineHeight", 1.2)

        # -- Compute usable width early (needed for title centering) --
        usable_w = canvas_w
        sidebar_margin = 30
        for _side, sb_w in self._sidebar_widths.items():
            usable_w -= sb_w + sidebar_margin

        # -- Title --
        title_y = 40
        if self.title:
            title_text = self.title.upper() if self.profile.get("title_transform") == "uppercase" else self.title
            title_size = self.profile["title_size"]

            # Gap 4: Auto-shrink title to fit single line
            # Only apply when title_max_lines == 1 and title has no explicit
            # newlines (user explicitly wants multi-line if \n is present).
            title_max_lines = self.profile.get("title_max_lines", 1)
            if title_max_lines == 1 and "\n" not in title_text:
                title_margin = 40  # side breathing room
                max_title_w = usable_w - title_margin
                measured_w = estimate_text_size(title_text, title_size, font_family=title_font)[0]
                while measured_w > max_title_w and title_size > 18:
                    title_size -= 2
                    measured_w = estimate_text_size(title_text, title_size, font_family=title_font)[0]

            title_w = max(
                estimate_text_size(title_text, title_size, font_family=title_font)[0],
                400,
            )
            title_el = _T(
                id="__title__",
                x=usable_w // 2 - title_w // 2,
                y=title_y,
                text=title_text,
                size=title_size,
                color=TEXT_COLORS["title"],
                align="center",
                w=title_w,
                roughness=roughness,
                font_family=title_font,
            )
            elements.append(title_el)
            title_lines = title_text.count("\n") + 1
            title_el_bottom = title_y + int(title_size * title_line_height * title_lines)
            title_y = title_el_bottom + self.profile.get("title_gap", 20)

            # Gap 5: Enforce minimum title-to-subtitle gap (floor)
            min_ts_gap = self.profile.get("min_title_subtitle_gap", 20)
            title_y = max(title_y, title_el_bottom + min_ts_gap)

        # -- Subtitle --
        if self.subtitle:
            sub_size = self.profile.get("subtitle_size", 20)
            subtitle_line_height = FONT_METRICS.get(subtitle_font, {}).get("lineHeight", 1.2)
            sub_w, sub_h = estimate_text_size(self.subtitle, sub_size, font_family=subtitle_font)
            sub_w = max(sub_w, 300)
            elements.append(_T(
                id="__subtitle__",
                x=usable_w // 2 - sub_w // 2,
                y=int(title_y),
                text=self.subtitle,
                size=sub_size,
                color=TEXT_COLORS["subtitle"],
                align="center",
                w=sub_w,
                roughness=roughness,
                font_family=subtitle_font,
            ))
            subtitle_el_bottom = int(title_y) + int(sub_size * subtitle_line_height)
            title_y += sub_size * subtitle_line_height + self.profile.get("subtitle_gap", 16)

            # Gap 5: Enforce minimum subtitle-to-content gap (floor)
            min_sc_gap = self.profile.get("min_subtitle_content_gap", 30)
            title_y = max(title_y, subtitle_el_bottom + min_sc_gap)

        # -- Timeline header (horizontal line + dots + labels) --
        if self._timeline_header_data is not None:
            th_labels = self._timeline_header_data["labels"]
            th_y_offset = self._timeline_header_data.get("y_offset", 0)
            th_y = int(title_y) + 20 + th_y_offset
            dot_size = 12
            label_font = max(self.profile["body_size"] - 2, 12)
            n_labels = len(th_labels)
            if n_labels > 0:
                # Margins from canvas edges
                th_margin = 80
                th_width = usable_w - th_margin * 2
                # Horizontal line
                elements.append(_LINE(
                    id="__timeline_header_line__",
                    x=th_margin,
                    y=th_y + dot_size // 2,
                    pts=[[0, 0], [th_width, 0]],
                    stroke=TEXT_COLORS["body"],
                    sw=2,
                    roughness=roughness,
                ))
                # Dots and labels
                for li, lbl in enumerate(th_labels):
                    if n_labels == 1:
                        lx = th_margin + th_width // 2
                    else:
                        lx = th_margin + int(li * th_width / (n_labels - 1))
                    # Filled dot
                    elements.append(_ELLIPSE(
                        id=f"__th_dot_{li}__",
                        x=lx - dot_size // 2,
                        y=th_y,
                        w=dot_size,
                        h=dot_size,
                        fill="#3b82f6",
                        stroke="#1e3a5f",
                        sw=1,
                        roughness=roughness,
                    ))
                    # Label below dot
                    lbl_w, lbl_h = estimate_text_size(lbl, label_font, font_family=body_font)
                    elements.append(_T(
                        id=f"__th_label_{li}__",
                        x=lx - lbl_w // 2,
                        y=th_y + dot_size + 6,
                        text=lbl,
                        size=label_font,
                        color=TEXT_COLORS["body"],
                        align="center",
                        w=lbl_w,
                        roughness=roughness,
                        font_family=body_font,
                    ))
                # Reserve vertical space (dots + labels + gap)
                title_y = th_y + dot_size + 6 + int(label_font * body_line_height) + self.profile.get("header_gap", 28)

        # -- Reserve space for top callouts --
        content_start_y = int(title_y) + self.profile.get("header_gap", 28)
        current_y = content_start_y
        top_callout_space = 0
        body_size_pre = self.profile["body_size"]
        callout_gap_pre = self.profile.get("callout_gap", 20)
        for co in self._callouts:
            if co.position == "top":
                co_font_pre = co.font_size or body_size_pre
                tw, th = estimate_text_size(co.text, co_font_pre, font_family=body_font)
                top_callout_space += th + 30 + callout_gap_pre  # height + padding + gap
        current_y += top_callout_space

        # -- Layout sections --
        for sec in self.sections:
            # Sidebar sections use full canvas_w for absolute positioning;
            # content sections use usable_w to avoid sidebar overlap.
            effective_w = canvas_w if sec.layout == "sidebar" else usable_w
            # If sidebar is on right, content sections use left-aligned usable_w.
            # If sidebar is on left, content sections need x offset (handled
            # by centering within usable_w starting from sidebar width).
            # For simplicity: offset content x when left sidebar exists.
            current_y = layout_section(
                nodes=sec.nodes,
                layout=sec.layout,
                canvas_width=effective_w,
                start_y=current_y,
                profile=self.profile,
                start_width=sec.start_width,
                end_width=sec.end_width,
                x_bias=sec.x_bias,
                entry_gap=sec.entry_gap,
                position=sec.position,
                sidebar_width=sec.sidebar_width,
            )

        # -- LinkedIn enforcement --
        total_nodes = sum(len(s.nodes) for s in self.sections)
        if self.profile_name == "linkedin":
            if total_nodes > self.profile["max_elements"]:
                raise ValueError(
                    f"LinkedIn profile allows max {self.profile['max_elements']} "
                    f"elements, but diagram has {total_nodes}. "
                    f"Reduce element count or use a different profile."
                )
            min_font = 20
            if self.profile["body_size"] < min_font:
                raise ValueError(
                    f"LinkedIn profile requires minimum {min_font}px font size."
                )

        # -- Build rectangle + text elements for each node --
        # First pass: collect arrow bindings per node
        arrow_bindings: dict[str, list[str]] = {}
        for i, conn in enumerate(self.connections):
            arrow_id = f"__arrow_{i}__"
            arrow_bindings.setdefault(conn.src_id, []).append(arrow_id)
            arrow_bindings.setdefault(conn.dst_id, []).append(arrow_id)

        # Collect timeline section IDs and their metadata for special rendering
        timeline_sections: dict[str, Section] = {}
        for sec in self.sections:
            if sec.layout == "timeline":
                timeline_sections[sec.id] = sec

        # Build timeline spine lines and dots
        for sec_id, sec in timeline_sections.items():
            if not sec.nodes:
                continue
            dot_size = 12
            # Compute spine x from the first node's position
            if sec.x_bias == "right":
                spine_x = sec.nodes[0].x - 40  # content_offset back to spine
            else:
                spine_x = sec.nodes[0].x + sec.nodes[0].w + 40

            # Spine line: from first dot to last dot (skip if only 1 entry)
            if len(sec.nodes) > 1:
                first_y = sec.nodes[0].y + sec.nodes[0].h // 2
                last_y = sec.nodes[-1].y + sec.nodes[-1].h // 2
                spine_height = last_y - first_y
                elements.append(_LINE(
                    id=f"__timeline_spine_{sec_id}__",
                    x=spine_x,
                    y=first_y,
                    pts=[[0, 0], [0, spine_height]],
                    stroke=TEXT_COLORS["body"],
                    sw=2,
                    dashed=True,
                    roughness=roughness,
                ))

            # Dots at each entry
            for node in sec.nodes:
                style = STYLES[node.style]
                dot_y = node.y + node.h // 2
                # Center correction (Pitfall 2): ellipse x/y is top-left corner
                dot_id = f"__dot_{node.id}__"
                elements.append(_ELLIPSE(
                    id=dot_id,
                    x=spine_x - dot_size // 2,
                    y=dot_y - dot_size // 2,
                    w=dot_size,
                    h=dot_size,
                    fill=style["stroke"],
                    stroke=style["stroke"],
                    sw=1,
                    bound_arrows=arrow_bindings.get(node.id),
                    roughness=roughness,
                ))

        # Build sidebar dashed container rectangles
        for sec_id, sec in self._sidebar_sections.items():
            if not sec.nodes:
                continue
            margin = 30
            inner_pad = 16
            if sec.position == "right":
                container_x = canvas_w - sec.sidebar_width - margin
            else:
                container_x = margin
            # Container spans from title area to below last node
            container_y = int(title_y) + 10
            last_node = sec.nodes[-1]
            container_bottom = last_node.y + last_node.h + inner_pad
            container_h = container_bottom - container_y
            # Dashed container rectangle
            container_id = f"__sidebar_container_{sec_id}__"
            elements.append(_R(
                id=container_id,
                x=container_x,
                y=container_y,
                w=sec.sidebar_width,
                h=container_h,
                fill="#f8fafc",
                stroke="#94a3b8",
                sw=1,
                dashed=True,
                roughness=roughness,
            ))
            # Title text at top of sidebar
            title_text = sec.id.replace("_", " ").title()
            title_tw, title_th = estimate_text_size(
                title_text, self.profile["body_size"], font_family=body_font
            )
            elements.append(_T(
                id=f"__sidebar_title_{sec_id}__",
                x=container_x + (sec.sidebar_width - title_tw) // 2,
                y=container_y + 8,
                text=title_text,
                size=self.profile["body_size"],
                color=TEXT_COLORS["subtitle"],
                align="center",
                w=title_tw,
                h=title_th,
                roughness=roughness,
                font_family=body_font,
            ))

        # Pre-compute consistent circle x for step markers (all circles
        # must align vertically like bullet points, regardless of box width)
        _step_circle_x: int | None = None
        if self._step_markers:
            step_nodes = [self.nodes_by_id[sid] for sid in self._step_markers]
            min_x = min(n.x for n in step_nodes)
            _step_circle_x = min_x - 36 - 12  # circle_d + circle_gap

        _deferred_circles: list[dict[str, Any]] = []  # circles emitted after arrows for z-order

        for node in self.nodes_by_id.values():
            style = STYLES[node.style]
            # Breadcrumb inner_of: fill from inner_of style, stroke from own style
            if node.inner_of and node.inner_of in STYLES:
                node_fill = STYLES[node.inner_of]["fill"]
                node_stroke = style["stroke"]
            else:
                node_fill = style["fill"]
                node_stroke = style["stroke"]
            text_id = f"{node.id}_t"
            # Text color: inner_of always on_light; otherwise WCAG luminance
            if node.inner_of and node.inner_of in STYLES:
                text_color = TEXT_COLORS["on_light"]  # always readable on pastel fills
            elif _is_dark_fill(node_fill):
                text_color = TEXT_COLORS["on_dark"]   # white on dark fills
            else:
                text_color = TEXT_COLORS["on_light"]  # dark gray on light fills

            # Timeline nodes: always render an invisible container rectangle
            # so arrows can bind to them, plus text inside.
            if node.section_id in timeline_sections:
                has_multiline = "\n" in node.text
                rect = _R(
                    id=node.id,
                    x=node.x,
                    y=node.y,
                    w=node.w,
                    h=node.h,
                    fill=node_fill if has_multiline else "transparent",
                    stroke=node_stroke if has_multiline else "transparent",
                    sw=1 if has_multiline else 0,
                    bound_text=text_id,
                    bound_arrows=arrow_bindings.get(node.id),
                    dashed=has_multiline,
                    roughness=roughness,
                )
                text_w, text_h = estimate_text_size(
                    node.text, self.profile["body_size"], font_family=body_font
                )
                text = _T(
                    id=text_id,
                    x=node.x,
                    y=node.y,
                    text=node.text,
                    size=self.profile["body_size"],
                    color=text_color if has_multiline else style["stroke"],
                    container=node.id,
                    cw=node.w,
                    ch=node.h,
                    roughness=roughness,
                    font_family=body_font,
                )
                elements.append(rect)
                elements.append(text)
                continue

            # Step marker nodes: render circle + label box composite
            if node.id in self._step_markers:
                step_num, circle_id = self._step_markers[node.id]
                circle_d = 36  # proven diameter from linkedin-portrait.py
                circle_gap = 12  # gap between circle and label box

                # Circle positioned to the left, centered on box midline,
                # same x for all step markers (vertical bullet-point column)
                circle_x = _step_circle_x if _step_circle_x is not None else (node.x - circle_d - circle_gap)
                circle_y = node.y + (node.h - circle_d) // 2
                num_text_id = f"{circle_id}_t"

                # Defer circle + number to after arrows for correct z-order
                _deferred_circles.append(_ELLIPSE(
                    id=circle_id,
                    x=circle_x,
                    y=circle_y,
                    w=circle_d,
                    h=circle_d,
                    fill=style["fill"],
                    stroke=style["stroke"],
                    sw=2,
                    bound_text=num_text_id,
                    roughness=roughness,
                ))
                # Number text centered in circle (18px font, proven ratio)
                _deferred_circles.append(_T(
                    id=num_text_id,
                    x=circle_x,
                    y=circle_y,
                    text=str(step_num),
                    size=18,
                    color=style["stroke"],
                    align="center",
                    container=circle_id,
                    cw=circle_d,
                    ch=circle_d,
                    roughness=roughness,
                    font_family=number_font,
                ))
                # Label box (standard rectangle + text, using node position)
                rect = _R(
                    id=node.id,
                    x=node.x,
                    y=node.y,
                    w=node.w,
                    h=node.h,
                    fill=node_fill,
                    stroke=node_stroke,
                    bound_text=text_id,
                    bound_arrows=arrow_bindings.get(node.id),
                    roughness=roughness,
                )
                # Use container dimensions for centering (same fix as general nodes)
                text = _T(
                    id=text_id,
                    x=node.x,
                    y=node.y,
                    text=node.text,
                    size=self.profile["body_size"],
                    color=text_color,
                    container=node.id,
                    cw=node.w,
                    ch=node.h,
                    roughness=roughness,
                    font_family=body_font,
                )
                elements.append(rect)
                elements.append(text)
                continue

            rect = _R(
                id=node.id,
                x=node.x,
                y=node.y,
                w=node.w,
                h=node.h,
                fill=node_fill,
                stroke=node_stroke,
                bound_text=text_id,
                bound_arrows=arrow_bindings.get(node.id),
                roughness=roughness,
            )
            # Text uses container dimensions -- Excalidraw centers via
            # textAlign:"center" + verticalAlign:"middle" when containerId is set.
            # Using container w/h (not text w/h) prevents centering offset from
            # estimate_text_size() disagreeing with Excalidraw's text measurement.
            text = _T(
                id=text_id,
                x=node.x,
                y=node.y,
                text=node.text,
                size=self.profile["body_size"],
                color=text_color,
                container=node.id,
                cw=node.w,
                ch=node.h,
                roughness=roughness,
                font_family=body_font,
            )
            elements.append(rect)
            elements.append(text)

        # -- Pre-compute arrow sides for annotation collision avoidance --
        all_nodes = list(self.nodes_by_id.values())
        resolved_sides: list[tuple[str, str]] = []
        for conn in self.connections:
            src = self.nodes_by_id.get(conn.src_id)
            dst = self.nodes_by_id.get(conn.dst_id)
            if src is None or dst is None:
                resolved_sides.append(("bottom", "top"))
                continue
            ex = conn.exit_side or _infer_exit_side(src, dst, all_nodes)
            en = conn.enter_side or _infer_enter_side(src, dst, all_nodes)
            resolved_sides.append((ex, en))

        # -- Arrows (full routing with waypoints, bindings, staggering) --
        # Arrows computed BEFORE annotations so annotation placement can
        # check for collisions against actual arrow paths.

        # Pass 1.5: compute stagger per (src_id, exit_side) group
        fan_groups: dict[tuple[str, str], list[int]] = {}
        conv_groups: dict[tuple[str, str], list[int]] = {}
        for i, conn in enumerate(self.connections):
            ex_side, en_side = resolved_sides[i]
            fan_groups.setdefault((conn.src_id, ex_side), []).append(i)
            conv_groups.setdefault((conn.dst_id, en_side), []).append(i)

        stagger_map: dict[int, int] = {}
        for key, indices in fan_groups.items():
            if len(indices) > 1:
                offsets = _compute_stagger_offsets(len(indices))
                for idx, offset in zip(indices, offsets):
                    stagger_map[idx] = offset
        for key, indices in conv_groups.items():
            if len(indices) > 1:
                offsets = _compute_stagger_offsets(len(indices))
                for idx, offset in zip(indices, offsets):
                    if idx not in stagger_map:
                        stagger_map[idx] = offset

        # Pass 1.5.1: detect cross-patterns for junction stagger
        junction_overrides = _detect_cross_patterns(
            conv_groups, self.connections
        )

        # Build phantom obstacles for step marker circles
        _circle_obstacles: list[Node] = []
        if self._step_markers and _step_circle_x is not None:
            circle_d = 36
            for sm_id in self._step_markers:
                sm_node = self.nodes_by_id.get(sm_id)
                if sm_node is None:
                    continue
                circle_y = sm_node.y + (sm_node.h - circle_d) // 2
                _circle_obstacles.append(Node(
                    id=f"__circle_obs_{sm_id}__",
                    text="",
                    x=_step_circle_x,
                    y=circle_y,
                    w=circle_d,
                    h=circle_d,
                ))

        # Pass 2: compute waypoints, build arrow elements, collect paths
        arrow_paths: list[tuple[int, int, list[list[int]]]] = []
        for i, conn in enumerate(self.connections):
            src = self.nodes_by_id.get(conn.src_id)
            dst = self.nodes_by_id.get(conn.dst_id)
            if src is None or dst is None:
                continue
            arrow_id = f"__arrow_{i}__"

            exit_side, enter_side = resolved_sides[i]

            # Compute stagger offset
            stagger = stagger_map.get(i, 0)

            # Determine if this is a loop arrow (same exit and enter side)
            is_loop = exit_side == enter_side

            # Compute waypoints with collision avoidance
            obstacles = [n for n in all_nodes
                         if n.id not in (conn.src_id, conn.dst_id)]
            obstacles.extend(_circle_obstacles)
            origin_x, origin_y, pts, actual_exit, actual_enter = compute_waypoints(
                src, dst, exit_side, enter_side,
                stagger_offset=stagger,
                obstacles=obstacles,
                junction_override=junction_overrides.get(i),
            )
            arrow_paths.append((origin_x, origin_y, pts))

            # Use actual sides from routing when pattern overrides (e.g. feedback)
            bind_exit = actual_exit or exit_side
            bind_enter = actual_enter or enter_side

            # Build bindings -- ALL arrows use orbit mode with fixedPoint
            if is_loop:
                # Loop arrows use separated anchor points for visual clarity
                is_self_loop = conn.src_id == conn.dst_id
                if is_self_loop and bind_exit in ("right", "left"):
                    start_fp = f"{bind_exit}_top"
                    end_fp = f"{bind_exit}_bottom"
                elif is_self_loop and bind_exit in ("top", "bottom"):
                    start_fp = f"{bind_exit}_left"
                    end_fp = f"{bind_exit}_right"
                else:
                    start_fp = bind_exit
                    end_fp = bind_enter
                start_bind = _make_binding(conn.src_id, start_fp)
                end_bind = _make_binding(conn.dst_id, end_fp)
            else:
                # Normal arrows use exit/enter side as fixedPoint
                start_bind = _make_binding(conn.src_id, bind_exit)
                end_bind = _make_binding(conn.dst_id, bind_enter)

            elements.append(
                _A(
                    id=arrow_id,
                    x=origin_x,
                    y=origin_y,
                    pts=pts,
                    stroke=STYLES.get(src.style, STYLES["primary"])["stroke"],
                    start_binding=start_bind,
                    end_binding=end_bind,
                    style="dashed" if conn.dashed else "solid",
                    roughness=roughness,
                )
            )

        # -- Emit deferred step marker circles (z-order: above arrows) --
        elements.extend(_deferred_circles)

        # -- Annotations (placed after arrows for path collision avoidance) --
        placed_annotations: list[tuple[int, int, int, int]] = []
        for ann in self.annotations:
            target = self.nodes_by_id.get(ann.target_id)
            if target is None:
                continue
            ann_font = max(self.profile["body_size"] - 2, self.profile.get("min_annotation_size", 13))
            ann_w, ann_h = estimate_text_size(ann.text, ann_font, font_family=body_font)
            margin = 20

            # For timeline nodes, position left annotations relative to the
            # spine dot (not the text box), which is 46px left of node.x.
            # For step markers, use _step_circle_x.
            is_timeline_node = target.section_id in timeline_sections
            if is_timeline_node:
                # Dot is at spine_x - dot_size/2; spine_x = node.x - 40
                dot_left_edge = target.x - 40 - 6  # spine_x - dot_size/2
                left_ann_x = dot_left_edge - ann_w - margin
            elif _step_circle_x is not None and target.id in self._step_markers:
                left_ann_x = _step_circle_x - ann_w - margin - 30
            else:
                left_ann_x = target.x - ann_w - margin

            # Standard positions + shifted variants to dodge center arrows
            candidates = {
                "right": (target.x + target.w + margin,
                          target.y + target.h // 2 - ann_h // 2),
                "left":  (left_ann_x,
                          target.y + target.h // 2 - ann_h // 2),
                "below": (target.x + target.w // 2 - ann_w // 2,
                          target.y + target.h + margin // 2),
                "below_left": (target.x - ann_w // 2,
                               target.y + target.h + margin // 2),
                "below_right": (target.x + target.w - ann_w // 2,
                                target.y + target.h + margin // 2),
                "right_low": (target.x + target.w + margin,
                              target.y + target.h - ann_h),
                "left_low": (left_ann_x,
                             target.y + target.h - ann_h),
            }

            def _ann_collides(px: int, py: int, pw: int, ph: int) -> bool:
                # Check node collisions (including step marker circles)
                for n in self.nodes_by_id.values():
                    if n.id == ann.target_id:
                        continue
                    if (px < n.x + n.w + 5 and px + pw > n.x - 5
                            and py < n.y + n.h + 5 and py + ph > n.y - 5):
                        return True
                    # Also check step marker circle to the left of this node
                    if n.id in self._step_markers and _step_circle_x is not None:
                        cx, cy = _step_circle_x, n.y + (n.h - 36) // 2
                        cw, ch = 36, 36
                        if (px < cx + cw + 5 and px + pw > cx - 5
                                and py < cy + ch + 5 and py + ph > cy - 5):
                            return True
                # Check arrow path collisions
                for aox, aoy, apts in arrow_paths:
                    for j in range(len(apts) - 1):
                        if _segment_hits_box(
                            aox + apts[j][0], aoy + apts[j][1],
                            aox + apts[j + 1][0], aoy + apts[j + 1][1],
                            px, py, pw, ph, margin=8,
                        ):
                            return True
                # Check previously placed annotation collisions
                for pax, pay, paw, pah in placed_annotations:
                    if (px < pax + paw + 5 and px + pw > pax - 5
                            and py < pay + pah + 5 and py + ph > pay - 5):
                        return True
                return False

            # Try preferred side first, then shifted variants, then all others
            side_map = {
                "right": ["right", "right_low", "below_right", "left", "left_low", "below_left", "below"],
                "left":  ["left", "left_low", "below_left", "right", "right_low", "below_right", "below"],
                "below": ["below", "below_left", "below_right", "right_low", "left_low", "right", "left"],
            }
            preferred_order = side_map.get(ann.side, list(candidates.keys()))
            ax, ay = candidates[ann.side]  # default
            chosen_side = ann.side
            for side in preferred_order:
                cx, cy = candidates[side]
                if not _ann_collides(cx, cy, ann_w, ann_h):
                    ax, ay = cx, cy
                    chosen_side = side
                    break
            placed_annotations.append((ax, ay, ann_w, ann_h))
            # Auto-derive annotation color from target node's stroke
            if ann.color:
                ann_color = ann.color
            elif target:
                ann_color = STYLES[target.style]["stroke"]
            else:
                ann_color = TEXT_COLORS["body"]
            # For left-side annotations, use right-align so the text right
            # edge stays at a fixed distance from the dot/node.
            is_left_ann = chosen_side.startswith("left")
            elements.append(
                _T(
                    id=f"__ann_{ann.target_id}_{ann.side}__",
                    x=ax,
                    y=ay,
                    text=ann.text,
                    size=ann_font,
                    color=ann_color,
                    align="right" if is_left_ann else "left",
                    w=ann_w,
                    roughness=roughness,
                    font_family=body_font,
                )
            )

        # -- Callout boxes (floating, not part of section flow) --
        # Top callouts placed in reserved space above sections.
        # Bottom callouts placed below all sections.
        body_size = self.profile["body_size"]
        content_bottom = current_y
        if self.nodes_by_id:
            content_bottom = max(n.y + n.h for n in self.nodes_by_id.values())
        top_y_cursor = content_start_y  # starts right after subtitle
        for i, co in enumerate(self._callouts):
            co_font = co.font_size or body_size
            text_w, text_h = estimate_text_size(co.text, co_font, font_family=body_font)
            co_w = co.width or max(text_w + 40, 200)
            co_h = text_h + 30  # 15px padding top/bottom
            co_x = usable_w // 2 - co_w // 2
            callout_gap = self.profile.get("callout_gap", 20)
            if co.position == "top":
                co_y = top_y_cursor
                top_y_cursor += co_h + callout_gap
            else:
                co_y = content_bottom + callout_gap
                content_bottom = co_y + co_h + 10
                current_y = co_y + co_h + 10
            sdata = STYLES.get(co.style, STYLES["decision"])
            fill, stroke = sdata["fill"], sdata["stroke"]
            rid = f"__callout_{i}__"
            tid = f"__callout_{i}_t__"
            elements.append(_R(
                id=rid, x=co_x, y=co_y, w=co_w, h=co_h,
                fill=fill, stroke=stroke, sw=1,
                bound_text=tid, dashed=True, roughness=roughness,
            ))
            elements.append(_T(
                id=tid, x=co_x, y=co_y, text=co.text,
                size=co_font, color=TEXT_COLORS["body"],
                align="center", container=rid,
                cw=co_w, ch=co_h, roughness=roughness,
                font_family=body_font,
            ))

        # -- Write output --
        doc = {
            "type": "excalidraw",
            "version": 2,
            "source": "layout-engine",
            "elements": elements,
            "appState": {
                "gridSize": None,
                "viewBackgroundColor": "#ffffff",
            },
            "files": {},
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
