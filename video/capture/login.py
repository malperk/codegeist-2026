# /// script
# dependencies = ["playwright"]
# ///
"""Open a visible browser on the demo site; the user signs in; the session is saved for captures.

  uv run capture/login.py

The session file goes to ../.cache/jira-state.json (git-ignored). No password passes through here:
the user types it into Atlassian's own page.
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = "https://one-atlas-htsv.atlassian.net/jira/software/c/projects/CLANG/issues"
STATE = Path(__file__).resolve().parents[2] / ".cache" / "jira-state.json"

with sync_playwright() as p:
    apps = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium-*/chrome-mac*/*.app/Contents/MacOS/*"))
    browser = p.chromium.launch(headless=False, executable_path=str(apps[-1]) if apps else None)
    ctx = browser.new_context(viewport={"width": 1600, "height": 900})
    page = ctx.new_page()
    page.goto(SITE)
    print("Sign in in the browser window; waiting up to 10 minutes ...", flush=True)
    deadline = time.time() + 600
    while time.time() < deadline:
        if "one-atlas-htsv.atlassian.net/jira" in page.url and "login" not in page.url:
            time.sleep(5)  # let cookies settle
            ctx.storage_state(path=str(STATE))
            STATE.chmod(0o600)
            print("saved session", flush=True)
            break
        time.sleep(2)
    browser.close()
