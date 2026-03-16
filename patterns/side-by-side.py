"""
Side-by-Side Comparison Diagram Builder
Demonstrates the comparison pattern: two bordered areas with shared elements in the center gap.
Canvas: 1800x1200, roughness 0
"""
import json
from pathlib import Path

# --- Layout constants ---
CW, CH = 1800, 1200
MARGIN = 60
GAP_CENTER = 440
LEFT_X = MARGIN
LEFT_W = (CW - GAP_CENTER) / 2 - MARGIN
RIGHT_X = CW - MARGIN - LEFT_W
RIGHT_W = LEFT_W
BADGE_X = CW / 2

TITLE_Y = 40
SECTION_TOP = 130
SECTION_H = 370
BULLET_START_Y = SECTION_TOP + 75
BULLET_LINE_H = 38
ANNOTATION_Y = SECTION_TOP + SECTION_H + 20
ANNOTATION_H = 55

BADGE_START_Y = 185
BADGE_GAP = 75
BADGE_W = 120
BADGE_H = 40

# Colors from palette
TITLE_COLOR = "#1e40af"
SUBTITLE_COLOR = "#3b82f6"
BODY_COLOR = "#374151"
MUTED_COLOR = "#94a3b8"
BORDER_COLOR = "#c4c4c4"
DARK_BG = "#1e293b"
WHITE = "#ffffff"
CANVAS_BG = "#ffffff"
ANNOT_BG = "#f8fafc"
ARROW_COLOR = "#374151"

seed_counter = 100000

def next_seed():
    global seed_counter
    seed_counter += 1
    return seed_counter

LINE_HT = {3: 1.2, 6: 1.25, 7: 1.15}
CHAR_WIDTH = {3: 0.60, 6: 0.60, 7: 0.58}

def T(id, x, y, w, h, text, size=16, color=BODY_COLOR, align="left", container=None, font_family=6, cw=None, ch=None):
    lh = LINE_HT.get(font_family, 1.25)
    char_w = CHAR_WIDTH.get(font_family, 0.58)
    text_w = int(max(len(line) for line in text.split("\n")) * size * char_w)
    text_h = int((text.count("\n") + 1) * size * lh)
    if container and cw is not None and ch is not None:
        x = x + (cw - text_w) // 2
        y = y + (ch - text_h) // 2
        w = text_w
        h = text_h
    return {
        "type": "text", "id": id, "x": x, "y": y, "width": w, "height": h,
        "text": text, "originalText": text, "fontSize": size, "fontFamily": font_family,
        "textAlign": align, "verticalAlign": "middle",
        "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False, "containerId": container, "lineHeight": lh
    }

def R(id, x, y, w, h, fill="transparent", stroke=BORDER_COLOR, sw=2, style="solid", bound=None, roundness=3):
    return {
        "type": "rectangle", "id": id, "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
        "strokeWidth": sw, "strokeStyle": style, "roughness": 0, "opacity": 100,
        "angle": 0, "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": bound or [],
        "link": None, "locked": False, "roundness": {"type": roundness}
    }

def A(id, x, y, pts, stroke=ARROW_COLOR, sw=1.5, start_bind=None, end_bind=None):
    return {
        "type": "arrow", "id": id, "x": x, "y": y,
        "width": abs(pts[-1][0] - pts[0][0]), "height": abs(pts[-1][1] - pts[0][1]),
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

elements = []

# Title
elements.append(T("title1", 0, TITLE_Y, CW, 32, "DEVELOPMENT VS PRODUCTION", size=28, color=TITLE_COLOR, align="center", font_family=7))
elements.append(T("title2", 0, TITLE_Y + 35, CW, 24, "Two Environment Model", size=20, color=BODY_COLOR, align="center"))
elements.append(T("title3", 0, TITLE_Y + 62, CW, 20, "Side-by-side comparison pattern", size=14, color=MUTED_COLOR, align="center"))

# LEFT SECTION
elements.append(R("left_border", LEFT_X, SECTION_TOP, LEFT_W, SECTION_H, fill="transparent", stroke=BORDER_COLOR, sw=1.5))
elements.append(T("left_title", LEFT_X + 25, SECTION_TOP + 15, 300, 28, "DEVELOPMENT", size=24, color=BODY_COLOR, align="left", font_family=7))
elements.append(T("left_subtitle", LEFT_X + 25, SECTION_TOP + 47, 350, 18, "Local Environment -- Interactive", size=13, color=MUTED_COLOR, align="left"))

dev_bullets = [
    "- Fast iteration cycle",
    "- Full debugging tools",
    "- Manual execution",
    "- Hot reload on changes",
    "- Test with small datasets",
    "- Local database instance",
]
by = BULLET_START_Y
for i, bullet in enumerate(dev_bullets):
    h = 20
    elements.append(T(f"left_b{i}", LEFT_X + 25, by, LEFT_W - 50, h, bullet, size=16, color=BODY_COLOR, align="left"))
    by += h + 12

elements.append(R("left_annot", LEFT_X + 15, ANNOTATION_Y, LEFT_W - 30, ANNOTATION_H, fill=ANNOT_BG, stroke=BORDER_COLOR, sw=1, style="dashed"))
elements.append(T("left_annot_t", LEFT_X + 30, ANNOTATION_Y + 5, LEFT_W - 60, ANNOTATION_H - 10,
    "Where features are built and tested.\nMove fast, break things safely.", size=14, color=MUTED_COLOR, align="left"))

# RIGHT SECTION
elements.append(R("right_border", RIGHT_X, SECTION_TOP, RIGHT_W, SECTION_H, fill="transparent", stroke=BORDER_COLOR, sw=1.5))
elements.append(T("right_title", RIGHT_X + 25, SECTION_TOP + 15, 300, 28, "PRODUCTION", size=24, color=BODY_COLOR, align="left", font_family=7))
elements.append(T("right_subtitle", RIGHT_X + 25, SECTION_TOP + 47, 350, 18, "Server Environment -- Automated", size=13, color=MUTED_COLOR, align="left"))

prod_bullets = [
    "- Automated pipelines",
    "- Structured and predictable",
    "- Monitoring and logging",
    "- Async task processing",
    "- Scheduled jobs (cron)",
    "- Multi-model orchestration",
    "- Scales horizontally",
]
by = BULLET_START_Y
for i, bullet in enumerate(prod_bullets):
    h = 20
    elements.append(T(f"right_b{i}", RIGHT_X + 25, by, RIGHT_W - 50, h, bullet, size=16, color=BODY_COLOR, align="left"))
    by += h + 12

elements.append(R("right_annot", RIGHT_X + 15, ANNOTATION_Y, RIGHT_W - 30, ANNOTATION_H, fill=ANNOT_BG, stroke=BORDER_COLOR, sw=1, style="dashed"))
elements.append(T("right_annot_t", RIGHT_X + 30, ANNOTATION_Y + 5, RIGHT_W - 60, ANNOTATION_H - 10,
    "Always on. Gets smarter over time.\nHandles scale automatically.", size=14, color=MUTED_COLOR, align="left"))

# CENTER BADGES
badges = ["Database", "Cache", "GitHub", "Monitoring"]
for i, name in enumerate(badges):
    bid = f"badge_{name.lower()}"
    bx = BADGE_X - BADGE_W / 2
    by_badge = BADGE_START_Y + i * BADGE_GAP

    elements.append(R(bid, bx, by_badge, BADGE_W, BADGE_H,
        fill=DARK_BG, stroke=DARK_BG, sw=1,
        bound=[{"id": f"{bid}_t", "type": "text"},
               {"id": f"arrow_left_{i}", "type": "arrow"},
               {"id": f"arrow_right_{i}", "type": "arrow"}], roundness=3))
    elements.append(T(f"{bid}_t", bx, by_badge, BADGE_W, BADGE_H,
        name, size=14, color=WHITE, align="center", container=bid, cw=BADGE_W, ch=BADGE_H))

    arrow_y_pos = by_badge + BADGE_H / 2
    left_arrow_start_x = bx - 5
    left_arrow_len = -(bx - 5 - LEFT_X - LEFT_W - 5)
    elements.append(A(f"arrow_left_{i}", left_arrow_start_x, arrow_y_pos,
        [[0, 0], [-left_arrow_len, 0]], stroke=ARROW_COLOR, sw=1.5,
        start_bind={"elementId": bid, "mode": "orbit", "fixedPoint": [-0.03, 0.5]}))
    right_arrow_start_x = bx + BADGE_W + 5
    right_arrow_len = RIGHT_X - right_arrow_start_x - 5
    elements.append(A(f"arrow_right_{i}", right_arrow_start_x, arrow_y_pos,
        [[0, 0], [right_arrow_len, 0]], stroke=ARROW_COLOR, sw=1.5,
        start_bind={"elementId": bid, "mode": "orbit", "fixedPoint": [1.03, 0.5]}))

# Build output
output = {
    "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"viewBackgroundColor": CANVAS_BG, "gridSize": 20},
    "files": {}
}

out_path = Path(__file__).parent.parent / "examples" / "side-by-side.excalidraw"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"[OK] Wrote {len(elements)} elements to {out_path}")
