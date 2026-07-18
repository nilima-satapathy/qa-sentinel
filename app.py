"""
QA Sentinel — Claude-style chat + Quality Gate artifact panel.

  python -m streamlit run app.py
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any, Literal

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.chat_client import ChatClient, load_red_team_prompts  # noqa: E402
from src.paths import ensure_import_paths  # noqa: E402
from src.quality_gate import GateResult, evaluate_answer, load_policy  # noqa: E402
from src.repair import pick_ab_winner, try_repair  # noqa: E402
from src.store import TurnStore  # noqa: E402

ThemeName = Literal["dark", "light"]

st.set_page_config(
    page_title="QA Sentinel",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Claude-inspired theme tokens
# Warm terracotta · cream canvas · reading-first typography · artifact panel
# ---------------------------------------------------------------------------

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;0,8..60,700;1,8..60,400&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
  font-family: 'Source Sans 3', system-ui, -apple-system, sans-serif;
}

.stApp {
  background: var(--c-bg);
  color: var(--c-text);
}

#MainMenu, footer, header { visibility: hidden; }
div[data-testid="stToolbar"] { display: none; }

.block-container {
  padding-top: 0.6rem !important;
  padding-bottom: 6.5rem !important;
  padding-left: 1.5rem !important;
  padding-right: 1.5rem !important;
  max-width: 1180px;
}

/* —— Header (minimal Claude) —— */
.c-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  padding: 0.15rem 0;
  margin: 0;
  width: 100%;
  min-height: 2.65rem;
}
.c-brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}
.c-mark {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: var(--c-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 600;
  box-shadow: 0 2px 8px var(--c-accent-glow);
}
.c-title {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 1.2rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--c-text-strong);
  line-height: 1.2;
}
.c-subtitle {
  font-size: 0.78rem;
  color: var(--c-muted);
  font-weight: 450;
  margin-top: 0.05rem;
}
.c-header-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  justify-content: flex-end;
}
.c-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 550;
  background: var(--c-chip-bg);
  color: var(--c-muted-strong);
  border: 1px solid var(--c-border);
}
.c-chip-accent {
  background: var(--c-accent-soft);
  color: var(--c-accent-text);
  border-color: var(--c-accent-border);
}

/* —— Chat column: reading width —— */
.c-label {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-muted);
  margin: 0.25rem 0 0.65rem;
}

.c-chat-frame {
  min-height: 380px;
  max-width: 720px;
  margin: 0 auto;
}

/* Empty / welcome — Claude centered prompt feel */
.c-welcome {
  text-align: center;
  padding: 3.5rem 1.25rem 2.25rem;
  max-width: 34rem;
  margin: 0 auto;
}
.c-welcome-mark {
  width: 44px;
  height: 44px;
  margin: 0 auto 1.1rem;
  border-radius: 999px;
  background: var(--c-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.15rem;
  box-shadow: 0 4px 16px var(--c-accent-glow);
}
.c-welcome h2 {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 1.55rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--c-text-strong);
  margin: 0 0 0.55rem;
  line-height: 1.25;
}
.c-welcome p {
  margin: 0 auto 1.35rem;
  color: var(--c-muted-strong);
  font-size: 0.98rem;
  line-height: 1.6;
}

/* Messages — flat Claude style, not SMS bubbles */
div[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  padding: 0.55rem 0 0.75rem !important;
  margin: 0 auto 0.15rem;
  max-width: 720px;
}
div[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
  max-width: 100%;
}
/* User: subtle warm pill on the right feel via background block */
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
div[data-testid="stChatMessage"][data-testid="stChatMessageUser"] {
  /* fallbacks handled via content styling */
}
div[data-testid="stChatMessage"] p {
  color: var(--c-text);
  font-size: 1.02rem;
  line-height: 1.7;
  font-family: 'Source Serif 4', Georgia, 'Times New Roman', serif;
}
/* Streamlit user avatar row — slightly dimmer serif not needed; keep readable */
div[data-testid="stChatMessage"] strong {
  font-weight: 600;
}

.c-msg-user-wrap {
  display: flex;
  justify-content: flex-end;
  margin: 0.35rem 0 0.9rem;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
}
.c-msg-user {
  max-width: 85%;
  padding: 0.75rem 1rem;
  border-radius: 18px;
  background: var(--c-user-bg);
  color: var(--c-text-strong);
  font-size: 0.98rem;
  line-height: 1.55;
  font-family: 'Source Sans 3', system-ui, sans-serif;
  border: 1px solid var(--c-border);
}
.c-msg-assistant {
  max-width: 720px;
  margin: 0.25rem auto 0.5rem;
  padding: 0.15rem 0.15rem 0.35rem;
}
.c-msg-assistant .c-body {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 1.05rem;
  line-height: 1.72;
  color: var(--c-text);
  white-space: pre-wrap;
}
.c-msg-role {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--c-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 0.35rem;
  font-family: 'Source Sans 3', system-ui, sans-serif;
}

/* Gate status under answer — quiet, not neon */
.c-status {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
  padding: 0.32rem 0.75rem;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 600;
  font-family: 'Source Sans 3', system-ui, sans-serif;
  border: 1px solid var(--c-border);
  background: var(--c-chip-bg);
}
.c-status-pass { color: var(--c-pass); border-color: var(--c-pass-border); background: var(--c-pass-bg); }
.c-status-warn { color: var(--c-warn); border-color: var(--c-warn-border); background: var(--c-warn-bg); }
.c-status-fail { color: var(--c-fail); border-color: var(--c-fail-border); background: var(--c-fail-bg); }
.c-status-meta { font-weight: 500; opacity: 0.8; color: var(--c-muted-strong); }

/* Free tier — thin Claude-like footer strip */
.c-freebar {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  max-width: 720px;
  margin: 1rem auto 0.35rem;
  padding: 0.5rem 0.15rem;
  font-size: 0.75rem;
  color: var(--c-muted);
}
.c-freebar-track {
  flex: 1;
  height: 4px;
  border-radius: 999px;
  background: var(--c-track);
  overflow: hidden;
}
.c-freebar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--c-accent);
}

/* Suggestion chips */
.c-chips-label {
  max-width: 720px;
  margin: 0.85rem auto 0.4rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--c-muted);
}
div[data-testid="column"] .stButton > button {
  border-radius: 999px !important;
  border: 1px solid var(--c-border) !important;
  background: var(--c-surface) !important;
  color: var(--c-text-strong) !important;
  font-weight: 500 !important;
  font-size: 0.82rem !important;
  padding: 0.4rem 0.85rem !important;
  box-shadow: none !important;
}
div[data-testid="column"] .stButton > button:hover {
  border-color: var(--c-accent-border) !important;
  background: var(--c-accent-soft) !important;
  color: var(--c-accent-text) !important;
}

/* —— Artifact panel (Claude Artifacts vibe) —— */
.c-artifact {
  border-radius: 14px;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  box-shadow: var(--c-shadow);
  overflow: hidden;
  position: sticky;
  top: 0.5rem;
}
.c-artifact-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.8rem 1rem;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-artifact-head);
}
.c-artifact-title {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--c-text-strong);
}
.c-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-family: 'Source Sans 3', system-ui, sans-serif;
}
.c-badge-pass { background: var(--c-pass-bg); color: var(--c-pass); }
.c-badge-warn { background: var(--c-warn-bg); color: var(--c-warn); }
.c-badge-fail { background: var(--c-fail-bg); color: var(--c-fail); }
.c-badge-idle { background: var(--c-chip-bg); color: var(--c-muted); }
.c-artifact-body { padding: 1.05rem 1rem 1.15rem; }
.c-ring-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 1rem;
}
.c-ring {
  width: 108px;
  height: 108px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 4px solid var(--c-track);
  background: var(--c-ring-bg);
}
.c-ring-pass { border-color: var(--c-pass); }
.c-ring-warn { border-color: var(--c-warn); }
.c-ring-fail { border-color: var(--c-fail); }
.c-ring-status {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--c-text-strong);
  letter-spacing: 0.02em;
}
.c-ring-sub {
  font-size: 0.68rem;
  color: var(--c-muted);
  margin-top: 0.1rem;
  font-family: 'Source Sans 3', system-ui, sans-serif;
}
.c-section {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--c-muted);
  margin: 0.4rem 0 0.45rem;
  font-family: 'Source Sans 3', system-ui, sans-serif;
}
.c-layer-list { display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 0.85rem; }
.c-layer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.48rem 0.6rem;
  border-radius: 10px;
  background: var(--c-inset);
  border: 1px solid var(--c-border);
  font-size: 0.78rem;
  font-family: 'Source Sans 3', system-ui, sans-serif;
}
.c-layer-name { font-weight: 600; color: var(--c-muted-strong); font-size: 0.74rem; }
.c-layer-val { font-weight: 650; font-size: 0.74rem; }
.c-ok { color: var(--c-pass); }
.c-wn { color: var(--c-warn); }
.c-fl { color: var(--c-fail); }
.c-sk { color: var(--c-muted); }
.c-reason {
  display: flex;
  gap: 0.45rem;
  align-items: flex-start;
  padding: 0.28rem 0;
  font-size: 0.84rem;
  color: var(--c-text);
  line-height: 1.45;
  font-family: 'Source Sans 3', system-ui, sans-serif;
}
.c-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-accent);
  margin-top: 0.4rem;
  flex-shrink: 0;
}
.c-idle-hint {
  text-align: center;
  padding: 0.35rem 0.4rem 0.75rem;
  color: var(--c-muted);
  font-size: 0.86rem;
  line-height: 1.55;
  font-family: 'Source Serif 4', Georgia, serif;
}
.c-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
  margin-top: 0.85rem;
}
.c-meta-card {
  padding: 0.48rem 0.55rem;
  border-radius: 10px;
  background: var(--c-inset);
  border: 1px solid var(--c-border);
}
.c-meta-card .k {
  font-size: 0.62rem;
  color: var(--c-muted);
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-family: 'Source Sans 3', system-ui, sans-serif;
}
.c-meta-card .v {
  font-size: 0.8rem;
  color: var(--c-text-strong);
  font-weight: 600;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  margin-top: 0.12rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: var(--c-sidebar) !important;
  border-right: 1px solid var(--c-border);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.15rem !important; }
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
  color: var(--c-text) !important;
}

.stButton > button {
  border-radius: 10px !important;
  border: 1px solid var(--c-border) !important;
  background: var(--c-surface) !important;
  color: var(--c-text-strong) !important;
  font-weight: 550 !important;
}
.stButton > button:hover {
  border-color: var(--c-accent-border) !important;
  background: var(--c-accent-soft) !important;
}
.stButton > button[kind="primary"] {
  background: var(--c-accent) !important;
  border: none !important;
  color: #fff !important;
}

/* Top bar: brand + actions on one aligned row */
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type {
  align-items: center !important;
  gap: 0.55rem !important;
  margin-bottom: 0.35rem !important;
}
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"] {
  display: flex !important;
  align-items: center !important;
}
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2),
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(3) {
  justify-content: flex-end !important;
}
/* Theme = icon-only circular control */
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) .stButton {
  width: 2.65rem !important;
  min-width: 2.65rem !important;
}
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) button {
  width: 2.65rem !important;
  min-width: 2.65rem !important;
  max-width: 2.65rem !important;
  height: 2.65rem !important;
  min-height: 2.65rem !important;
  padding: 0 !important;
  border-radius: 999px !important;
  font-size: 1.2rem !important;
  line-height: 1 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) button p {
  margin: 0 !important;
  font-size: 1.2rem !important;
}
/* New conversation — same height as icon, pill shape */
section.main .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(3) button {
  height: 2.65rem !important;
  min-height: 2.65rem !important;
  border-radius: 999px !important;
  padding: 0 1rem !important;
  white-space: nowrap !important;
  font-size: 0.88rem !important;
}

div[data-testid="stProgress"] > div {
  background: var(--c-track) !important;
  border-radius: 999px !important;
}
div[data-testid="stProgress"] > div > div {
  background: var(--c-accent) !important;
}
div[data-testid="stExpander"] {
  background: var(--c-inset);
  border-radius: 12px;
  border: 1px solid var(--c-border);
}

/* —— Bottom dock + chat composer (must match body theme) —— */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
section.main > div > div > [data-testid="stBottom"] {
  background: var(--c-bg) !important;
  background-color: var(--c-bg) !important;
  background-image: none !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stBottomBlockContainer"] {
  background: var(--c-bg) !important;
  background-color: var(--c-bg) !important;
  border-top: 1px solid var(--c-border) !important;
  padding-top: 0.65rem !important;
  padding-bottom: 0.85rem !important;
  max-width: 1180px !important;
}
/* Soft top fade so content doesn't hard-cut into the dock */
[data-testid="stBottom"]::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: -28px;
  height: 28px;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent, var(--c-bg));
}
[data-testid="stBottom"] {
  position: relative;
}

div[data-testid="stChatInput"] {
  max-width: 720px !important;
  margin: 0 auto !important;
  background: transparent !important;
  background-color: transparent !important;
}
/* Outer rounded shell of the input */
div[data-testid="stChatInput"] > div {
  background: var(--c-surface) !important;
  background-color: var(--c-surface) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: 1.35rem !important;
  box-shadow: var(--c-shadow) !important;
  color: var(--c-text) !important;
}
/* Nested emotion wrappers that often keep secondaryBg */
div[data-testid="stChatInput"] div,
div[data-testid="stChatInput"] form {
  background-color: transparent !important;
  color: var(--c-text) !important;
}
div[data-testid="stChatInput"] > div {
  background: var(--c-surface) !important;
  background-color: var(--c-surface) !important;
}

textarea[data-testid="stChatInputTextArea"],
div[data-testid="stChatInput"] textarea {
  background: transparent !important;
  background-color: transparent !important;
  color: var(--c-text) !important;
  caret-color: var(--c-accent) !important;
  font-family: 'Source Sans 3', system-ui, sans-serif !important;
  font-size: 0.98rem !important;
}
textarea[data-testid="stChatInputTextArea"]::placeholder,
div[data-testid="stChatInput"] textarea::placeholder {
  color: var(--c-muted) !important;
  opacity: 1 !important;
}

/* Send button — avoid broken Material glyph (was a white square) */
button[data-testid="stChatInputSubmitButton"] {
  position: relative !important;
  background: var(--c-accent) !important;
  background-color: var(--c-accent) !important;
  color: transparent !important;
  border: none !important;
  border-radius: 999px !important;
  min-width: 2.35rem !important;
  min-height: 2.35rem !important;
  width: 2.35rem !important;
  height: 2.35rem !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: 0 2px 8px var(--c-accent-glow) !important;
}
button[data-testid="stChatInputSubmitButton"]:hover {
  filter: brightness(1.07);
}
/* Hide native icon (often renders as solid square under custom fills) */
button[data-testid="stChatInputSubmitButton"] > *,
button[data-testid="stChatInputSubmitButton"] span,
button[data-testid="stChatInputSubmitButton"] svg {
  opacity: 0 !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
  position: absolute !important;
}
/* Crisp send arrow (replaces broken white square icon) */
button[data-testid="stChatInputSubmitButton"]::after {
  content: "↑" !important;
  display: block !important;
  color: #ffffff !important;
  font-size: 1.2rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  opacity: 1 !important;
  position: static !important;
  width: auto !important;
  height: auto !important;
  transform: none !important;
  font-family: system-ui, -apple-system, sans-serif !important;
}
button[data-testid="stChatInputFileUploadButton"],
button[data-testid="stChatInputMicButton"] {
  color: var(--c-muted-strong) !important;
  background: transparent !important;
}
[data-testid="stChatInputInstructions"] {
  color: var(--c-muted) !important;
}
</style>
"""

LIGHT_VARS = """
<style>
.stApp {
  /* Claude light: cream / warm paper */
  --c-bg: #f5f0e8;
  --c-surface: #fffcf7;
  --c-sidebar: #efe9df;
  --c-inset: #f3ede4;
  --c-border: rgba(60, 40, 20, 0.1);
  --c-text: #2c2418;
  --c-text-strong: #1a1510;
  --c-muted: #9a8b78;
  --c-muted-strong: #6b5d4d;
  --c-chip-bg: rgba(60, 40, 20, 0.04);
  --c-user-bg: #ebe4d8;
  --c-accent: #c96442;
  --c-accent-text: #9a4128;
  --c-accent-soft: rgba(201, 100, 66, 0.12);
  --c-accent-border: rgba(201, 100, 66, 0.32);
  --c-accent-glow: rgba(201, 100, 66, 0.28);
  --c-pass: #3d7a5c;
  --c-pass-bg: rgba(61, 122, 92, 0.12);
  --c-pass-border: rgba(61, 122, 92, 0.3);
  --c-warn: #a66a1a;
  --c-warn-bg: rgba(166, 106, 26, 0.12);
  --c-warn-border: rgba(166, 106, 26, 0.3);
  --c-fail: #b5453a;
  --c-fail-bg: rgba(181, 69, 58, 0.1);
  --c-fail-border: rgba(181, 69, 58, 0.28);
  --c-track: rgba(60, 40, 20, 0.1);
  --c-shadow: 0 10px 30px rgba(60, 40, 20, 0.06);
  --c-artifact-head: rgba(201, 100, 66, 0.06);
  --c-ring-bg: radial-gradient(circle at 40% 30%, rgba(201,100,66,0.06), transparent 60%);
  color: #2c2418;
  background:
    radial-gradient(800px 360px at 50% -10%, rgba(201, 100, 66, 0.06), transparent 55%),
    #f5f0e8;
}
</style>
"""

DARK_VARS = """
<style>
.stApp {
  /* Claude dark: warm evening, not cold blue-black */
  --c-bg: #1c1917;
  --c-surface: #26211d;
  --c-sidebar: #211d19;
  --c-inset: rgba(0,0,0,0.28);
  --c-border: rgba(255, 240, 220, 0.08);
  --c-text: #e8e0d5;
  --c-text-strong: #f5f0e8;
  --c-muted: #8a7f72;
  --c-muted-strong: #b0a497;
  --c-chip-bg: rgba(255, 240, 220, 0.05);
  --c-user-bg: #322c26;
  --c-accent: #d47855;
  --c-accent-text: #f0b89a;
  --c-accent-soft: rgba(212, 120, 85, 0.14);
  --c-accent-border: rgba(212, 120, 85, 0.35);
  --c-accent-glow: rgba(212, 120, 85, 0.3);
  --c-pass: #7dba98;
  --c-pass-bg: rgba(125, 186, 152, 0.12);
  --c-pass-border: rgba(125, 186, 152, 0.32);
  --c-warn: #e0b06a;
  --c-warn-bg: rgba(224, 176, 106, 0.12);
  --c-warn-border: rgba(224, 176, 106, 0.3);
  --c-fail: #e08a80;
  --c-fail-bg: rgba(224, 138, 128, 0.12);
  --c-fail-border: rgba(224, 138, 128, 0.3);
  --c-track: rgba(255, 240, 220, 0.1);
  --c-shadow: 0 12px 36px rgba(0,0,0,0.35);
  --c-artifact-head: rgba(212, 120, 85, 0.08);
  --c-ring-bg: radial-gradient(circle at 40% 30%, rgba(212,120,85,0.08), transparent 60%);
  color: #e8e0d5;
  background:
    radial-gradient(700px 320px at 50% -8%, rgba(212, 120, 85, 0.08), transparent 50%),
    #1c1917;
}
</style>
"""


def get_theme() -> ThemeName:
    t = st.session_state.get("theme", "light")
    return "dark" if t == "dark" else "light"


def set_theme(theme: ThemeName) -> None:
    st.session_state._pending_theme = theme


def apply_pending_theme() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = "light"  # Claude default: warm light
    pending = st.session_state.pop("_pending_theme", None)
    if pending in ("dark", "light"):
        st.session_state.theme = pending
    st.session_state.theme_radio = (
        "☀️ Light" if get_theme() == "light" else "🌙 Dark"
    )


def inject_css(theme: ThemeName) -> None:
    vars_css = LIGHT_VARS if theme == "light" else DARK_VARS
    st.markdown(vars_css + BASE_CSS, unsafe_allow_html=True)


def esc(text: Any) -> str:
    return html.escape("" if text is None else str(text))


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


def get_store() -> TurnStore:
    if "store" not in st.session_state:
        st.session_state.store = TurnStore()
    return st.session_state.store


def get_client() -> ChatClient:
    if "client" not in st.session_state:
        st.session_state.client = ChatClient()
    return st.session_state.client


def _track_usage(store: TurnStore, resp: Any, gate: GateResult, use_judge: bool) -> None:
    if resp.backend == "openai" and not (resp.error and "fallback" in (resp.error or "")):
        store.add_usage(resp.total_tokens, requests=1)
    if use_judge and gate.scores.get("L3", {}).get("tokens"):
        store.add_usage(gate.scores["L3"]["tokens"], requests=1)


def process_turn(
    question: str,
    use_judge: bool,
    *,
    enable_repair: bool = False,
    enable_ab: bool = False,
) -> None:
    client = get_client()
    store = get_store()
    policy = load_policy()
    # Snapshot BEFORE this turn's usage — L2 only when free tier already exhausted
    free_tier = store.free_tier_snapshot(policy)

    with st.spinner("Thinking…"):
        if enable_ab and client.has_api_key:
            model_a = client.model
            model_b = client.secondary_model()
            resp_a = client.complete(question, model=model_a)
            resp_b = client.complete(question, model=model_b)
            if (resp_a.error and not resp_a.answer) and (resp_b.error and not resp_b.answer):
                st.error(f"Model error: {resp_a.error or resp_b.error}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"(error) {resp_a.error or resp_b.error}",
                        "gate": None,
                        "meta": {"backend": "openai", "model": model_a},
                    }
                )
                st.session_state.last_gate = None
                st.session_state.last_meta = {}
                return
            with st.spinner("Scoring quality gate…"):
                gate_a = evaluate_answer(
                    question,
                    resp_a.answer or "",
                    use_judge=use_judge,
                    judge_client=client if use_judge else None,
                    policy=policy,
                    free_tier=free_tier,
                )
                gate_b = evaluate_answer(
                    question,
                    resp_b.answer or "",
                    use_judge=use_judge,
                    judge_client=client if use_judge else None,
                    policy=policy,
                    free_tier=free_tier,
                )
            pick = pick_ab_winner(
                resp_a.answer or "",
                gate_a,
                resp_a,
                resp_b.answer or "",
                gate_b,
                resp_b,
            )
            resp = pick["response"]
            answer = pick["answer"]
            gate = pick["gate"]
            ab_meta = {
                "enabled": True,
                "winner": pick["winner"],
                "model_a": resp_a.model,
                "model_b": resp_b.model,
                "status_a": gate_a.status,
                "status_b": gate_b.status,
                "loser_status": pick["loser_status"],
            }
            for r, g in ((resp_a, gate_a), (resp_b, gate_b)):
                _track_usage(store, r, g, use_judge)
        else:
            resp = client.complete(question)
            ab_meta = {"enabled": False}
            if resp.error == "empty_question":
                st.warning("Enter a non-empty question.")
                return
            answer = resp.answer or ""
            if resp.error and not answer:
                st.error(f"Model error: {resp.error}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"(error) {resp.error}",
                        "gate": None,
                        "meta": {"backend": resp.backend, "model": resp.model},
                    }
                )
                st.session_state.last_gate = None
                st.session_state.last_meta = {}
                return
            with st.spinner("Scoring quality gate…"):
                gate = evaluate_answer(
                    question,
                    answer,
                    use_judge=use_judge,
                    judge_client=client if use_judge else None,
                    policy=policy,
                    free_tier=free_tier,
                )
            _track_usage(store, resp, gate, use_judge)

    repair_meta: dict[str, Any] = {"attempted": False}
    if enable_repair and gate.status in ("WARN", "FAIL"):
        with st.spinner("Repairing answer…"):
            outcome = try_repair(
                question,
                answer,
                gate,
                client,
                use_judge=use_judge,
                model=resp.model if resp.backend == "openai" else None,
                policy=policy,
                free_tier=free_tier,
            )
        repair_meta = {
            "attempted": outcome.attempted,
            "improved": outcome.improved,
            "original_status": outcome.original_status,
            "final_status": outcome.final_status,
            "notes": outcome.notes or [],
        }
        if outcome.attempted and outcome.repair_response:
            rr = outcome.repair_response
            if rr.backend == "openai":
                store.add_usage(rr.total_tokens, requests=1)
        answer = outcome.final_answer
        gate = outcome.final_gate
        if outcome.attempted:
            resp = outcome.repair_response or resp

    store.add_turn(
        question=question,
        answer=answer,
        gate_status=gate.status,
        scores=gate.scores,
        reasons=gate.reasons,
        latency_ms=resp.latency_ms,
        total_tokens=resp.total_tokens,
        model=resp.model,
        backend=resp.backend,
        golden_case_id=gate.golden_case_id,
    )

    meta = {
        "backend": resp.backend,
        "model": resp.model,
        "latency_ms": resp.latency_ms,
        "tokens": resp.total_tokens,
        "error": resp.error,
        "ab": ab_meta,
        "repair": repair_meta,
    }
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "gate": gate.to_dict(),
            "meta": meta,
        }
    )
    st.session_state.last_gate = gate.to_dict()
    st.session_state.last_meta = meta


def session_pass_rate(stats: dict) -> float:
    total = stats.get("total") or 0
    if total <= 0:
        return 0.0
    return 100.0 * (stats.get("pass") or 0) / total


def clear_conversation() -> None:
    """Reset chat UI and quality-gate artifact for a fresh conversation."""
    st.session_state.messages = []
    st.session_state.last_gate = None
    st.session_state.last_meta = {}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


def _layer_status(gate: dict, key: str) -> tuple[str, str]:
    layers = gate.get("layers") or {}
    scores = gate.get("scores") or {}
    layer = layers.get(key) or {}
    sc = scores.get(key) or {}
    st_val = (layer.get("status") or "").upper()
    if key == "L3" and (sc.get("skipped") or sc.get("applicable") is False):
        return "off", "c-sk"
    if key == "L2" and sc.get("applicable") is False:
        return "n/a", "c-sk"
    if st_val == "PASS":
        return "PASS", "c-ok"
    if st_val == "WARN":
        return "WARN", "c-wn"
    if st_val == "FAIL":
        return "FAIL", "c-fl"
    return "—", "c-sk"


def render_status_chip(gate: dict, meta: dict) -> None:
    status = (gate.get("status") or "PASS").upper()
    cls = {
        "PASS": "c-status-pass",
        "WARN": "c-status-warn",
        "FAIL": "c-status-fail",
    }.get(status, "c-status-warn")
    icon = {"PASS": "✓", "WARN": "!", "FAIL": "✕"}.get(status, "·")
    latency = meta.get("latency_ms")
    lat = f"{float(latency):.0f} ms" if latency is not None else "—"
    backend = meta.get("backend") or "—"
    st.markdown(
        f'<div class="c-status {cls}">'
        f"{icon} {esc(status)}"
        f'<span class="c-status-meta">· Quality gate · {esc(lat)} · {esc(backend)}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_messages() -> None:
    """Claude-style flat messages (custom HTML, not SMS bubbles)."""
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="c-msg-user-wrap"><div class="c-msg-user">{esc(msg["content"])}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            body = esc(msg["content"]).replace("\n", "<br/>")
            st.markdown(
                f"""
<div class="c-msg-assistant">
  <div class="c-msg-role">QA Sentinel</div>
  <div class="c-body">{body}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            if msg.get("gate"):
                render_status_chip(msg["gate"], msg.get("meta") or {})


def render_artifact_panel(gate: dict | None, meta: dict | None) -> None:
    if not gate:
        st.markdown(
            """
<div class="c-artifact">
  <div class="c-artifact-head">
    <span class="c-artifact-title">Quality Gate</span>
    <span class="c-badge c-badge-idle">Idle</span>
  </div>
  <div class="c-artifact-body">
    <div class="c-ring-wrap">
      <div class="c-ring">
        <div class="c-ring-status" style="opacity:0.45;font-size:0.95rem">—</div>
        <div class="c-ring-sub">awaiting turn</div>
      </div>
    </div>
    <div class="c-idle-hint">
      Your answer will open here as an artifact — scored by L1 · L2 · L3.
    </div>
    <div class="c-section">Layers</div>
    <div class="c-layer-list">
      <div class="c-layer-row"><span class="c-layer-name">L1 Offline</span><span class="c-layer-val c-sk">—</span></div>
      <div class="c-layer-row"><span class="c-layer-name">L2 Golden</span><span class="c-layer-val c-sk">—</span></div>
      <div class="c-layer-row"><span class="c-layer-name">L3 Factual judge</span><span class="c-layer-val c-sk">off</span></div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    status = (gate.get("status") or "PASS").upper()
    ring_cls = {
        "PASS": "c-ring-pass",
        "WARN": "c-ring-warn",
        "FAIL": "c-ring-fail",
    }.get(status, "")
    badge_cls = {
        "PASS": "c-badge-pass",
        "WARN": "c-badge-warn",
        "FAIL": "c-badge-fail",
    }.get(status, "c-badge-idle")

    layers_html = ""
    labels = {
        "L1": "L1 Offline policy",
        "L2": "L2 Golden match",
        "L3": "L3 Factual judge",
    }
    for key in ("L1", "L2", "L3"):
        val, cls = _layer_status(gate, key)
        layers_html += (
            f'<div class="c-layer-row">'
            f'<span class="c-layer-name">{esc(labels[key])}</span>'
            f'<span class="c-layer-val {cls}">{esc(val)}</span>'
            f"</div>"
        )

    reasons_html = ""
    for r in (gate.get("reasons") or [])[:6]:
        reasons_html += (
            f'<div class="c-reason"><span class="c-dot"></span><span>{esc(r)}</span></div>'
        )
    if not reasons_html:
        reasons_html = (
            '<div class="c-reason"><span class="c-dot"></span><span>No reasons</span></div>'
        )

    meta = meta or {}
    latency = meta.get("latency_ms")
    lat_s = f"{float(latency):.0f} ms" if latency is not None else "—"
    tokens = meta.get("tokens")
    tok_s = str(tokens) if tokens is not None else "—"
    model = meta.get("model") or "—"
    backend = meta.get("backend") or "—"

    extras_html = ""
    extras = []
    ab = meta.get("ab") or {}
    if ab.get("enabled"):
        extras.append(
            f"A/B winner {esc(ab.get('winner'))}: "
            f"A {esc(ab.get('status_a'))} vs B {esc(ab.get('status_b'))}"
        )
    repair = meta.get("repair") or {}
    if repair.get("attempted"):
        extras.append(
            f"Repair {esc(repair.get('original_status'))} → "
            f"{esc(repair.get('final_status'))}"
            + (" · improved" if repair.get("improved") else "")
        )
    if extras:
        extras_html = (
            '<div class="c-section">Notes</div>'
            + "".join(
                f'<div class="c-reason"><span class="c-dot"></span><span>{x}</span></div>'
                for x in extras
            )
        )

    st.markdown(
        f"""
<div class="c-artifact">
  <div class="c-artifact-head">
    <span class="c-artifact-title">Quality Gate</span>
    <span class="c-badge {badge_cls}">{esc(status)}</span>
  </div>
  <div class="c-artifact-body">
    <div class="c-ring-wrap">
      <div class="c-ring {ring_cls}">
        <div class="c-ring-status">{esc(status)}</div>
        <div class="c-ring-sub">{esc(backend)}</div>
      </div>
    </div>
    <div class="c-section">Layers</div>
    <div class="c-layer-list">{layers_html}</div>
    <div class="c-section">Reasons</div>
    {reasons_html}
    {extras_html}
    <div class="c-meta-grid">
      <div class="c-meta-card"><div class="k">Latency</div><div class="v">{esc(lat_s)}</div></div>
      <div class="c-meta-card"><div class="k">Tokens</div><div class="v">{esc(tok_s)}</div></div>
      <div class="c-meta-card" style="grid-column:1/-1"><div class="k">Model</div><div class="v">{esc(model)}</div></div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_header(client: ChatClient, meter: dict, pass_rate: float, stats: dict) -> None:
    mode = (
        '<span class="c-chip c-chip-accent">Live free-tier</span>'
        if client.has_api_key
        else '<span class="c-chip">Offline golden</span>'
    )
    rate = (
        f'<span class="c-chip">Session {pass_rate:.0f}% PASS</span>'
        if stats.get("total")
        else ""
    )
    st.markdown(
        f"""
<div class="c-header">
  <div class="c-brand">
    <div class="c-mark">✦</div>
    <div>
      <div class="c-title">QA Sentinel</div>
      <div class="c-subtitle">Software-testing assistant · gated answers</div>
    </div>
  </div>
  <div class="c-header-right">
    {mode}
    {rate}
    <span class="c-chip">{meter["tokens_remaining"]:,} tokens</span>
    <span class="c-chip">{esc(client.model)}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_freebar(meter: dict) -> None:
    used = meter["tokens_used"]
    limit = meter["tokens_limit"] or 1
    pct = int(round(min(1.0, used / limit) * 100)) if limit else 0
    st.markdown(
        f"""
<div class="c-freebar">
  <span>Free tier</span>
  <div class="c-freebar-track"><div class="c-freebar-fill" style="width:{pct}%"></div></div>
  <span>{used:,} / {limit:,}</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_theme_toggle() -> ThemeName:
    current = get_theme()
    options = ["☀️ Light", "🌙 Dark"]
    choice = st.radio(
        "Theme",
        options,
        horizontal=True,
        label_visibility="collapsed",
        key="theme_radio",
    )
    new_theme: ThemeName = "dark" if "Dark" in str(choice) else "light"
    if new_theme != current:
        st.session_state.theme = new_theme
        st.rerun()
    return new_theme


EXAMPLE_PROMPTS = [
    "What is a flaky test, and why is it harmful in CI?",
    "What is the difference between smoke and regression testing?",
    "How should I design API test cases for a REST service?",
    "What is shift-left testing?",
]


def main() -> None:
    apply_pending_theme()
    theme = get_theme()
    inject_css(theme)

    try:
        ensure_import_paths()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_gate" not in st.session_state:
        st.session_state.last_gate = None
    if "last_meta" not in st.session_state:
        st.session_state.last_meta = {}

    store = get_store()
    client = get_client()
    policy = load_policy()
    meter = store.free_tier_snapshot(policy)
    stats = store.session_stats()
    pass_rate = session_pass_rate(stats)

    with st.sidebar:
        st.markdown("### Appearance")
        render_theme_toggle()
        st.caption("Claude-style warm light / evening dark")
        st.divider()
        st.markdown("### Settings")
        use_judge = st.toggle(
            "L3 factual accuracy (AI judge)",
            value=True,
            help=(
                "While free-tier credits remain: scores FACTUAL ACCURACY of the answer "
                "(extra free-tier call). May ground against a related golden reference. "
                "Turn off to save tokens."
            ),
        )
        enable_repair = st.toggle("Repair loop", value=False)
        enable_ab = st.toggle(
            "A/B dual models",
            value=False,
            disabled=not client.has_api_key,
        )
        st.divider()
        st.markdown("**Red-team**")
        attacks = load_red_team_prompts(limit=5)
        for a in attacks:
            label = a["id"].replace("_", " ").replace("-", " ")
            if st.button(label, key=f"rt_{a['id']}", use_container_width=True):
                process_turn(
                    a["question"],
                    use_judge,
                    enable_repair=enable_repair,
                    enable_ab=enable_ab,
                )
                st.rerun()
        st.divider()
        if st.button("Export turns CSV", use_container_width=True):
            path = store.export_csv()
            st.success(f"Wrote {path.name}")
    # Top bar: brand/meta | theme icon | New conversation
    h1, h2, h3 = st.columns([6.2, 0.55, 1.55], gap="small", vertical_alignment="center")
    with h1:
        render_header(client, meter, pass_rate, stats)
    with h2:
        if get_theme() == "light":
            if st.button(
                "🌙",
                key="theme_main_to_dark",
                help="Switch to dark theme",
                use_container_width=True,
            ):
                set_theme("dark")
                st.rerun()
        else:
            if st.button(
                "☀️",
                key="theme_main_to_light",
                help="Switch to light theme",
                use_container_width=True,
            ):
                set_theme("light")
                st.rerun()
    with h3:
        if st.button(
            "New conversation",
            key="header_new_conversation",
            type="primary",
            use_container_width=True,
            help="Clear the chat and quality gate artifact, then start a new conversation",
        ):
            clear_conversation()
            st.rerun()

    chat_col, art_col = st.columns([1.55, 1], gap="large")

    with chat_col:
        if not st.session_state.messages:
            st.markdown(
                """
<div class="c-welcome">
  <div class="c-welcome-mark">✦</div>
  <h2>How can I help you test today?</h2>
  <p>
    Ask about software testing. Every answer is quality-gated —
    offline rules, golden metrics, optional AI judge.
  </p>
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            render_messages()

        if st.session_state.messages:
            render_freebar(meter)

        st.markdown(
            '<div class="c-chips-label">Suggestions</div>',
            unsafe_allow_html=True,
        )
        chip_cols = st.columns(2)
        for i, ex in enumerate(EXAMPLE_PROMPTS):
            short = ex if len(ex) < 48 else ex[:45] + "…"
            col = chip_cols[i % 2]
            if col.button(short, key=f"chip_{i}", use_container_width=True):
                process_turn(
                    ex,
                    use_judge,
                    enable_repair=enable_repair,
                    enable_ab=enable_ab,
                )
                st.rerun()

    with art_col:
        render_artifact_panel(
            st.session_state.last_gate,
            st.session_state.last_meta,
        )
        if st.session_state.last_gate:
            with st.expander("Scores detail"):
                st.json(st.session_state.last_gate.get("scores") or {})

    prompt = st.chat_input("Message QA Sentinel…")
    if prompt:
        process_turn(
            prompt,
            use_judge,
            enable_repair=enable_repair,
            enable_ab=enable_ab,
        )
        st.rerun()


if __name__ == "__main__":
    main()
