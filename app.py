"""
ExamHelp v2 — AI-Powered Study Assistant
Redesigned with premium SaaS aesthetics: neon glows, deep gradients,
spring hover physics, and a polished chat interface.

Backend hooks:  process_pdf(file) → dict
                ask_question(question, doc_meta) → dict
"""

import streamlit as st
import time
import random
from datetime import datetime
import requests

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ExamHelp — AI Study Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
#  BACKEND CONFIG
#  Make sure the FastAPI server is running:
#    cd backend && uvicorn main:app --reload --port 8000
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_URL = "http://localhost:8000"


def check_backend_alive() -> bool:
    """Returns True if the FastAPI backend is reachable."""
    try:
        r = requests.get(f"{BACKEND_URL}/status", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def process_pdf(file) -> dict:
    """
    Upload PDF to FastAPI backend.
    Backend runs: OCR → chunk → TF-IDF index → store in db.json
    Returns metadata dict used by the UI.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/upload",
            files={"file": (file.name, file.getvalue(), "application/pdf")},
            timeout=120,   # OCR can take a while on large PDFs
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "filename":   data["filename"],
            "pages":      data["pages_processed"],
            "ocr_done":   True,
            "indexed":    True,
            "ready":      True,
            "ocr_mode":   data.get("ocr_mode", "unknown"),
            "chunks":     data["chunks_created"],
        }
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Is the FastAPI server running?\n\n"
                 "`cd backend && uvicorn main:app --reload --port 8000`")
        st.stop()
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"❌ Upload failed: {detail}")
        st.stop()


def ask_question(question: str, doc_meta: dict) -> dict:
    """
    Send question to FastAPI backend.
    Backend runs: TF-IDF retrieval → Flan-T5 answer generation
    Returns answer, sources (as list of tuples), and confidence.
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/ask",
            json={"question": question, "k": 4},
            timeout=60,   # Flan-T5 on CPU can take a few seconds
        )
        resp.raise_for_status()
        data = resp.json()

        # Convert sources from list of dicts → list of (page_str, section_str) tuples
        # so the existing UI rendering code works unchanged
        sources = [
            (f"Page {s['page']}", f"Section {s['section']}")
            for s in data.get("sources", [])
        ]

        return {
            "answer":     data["answer"],
            "sources":    sources,
            "confidence": data["confidence"],
        }
    except requests.exceptions.ConnectionError:
        return {
            "answer":     "❌ Backend is not reachable. Please restart the FastAPI server.",
            "sources":    [],
            "confidence": 0.0,
        }
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        return {
            "answer":     f"❌ Error from backend: {detail}",
            "sources":    [],
            "confidence": 0.0,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "doc_meta": None,
        "chat_history": [],
        "uploaded_file": None,
        "last_replaced_filename": None,   # guards against sidebar uploader re-firing
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
doc_ready = st.session_state.doc_meta is not None

# ─────────────────────────────────────────────────────────────────────────────
#  MASTER CSS  — Deep space palette + neon accents + spring hover physics
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
<style>
/* ════════════════════════════════════════════════════
   FONTS
════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=DM+Sans:wght@400;500;600;700&display=swap');

/* ════════════════════════════════════════════════════
   DESIGN TOKENS
════════════════════════════════════════════════════ */
:root {
  /* Core palette – deep indigo night with neon highlights */
  --space:       #07060f;
  --space2:      #0e0c1e;
  --surface:     #13112a;
  --surface2:    #1a1735;
  --surface3:    #221f42;
  --border:      rgba(120,100,255,0.18);
  --border2:     rgba(120,100,255,0.35);

  /* Neon accents */
  --violet:      #7c6fff;
  --violet2:     #a78bfa;
  --cyan:        #22d3ee;
  --pink:        #f472b6;
  --amber:       #fbbf24;
  --green:       #34d399;

  /* Gradients */
  --grad-main:   linear-gradient(135deg, #7c6fff 0%, #22d3ee 100%);
  --grad-warm:   linear-gradient(135deg, #f472b6 0%, #fbbf24 100%);
  --grad-cool:   linear-gradient(135deg, #6366f1 0%, #06b6d4 100%);
  --grad-card:   linear-gradient(145deg, rgba(28,25,60,0.9) 0%, rgba(20,18,48,0.95) 100%);

  /* Text */
  --text:        #e8e6ff;
  --text2:       #9b97cc;
  --text3:       #6b6799;

  /* Misc */
  --radius-sm:   10px;
  --radius:      18px;
  --radius-lg:   26px;
  --radius-xl:   36px;
  --shadow-neon: 0 0 30px rgba(124,111,255,0.25), 0 8px 32px rgba(0,0,0,0.4);
  --shadow-card: 0 4px 24px rgba(0,0,0,0.35);
  --transition:  all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ════════════════════════════════════════════════════
   GLOBAL RESET & BASE
════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
section[data-testid="stMain"] > div {
  font-family: 'DM Sans', sans-serif !important;
  background: transparent !important;
  color: var(--text) !important;
}

[data-testid="stHeader"]      { background: transparent !important; display: none; }
[data-testid="stDecoration"]  { display: none; }

/* Main content padding */
.main .block-container {
  padding-top: 0 !important;
  padding-bottom: 2rem !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
  max-width: 960px !important;
}

/* ════════════════════════════════════════════════════
   LIGHT BEAM BACKGROUND  (inspired by screenshot)
════════════════════════════════════════════════════ */
body::before {
  content: '';
  position: fixed; inset: 0;
  background: #020510;
  z-index: -20;
}

/* The two dramatic crossing light beams */
body::after {
  content: '';
  position: fixed; inset: 0;
  background:
    /* Left beam — sweeps from bottom-left upward */
    radial-gradient(ellipse 55% 80% at -5% 110%,
      rgba(30, 100, 255, 0.55) 0%,
      rgba(20, 60, 200, 0.25) 35%,
      transparent 65%),
    /* Right beam — sweeps from bottom-right upward */
    radial-gradient(ellipse 55% 80% at 105% 110%,
      rgba(30, 100, 255, 0.55) 0%,
      rgba(20, 60, 200, 0.25) 35%,
      transparent 65%),
    /* Center glow where beams meet */
    radial-gradient(ellipse 60% 35% at 50% 100%,
      rgba(80, 160, 255, 0.35) 0%,
      rgba(40, 100, 255, 0.15) 50%,
      transparent 75%),
    /* Top center subtle glow */
    radial-gradient(ellipse 40% 30% at 50% 0%,
      rgba(20, 60, 180, 0.2) 0%,
      transparent 70%),
    /* Base deep navy */
    linear-gradient(180deg, #020510 0%, #040820 50%, #020510 100%);
  z-index: -18;
  animation: beamPulse 6s ease-in-out infinite alternate;
}

@keyframes beamPulse {
  0%   { opacity: 0.85; }
  100% { opacity: 1; }
}

/* Floating blob layer */
.blob-container {
  position: fixed; inset: 0;
  overflow: hidden;
  z-index: -15;
  pointer-events: none;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(110px);
  opacity: 0.12;
  animation: blobFloat ease-in-out infinite alternate;
}
.b1 { width:600px;height:300px; background:#1e50ff; bottom:-5%;left:-10%; animation-duration:22s; }
.b2 { width:600px;height:300px; background:#1e50ff; bottom:-5%;right:-10%; animation-duration:26s; animation-delay:-8s; }
.b3 { width:400px;height:400px; background:#0a2fcc; top:20%;left:30%; animation-duration:30s; animation-delay:-14s; opacity:0.08; }
.b4 { width:200px;height:200px; background:#60a0ff; bottom:10%;left:46%; animation-duration:18s; animation-delay:-4s; opacity:0.18; }

@keyframes blobFloat {
  0%   { transform: translate(0,0) scale(1); }
  50%  { transform: translate(20px,-30px) scale(1.04); }
  100% { transform: translate(-15px,20px) scale(0.97); }
}

/* Subtle star field */
.blob-container::after {
  content: '';
  position: absolute; inset: 0;
  background-image:
    radial-gradient(1px 1px at 15% 20%, rgba(255,255,255,0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 35% 8%,  rgba(255,255,255,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 60% 15%, rgba(255,255,255,0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 80% 5%,  rgba(255,255,255,0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 25%, rgba(255,255,255,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 5%  40%, rgba(255,255,255,0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 70% 35%, rgba(255,255,255,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 25% 55%, rgba(255,255,255,0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 45% 45%, rgba(255,255,255,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 95% 50%, rgba(255,255,255,0.2) 0%, transparent 100%);
  pointer-events: none;
}

/* Rising particles */
.particle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: -10;
  animation: riseUp linear infinite;
}
@keyframes riseUp {
  0%   { transform: translateY(0) translateX(0) scale(1); opacity: 0; }
  8%   { opacity: 0.5; }
  92%  { opacity: 0.3; }
  100% { transform: translateY(-110vh) translateX(var(--drift,20px)) scale(0.6); opacity: 0; }
}

/* ════════════════════════════════════════════════════
   SIDEBAR  — deep glass card
════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: rgba(10,9,28,0.92) !important;
  border-right: 1px solid var(--border) !important;
  backdrop-filter: blur(20px) saturate(180%) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1rem !important; }

.sb-brand {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.3rem;
  font-weight: 900;
  background: var(--grad-main);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 18px;
  letter-spacing: -0.5px;
}

.sb-card {
  background: var(--grad-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  margin-bottom: 12px;
  transition: var(--transition-smooth);
  position: relative;
  overflow: hidden;
}
.sb-card::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(124,111,255,0.06) 0%, transparent 60%);
  opacity: 0;
  transition: opacity 0.3s;
}
.sb-card:hover::before { opacity: 1; }
.sb-card:hover {
  border-color: var(--border2);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(124,111,255,0.15);
}

.sb-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--text3);
  margin-bottom: 8px;
}
.sb-docname {
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--text);
  word-break: break-all;
  line-height: 1.4;
}
.sb-pages {
  font-size: 0.78rem;
  color: var(--text3);
  margin-top: 4px;
}

/* Status rows */
.status-item {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 0.88rem;
  color: var(--text2);
  margin-bottom: 8px;
}
.dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-on  { background: var(--green); box-shadow: 0 0 8px rgba(52,211,153,0.7); animation: pulse-dot 2s ease infinite; }
.dot-off { background: var(--surface3); }
@keyframes pulse-dot {
  0%,100% { box-shadow: 0 0 4px rgba(52,211,153,0.5); }
  50%     { box-shadow: 0 0 12px rgba(52,211,153,0.9); }
}

/* ════════════════════════════════════════════════════
   BUTTONS  — spring bounce hover
════════════════════════════════════════════════════ */
div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
  border: none !important;
  border-radius: 50px !important;
  padding: 0.55rem 1.6rem !important;
  cursor: pointer !important;
  position: relative !important;
  overflow: hidden !important;
  transition: var(--transition) !important;
  letter-spacing: 0.2px !important;
}

/* Primary send button */
div[data-testid="stButton"]:not(.sb-btn) > button {
  background: linear-gradient(135deg, #7c6fff, #22d3ee) !important;
  color: #fff !important;
  box-shadow: 0 4px 20px rgba(124,111,255,0.45), 0 0 0 0 rgba(124,111,255,0) !important;
}
div[data-testid="stButton"] > button::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.15), transparent);
  opacity: 0;
  transition: opacity 0.25s;
}
div[data-testid="stButton"] > button:hover {
  transform: translateY(-3px) scale(1.04) !important;
  box-shadow: 0 8px 32px rgba(124,111,255,0.6), 0 0 20px rgba(34,211,238,0.3) !important;
}
div[data-testid="stButton"] > button:hover::after { opacity: 1; }
div[data-testid="stButton"] > button:active {
  transform: translateY(1px) scale(0.98) !important;
  box-shadow: 0 2px 10px rgba(124,111,255,0.4) !important;
}

/* Download button */
div[data-testid="stDownloadButton"] > button {
  background: linear-gradient(135deg, #6366f1, #a855f7) !important;
  color: #fff !important;
  box-shadow: 0 4px 18px rgba(99,102,241,0.4) !important;
  width: 100% !important;
}
div[data-testid="stDownloadButton"] > button:hover {
  transform: translateY(-3px) scale(1.03) !important;
  box-shadow: 0 8px 28px rgba(99,102,241,0.55), 0 0 16px rgba(168,85,247,0.3) !important;
}

/* ════════════════════════════════════════════════════
   FILE UPLOADER  — glowing dropzone
════════════════════════════════════════════════════ */
.stFileUploader > div { border: none !important; }
[data-testid="stFileUploaderDropzone"] {
  background: rgba(124,111,255,0.06) !important;
  border: 2px dashed rgba(124,111,255,0.4) !important;
  border-radius: var(--radius) !important;
  transition: var(--transition-smooth) !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
  background: rgba(124,111,255,0.1) !important;
  border-color: var(--violet) !important;
  box-shadow: 0 0 24px rgba(124,111,255,0.2) inset, 0 0 16px rgba(124,111,255,0.15) !important;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--text2) !important; }

/* ════════════════════════════════════════════════════
   TEXT INPUT  — glowing focus ring
════════════════════════════════════════════════════ */
div[data-testid="stTextInput"] input {
  background: rgba(20,18,48,0.9) !important;
  border: 1px solid var(--border) !important;
  border-radius: 50px !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.95rem !important;
  padding: 0.7rem 1.4rem !important;
  transition: var(--transition-smooth) !important;
  box-shadow: 0 0 0 0 rgba(124,111,255,0) !important;
}
div[data-testid="stTextInput"] input:focus {
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 3px rgba(124,111,255,0.2), 0 0 20px rgba(124,111,255,0.15) !important;
  outline: none !important;
}
div[data-testid="stTextInput"] input::placeholder { color: var(--text3) !important; }

/* ════════════════════════════════════════════════════
   HERO  (pre-upload screen)
════════════════════════════════════════════════════ */
.hero {
  text-align: center;
  padding: 52px 0 16px;
  animation: fadeDown 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.hero-wordmark {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 4.8rem;
  font-weight: 900;
  letter-spacing: -3px;
  line-height: 1;
  background: linear-gradient(135deg, #a78bfa 0%, #38bdf8 50%, #f472b6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 40px rgba(124,111,255,0.4));
  animation: shimmer 4s ease-in-out infinite;
  background-size: 200% 200%;
}
@keyframes shimmer {
  0%,100% { background-position: 0% 50%; }
  50%      { background-position: 100% 50%; }
}
.hero-tagline {
  font-family: 'DM Sans', sans-serif;
  font-size: 1.1rem;
  color: var(--text2);
  margin-top: 12px;
  letter-spacing: 0.3px;
}
.hero-sub {
  font-size: 0.95rem;
  color: var(--text3);
  margin-top: 8px;
  max-width: 480px;
  margin-left: auto; margin-right: auto;
  line-height: 1.6;
}

@keyframes fadeDown {
  from { opacity: 0; transform: translateY(-32px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ════════════════════════════════════════════════════
   UPLOAD CARD  (pre-upload)
════════════════════════════════════════════════════ */
.upload-card {
  background: var(--grad-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 40px 44px 32px;
  text-align: center;
  position: relative;
  overflow: hidden;
  animation: fadeUp 0.8s cubic-bezier(0.22,1,0.36,1) 0.15s both;
  transition: var(--transition-smooth);
}
.upload-card::before {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 70% 50% at 50% 0%, rgba(124,111,255,0.15) 0%, transparent 70%);
}
.upload-card:hover {
  border-color: rgba(124,111,255,0.5);
  box-shadow: 0 0 40px rgba(124,111,255,0.15), 0 16px 48px rgba(0,0,0,0.3);
  transform: translateY(-4px);
}
.upload-icon { font-size: 3rem; margin-bottom: 12px; display: block; animation: float 3s ease-in-out infinite; }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
.upload-h { font-family:'Plus Jakarta Sans',sans-serif; font-size:1.35rem; font-weight:800; color:var(--text); margin-bottom:6px; }
.upload-p { font-size:0.9rem; color:var(--text3); margin-bottom:20px; }

/* ════════════════════════════════════════════════════
   FEATURE PILLS  (pre-upload)
════════════════════════════════════════════════════ */
.pills-row {
  display: flex; flex-wrap: wrap; gap: 10px;
  justify-content: center;
  margin: 20px auto 28px;
  max-width: 660px;
  animation: fadeUp 0.9s cubic-bezier(0.22,1,0.36,1) 0.3s both;
}
.pill {
  background: rgba(124,111,255,0.1);
  border: 1px solid rgba(124,111,255,0.25);
  border-radius: 40px;
  padding: 8px 18px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--violet2);
  display: flex; align-items: center; gap: 6px;
  backdrop-filter: blur(8px);
  transition: var(--transition);
  cursor: default;
}
.pill:hover {
  background: rgba(124,111,255,0.2);
  border-color: rgba(124,111,255,0.5);
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 6px 20px rgba(124,111,255,0.25);
}

/* ════════════════════════════════════════════════════
   TOAST BANNER  (post-upload)
════════════════════════════════════════════════════ */
.toast-banner {
  background: linear-gradient(90deg, rgba(52,211,153,0.15) 0%, rgba(34,211,238,0.1) 100%);
  border: 1px solid rgba(52,211,153,0.3);
  border-radius: var(--radius);
  padding: 12px 22px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #6ee7b7;
  font-weight: 600;
  font-size: 0.92rem;
  margin-bottom: 20px;
  animation: fadeUp 0.5s ease both;
  box-shadow: 0 0 20px rgba(52,211,153,0.08);
}
.toast-dot { width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 8px rgba(52,211,153,0.8);animation:pulse-dot 1.5s ease infinite; }

/* ════════════════════════════════════════════════════
   CHAT  — premium bubbles
════════════════════════════════════════════════════ */
.chat-scroll {
  max-height: 58vh;
  overflow-y: auto;
  padding: 4px 2px 12px;
  scrollbar-width: thin;
  scrollbar-color: rgba(124,111,255,0.25) transparent;
}
.chat-scroll::-webkit-scrollbar { width: 4px; }
.chat-scroll::-webkit-scrollbar-thumb { background: rgba(124,111,255,0.25); border-radius: 8px; }

.chat-empty {
  text-align: center;
  padding: 64px 20px;
  color: var(--text3);
}
.chat-empty .empty-icon { font-size: 3.2rem; margin-bottom: 14px; opacity: 0.7; animation: float 4s ease-in-out infinite; }
.chat-empty .empty-h    { font-size: 1rem; font-weight: 700; color: var(--text2); }
.chat-empty .empty-sub  { font-size: 0.83rem; margin-top: 5px; }

.msg-row {
  display: flex;
  gap: 11px;
  margin-bottom: 20px;
  animation: msgSlide 0.35s cubic-bezier(0.22,1,0.36,1) both;
}
.msg-row.user  { flex-direction: row-reverse; }
@keyframes msgSlide {
  from { opacity: 0; transform: translateY(14px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
  position: relative;
}
.avatar-user { background: linear-gradient(135deg, #f472b6, #fbbf24); box-shadow: 0 0 12px rgba(244,114,182,0.4); }
.avatar-ai   { background: linear-gradient(135deg, #7c6fff, #22d3ee); box-shadow: 0 0 12px rgba(124,111,255,0.4); }

.bubble {
  max-width: 70%;
  padding: 14px 18px;
  border-radius: 20px;
  font-size: 0.94rem;
  line-height: 1.65;
  position: relative;
  transition: var(--transition-smooth);
}
.bubble:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(0,0,0,0.25) !important;
}

.bubble-user {
  background: linear-gradient(135deg, rgba(244,114,182,0.18), rgba(251,191,36,0.12));
  border: 1px solid rgba(244,114,182,0.25);
  border-bottom-right-radius: 4px;
  color: var(--text);
  box-shadow: 0 2px 16px rgba(244,114,182,0.1);
}
.bubble-ai {
  background: var(--grad-card);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
  color: var(--text);
  box-shadow: 0 2px 16px rgba(0,0,0,0.2);
}

/* Sources row */
.sources {
  display: flex; flex-wrap: wrap; gap: 6px;
  align-items: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(124,111,255,0.12);
}
.src-lbl { font-size: 0.73rem; font-weight: 700; color: var(--text3); text-transform: uppercase; letter-spacing: 0.8px; }
.src-chip {
  background: rgba(34,211,238,0.1);
  border: 1px solid rgba(34,211,238,0.25);
  color: #67e8f9;
  font-size: 0.75rem; font-weight: 600;
  padding: 3px 10px; border-radius: 20px;
  transition: var(--transition);
  cursor: default;
}
.src-chip:hover {
  background: rgba(34,211,238,0.2);
  border-color: rgba(34,211,238,0.5);
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 12px rgba(34,211,238,0.2);
}

/* Confidence badge */
.conf { display:inline-block; font-size:0.73rem; font-weight:700; padding:3px 12px; border-radius:20px; margin-top:8px; letter-spacing:0.3px; }
.conf-high   { background:rgba(52,211,153,0.15);  color:#6ee7b7; border:1px solid rgba(52,211,153,0.3); }
.conf-medium { background:rgba(251,191,36,0.15);  color:#fde68a; border:1px solid rgba(251,191,36,0.3); }
.conf-low    { background:rgba(248,113,113,0.15); color:#fca5a5; border:1px solid rgba(248,113,113,0.3); }

/* ════════════════════════════════════════════════════
   CHAT INPUT ROW  — floating bar
════════════════════════════════════════════════════ */
.input-wrapper {
  background: rgba(13,11,30,0.85);
  border: 1px solid var(--border);
  border-radius: 60px;
  padding: 6px 8px 6px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  backdrop-filter: blur(20px);
  transition: var(--transition-smooth);
  margin-top: 14px;
}
.input-wrapper:focus-within {
  border-color: rgba(124,111,255,0.6);
  box-shadow: 0 0 0 3px rgba(124,111,255,0.12), 0 8px 32px rgba(0,0,0,0.3);
}

/* ════════════════════════════════════════════════════
   SUGGESTION CHIPS
════════════════════════════════════════════════════ */
.sug-chip {
  background: rgba(124,111,255,0.08);
  border: 1px solid rgba(124,111,255,0.2);
  border-radius: var(--radius);
  padding: 10px 14px;
  font-size: 0.83rem;
  font-weight: 500;
  color: var(--text2);
  text-align: center;
  transition: var(--transition);
  cursor: pointer;
}
.sug-chip:hover {
  background: rgba(124,111,255,0.16);
  border-color: rgba(124,111,255,0.45);
  color: var(--violet2);
  transform: translateY(-3px) scale(1.03);
  box-shadow: 0 6px 22px rgba(124,111,255,0.2);
}

/* ════════════════════════════════════════════════════
   PROCESSING SPINNER
════════════════════════════════════════════════════ */
.proc-wrap {
  text-align: center;
  padding: 32px;
}
.proc-ring {
  width: 52px; height: 52px;
  border-radius: 50%;
  border: 3px solid rgba(124,111,255,0.15);
  border-top-color: var(--violet);
  border-right-color: var(--cyan);
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.proc-text { font-size: 0.9rem; font-weight: 600; color: var(--text2); }
.proc-sub  { font-size: 0.8rem; color: var(--text3); margin-top: 4px; }

/* ════════════════════════════════════════════════════
   TOP NAVBAR
════════════════════════════════════════════════════ */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, rgba(20,18,48,0.95) 0%, rgba(13,11,30,0.98) 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 24px;
  margin-bottom: 16px;
  backdrop-filter: blur(20px);
  animation: fadeDown 0.5s ease both;
  box-shadow: 0 4px 24px rgba(0,0,0,0.3), 0 0 0 1px rgba(124,111,255,0.05);
}
.topbar-left { display: flex; flex-direction: column; gap: 3px; }
.topbar-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.3px;
}
.topbar-sub { font-size: 0.78rem; color: var(--text3); font-family: monospace; }

.topbar-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.topbar-stat {
  text-align: center;
  padding: 6px 14px;
  background: rgba(124,111,255,0.08);
  border: 1px solid rgba(124,111,255,0.15);
  border-radius: 12px;
  transition: var(--transition);
}
.topbar-stat:hover {
  background: rgba(124,111,255,0.15);
  border-color: rgba(124,111,255,0.3);
  transform: translateY(-2px);
}
.topbar-stat-val {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.1rem;
  font-weight: 800;
  background: var(--grad-main);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}
.topbar-stat-lbl { font-size: 0.68rem; color: var(--text3); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.8px; }

.topbar-avatar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px 6px 6px;
  background: rgba(244,114,182,0.08);
  border: 1px solid rgba(244,114,182,0.2);
  border-radius: 40px;
  transition: var(--transition);
  cursor: default;
}
.topbar-avatar:hover {
  background: rgba(244,114,182,0.14);
  border-color: rgba(244,114,182,0.35);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(244,114,182,0.15);
}
.avatar-ring {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f472b6, #fbbf24);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 800; font-size: 0.95rem;
  color: white;
  box-shadow: 0 0 12px rgba(244,114,182,0.4);
  flex-shrink: 0;
}
.avatar-name { font-size: 0.85rem; font-weight: 700; color: var(--text); line-height: 1.2; }
.avatar-role { font-size: 0.7rem; color: var(--text3); }

/* ════════════════════════════════════════════════════
   SIDEBAR HOME BUTTON
════════════════════════════════════════════════════ */
div[data-testid="stSidebar"] div[data-testid="stButton"]:first-child > button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 1.3rem !important;
  font-weight: 900 !important;
  padding: 4px 0 !important;
  border-radius: 8px !important;
  background: linear-gradient(135deg, #7c6fff, #22d3ee) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
  letter-spacing: -0.5px !important;
  width: auto !important;
  transition: opacity 0.2s, transform 0.2s !important;
}
div[data-testid="stSidebar"] div[data-testid="stButton"]:first-child > button:hover {
  opacity: 0.75 !important;
  transform: translateY(-1px) !important;
  box-shadow: none !important;
}

/* ════════════════════════════════════════════════════
   SPINNER (st.spinner override)
════════════════════════════════════════════════════ */
[data-testid="stSpinner"] > div {
  border-top-color: var(--violet) !important;
}

/* ════════════════════════════════════════════════════
   MISC HELPERS
════════════════════════════════════════════════════ */
hr { border-color: var(--border) !important; margin: 12px 0 !important; }

/* Markdown text */
.stMarkdown p, .stMarkdown li { color: var(--text2) !important; }
.stMarkdown strong { color: var(--text) !important; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND PARTICLES  (generated once per render)
# ─────────────────────────────────────────────────────────────────────────────

def render_bg():
    colors = [
        "rgba(124,111,255,0.5)", "rgba(34,211,238,0.5)",
        "rgba(244,114,182,0.4)", "rgba(99,102,241,0.5)",
        "rgba(167,139,250,0.4)", "rgba(14,165,233,0.4)",
    ]
    p_html = ""
    for _ in range(22):
        sz   = random.randint(4, 16)
        left = random.randint(0, 100)
        bot  = random.randint(-5, 5)
        dur  = random.uniform(14, 32)
        dly  = random.uniform(0, 20)
        drift = random.randint(-30, 30)
        col  = random.choice(colors)
        p_html += (
            f'<div class="particle" style="'
            f'width:{sz}px;height:{sz}px;background:{col};'
            f'left:{left}vw;bottom:{bot}vh;'
            f'--drift:{drift}px;'
            f'animation-duration:{dur:.1f}s;animation-delay:{dly:.1f}s;'
            f'"></div>'
        )
    st.markdown(
        f'<div class="blob-container">'
        f'<div class="blob b1"></div>'
        f'<div class="blob b2"></div>'
        f'<div class="blob b3"></div>'
        f'<div class="blob b4"></div>'
        f'<div class="blob b5"></div>'
        f'{p_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def confidence_badge(score: float) -> str:
    pct = int(score * 100)
    if score >= 0.85:
        return f'<span class="conf conf-high">✦ {pct}% confident</span>'
    elif score >= 0.65:
        return f'<span class="conf conf-medium">◈ {pct}% confident</span>'
    return f'<span class="conf conf-low">⚠ {pct}% confident</span>'


def render_message(role: str, content: str, sources=None, confidence=None) -> str:
    is_user = role == "user"
    avatar_cls = "avatar-user" if is_user else "avatar-ai"
    bubble_cls = "bubble-user" if is_user else "bubble-ai"
    icon = "🎓" if is_user else "✦"
    extra = ""
    if not is_user and sources:
        chips = "".join(f'<span class="src-chip">📄 {p} · {s}</span>' for p, s in sources)
        badge = confidence_badge(confidence) if confidence else ""
        extra = f'<div class="sources"><span class="src-lbl">Sources</span>{chips}</div>{badge}'
    row_cls = "user" if is_user else "ai"
    return f"""
    <div class="msg-row {row_cls}">
      <div class="avatar {avatar_cls}">{icon}</div>
      <div class="bubble {bubble_cls}">{content}{extra}</div>
    </div>"""


def build_report(history: list) -> str:
    lines = [
        "# ExamHelp — Study Session Report",
        f"_Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}_",
        "", "---", "",
    ]
    for i, m in enumerate(history, 1):
        label = "**You**" if m["role"] == "user" else "**ExamHelp**"
        lines += [f"### {i}. {label}", m["content"]]
        if m.get("sources"):
            lines.append("*Sources: " + ", ".join(f"{p} – {s}" for p,s in m["sources"]) + "*")
        if m.get("confidence"):
            lines.append(f"*Confidence: {int(m['confidence']*100)}%*")
        lines.append("")
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
#  INJECT CSS + BACKGROUND
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(CSS, unsafe_allow_html=True)
render_bg()

# ─────────────────────────────────────────────────────────────────────────────
#  ██████████  PRE-UPLOAD SCREEN  ██████████
# ─────────────────────────────────────────────────────────────────────────────

if not doc_ready:

    backend_alive = check_backend_alive()
    backend_warn = "" if backend_alive else """
    <div class="be-warn">
      ⚠️ <strong>Backend not running.</strong>
      Start: <code>cd backend &amp;&amp; uvicorn main:app --reload --port 8000</code>
    </div>"""

    st.markdown(f"""
    <style>
    /* Hide sidebar on landing */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"] {{ display:none !important; }}
    .main .block-container,
    .block-container {{
      padding: 0 !important;
      margin: 0 !important;
      max-width: 100% !important;
      min-width: 100% !important;
    }}
    /* Kill any Streamlit top gap */
    .main > div:first-child {{ padding-top: 0 !important; }}
    section[data-testid="stMain"] > div {{ padding-top: 0 !important; }}

    /* ── Navbar ── */
    .lp-nav {{
      display:flex; align-items:center; justify-content:space-between;
      padding: 18px 56px;
      background: rgba(2,5,16,0.65);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid rgba(255,255,255,0.05);
      animation: fadeDown 0.5s ease both;
    }}
    .lp-logo {{
      font-family:'Plus Jakarta Sans',sans-serif;
      font-size:1.2rem; font-weight:900;
      background: linear-gradient(135deg,#fff 0%,#7eb3ff 100%);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      background-clip:text; letter-spacing:-0.5px;
    }}
    .lp-links {{
      display:flex; align-items:center; gap:2px;
      background:rgba(255,255,255,0.05);
      border:1px solid rgba(255,255,255,0.09);
      border-radius:40px; padding:4px 6px;
    }}
    .lp-link {{
      font-size:0.82rem; font-weight:500;
      color:rgba(255,255,255,0.5);
      padding:6px 18px; border-radius:30px;
      transition:all 0.2s; cursor:default;
    }}
    .lp-link:hover {{ color:#fff; background:rgba(255,255,255,0.08); }}
    .lp-link.on {{ color:#fff; background:rgba(255,255,255,0.1); font-weight:600; }}
    .lp-cta {{
      font-family:'Plus Jakarta Sans',sans-serif;
      font-size:0.82rem; font-weight:700; color:#fff;
      background:linear-gradient(135deg,#1e50ff,#0ea5e9);
      border:none; border-radius:30px; padding:8px 22px;
      box-shadow:0 0 18px rgba(30,80,255,0.45);
      cursor:default; transition:all 0.2s;
    }}
    .lp-cta:hover {{ transform:translateY(-1px); box-shadow:0 0 28px rgba(30,80,255,0.6); }}

    /* ── Hero ── */
    .lp-hero {{
      text-align:center;
      padding: 96px 24px 72px;
      animation: fadeDown 0.7s ease 0.1s both;
    }}
    .lp-eyebrow {{
      display:inline-flex; align-items:center; gap:8px;
      background:rgba(255,255,255,0.05);
      border:1px solid rgba(255,255,255,0.1);
      border-radius:30px; padding:6px 16px;
      font-size:0.72rem; color:rgba(255,255,255,0.45);
      letter-spacing:1.8px; text-transform:uppercase;
      font-family:'DM Sans',monospace;
      margin-bottom:28px;
    }}
    .lp-eyebrow-dot {{
      width:6px; height:6px; border-radius:50%;
      background:#1e90ff; box-shadow:0 0 8px #1e90ff;
    }}
    .lp-h1 {{
      font-family:'Plus Jakarta Sans',sans-serif;
      font-size:clamp(2.8rem,5.5vw,4.8rem);
      font-weight:900; letter-spacing:-2.5px; line-height:1.05;
      color:#fff; margin-bottom:22px;
    }}
    .lp-h1 .grad {{
      background:linear-gradient(135deg,#4d9fff 0%,#a78bfa 50%,#60cfff 100%);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      background-clip:text; background-size:200% 200%;
      animation:shimmer 4s ease infinite;
    }}
    .lp-tagline {{
      font-size:1.05rem; color:rgba(255,255,255,0.4);
      max-width:460px; margin:0 auto 56px; line-height:1.7;
      font-family:'DM Sans',sans-serif;
    }}

    /* ── Divider ── */
    .lp-div {{
      height:1px; max-width:840px; margin:0 auto;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent);
    }}

    /* ── Features ── */
    .lp-feat {{
      padding:68px 48px 72px; text-align:center;
    }}
    .lp-sect-label {{
      display:inline-flex; align-items:center; gap:10px;
      font-size:0.72rem; color:rgba(255,255,255,0.3);
      letter-spacing:2px; text-transform:uppercase;
      font-family:'DM Sans',monospace; margin-bottom:20px;
    }}
    .lp-sect-label::before,.lp-sect-label::after {{
      content:''; width:60px; height:1px;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,0.12),transparent);
    }}
    .lp-feat-h {{
      font-family:'Plus Jakarta Sans',sans-serif;
      font-size:clamp(1.7rem,3vw,2.6rem);
      font-weight:800; color:#fff; letter-spacing:-1px; margin-bottom:10px;
    }}
    .lp-feat-sub {{
      font-size:0.9rem; color:rgba(255,255,255,0.35);
      margin-bottom:44px; font-family:'DM Sans',sans-serif;
    }}
    .lp-grid {{
      display:grid; grid-template-columns:repeat(3,1fr);
      gap:14px; max-width:880px; margin:0 auto;
    }}
    .lp-card {{
      background:rgba(255,255,255,0.04);
      border:1px solid rgba(255,255,255,0.07);
      border-radius:18px; padding:26px 22px; text-align:left;
      transition:all 0.3s cubic-bezier(0.34,1.56,0.64,1);
      position:relative; overflow:hidden;
    }}
    .lp-card::after {{
      content:''; position:absolute;
      top:0;left:0;right:0;height:1px;
      background:linear-gradient(90deg,transparent,rgba(80,140,255,0.4),transparent);
      opacity:0; transition:opacity 0.3s;
    }}
    .lp-card:hover {{
      transform:translateY(-6px);
      background:rgba(255,255,255,0.07);
      border-color:rgba(80,140,255,0.22);
      box-shadow:0 20px 40px rgba(0,0,0,0.25),0 0 30px rgba(30,80,255,0.06);
    }}
    .lp-card:hover::after {{ opacity:1; }}
    .lp-card-ico {{
      width:42px;height:42px; border-radius:11px;
      background:rgba(30,80,255,0.12);
      border:1px solid rgba(30,80,255,0.22);
      display:flex;align-items:center;justify-content:center;
      font-size:1.2rem; margin-bottom:13px;
    }}
    .lp-card-h {{ font-family:'Plus Jakarta Sans',sans-serif; font-size:0.92rem; font-weight:700; color:#fff; margin-bottom:5px; }}
    .lp-card-p {{ font-size:0.8rem; color:rgba(255,255,255,0.35); line-height:1.6; }}

    /* ── Upload section ── */
    .lp-upload {{
      padding:16px 48px 72px; text-align:center;
    }}
    .lp-upload-h {{
      font-family:'Plus Jakarta Sans',sans-serif;
      font-size:clamp(1.5rem,2.5vw,2.2rem);
      font-weight:800; color:#fff;
      margin-bottom:8px; letter-spacing:-0.8px;
    }}
    .lp-upload-sub {{
      font-size:0.88rem; color:rgba(255,255,255,0.35);
      margin-bottom:28px; font-family:'DM Sans',sans-serif;
    }}
    .be-warn {{
      background:rgba(248,113,113,0.1);
      border:1px solid rgba(248,113,113,0.28);
      border-radius:12px; padding:11px 18px;
      font-size:0.8rem; color:#fca5a5;
      max-width:520px; margin:0 auto 20px;
    }}
    .be-warn code {{
      background:rgba(255,255,255,0.08);
      padding:2px 7px; border-radius:5px; font-size:0.78rem;
    }}
    </style>

    <!-- NAVBAR -->
    <div class="lp-nav">
      <div class="lp-logo">✦ ExamHelp</div>
      <div class="lp-links">
        <span class="lp-link on">Home</span>
        <span class="lp-link">Features</span>
        <span class="lp-link">How it works</span>
        <span class="lp-link">Contact</span>
      </div>
      <div class="lp-cta">Get Started ↓</div>
    </div>

    <!-- HERO -->
    <div class="lp-hero">
      <div class="lp-eyebrow">
        <span class="lp-eyebrow-dot"></span>
        Gen AI Hackathon 2026
      </div>
      <div class="lp-h1">
        Study smarter with<br>
        <span class="grad">AI-powered notes</span>
      </div>
      <div class="lp-tagline">
        Upload your handwritten notes and get instant answers,<br>
        cited sources, and confidence scores — all offline.
      </div>
    </div>

    <div class="lp-div"></div>

    <!-- FEATURES -->
    <div class="lp-feat">
      <div class="lp-sect-label">Features</div>
      <div class="lp-feat-h">Everything you need to ace your exams</div>
      <div class="lp-feat-sub">Powered by OCR, TF-IDF retrieval, and local AI — no data leaves your machine.</div>
      <div class="lp-grid">
        <div class="lp-card"><div class="lp-card-ico">🔍</div><div class="lp-card-h">Handwriting OCR</div><div class="lp-card-p">Reads handwritten notes using Mistral Pixtral vision model with high accuracy.</div></div>
        <div class="lp-card"><div class="lp-card-ico">🧠</div><div class="lp-card-h">Smart Q&amp;A</div><div class="lp-card-p">Ask anything about your notes and get answers grounded only in your content.</div></div>
        <div class="lp-card"><div class="lp-card-ico">📄</div><div class="lp-card-h">Source Citations</div><div class="lp-card-p">Every answer shows which page and section it came from in your notes.</div></div>
        <div class="lp-card"><div class="lp-card-ico">💡</div><div class="lp-card-h">Confidence Scores</div><div class="lp-card-p">Color-coded badges show how well each answer matches your notes.</div></div>
        <div class="lp-card"><div class="lp-card-ico">☁️</div><div class="lp-card-h">Fully Offline</div><div class="lp-card-p">After OCR, everything runs locally. No cloud AI, no data sharing.</div></div>
        <div class="lp-card"><div class="lp-card-ico">📥</div><div class="lp-card-h">Export Report</div><div class="lp-card-p">Download a full markdown report of your Q&amp;A session with all sources.</div></div>
      </div>
    </div>

    <div class="lp-div"></div>

    <!-- UPLOAD HEADER -->
    <div class="lp-upload">
      <div class="lp-sect-label">Get Started</div>
      <div class="lp-upload-h">Upload your notes to begin</div>
      <div class="lp-upload-sub">Supports handwritten &amp; printed PDFs — any subject, any format</div>
      {backend_warn}
    </div>
    """, unsafe_allow_html=True)

    # Streamlit file uploader — centered
    _, col, _ = st.columns([1, 2.2, 1])
    with col:
        st.markdown("""
        <style>
        [data-testid="stFileUploaderDropzone"] {
          background: rgba(255,255,255,0.03) !important;
          border: 1px solid rgba(80,140,255,0.22) !important;
          border-radius: 22px !important;
          padding: 44px 44px 36px !important;
          text-align: center !important;
          transition: all 0.3s ease !important;
        }
        [data-testid="stFileUploaderDropzone"]:hover {
          border-color: rgba(80,140,255,0.5) !important;
          background: rgba(30,80,255,0.06) !important;
          box-shadow: 0 0 50px rgba(30,80,255,0.1), 0 0 100px rgba(30,80,255,0.05) !important;
          transform: translateY(-3px) !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] svg { display:none !important; }
        [data-testid="stFileUploaderDropzoneInstructions"]::before {
          content:"📂"; display:block;
          font-size:2.8rem; margin-bottom:10px;
          animation:float 3s ease-in-out infinite;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] > div > span {
          font-family:'Plus Jakarta Sans',sans-serif !important;
          font-size:1.05rem !important; font-weight:700 !important;
          color:rgba(255,255,255,0.8) !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] > div > small {
          color:rgba(255,255,255,0.28) !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
          background:linear-gradient(135deg,#1e50ff,#0ea5e9) !important;
          color:white !important; border:none !important;
          border-radius:50px !important;
          font-family:'Plus Jakarta Sans',sans-serif !important;
          font-weight:700 !important; font-size:0.88rem !important;
          padding:0.45rem 1.6rem !important; margin-top:10px !important;
          box-shadow:0 4px 20px rgba(30,80,255,0.4) !important;
          transition:all 0.25s cubic-bezier(0.34,1.56,0.64,1) !important;
        }
        [data-testid="stFileUploaderDropzone"] button:hover {
          transform:translateY(-3px) scale(1.05) !important;
          box-shadow:0 8px 28px rgba(30,80,255,0.55) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Upload PDF", type=["pdf"],
            label_visibility="collapsed",
        )

        if uploaded:
            prog = st.empty()
            prog.markdown("""
            <div class="proc-wrap">
              <div class="proc-ring"></div>
              <div class="proc-text">Processing your notes…</div>
              <div class="proc-sub">Running OCR · Chunking · Indexing</div>
            </div>
            """, unsafe_allow_html=True)
            meta = process_pdf(uploaded)
            st.session_state.doc_meta = meta
            st.session_state.uploaded_file = uploaded
            prog.empty()
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  ██████████  POST-UPLOAD SCREEN  ██████████
# ─────────────────────────────────────────────────────────────────────────────

else:
    meta = st.session_state.doc_meta
    history = st.session_state.chat_history

    # ── SIDEBAR ─────────────────────────────────────────────────────────────
    with st.sidebar:
        # Clicking the brand resets to home (page 1)
        if st.button("✦ ExamHelp", key="home_btn", use_container_width=False):
            st.session_state.doc_meta = None
            st.session_state.chat_history = []
            st.session_state.uploaded_file = None
            st.session_state.last_replaced_filename = None
            st.rerun()

        # Backend connectivity indicator
        backend_alive = check_backend_alive()
        be_dot = "dot-on" if backend_alive else "dot-off"
        be_label = "Backend connected" if backend_alive else "Backend offline"
        be_color = "" if backend_alive else "color:#f87171"
        st.markdown(f"""
        <div class="sb-card">
          <div class="sb-label">🔌 Server</div>
          <div class="status-item" style="{be_color}">
            <span class="dot {be_dot}"></span>{be_label}
          </div>
          <div style="font-size:0.72rem;color:var(--text3);margin-top:4px;font-family:monospace">
            localhost:8000
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Active document card
        ocr_mode = meta.get("ocr_mode", "mock")
        ocr_label = "🌐 Mistral Pixtral" if ocr_mode == "mistral_pixtral" else "🧪 Mock (add API key)"
        chunks_info = f"{meta.get('chunks', '?')} chunks indexed"
        st.markdown(f"""
        <div class="sb-card">
          <div class="sb-label">📄 Active Document</div>
          <div class="sb-docname">{meta["filename"]}</div>
          <div class="sb-pages">📑 {meta["pages"]} pages · {chunks_info}</div>
          <div style="font-size:0.75rem;color:var(--text3);margin-top:6px">OCR: {ocr_label}</div>
        </div>
        """, unsafe_allow_html=True)

        # System status card
        statuses = [
            ("OCR Completed",  meta.get("ocr_done", False)),
            ("Notes Indexed",  meta.get("indexed",  False)),
            ("Ready for Q&A",  meta.get("ready",    False)),
        ]
        rows_html = "".join(
            f'<div class="status-item"><span class="dot {"dot-on" if ok else "dot-off"}"></span>{label}</div>'
            for label, ok in statuses
        )
        st.markdown(f"""
        <div class="sb-card">
          <div class="sb-label">⚡ System Status</div>
          {rows_html}
        </div>
        """, unsafe_allow_html=True)

        # Session stats card
        n_q = sum(1 for m in history if m["role"] == "user")
        st.markdown(f"""
        <div class="sb-card">
          <div class="sb-label">💬 Session</div>
          <div class="status-item">
            <span class="dot dot-on"></span>
            {n_q} question{"s" if n_q != 1 else ""} asked
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Replace document — guard with filename check to prevent re-firing on reruns
        new_file = st.file_uploader("📎 Replace document", type=["pdf"], key="sidebar_uploader")
        if new_file and new_file.name != st.session_state.last_replaced_filename:
            with st.spinner("Processing new document…"):
                new_meta = process_pdf(new_file)
            # Reset all state for the new document
            st.session_state.doc_meta = new_meta
            st.session_state.uploaded_file = new_file
            st.session_state.chat_history = []
            st.session_state.last_replaced_filename = new_file.name
            st.rerun()

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        # Clear chat
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

        # Download report
        if history:
            st.download_button(
                label="📥 Download Report",
                data=build_report(history),
                file_name=f"examhelp_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    # ── MAIN AREA ────────────────────────────────────────────────────────────

    # Top navbar with user profile
    n_q = sum(1 for m in history if m["role"] == "user")
    st.markdown(f"""
    <div class="topbar">
      <div class="topbar-left">
        <div class="topbar-title">Study Session</div>
        <div class="topbar-sub">📄 {meta["filename"]}</div>
      </div>
      <div class="topbar-right">
        <div class="topbar-stat">
          <div class="topbar-stat-val">{meta["pages"]}</div>
          <div class="topbar-stat-lbl">Pages</div>
        </div>
        <div class="topbar-stat">
          <div class="topbar-stat-val">{meta.get("chunks","—")}</div>
          <div class="topbar-stat-lbl">Chunks</div>
        </div>
        <div class="topbar-stat">
          <div class="topbar-stat-val">{n_q}</div>
          <div class="topbar-stat-lbl">Asked</div>
        </div>
        <div class="topbar-avatar">
          <div class="avatar-ring">S</div>
          <div class="avatar-info">
            <div class="avatar-name">Srushti</div>
            <div class="avatar-role">Student</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Ready toast
    st.markdown(f"""
    <div class="toast-banner">
      <span class="toast-dot"></span>
      Your notes are ready — ask anything about <strong>{meta["filename"]}</strong>
    </div>
    """, unsafe_allow_html=True)

    # ── Chat history ─────────────────────────────────────────────────────────
    if not history:
        chat_inner = """
        <div class="chat-empty">
          <div class="empty-icon">💬</div>
          <div class="empty-h">Ask your first question</div>
          <div class="empty-sub">Try "Summarise my notes" or "Explain the concept on page 3"</div>
        </div>"""
    else:
        chat_inner = "".join(
            render_message(m["role"], m["content"], m.get("sources"), m.get("confidence"))
            for m in history
        )

    st.markdown(f'<div class="chat-scroll">{chat_inner}</div>', unsafe_allow_html=True)

    # ── Question input + send ─────────────────────────────────────────────────
    col_q, col_btn = st.columns([5, 1])
    with col_q:
        question = st.text_input(
            "question", label_visibility="collapsed",
            placeholder="e.g.  What are the main themes in my notes?",
            key="q_input",
        )
    with col_btn:
        send = st.button("Send ➤", use_container_width=True)

    # ── Suggestion chips (empty state) ───────────────────────────────────────
    if not history:
        suggestions = [
            "Summarise the key points",
            "What topics are covered?",
            "Explain page 2 in simple terms",
            "List the most important formulas",
        ]
        st.markdown('<div style="margin-top:16px; margin-bottom:4px;">', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, sug in enumerate(suggestions):
            with cols[i]:
                if st.button(sug, key=f"sug_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": sug})
                    with st.spinner("ExamHelp is thinking…"):
                        res = ask_question(sug, meta)
                    st.session_state.chat_history.append({
                        "role": "assistant", "content": res["answer"],
                        "sources": res["sources"], "confidence": res["confidence"],
                    })
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Send logic ────────────────────────────────────────────────────────────
    if send and question.strip():
        st.session_state.chat_history.append({"role": "user", "content": question.strip()})
        with st.spinner("ExamHelp is thinking…"):
            res = ask_question(question.strip(), meta)
        st.session_state.chat_history.append({
            "role": "assistant", "content": res["answer"],
            "sources": res["sources"], "confidence": res["confidence"],
        })
        st.rerun()
