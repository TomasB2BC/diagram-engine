"""
Layered Stack Diagram Builder
Demonstrates the layered architecture pattern: colored layers with description sidebar.
Canvas: 1400x1400, roughness 0
"""
import json
from pathlib import Path

elements = []
seed_counter = 100000

def next_seed():
    global seed_counter
    seed_counter += 1
    return seed_counter

def R(id, x, y, w, h, fill, stroke, sw=2, style="solid", roundness=3, bound_text=None, bound_arrows=None):
    be = []
    if bound_text:
        be.append({"id": bound_text, "type": "text"})
    if bound_arrows:
        for aid in bound_arrows:
            be.append({"id": aid, "type": "arrow"})
    return {
        "type": "rectangle", "id": id, "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
        "strokeWidth": sw, "strokeStyle": style, "roughness": 0, "opacity": 100,
        "angle": 0, "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": be if be else None,
        "link": None, "locked": False, "roundness": {"type": roundness}
    }

CHAR_WIDTH = {3: 0.60, 6: 0.60, 7: 0.58}
LINE_HT = {3: 1.2, 6: 1.25, 7: 1.15}

def T(id, x, y, w, h, text, size=16, color="#374151", align="center", valign="middle",
      container=None, family=6, cw=None, ch=None):
    line_height = LINE_HT.get(family, 1.25)
    char_w = CHAR_WIDTH.get(family, 0.58)
    text_w = int(max(len(line) for line in text.split("\n")) * size * char_w)
    text_h = int((text.count("\n") + 1) * size * line_height)
    if container and cw is not None and ch is not None:
        x = x + (cw - text_w) // 2
        y = y + (ch - text_h) // 2
        w = text_w
        h = text_h
    return {
        "type": "text", "id": id, "x": x, "y": y, "width": w, "height": h,
        "text": text, "originalText": text,
        "fontSize": size, "fontFamily": family,
        "textAlign": align, "verticalAlign": valign,
        "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False,
        "containerId": container, "lineHeight": line_height, "autoResize": True
    }

def A(id, x, y, pts, stroke="#374151", sw=1.5, start_bind=None, end_bind=None):
    return {
        "type": "arrow", "id": id, "x": x, "y": y,
        "width": abs(pts[-1][0] - pts[0][0]) if len(pts) > 1 else 0,
        "height": abs(pts[-1][1] - pts[0][1]) if len(pts) > 1 else 0,
        "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False, "points": pts,
        "startBinding": start_bind, "endBinding": end_bind,
        "startArrowhead": None, "endArrowhead": "triangle_outline",
        "roundness": {"type": 2}, "elbowed": True,
        "fixedSegments": None, "startIsSpecial": None, "endIsSpecial": None
    }

# Layout constants
CANVAS_W = 1400
LEFT_MARGIN = 40
LAYER_X = LEFT_MARGIN
LAYER_W = 800
DESC_GAP = 20
DESC_X = LAYER_X + LAYER_W + DESC_GAP
DESC_W = CANVAS_W - DESC_X - LEFT_MARGIN
TRANS_GAP = 48
INNER_BOX_H = 42
LAYER_HEIGHTS = [120, 120, 140, 120, 120]
TITLE_Y = 30
START_Y = 90

LAYERS = [
    {
        "name": "PRESENTATION",
        "fill": "#fed7aa", "stroke": "#c2410c", "text_color": "#9a3412",
        "items": ["Web Dashboard"],
        "desc": "User interface for reviewing data,\napproving actions, and\nmonitoring system health",
        "inner_stroke": "#c2410c",
    },
    {
        "name": "API GATEWAY",
        "fill": "#fef3c7", "stroke": "#b45309", "text_color": "#92400e",
        "items": ["REST API Server"],
        "desc": "Routes requests to services,\nhandles authentication,\nserves static assets",
        "inner_stroke": "#b45309",
    },
    {
        "name": "SERVICES",
        "fill": "#dbeafe", "stroke": "#1e40af", "text_color": "#1e3a5f",
        "items": ["Processing Engine", "Notification Service", "Sync Worker", "API Bridge"],
        "desc": "Core processing engines that\ntransform data, send alerts,\nand integrate services",
        "inner_stroke": "#1e40af",
    },
    {
        "name": "DATA LAYER",
        "fill": "#a7f3d0", "stroke": "#047857", "text_color": "#065f46",
        "items": ["PostgreSQL", "Document Store"],
        "desc": "Persistent storage for pipeline\noutputs, knowledge base,\nand structured records",
        "inner_stroke": "#047857",
    },
    {
        "name": "INTEGRATIONS",
        "fill": "#ddd6fe", "stroke": "#6d28d9", "text_color": "#5b21b6",
        "items": ["CRM", "Analytics", "Messaging"],
        "desc": "Third-party platforms providing\nexternal data, enrichment,\nand communication channels",
        "inner_stroke": "#6d28d9",
    },
]

TRANSITIONS = [
    "HTTP requests / webhooks",
    "Internal function calls",
    "SQL queries / document API",
    "REST APIs / webhooks",
]

# Title
elements.append(T("title", LEFT_MARGIN, TITLE_Y, 700, 40,
    "PLATFORM ARCHITECTURE", size=28, color="#1e40af", align="left", family=7))

# Build layers
y = START_Y
for i, layer in enumerate(LAYERS):
    layer_id = f"layer_{i}"
    LAYER_H = LAYER_HEIGHTS[i]

    elements.append(R(layer_id, LAYER_X, y, LAYER_W, LAYER_H, layer["fill"], layer["stroke"], sw=2))
    elements.append(T(f"layer_title_{i}", LAYER_X + 16, y + 10, 350, 22,
        layer["name"], size=18, color=layer["text_color"], align="left", family=7))

    num_items = len(layer["items"])
    inner_y = y + 50
    box_w = {1: 230, 2: 250, 3: 180}.get(num_items, 158)
    gap = 12
    inner_x_start = LAYER_X + 16

    for j, item in enumerate(layer["items"]):
        box_id = f"inner_{i}_{j}"
        bx = inner_x_start + j * (box_w + gap)
        elements.append(R(box_id, bx, inner_y, box_w, INNER_BOX_H,
            layer["fill"], layer["inner_stroke"], sw=1.5))
        elements.append(T(f"inner_text_{i}_{j}", bx, inner_y, box_w, INNER_BOX_H,
            item, size=14, color=layer["inner_stroke"], align="center",
            container=box_id, cw=box_w, ch=INNER_BOX_H))
        for el in elements:
            if el["id"] == box_id:
                el["boundElements"] = [{"id": f"inner_text_{i}_{j}", "type": "text"}]

    # Description box
    desc_id = f"desc_box_{i}"
    desc_text_id = f"desc_text_{i}"
    elements.append(R(desc_id, DESC_X, y, DESC_W, LAYER_H, "#f8fafc", "#e2e8f0", sw=1, bound_text=desc_text_id))
    elements.append(T(f"desc_label_{i}", DESC_X + 14, y + 8, 120, 16, "WHAT IT DOES", size=11, color="#94a3b8", align="left"))
    elements.append(T(desc_text_id, DESC_X + 14, y + 32, DESC_W - 28, LAYER_H - 42,
        layer["desc"], size=15, color="#64748b", align="left"))

    # Transition arrow
    if i < len(TRANSITIONS) and i < len(LAYERS) - 1:
        arrow_id = f"trans_arrow_{i}"
        arrow_x = LAYER_X + LAYER_W // 2
        elements.append(A(arrow_id, arrow_x, y + LAYER_H, [[0, 0], [0, TRANS_GAP]],
            stroke=layer["stroke"], sw=1.5,
            start_bind={"elementId": layer_id, "mode": "orbit", "fixedPoint": [0.5, 1.037]},
            end_bind={"elementId": f"layer_{i+1}", "mode": "orbit", "fixedPoint": [0.5, -0.037]}))
        for el in elements:
            if el["id"] == layer_id:
                if el["boundElements"] is None:
                    el["boundElements"] = []
                el["boundElements"].append({"id": arrow_id, "type": "arrow"})

        elements.append(T(f"trans_label_{i}", arrow_x + 16, y + LAYER_H + 12,
            250, 20, TRANSITIONS[i], size=13, color="#64748b", align="left"))

    y += LAYER_H + TRANS_GAP

# Add arrow bindings to receiving layers
for i in range(1, len(LAYERS)):
    arrow_id = f"trans_arrow_{i-1}"
    layer_id = f"layer_{i}"
    for el in elements:
        if el["id"] == layer_id:
            if el["boundElements"] is None:
                el["boundElements"] = []
            el["boundElements"].append({"id": arrow_id, "type": "arrow"})

# Output
excalidraw = {
    "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
    "files": {}
}

out_path = Path(__file__).parent.parent / "examples" / "layered-stack.excalidraw"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(excalidraw, f, indent=2)

print(f"[OK] Wrote {len(elements)} elements to {out_path}")
