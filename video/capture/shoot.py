# /// script
# dependencies = ["playwright"]
# ///
"""Sharp page captures for the video: a 2x screenshot plus the bounding boxes of named elements.

  [STORAGE=../.cache/jira-state.json] uv run capture/shoot.py NAME URL 'label=css selector' ...

Writes public/shots/NAME.png and public/shots/NAME.json ({"width", "height", "boxes": {label: [x, y, w, h]}})
in screenshot pixels, so Remotion can zoom on exactly those elements.
"""

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "public" / "shots"
VIEW = {"width": 1600, "height": 900}
SCALE = 2


def main(name: str, url: str, targets: list[str], storage: str | None = None) -> None:
    with sync_playwright() as p:
        # Reuse the newest headless shell already on this machine instead of downloading another.
        shells = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/*/*headless*shell"))
        browser = p.chromium.launch(executable_path=str(shells[-1]) if shells else None)
        ctx = browser.new_context(viewport=VIEW, device_scale_factor=SCALE, storage_state=storage)
        page = ctx.new_page()
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_timeout(int(os.environ.get("SETTLE_MS", "6000")))  # SPAs never go network-idle
        boxes = {}
        for t in targets:
            label, sel = t.split("=", 1)
            el = page.locator(sel).first
            el.scroll_into_view_if_needed(timeout=10000) if not boxes else None
            b = el.bounding_box()
            if b:
                boxes[label] = [round(v * SCALE) for v in (b["x"], b["y"], b["width"], b["height"])]
        page.screenshot(path=str(OUT / f"{name}.png"))
        (OUT / f"{name}.json").write_text(json.dumps(
            {"url": url, "width": VIEW["width"] * SCALE, "height": VIEW["height"] * SCALE, "boxes": boxes}, indent=1))
        print(name, boxes)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:], os.environ.get("STORAGE"))
