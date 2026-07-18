"""
Record a short QA Sentinel demo video for LinkedIn (Playwright).

  .venv/Scripts/python.exe scripts/record_demo.py

Output: reports/qa_sentinel_demo.webm (and .mp4 if ffmpeg available)
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR = OUT_DIR / "playwright_video"
URL = "http://127.0.0.1:8501"
FLAKY_Q = "What is a flaky test, and why is it harmful in CI?"


def main() -> int:
    if VIDEO_DIR.exists():
        for p in VIDEO_DIR.glob("*"):
            try:
                p.unlink()
            except OSError:
                pass
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)

        # Welcome / empty state visible
        page.wait_for_timeout(1500)

        # Click first suggestion chip if present (flaky test)
        chips = page.get_by_role("button")
        clicked = False
        for i in range(chips.count()):
            label = chips.nth(i).inner_text(timeout=1000)
            if "flaky" in label.lower() or "What is a flaky" in label:
                chips.nth(i).click()
                clicked = True
                break

        if not clicked:
            # Type into Streamlit chat input
            box = page.locator('[data-testid="stChatInputTextArea"]')
            if box.count() == 0:
                box = page.locator("textarea").first
            box.click()
            box.fill(FLAKY_Q)
            page.wait_for_timeout(400)
            # Submit
            submit = page.locator('[data-testid="stChatInputSubmitButton"]')
            if submit.count():
                submit.click()
            else:
                box.press("Enter")

        # Wait for answer + gate artifact
        page.wait_for_timeout(8000)
        # Scroll a bit so gate panel is in view
        page.mouse.wheel(0, 200)
        page.wait_for_timeout(2500)
        page.mouse.wheel(0, -100)
        page.wait_for_timeout(2000)

        # Capture still for thumbnail
        page.screenshot(path=str(OUT_DIR / "qa_sentinel_demo_frame.png"), full_page=False)

        context.close()
        browser.close()

    videos = list(VIDEO_DIR.glob("*.webm"))
    if not videos:
        print("ERROR: no video recorded", file=sys.stderr)
        return 1

    webm = OUT_DIR / "qa_sentinel_demo.webm"
    src = videos[0]
    if webm.exists():
        webm.unlink()
    src.replace(webm)
    print(f"Wrote {webm}")

    # Convert to mp4 for LinkedIn (prefers mp4)
    mp4 = OUT_DIR / "qa_sentinel_demo.mp4"
    ffmpeg = None
    for cand in (
        r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe",
        "ffmpeg",
    ):
        try:
            r = subprocess.run(
                [cand, "-y", "-i", str(webm), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(mp4)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode == 0 and mp4.exists():
                ffmpeg = cand
                print(f"Wrote {mp4}")
                break
            print(r.stderr[-500:] if r.stderr else r.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            print(f"ffmpeg try failed: {exc}")

    if not ffmpeg and not mp4.exists():
        print("MP4 conversion skipped; use .webm or convert manually.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
