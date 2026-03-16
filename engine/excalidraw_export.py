"""Native Excalidraw PNG export via Playwright.

Loads excalidraw.com, injects a scene via localStorage, opens the export
dialog (Ctrl+Shift+E), selects the desired scale, and captures the
exported PNG by intercepting the File System Access API (showSaveFilePicker).

Falls back to capturing the export preview canvas if FSA intercept fails.

Usage:
    python excalidraw_export.py <input.excalidraw> <output.png> [--scale 2]

Requires: Playwright with Chromium installed
    pip install playwright && playwright install chromium
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path


def _inject_scene(page, scene: dict) -> None:
    """Inject Excalidraw scene data via localStorage and reload."""
    scene_json = json.dumps(scene)
    page.evaluate(
        """(sceneStr) => {
        const scene = JSON.parse(sceneStr);
        localStorage.setItem('excalidraw', JSON.stringify(scene.elements));
        localStorage.setItem('excalidraw-state', JSON.stringify({
            ...(scene.appState || {}),
            collaborators: [],
        }));
    }""",
        scene_json,
    )
    page.reload(wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(3000)


def _open_export_dialog(page) -> bool:
    """Open the export dialog and wait for it to render.

    Returns True if the ImageExportModal was found.
    """
    # Dismiss any existing popups
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # Select all elements so the export includes everything
    page.keyboard.press("Control+a")
    page.wait_for_timeout(500)

    # Open export dialog (Ctrl+Shift+E)
    page.keyboard.press("Control+Shift+e")
    page.wait_for_timeout(3000)

    # Verify the modal appeared
    modal = page.query_selector(".ImageExportModal")
    if not modal:
        page.wait_for_timeout(2000)
        modal = page.query_selector(".ImageExportModal")

    return modal is not None


def _set_scale(page, scale: int) -> dict:
    """Click the scale radio button in the export dialog."""
    choices = page.query_selector_all(".RadioGroup__choice")
    for choice in choices:
        text = (choice.text_content() or "").strip()
        if text.startswith(str(scale)):
            choice.click()
            return {"set": True, "method": "playwright-click", "text": text}

    available = [(c.text_content() or "").strip() for c in choices]
    return {"set": False, "reason": "scale-not-found", "available": available}


def _install_fsa_hook(page) -> None:
    """Hook showSaveFilePicker to intercept the PNG export blob."""
    page.evaluate("""() => {
        window.__capturedExport = null;
        if (window.showSaveFilePicker) {
            window.showSaveFilePicker = async function() {
                return {
                    createWritable: async () => ({
                        write: async (data) => {
                            if (data instanceof Blob) {
                                window.__capturedExport = data;
                            } else if (data instanceof ArrayBuffer) {
                                window.__capturedExport = new Blob([data], {type: 'image/png'});
                            }
                        },
                        close: async () => {},
                    }),
                };
            };
        }
    }""")


def _click_png_and_capture(page, timeout_ms: int = 10000) -> dict:
    """Click the PNG button and read the intercepted blob."""
    buttons = page.query_selector_all(".ImageExportModal button")
    png_btn = None
    for btn in buttons:
        if "PNG" in (btn.text_content() or ""):
            png_btn = btn
            break

    if not png_btn:
        return {"success": False, "error": "png-button-not-found"}

    png_btn.click()

    waited = 0
    step = 500
    while waited < timeout_ms:
        page.wait_for_timeout(step)
        waited += step
        has_blob = page.evaluate(
            "() => window.__capturedExport !== null"
        )
        if has_blob:
            break

    if not page.evaluate("() => window.__capturedExport !== null"):
        return {"success": False, "error": "fsa-capture-timeout"}

    blob_info = page.evaluate("""() => {
        return new Promise((resolve) => {
            const blob = window.__capturedExport;
            const reader = new FileReader();
            reader.onload = () => {
                resolve({
                    type: blob.type,
                    size: blob.size,
                    data: reader.result.split(',')[1],
                });
            };
            reader.readAsDataURL(blob);
        });
    }""")

    return {
        "success": True,
        "data": blob_info["data"],
        "size": blob_info["size"],
        "type": blob_info.get("type", "image/png"),
    }


def _capture_canvas_fallback(page) -> dict:
    """Fallback: capture the export preview canvas via toDataURL."""
    return page.evaluate(
        """() => {
        const modal = document.querySelector('.ImageExportModal');
        if (!modal) return { success: false, error: 'no-modal' };

        const canvases = modal.querySelectorAll('canvas');
        for (const c of canvases) {
            if (c.width > 10 && c.height > 10) {
                try {
                    return {
                        success: true,
                        data: c.toDataURL('image/png').split(',')[1],
                        width: c.width,
                        height: c.height,
                    };
                } catch (e) {
                    return { success: false, error: 'tainted: ' + e.message };
                }
            }
        }
        return { success: false, error: 'no-canvas', canvasCount: canvases.length };
    }"""
    )


def _read_png_dimensions(png_bytes: bytes) -> tuple[int | None, int | None]:
    """Read width and height from PNG IHDR chunk."""
    if len(png_bytes) < 24 or png_bytes[:8] != b'\x89PNG\r\n\x1a\n':
        return None, None
    import struct
    w = struct.unpack('>I', png_bytes[16:20])[0]
    h = struct.unpack('>I', png_bytes[20:24])[0]
    return w, h


def export_native_png(
    excalidraw_path: str, output_path: str, scale: int = 2
) -> dict:
    """Export an Excalidraw file to PNG using the native export dialog.

    Primary approach: Intercepts the File System Access API to capture
    the full-resolution PNG.

    Fallback: Captures the export preview canvas via toDataURL.

    Args:
        excalidraw_path: Path to the .excalidraw JSON file.
        output_path: Destination path for the PNG file.
        scale: Export scale factor (1, 2, or 3). Default 2.

    Returns:
        Dict with keys: status, method, width, height, size_bytes, scale,
        scale_applied. On failure: status="failed" with error details.
    """
    from playwright.sync_api import sync_playwright

    excalidraw_path = str(Path(excalidraw_path).resolve())
    output_path = str(Path(output_path).resolve())

    with open(excalidraw_path, encoding="utf-8") as f:
        scene = json.load(f)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print("[1] Loading excalidraw.com...")
        page.goto("https://excalidraw.com", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        print("[2] Injecting scene...")
        _inject_scene(page, scene)

        print("[3] Opening export dialog...")
        if not _open_export_dialog(page):
            browser.close()
            return {"status": "failed", "error": "export-dialog-not-found"}

        print(f"[4] Setting scale to {scale}x...")
        scale_result = _set_scale(page, scale)
        print(f"    Scale result: {scale_result}")
        if scale_result.get("set"):
            page.wait_for_timeout(2000)

        print("[5] Installing FSA hook and clicking PNG (primary approach)...")
        _install_fsa_hook(page)
        fsa_result = _click_png_and_capture(page)

        if fsa_result.get("success"):
            png_data = base64.b64decode(fsa_result["data"])
            with open(output_path, "wb") as f:
                f.write(png_data)

            width, height = _read_png_dimensions(png_data)
            browser.close()

            result = {
                "status": "ok",
                "method": "fsa-intercept",
                "width": width,
                "height": height,
                "size_bytes": len(png_data),
                "scale": scale,
                "scale_applied": scale_result.get("set", False),
            }
            print(f"[OK] Exported {width}x{height} "
                  f"({len(png_data)} bytes) via {result['method']}")
            return result

        print(f"[6] FSA failed ({fsa_result.get('error')}), "
              f"trying canvas fallback...")
        canvas_result = _capture_canvas_fallback(page)

        if canvas_result.get("success"):
            png_data = base64.b64decode(canvas_result["data"])
            with open(output_path, "wb") as f:
                f.write(png_data)

            browser.close()
            result = {
                "status": "ok",
                "method": "canvas-toDataURL-fallback",
                "width": canvas_result["width"],
                "height": canvas_result["height"],
                "size_bytes": len(png_data),
                "scale": scale,
                "scale_applied": scale_result.get("set", False),
            }
            print(f"[OK] Exported {result['width']}x{result['height']} "
                  f"({result['size_bytes']} bytes) via {result['method']}")
            return result

        browser.close()
        return {
            "status": "failed",
            "error": "all-approaches-failed",
            "fsa_error": fsa_result.get("error"),
            "canvas_error": canvas_result.get("error"),
            "scale_debug": scale_result,
        }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python excalidraw_export.py <input.excalidraw> <output.png> [--scale 2]")
        sys.exit(1)

    input_path = sys.argv[1]
    out_path = sys.argv[2]
    s = 2
    if "--scale" in sys.argv:
        idx = sys.argv.index("--scale")
        if idx + 1 < len(sys.argv):
            s = int(sys.argv[idx + 1])

    result = export_native_png(input_path, out_path, scale=s)
    print(f"\n[RESULT] {json.dumps(result, indent=2)}")
    sys.exit(0 if result["status"] == "ok" else 1)
