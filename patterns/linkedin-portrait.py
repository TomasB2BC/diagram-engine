"""
LinkedIn Portrait Diagram Builder
Demonstrates the numbered sequence trail pattern with loop-back and side annotations.
Canvas: 1080x1350 (portrait 4:5), roughness 1
"""
import json
from pathlib import Path

seed_counter = 100000
def next_seed():
    global seed_counter
    seed_counter += 1
    return seed_counter

W = 1080; H = 1350; ROUGHNESS = 1; FONT = 6
elements = []

LINE_HT = {3: 1.2, 6: 1.25, 7: 1.15}
CHAR_WIDTH = {3: 0.60, 6: 0.60, 7: 0.58}

def T(id, x, y, w, h, text, size=20, color="#374151", align="center", valign="middle", container=None, font_family=None, cw=None, ch=None):
    ff = font_family if font_family is not None else FONT
    lh = LINE_HT.get(ff, 1.25)
    char_w = CHAR_WIDTH.get(ff, 0.58)
    text_w = int(max(len(line) for line in text.split("\n")) * size * char_w)
    text_h = int((text.count("\n") + 1) * size * lh)
    if container and cw is not None and ch is not None:
        x = x + (cw - text_w) // 2
        y = y + (ch - text_h) // 2
        w = text_w; h = text_h
    return {
        "type": "text", "id": id, "x": x, "y": y, "width": w, "height": h,
        "text": text, "originalText": text, "fontSize": size, "fontFamily": ff,
        "textAlign": align, "verticalAlign": valign,
        "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": ROUGHNESS, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False, "containerId": container, "lineHeight": lh
    }

def R(id, x, y, w, h, fill, stroke, sw=2, style="solid", bound_text=None, bound_arrows=None):
    be = []
    if bound_text: be.append({"id": bound_text, "type": "text"})
    if bound_arrows:
        for a in bound_arrows: be.append({"id": a, "type": "arrow"})
    return {
        "type": "rectangle", "id": id, "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
        "strokeWidth": sw, "strokeStyle": style, "roughness": ROUGHNESS, "opacity": 100,
        "angle": 0, "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": be if be else [],
        "link": None, "locked": False, "roundness": {"type": 3}
    }

def ELLIPSE(id, x, y, w, h, fill, stroke, sw=2, bound_text=None, bound_arrows=None):
    be = []
    if bound_text: be.append({"id": bound_text, "type": "text"})
    if bound_arrows:
        for a in bound_arrows: be.append({"id": a, "type": "arrow"})
    return {
        "type": "ellipse", "id": id, "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
        "strokeWidth": sw, "strokeStyle": "solid", "roughness": ROUGHNESS, "opacity": 100,
        "angle": 0, "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": be if be else [],
        "link": None, "locked": False, "roundness": {"type": 2}
    }

def A(id, x, y, pts, stroke="#374151", sw=1.5, start_bind=None, end_bind=None,
      start_arrow=None, end_arrow="triangle_outline", dash=False):
    w = max(abs(p[0]) for p in pts) if pts else 0
    h = max(abs(p[1]) for p in pts) if pts else 0
    return {
        "type": "arrow", "id": id, "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw,
        "strokeStyle": "dashed" if dash else "solid",
        "roughness": 1, "opacity": 100, "angle": 0,
        "seed": next_seed(), "version": 1, "versionNonce": next_seed(),
        "isDeleted": False, "groupIds": [], "boundElements": None,
        "link": None, "locked": False, "points": pts,
        "startBinding": start_bind, "endBinding": end_bind,
        "startArrowhead": start_arrow, "endArrowhead": end_arrow,
        "roundness": {"type": 2}, "elbowed": True,
        "fixedSegments": None, "startIsSpecial": None, "endIsSpecial": None
    }

# Layout grid
cx = 295; bw = 410; col_center = cx + bw / 2
step_h = 55; gap = 58; num_d = 36

# Title
elements.append(T("title", 50, 35, 980, 75, "Small changes compound into\nbig results", size=36, color="#1e40af", align="center", font_family=7))
elements.append(T("subtitle", 50, 120, 980, 28, "The iteration methodology that actually works", size=20, color="#64748b", align="center"))

# Contrast box
elements.append(T("contrast_label", 45, 175, 210, 20, "What most people do:", size=15, color="#dc2626", align="left"))
elements.append(R("wrong_box", 45, 198, 215, 42, "#fee2e2", "#dc2626", sw=1, style="dashed", bound_text="wrong_t"))
elements.append(T("wrong_t", 45, 198, 215, 42, "Build >> Ship >> Hope", size=15, color="#dc2626", container="wrong_box"))

# Step 1
s1_y = 290
elements.append(R("s1_box", cx, s1_y, bw, step_h, "#fed7aa", "#c2410c", bound_text="s1_t", bound_arrows=["a_1_2"]))
elements.append(T("s1_t", cx, s1_y, bw, step_h, "Start small -- test on 5 examples", size=22, color="#374151", container="s1_box"))
elements.append(ELLIPSE("n1", cx - 52, s1_y + 10, num_d, num_d, "#fed7aa", "#c2410c", sw=2, bound_text="n1_t"))
elements.append(T("n1_t", cx - 52, s1_y + 10, num_d, num_d, "1", size=18, color="#c2410c", container="n1", font_family=3, cw=num_d, ch=num_d))

s2_y = s1_y + step_h + gap
elements.append(A("a_1_2", col_center, s1_y + step_h, [[0, 0], [0, gap]], stroke="#c2410c",
    start_bind={"elementId": "s1_box", "mode": "orbit", "fixedPoint": [0.5, 1.037]},
    end_bind={"elementId": "s2_box", "mode": "orbit", "fixedPoint": [0.5, -0.037]}))

# Step 2
elements.append(R("s2_box", cx, s2_y, bw, step_h, "#ddd6fe", "#6d28d9", bound_text="s2_t", bound_arrows=["a_1_2", "a_2_3", "a_loop_3", "a_loop_4"]))
elements.append(T("s2_t", cx, s2_y, bw, step_h, "Analyze what went wrong", size=22, color="#374151", container="s2_box"))
elements.append(ELLIPSE("n2", cx - 52, s2_y + 10, num_d, num_d, "#ddd6fe", "#6d28d9", sw=2, bound_text="n2_t"))
elements.append(T("n2_t", cx - 52, s2_y + 10, num_d, num_d, "2", size=18, color="#6d28d9", container="n2", font_family=3, cw=num_d, ch=num_d))
elements.append(T("ann2a", 45, s2_y + 8, 215, 22, "Why did it fail?", size=18, color="#6d28d9", align="left"))
elements.append(T("ann2b", 45, s2_y + 32, 215, 20, "Not what to add.", size=15, color="#64748b", align="left"))

s3_y = s2_y + step_h + gap
elements.append(A("a_2_3", col_center, s2_y + step_h, [[0, 0], [0, gap]], stroke="#6d28d9",
    start_bind={"elementId": "s2_box", "mode": "orbit", "fixedPoint": [0.5, 1.037]},
    end_bind={"elementId": "s3_box", "mode": "orbit", "fixedPoint": [0.5, -0.037]}))

# Step 3
elements.append(R("s3_box", cx, s3_y, bw, step_h, "#fef3c7", "#b45309", bound_text="s3_t", bound_arrows=["a_2_3", "a_3_4", "a_loop_3"]))
elements.append(T("s3_t", cx, s3_y, bw, step_h, "Make one precise change", size=22, color="#374151", container="s3_box"))
elements.append(ELLIPSE("n3", cx - 52, s3_y + 10, num_d, num_d, "#fef3c7", "#b45309", sw=2, bound_text="n3_t"))
elements.append(T("n3_t", cx - 52, s3_y + 10, num_d, num_d, "3", size=18, color="#b45309", container="n3", font_family=3, cw=num_d, ch=num_d))
elements.append(T("ins_l1", 45, s3_y + 4, 215, 24, "NOT a rewrite.", size=18, color="#b45309", align="left"))
elements.append(T("ins_l2", 45, s3_y + 30, 215, 20, "Change one thing.", size=15, color="#64748b", align="left"))

s4_y = s3_y + step_h + gap
elements.append(A("a_3_4", col_center, s3_y + step_h, [[0, 0], [0, gap]], stroke="#b45309",
    start_bind={"elementId": "s3_box", "mode": "orbit", "fixedPoint": [0.5, 1.037]},
    end_bind={"elementId": "s4_box", "mode": "orbit", "fixedPoint": [0.5, -0.037]}))

# Step 4
elements.append(R("s4_box", cx, s4_y, bw, step_h, "#dbeafe", "#1e40af", bound_text="s4_t", bound_arrows=["a_3_4", "a_4_5", "a_loop_4"]))
elements.append(T("s4_t", cx, s4_y, bw, step_h, "Test again on 20 examples", size=22, color="#374151", container="s4_box"))
elements.append(ELLIPSE("n4", cx - 52, s4_y + 10, num_d, num_d, "#dbeafe", "#1e40af", sw=2, bound_text="n4_t"))
elements.append(T("n4_t", cx - 52, s4_y + 10, num_d, num_d, "4", size=18, color="#1e40af", container="n4", font_family=3, cw=num_d, ch=num_d))

# Loop arrows
loop_right_x = cx + bw + 12
loop_s3_mid = s3_y + step_h / 2; loop_s4_mid = s4_y + step_h / 2; loop_s2_mid = s2_y + step_h / 2
elements.append(A("a_loop_3", loop_right_x, loop_s3_mid,
    [[0, 0], [100, 0], [100, loop_s2_mid - loop_s3_mid], [0, loop_s2_mid - loop_s3_mid]],
    stroke="#b45309", sw=2, dash=True,
    start_bind={"elementId": "s3_box", "mode": "orbit", "fixedPoint": [1.007, 0.5]},
    end_bind={"elementId": "s2_box", "mode": "orbit", "fixedPoint": [1.007, 0.5]}))
elements.append(A("a_loop_4", loop_right_x, loop_s4_mid,
    [[0, 0], [140, 0], [140, loop_s2_mid - loop_s4_mid], [0, loop_s2_mid - loop_s4_mid]],
    stroke="#1e40af", sw=2, dash=True,
    start_bind={"elementId": "s4_box", "mode": "orbit", "fixedPoint": [1.007, 0.5]},
    end_bind={"elementId": "s2_box", "mode": "orbit", "fixedPoint": [1.007, 0.5]}))
elements.append(T("loop_label", loop_right_x + 150, (s2_y + s4_y) / 2 + 15, 170, 45,
    "Repeat until\nit works reliably", size=17, color="#1e40af", align="left"))

s5_y = s4_y + step_h + gap
elements.append(A("a_4_5", col_center, s4_y + step_h, [[0, 0], [0, gap]], stroke="#1e40af",
    start_bind={"elementId": "s4_box", "mode": "orbit", "fixedPoint": [0.5, 1.037]},
    end_bind={"elementId": "s5_box", "mode": "orbit", "fixedPoint": [0.5, -0.037]}))

# Step 5
elements.append(R("s5_box", cx, s5_y, bw, step_h, "#93c5fd", "#1e3a5f", bound_text="s5_t", bound_arrows=["a_4_5", "a_5_6"]))
elements.append(T("s5_t", cx, s5_y, bw, step_h, "Scale to 100+ examples", size=22, color="#374151", container="s5_box"))
elements.append(ELLIPSE("n5", cx - 52, s5_y + 10, num_d, num_d, "#93c5fd", "#1e3a5f", sw=2, bound_text="n5_t"))
elements.append(T("n5_t", cx - 52, s5_y + 10, num_d, num_d, "5", size=18, color="#1e3a5f", container="n5", font_family=3, cw=num_d, ch=num_d))

s6_y = s5_y + step_h + gap + 10
elements.append(A("a_5_6", col_center, s5_y + step_h, [[0, 0], [0, gap + 10]], stroke="#1e3a5f",
    start_bind={"elementId": "s5_box", "mode": "orbit", "fixedPoint": [0.5, 1.037]},
    end_bind={"elementId": "s6_box", "mode": "orbit", "fixedPoint": [0.5, -0.037]}))

# Step 6
s6_h = 60
elements.append(R("s6_box", cx, s6_y, bw, s6_h, "#a7f3d0", "#047857", bound_text="s6_t", bound_arrows=["a_5_6"]))
elements.append(T("s6_t", cx, s6_y, bw, s6_h, "Ship with confidence", size=26, color="#047857", container="s6_box"))
elements.append(ELLIPSE("n6", cx - 52, s6_y + 13, num_d, num_d, "#a7f3d0", "#047857", sw=2, bound_text="n6_t"))
elements.append(T("n6_t", cx - 52, s6_y + 13, num_d, num_d, "6", size=18, color="#047857", container="n6", font_family=3, cw=num_d, ch=num_d))
elements.append(T("ann6", cx + bw + 20, s6_y + 12, 200, 38, "Data backs every\ndecision you made.", size=16, color="#047857", align="left"))

# Insight box
insight_y = s6_y + s6_h + 65
insight_w = 720; insight_x = (W - insight_w) / 2; insight_h = 95
elements.append(R("insight_box", insight_x, insight_y, insight_w, insight_h, "#f8fafc", "#1e40af", sw=2, style="dashed"))
elements.append(T("insight_main", insight_x + 15, insight_y + 12, insight_w - 30, 55,
    "Most problems are smaller\nthan they look.", size=24, color="#1e40af", align="center"))
elements.append(T("insight_sub", insight_x + 15, insight_y + 68, insight_w - 30, 22,
    "The right change >> the right amount of change.", size=17, color="#64748b", align="center"))

# Output
excalidraw = {
    "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": 20},
    "files": {}
}

out_path = Path(__file__).parent.parent / "examples" / "linkedin-portrait.excalidraw"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(excalidraw, f, indent=2)

print(f"[OK] Wrote {len(elements)} elements")
print(f"Bottom edge: {insight_y + insight_h} / {H}")
