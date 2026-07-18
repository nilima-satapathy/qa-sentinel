"""
Record a ~10s QA Sentinel demo + thumbnail for LinkedIn.

  .venv/Scripts/python.exe scripts/record_10s_demo.py

Outputs (also copied to C:\\Users\\admin\\Code\\):
  reports/qa_sentinel_10s.mp4
  reports/qa_sentinel_10s_thumbnail.png
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)
RAW = OUT / "raw_10s"
URL = "http://127.0.0.1:8501"
FLAKY = "What is a flaky test, and why is it harmful in CI?"
EASY = Path(r"C:\Users\admin\Code")
FFMPEG = r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"


def send(page, text: str) -> None:
    box = page.locator('[data-testid="stChatInputTextArea"]')
    if box.count() == 0:
        box = page.locator("textarea").first
    box.click()
    page.wait_for_timeout(150)
    box.fill(text)
    page.wait_for_timeout(200)
    sub = page.locator('[data-testid="stChatInputSubmitButton"]')
    if sub.count():
        sub.click()
    else:
        box.press("Enter")


def main() -> int:
    if RAW.exists():
        for p in RAW.rglob("*"):
            if p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass
    RAW.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(RAW),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2000)

        # Fresh chat
        try:
            nb = page.get_by_role("button", name="New conversation")
            if nb.count():
                nb.first.click()
                page.wait_for_timeout(1200)
        except Exception:
            pass

        # Kick off important flow quickly: question → gate
        clicked = False
        for i in range(page.get_by_role("button").count()):
            try:
                t = page.get_by_role("button").nth(i).inner_text(timeout=500)
            except Exception:
                continue
            if "flaky" in t.lower():
                page.get_by_role("button").nth(i).click()
                clicked = True
                break
        if not clicked:
            send(page, FLAKY)

        # Wait for answer + gate (core of the demo)
        page.wait_for_timeout(9000)
        page.mouse.wheel(0, 100)
        page.wait_for_timeout(1500)

        # Thumbnail at peak state
        thumb = OUT / "qa_sentinel_10s_thumbnail.png"
        page.screenshot(path=str(thumb), full_page=False)
        page.wait_for_timeout(800)

        context.close()
        browser.close()

    webms = sorted(RAW.glob("*.webm"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not webms:
        print("No video", file=sys.stderr)
        return 1

    raw_webm = OUT / "qa_sentinel_10s_raw.webm"
    if raw_webm.exists():
        raw_webm.unlink()
    webms[0].replace(raw_webm)

    # Probe duration, take last 10s (best: answer + gate visible)
    probe = subprocess.run(
        [
            FFMPEG,
            "-i",
            str(raw_webm),
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    dur = 12.0
    for line in (probe.stderr or "").splitlines():
        if "Duration:" in line:
            # Duration: 00:00:14.50
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            dur = float(h) * 3600 + float(m) * 60 + float(s)
            break

    start = max(0.0, dur - 10.0)
    mp4 = OUT / "qa_sentinel_10s.mp4"
    r = subprocess.run(
        [
            FFMPEG,
            "-y",
            "-ss",
            f"{start:.2f}",
            "-i",
            str(raw_webm),
            "-t",
            "10",
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
        timeout=120,
    )
    if r.returncode != 0 or not mp4.exists():
        print(r.stderr[-1000:], file=sys.stderr)
        return 1

    # Ensure exact 10s pad/trim if slightly short
    print(f"Wrote {mp4} ({mp4.stat().st_size} bytes), start={start:.1f}s of {dur:.1f}s raw")

    # Copy easy paths for LinkedIn
    EASY.mkdir(parents=True, exist_ok=True)
    (EASY / "qa_sentinel_10s.mp4").write_bytes(mp4.read_bytes())
    thumb_src = OUT / "qa_sentinel_10s_thumbnail.png"
    if thumb_src.exists():
        (EASY / "qa_sentinel_10s_thumbnail.png").write_bytes(thumb_src.read_bytes())
        print(f"Wrote thumbnail {thumb_src}")
    print(f"Easy upload: {EASY / 'qa_sentinel_10s.mp4'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
