"""
Record a polished QA Sentinel launch demo for LinkedIn / portfolio.

Prereq: Streamlit app on http://127.0.0.1:8501

  .venv/Scripts/python.exe scripts/record_launch_video.py

Outputs:
  reports/qa_sentinel_launch.webm
  reports/qa_sentinel_launch.mp4
  reports/qa_sentinel_launch_poster.png
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)
VID_DIR = OUT / "launch_video_raw"
URL = "http://127.0.0.1:8501"
FLAKY = "What is a flaky test, and why is it harmful in CI?"
SMOKE = "What is the difference between smoke and regression testing?"


def _click_button_containing(page, text: str) -> bool:
    buttons = page.get_by_role("button")
    n = buttons.count()
    for i in range(n):
        try:
            label = buttons.nth(i).inner_text(timeout=600)
        except Exception:
            continue
        if text.lower() in label.lower():
            buttons.nth(i).click()
            return True
    return False


def _send_chat(page, message: str) -> None:
    box = page.locator('[data-testid="stChatInputTextArea"]')
    if box.count() == 0:
        box = page.locator("textarea").first
    box.click()
    page.wait_for_timeout(200)
    box.fill(message)
    page.wait_for_timeout(350)
    submit = page.locator('[data-testid="stChatInputSubmitButton"]')
    if submit.count():
        submit.click()
    else:
        box.press("Enter")


def main() -> int:
    if VID_DIR.exists():
        for p in VID_DIR.rglob("*"):
            if p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass
    VID_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(VID_DIR),
            record_video_size={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()

        # 1) Launch / load
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4000)

        # 2) Fresh conversation if possible
        try:
            nb = page.get_by_role("button", name="New conversation")
            if nb.count():
                nb.first.click()
                page.wait_for_timeout(2000)
        except Exception:
            pass

        # 3) Hold on welcome / brand
        page.wait_for_timeout(2500)

        # 4) First demo: flaky test via suggestion or type
        if not _click_button_containing(page, "flaky"):
            _send_chat(page, FLAKY)
        page.wait_for_timeout(12000)

        # Show gate panel
        page.mouse.wheel(0, 180)
        page.wait_for_timeout(2500)
        page.mouse.wheel(0, -80)
        page.wait_for_timeout(1500)

        # Poster frame at peak demo state
        page.screenshot(path=str(OUT / "qa_sentinel_launch_poster.png"), full_page=False)

        # 5) Optional second question (smoke vs regression) for richer launch cut
        if not _click_button_containing(page, "smoke"):
            try:
                _send_chat(page, SMOKE)
                page.wait_for_timeout(11000)
            except Exception:
                page.wait_for_timeout(1500)

        page.mouse.wheel(0, 120)
        page.wait_for_timeout(2000)
        page.mouse.wheel(0, -200)
        page.wait_for_timeout(1800)

        context.close()
        browser.close()

    videos = sorted(VID_DIR.glob("*.webm"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not videos:
        print("ERROR: no video recorded", file=sys.stderr)
        return 1

    webm = OUT / "qa_sentinel_launch.webm"
    if webm.exists():
        webm.unlink()
    videos[0].replace(webm)
    print(f"Wrote {webm} ({webm.stat().st_size} bytes)")

    mp4 = OUT / "qa_sentinel_launch.mp4"
    ffmpeg_candidates = [
        r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe",
        "ffmpeg",
    ]
    for ff in ffmpeg_candidates:
        try:
            r = subprocess.run(
                [
                    ff,
                    "-y",
                    "-i",
                    str(webm),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    "-an",
                    str(mp4),
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if r.returncode == 0 and mp4.exists():
                print(f"Wrote {mp4} ({mp4.stat().st_size} bytes)")
                # Also copy to user Code folder for easy LinkedIn upload
                easy = Path(r"C:\Users\admin\Code\qa_sentinel_launch.mp4")
                easy.write_bytes(mp4.read_bytes())
                poster = Path(r"C:\Users\admin\Code\qa_sentinel_launch_poster.png")
                src_poster = OUT / "qa_sentinel_launch_poster.png"
                if src_poster.exists():
                    poster.write_bytes(src_poster.read_bytes())
                print(f"Copied to {easy}")
                return 0
            print(r.stderr[-800:] if r.stderr else "ffmpeg failed")
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
            print(f"ffmpeg skip: {exc}")

    print("MP4 not created; use .webm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
