"""Section-level zoom inspector for Excalidraw diagrams using Playwright.

Loads the .excalidraw file into excalidraw.com via Playwright, takes a
full overview screenshot, then scrolls/zooms to each visual section for
close-up screenshots. All rendering is done by Excalidraw's real engine
in the browser -- no custom renderer, minimal token cost.

Usage:
    python section_inspector.py <excalidraw_path> <output_prefix>

Output:
    <output_prefix>_full.png           -- full diagram overview
    <output_prefix>_section_00.png     -- zoomed into section 0
    <output_prefix>_section_01.png     -- zoomed into section 1
    ...

Requires: playwright with chromium installed
    pip install playwright && playwright install chromium
"""
import json
import sys


def get_section_bounds(excalidraw_path):
    """Extract element bounding boxes grouped by vertical proximity into sections."""
    with open(excalidraw_path) as f:
        data = json.load(f)

    elements = data.get("elements", [])

    positioned = []
    for el in elements:
        if el.get("isDeleted"):
            continue
        if el.get("type") in ("rectangle", "ellipse", "text", "diamond", "line", "arrow"):
            x = el.get("x", 0)
            y = el.get("y", 0)
            w = el.get("width", 0)
            h = el.get("height", 0)
            # Skip tiny elements (dots, markers) for section grouping
            if el.get("type") in ("line", "arrow"):
                continue
            if w < 5 or h < 5:
                continue
            positioned.append({"x": x, "y": y, "w": w, "h": h,
                               "type": el["type"], "id": el.get("id", "")})

    if not positioned:
        return [], data

    positioned.sort(key=lambda e: e["y"])

    # Group into sections by vertical proximity (80px threshold)
    sections = []
    current_section = [positioned[0]]
    for el in positioned[1:]:
        section_max_y = max(e["y"] + e["h"] for e in current_section)
        if el["y"] < section_max_y + 80:
            current_section.append(el)
        else:
            sections.append(current_section)
            current_section = [el]
    sections.append(current_section)

    bounds = []
    for i, section in enumerate(sections):
        min_x = min(e["x"] for e in section)
        min_y = min(e["y"] for e in section)
        max_x = max(e["x"] + e["w"] for e in section)
        max_y = max(e["y"] + e["h"] for e in section)
        # Add padding in excalidraw coordinates
        pad = 40
        bounds.append({
            "index": i,
            "min_x": min_x - pad, "min_y": min_y - pad,
            "max_x": max_x + pad, "max_y": max_y + pad,
            "element_count": len(section),
        })

    return bounds, data


def run_inspection(excalidraw_path, output_prefix):
    """Load diagram in Playwright, take full + per-section screenshots.

    The full overview uses native export (excalidraw_export.export_native_png)
    for a clean, cropped PNG with no browser chrome. Falls back to
    page.screenshot() if native export fails.

    Per-section zoomed screenshots still use page.screenshot() since they
    require viewport manipulation (scroll + zoom) that the export dialog
    cannot provide.
    """
    from playwright.sync_api import sync_playwright

    bounds, data = get_section_bounds(excalidraw_path)
    print(f"Found {len(bounds)} visual sections")
    for b in bounds:
        print(f"  Section {b['index']}: y={b['min_y']:.0f}-{b['max_y']:.0f}, "
              f"{b['element_count']} elements")

    if not bounds:
        print("[!] No sections found, nothing to inspect")
        return

    # -- FULL OVERVIEW via native export --
    full_path = f"{output_prefix}_full.png"
    native_ok = False
    try:
        from excalidraw_export import export_native_png

        print("[>>] Attempting native export for full overview...")
        result = export_native_png(excalidraw_path, full_path, scale=2)
        if result.get("status") == "ok":
            native_ok = True
            print(f"[OK] Full overview (native {result.get('width')}x"
                  f"{result.get('height')}, {result.get('method')}) -> {full_path}")
        else:
            print(f"[!] Native export failed: {result.get('error')}, "
                  f"falling back to page.screenshot()")
    except ImportError:
        print("[!] excalidraw_export not available, using page.screenshot() fallback")
    except Exception as e:
        print(f"[!] Native export error: {e}, falling back to page.screenshot()")

    VP_W = 1920
    VP_H = 1080

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": VP_W, "height": VP_H})

        # Load excalidraw.com
        page.goto("https://excalidraw.com", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        # Inject diagram data via localStorage
        page.evaluate("""(data) => {
            localStorage.setItem('excalidraw', JSON.stringify(data.elements));
            localStorage.setItem('excalidraw-state', JSON.stringify({
                ...JSON.parse(localStorage.getItem('excalidraw-state') || '{}'),
                theme: 'light'
            }));
        }""", data)

        # Reload to pick up localStorage
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Dismiss any welcome dialogs
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:
            pass

        # -- FULL OVERVIEW FALLBACK (only if native export failed) --
        if not native_ok:
            page.keyboard.press("Control+Shift+Digit1")
            page.wait_for_timeout(2000)
            page.keyboard.press("Control+Minus")
            page.wait_for_timeout(300)
            page.keyboard.press("Control+Minus")
            page.wait_for_timeout(300)
            page.wait_for_timeout(1000)

            page.screenshot(path=full_path)
            print(f"[OK] Full overview (page.screenshot fallback) -> {full_path}")

        # -- PER-SECTION ZOOMED SCREENSHOTS --
        for b in bounds:
            sec_w = b["max_x"] - b["min_x"]
            sec_h = b["max_y"] - b["min_y"]
            center_x = (b["min_x"] + b["max_x"]) / 2
            center_y = (b["min_y"] + b["max_y"]) / 2

            zoom_x = (VP_W * 0.8) / sec_w if sec_w > 0 else 1
            zoom_y = (VP_H * 0.8) / sec_h if sec_h > 0 else 1
            zoom = min(zoom_x, zoom_y, 3.0)
            zoom = max(zoom, 0.3)

            scroll_x = center_x - (VP_W / zoom) / 2
            scroll_y = center_y - (VP_H / zoom) / 2

            page.evaluate("""({scrollX, scrollY, zoom}) => {
                const appState = JSON.parse(
                    localStorage.getItem('excalidraw-state') || '{}'
                );
                appState.scrollX = -scrollX;
                appState.scrollY = -scrollY;
                appState.zoom = { value: zoom };
                localStorage.setItem('excalidraw-state',
                    JSON.stringify(appState));
            }""", {"scrollX": scroll_x, "scrollY": scroll_y, "zoom": zoom})

            page.reload(wait_until="networkidle")
            page.wait_for_timeout(2500)

            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            except Exception:
                pass

            sec_path = f"{output_prefix}_section_{b['index']:02d}.png"
            page.screenshot(path=sec_path)
            print(f"[OK] Section {b['index']} (zoom {zoom:.1f}x, "
                  f"{b['element_count']} elements) -> {sec_path}")

        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python section_inspector.py <excalidraw_path> <output_prefix>")
        sys.exit(1)

    run_inspection(sys.argv[1], sys.argv[2])
