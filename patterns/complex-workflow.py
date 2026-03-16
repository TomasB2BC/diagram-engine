"""
Complex Vertical Workflow Diagram Builder
Demonstrates convergence, processing, fan-out, and persistence patterns.
Canvas: 1800x1200, roughness 0
"""
import json
from pathlib import Path

W = 1800
CENTER = W // 2
LEFT = 80

# Color palette
PRIMARY_FILL = "#3b82f6"; PRIMARY_STROKE = "#1e3a5f"
TERTIARY_FILL = "#93c5fd"; SECONDARY_FILL = "#60a5fa"
TRIGGER_FILL = "#fed7aa"; TRIGGER_STROKE = "#c2410c"
SUCCESS_FILL = "#a7f3d0"; SUCCESS_STROKE = "#047857"
DECISION_FILL = "#fef3c7"; DECISION_STROKE = "#b45309"
AI_FILL = "#ddd6fe"; AI_STROKE = "#6d28d9"
INACTIVE_FILL = "#dbeafe"; INACTIVE_STROKE = "#1e40af"
DARK_BG = "#1e293b"
TITLE_COLOR = "#1e40af"; SUBTITLE_COLOR = "#3b82f6"
BODY_COLOR = "#64748b"; ON_LIGHT = "#374151"; ON_DARK = "#ffffff"
LINE_COLOR = "#64748b"

# Source colors
HOT_FILL = "#fed7aa"; HOT_STROKE = "#c2410c"
WARM_FILL = "#93c5fd"; WARM_STROKE = "#1e3a5f"
COLD_FILL = "#dbeafe"; COLD_STROKE = "#1e40af"

seed_counter = 100000
def next_seed():
    global seed_counter
    seed_counter += 1
    return seed_counter

CHAR_WIDTH = {3: 0.60, 6: 0.60, 7: 0.58}
LINE_HT = {3: 1.2, 6: 1.25, 7: 1.15}

def T(id, x, y, text, size=16, color=BODY_COLOR, align="left", container=None, w=None, h=None, font_family=6, cw=None, ch=None):
    char_w = CHAR_WIDTH.get(font_family, 0.58)
    lh = LINE_HT.get(font_family, 1.25)
    text_w = int(max(len(line) for line in text.split("\n")) * size * char_w)
    text_h = int((text.count("\n") + 1) * size * lh)
    if w is None: w = text_w
    if h is None: h = text_h
    if container and cw is not None and ch is not None:
        x = x + (cw - text_w) // 2
        y = y + (ch - text_h) // 2
        w = text_w; h = text_h
    return {
        "type": "text", "id": id, "x": x, "y": y, "width": w, "height": h,
        "text": text, "originalText": text, "fontSize": size, "fontFamily": font_family,
        "textAlign": align if not container else "center",
        "verticalAlign": "top" if not container else "middle",
        "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False, "containerId": container, "lineHeight": lh,
    }

def R(id, x, y, w, h, fill, stroke, sw=2, bound_text=None, bound_arrows=None, dashed=False):
    be = []
    if bound_text: be.append({"id": bound_text, "type": "text"})
    if bound_arrows:
        for aid in bound_arrows: be.append({"id": aid, "type": "arrow"})
    return {
        "type": "rectangle", "id": id, "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
        "strokeWidth": sw, "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": be if be else None,
        "link": None, "locked": False, "roundness": {"type": 3},
    }

def A(id, x, y, pts, stroke, sw=1.5, start_id=None, end_id=None, style="solid"):
    return {
        "type": "arrow", "id": id, "x": x, "y": y,
        "width": abs(pts[-1][0] - pts[0][0]) if len(pts) > 1 else 0,
        "height": abs(pts[-1][1] - pts[0][1]) if len(pts) > 1 else 0,
        "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": style,
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False, "points": pts,
        "startBinding": {"elementId": start_id, "focus": 0, "gap": 2} if start_id else None,
        "endBinding": {"elementId": end_id, "focus": 0, "gap": 2} if end_id else None,
        "startArrowhead": None, "endArrowhead": "triangle_outline",
        "roundness": {"type": 2}, "elbowed": True,
    }

def LINE_EL(id, x, y, pts, stroke=LINE_COLOR, sw=2, dashed=False):
    return {
        "type": "line", "id": id, "x": x, "y": y,
        "width": abs(pts[-1][0]) if pts else 0, "height": abs(pts[-1][1]) if pts else 0,
        "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False, "points": pts,
    }

els = []

# Title
els.append(T("title", LEFT, 35, "DATA PROCESSING PIPELINE", size=26, color=TITLE_COLOR, font_family=7))
els.append(T("subtitle", LEFT, 70, "Ingest >> Process >> Route >> Store", size=14, color=SUBTITLE_COLOR))

# Three input sources
ctx_y = 140
box_w = 280; box_h = 95; gap = 40
total_ctx = box_w * 3 + gap * 2
ctx_left = CENTER - total_ctx // 2

els.append(T("ctx_label", ctx_left, ctx_y - 22, "INPUT SOURCES", size=16, color=TITLE_COLOR, font_family=7))

# Source 1 (hot)
s1_x = ctx_left
els.append(R("src_hot", s1_x, ctx_y, box_w, box_h, HOT_FILL, HOT_STROKE, bound_text="src_hot_t"))
els.append(T("src_hot_t", s1_x, ctx_y, "REAL-TIME STREAM\nEvent-driven source\nLow latency, high volume",
    size=13, color=ON_LIGHT, container="src_hot", w=box_w - 20, cw=box_w, ch=box_h))

# Source 2 (warm)
s2_x = s1_x + box_w + gap
els.append(R("src_warm", s2_x, ctx_y, box_w, box_h, WARM_FILL, WARM_STROKE, bound_text="src_warm_t"))
els.append(T("src_warm_t", s2_x, ctx_y, "BATCH IMPORT\nScheduled data pulls\nMedium volume, structured",
    size=13, color=ON_LIGHT, container="src_warm", w=box_w - 20, cw=box_w, ch=box_h))

# Source 3 (cold)
s3_x = s2_x + box_w + gap
els.append(R("src_cold", s3_x, ctx_y, box_w, box_h, COLD_FILL, COLD_STROKE, bound_text="src_cold_t"))
els.append(T("src_cold_t", s3_x, ctx_y, "HISTORICAL ARCHIVE\nReference data\nLarge volume, infrequent updates",
    size=13, color=ON_LIGHT, container="src_cold", w=box_w - 20, cw=box_w, ch=box_h))

# Processing stage
proc_y = ctx_y + box_h + 70
proc_w = 320; proc_h = 65; proc_x = CENTER - proc_w // 2
els.append(R("proc_box", proc_x, proc_y, proc_w, proc_h, AI_FILL, AI_STROKE, bound_text="proc_t"))
els.append(T("proc_t", proc_x, proc_y, "PROCESSING ENGINE\nTransform, validate, enrich",
    size=14, color=ON_LIGHT, container="proc_box", w=proc_w - 20, cw=proc_w, ch=proc_h))

# Convergence arrows
s1_cx = s1_x + box_w // 2; s2_cx = s2_x + box_w // 2; s3_cx = s3_x + box_w // 2
ctx_bot = ctx_y + box_h; jy = ctx_bot + 30
els.append(A("a_s1_proc", s1_cx, ctx_bot,
    [[0, 0], [0, jy - ctx_bot], [CENTER - s1_cx, jy - ctx_bot], [CENTER - s1_cx, proc_y - ctx_bot]],
    HOT_STROKE, start_id="src_hot", end_id="proc_box"))
els.append(A("a_s2_proc", s2_cx, ctx_bot, [[0, 0], [0, proc_y - ctx_bot]],
    WARM_STROKE, start_id="src_warm", end_id="proc_box"))
els.append(A("a_s3_proc", s3_cx, ctx_bot,
    [[0, 0], [0, jy - ctx_bot], [CENTER - s3_cx, jy - ctx_bot], [CENTER - s3_cx, proc_y - ctx_bot]],
    COLD_STROKE, start_id="src_cold", end_id="proc_box"))

# Router
route_y = proc_y + proc_h + 50
route_w = 290; route_h = 55; route_x = CENTER - route_w // 2
els.append(R("route_box", route_x, route_y, route_w, route_h, DECISION_FILL, DECISION_STROKE, bound_text="route_t"))
els.append(T("route_t", route_x, route_y, "OUTPUT ROUTER\nClassify and distribute results",
    size=13, color=ON_LIGHT, container="route_box", w=route_w - 20, cw=route_w, ch=route_h))
els.append(A("a_proc_route", CENTER, proc_y + proc_h, [[0, 0], [0, route_y - proc_y - proc_h]],
    AI_STROKE, start_id="proc_box", end_id="route_box"))

# Fan-out outputs
out_y = route_y + route_h + 70
out_w = 200; out_h = 55; out_gap = 20
outputs = [
    ("out_alert", "Alerts", SUCCESS_FILL, SUCCESS_STROKE),
    ("out_report", "Reports", PRIMARY_FILL, PRIMARY_STROKE),
    ("out_archive", "Archive", DECISION_FILL, DECISION_STROKE),
    ("out_webhook", "Webhooks", AI_FILL, AI_STROKE),
]
total_out = len(outputs) * out_w + (len(outputs) - 1) * out_gap
out_start = CENTER - total_out // 2
route_bot = route_y + route_h; fan_jy = route_bot + 28

for i, (oid, label, fill, stroke) in enumerate(outputs):
    ox = out_start + i * (out_w + out_gap)
    ocx = ox + out_w // 2
    els.append(R(oid, ox, out_y, out_w, out_h, fill, stroke, bound_text=f"{oid}_t"))
    els.append(T(f"{oid}_t", ox, out_y, label, size=14, color=ON_LIGHT, container=oid, w=out_w - 16, cw=out_w, ch=out_h))
    els.append(A(f"a_route_{oid}", CENTER, route_bot,
        [[0, 0], [0, fan_jy - route_bot], [ocx - CENTER, fan_jy - route_bot], [ocx - CENTER, out_y - route_bot]],
        stroke, start_id="route_box", end_id=oid))

# Persistence layer
dw_y = out_y + out_h + 70
els.append(LINE_EL("dw_divider", 150, dw_y - 28, [[0, 0], [W - 300, 0]], stroke=LINE_COLOR, sw=1, dashed=True))
els.append(T("dw_label", CENTER + 40, dw_y - 46, "PERSISTENCE", size=14, color=TITLE_COLOR, align="left", w=140, font_family=7))

dest_w = 250; dest_h = 65; dest_gap = 80
total_dest = dest_w * 2 + dest_gap
dest_left = CENTER - total_dest // 2

# Primary store
els.append(R("dest_primary", dest_left, dw_y, dest_w, dest_h, DARK_BG, PRIMARY_STROKE, bound_text="dest_primary_t"))
els.append(T("dest_primary_t", dest_left, dw_y, "Primary Database\nStructured records", size=15, color=ON_DARK,
    container="dest_primary", w=dest_w - 16, cw=dest_w, ch=dest_h))

# Secondary store
sec_x = dest_left + dest_w + dest_gap
els.append(R("dest_secondary", sec_x, dw_y, dest_w, dest_h, DARK_BG, WARM_STROKE, bound_text="dest_secondary_t"))
els.append(T("dest_secondary_t", sec_x, dw_y, "Document Store\nUnstructured data", size=15, color=ON_DARK,
    container="dest_secondary", w=dest_w - 16, cw=dest_w, ch=dest_h))

# Output
diagram = {
    "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
    "elements": els,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
    "files": {},
}

out_path = Path(__file__).parent.parent / "examples" / "complex-workflow.excalidraw"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    json.dump(diagram, f, indent=2)

print(f"[OK] Wrote {len(els)} elements to {out_path}")
