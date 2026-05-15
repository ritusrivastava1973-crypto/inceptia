import streamlit as st
import json, time, uuid
import pandas as pd
import altair as alt
from pathlib import Path
import sys, importlib.util
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_state, save_state, STARTING_CASH, ROUND_DURATION
from streamlit_autorefresh import st_autorefresh

BREAK_DURATION = 300

st.set_page_config(page_title="Market Mayhem — Inceptia", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=3000, key="trade_refresh")

# FIX 1: JS-driven countdown — no Streamlit reruns needed for the timer
# Timer runs purely in JS, progress bar animates smoothly in CSS
# Streamlit only reruns for data (prices, news) every 8s — much less laggy

st.markdown("""
<style>
#MainMenu, header, footer { visibility: hidden; }
[data-testid="stSidebarNav"],[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stToolbar"],.stDeployButton,div[data-testid="stDecoration"],div[data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding-top: 0 !important; margin-top: 0 !important; }
div[data-testid="stAppViewContainer"] > section > div { padding-top: 0 !important; }

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.ticker-wrap { width:100%; overflow:hidden; background:#0a0a0f; border-bottom:1px solid #1e2030; padding:12px 0; }
.ticker { display:flex; white-space:nowrap; animation:ticker 40s linear infinite; }
.ticker-item { display:inline-block; padding:0 40px; font-size:15px; font-family:'Space Grotesk',monospace; letter-spacing:0.5px; color:#888; }
.ticker-item .sym { color:#fff; font-weight:700; margin-right:8px; }
.ticker-item .up { color:#00C896; } .ticker-item .down { color:#FF4D6A; }
@keyframes ticker { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }

.hero { background:linear-gradient(135deg,#0d0f1a 0%,#111420 50%,#0a1628 100%); border:1px solid #1e2535; border-radius:16px; padding:80px 48px; text-align:center; position:relative; overflow:hidden; margin-bottom:32px; }
.hero::before { content:''; position:absolute; top:-100px; left:50%; transform:translateX(-50%); width:600px; height:300px; background:radial-gradient(ellipse,rgba(0,200,150,0.08) 0%,transparent 70%); pointer-events:none; }
.hero-tag { display:inline-block; font-size:13px; font-weight:700; letter-spacing:4px; text-transform:uppercase; color:#00C896; border:1px solid rgba(0,200,150,0.3); padding:6px 18px; border-radius:99px; margin-bottom:20px; }
.hero h1 { font-family:'Space Grotesk',sans-serif; font-size:56px; font-weight:700; color:#ffffff; letter-spacing:-2px; line-height:1; margin-bottom:12px; }
.hero h1 span { color:#00C896; }
.hero p { font-size:16px; color:rgba(255,255,255,0.4); }

.phase-banner { padding:14px 20px; border-radius:10px; font-size:14px; font-weight:500; margin-bottom:16px; border:1px solid; }
.phase-lobby   { background:rgba(255,200,0,0.06);  border-color:rgba(255,200,0,0.2);  color:#ffd93d; }
.phase-trading { background:rgba(0,200,150,0.06);  border-color:rgba(0,200,150,0.2);  color:#00C896; }
.phase-between { background:rgba(255,140,0,0.06);  border-color:rgba(255,140,0,0.2);  color:#ff9a3c; }
.phase-ended   { background:rgba(255,77,106,0.06); border-color:rgba(255,77,106,0.2); color:#FF4D6A; }

/* JS countdown bar handled inline via components.html */

.metric-row { display:grid; gap:12px; margin-bottom:20px; }
.metric-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:16px 20px; }
.metric-card .label { font-size:11px; color:rgba(255,255,255,0.35); font-weight:500; letter-spacing:1px; text-transform:uppercase; margin-bottom:6px; }
.metric-card .value { font-size:22px; font-weight:600; font-family:'Space Grotesk',monospace; }
.metric-card .delta { font-size:12px; margin-top:4px; }
.delta-up { color:#00C896; } .delta-down { color:#FF4D6A; } .delta-neutral { color:rgba(255,255,255,0.3); }

/* FIX 3: Nav buttons — no emojis, bigger font, coloured matching metric tiles */
.nav-row { display:grid; grid-template-columns:repeat(4,1fr); gap:0; margin-bottom:24px; border-radius:12px; overflow:hidden; border:1px solid #1e2535; }
.nav-btn { padding:16px 8px; text-align:center; cursor:pointer; font-size:15px; font-weight:700; letter-spacing:0.5px; text-transform:uppercase; border-right:1px solid #1e2535; transition:all 0.15s; user-select:none; }
.nav-btn:last-child { border-right:none; }
/* Colours match metric tiles: Market=green, Intel=yellow, Banks=purple, Portfolio=blue */
.nav-market  { background:rgba(0,200,150,0.07);  color:rgba(0,200,150,0.5); }
.nav-intel   { background:rgba(255,211,61,0.06); color:rgba(255,211,61,0.5); }
.nav-banks   { background:rgba(167,139,250,0.07);color:rgba(167,139,250,0.5); }
.nav-portf   { background:rgba(79,142,247,0.07); color:rgba(79,142,247,0.5); }
.nav-market.nav-active  { background:rgba(0,200,150,0.15);  color:#00C896; }
.nav-intel.nav-active   { background:rgba(255,211,61,0.14); color:#ffd93d; }
.nav-banks.nav-active   { background:rgba(167,139,250,0.15);color:#a78bfa; }
.nav-portf.nav-active   { background:rgba(79,142,247,0.15); color:#4f8ef7; }
.nav-notif { display:inline-block; background:#FF4D6A; color:#fff; font-size:9px; font-weight:700; padding:1px 5px; border-radius:99px; margin-left:5px; vertical-align:middle; }

.section-hdr { font-family:'Space Grotesk',sans-serif; font-size:18px; font-weight:600; color:#fff; margin:0 0 16px; letter-spacing:-0.3px; border-bottom:1px solid #1e2535; padding-bottom:10px; }

.company-card { background:#0d0f1a; border:1px solid #1e2535; padding:20px 24px; }
.company-name { font-size:16px; font-weight:600; color:#fff; }
.company-meta { font-size:12px; color:rgba(255,255,255,0.35); margin-top:2px; }
.company-trait { font-size:12px; color:rgba(255,255,255,0.45); font-style:italic; margin-top:4px; }
.price-main { font-size:22px; font-weight:700; color:#fff; font-family:'Space Grotesk',monospace; }
.price-chg { font-size:13px; margin-top:2px; }
.risk-badge { display:inline-block; font-size:10px; font-weight:600; padding:3px 10px; border-radius:99px; letter-spacing:0.5px; text-transform:uppercase; margin-left:8px; }
.risk-low         { background:rgba(0,200,150,0.1);  color:#00C896; border:1px solid rgba(0,200,150,0.2); }
.risk-medium      { background:rgba(255,200,0,0.1);  color:#ffd93d; border:1px solid rgba(255,200,0,0.2); }
.risk-high        { background:rgba(255,77,106,0.1); color:#FF4D6A; border:1px solid rgba(255,77,106,0.2); }
.risk-medium-high { background:rgba(255,140,0,0.1);  color:#ff9a3c; border:1px solid rgba(255,140,0,0.2); }
.company-bio { font-size:13px; color:rgba(255,255,255,0.45); line-height:1.6; margin:10px 0 14px; padding:12px 16px; background:rgba(255,255,255,0.02); border-radius:8px; border-left:3px solid #1e2535; }

.buy-btn  button { background:#0a4a35 !important; border:1px solid #00C896 !important; color:#00C896 !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.buy-btn  button:hover { background:#0d5c42 !important; }
.sell-btn button { background:rgba(255,77,106,0.1) !important; border:1px solid rgba(255,77,106,0.35) !important; color:#FF4D6A !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.sell-btn button:hover { background:rgba(255,77,106,0.2) !important; }
.sell-btn button:disabled { opacity:0.3 !important; }
.max-btn  button { background:rgba(255,200,0,0.07) !important; border:1px solid rgba(255,200,0,0.25) !important; color:#ffd93d !important; font-size:11px !important; font-weight:700 !important; height:42px !important; }

.port-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:18px 22px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }
.port-name { font-size:15px; font-weight:600; color:#fff; }
.port-qty { font-size:12px; color:rgba(255,255,255,0.35); margin-top:2px; }
.port-stats { display:flex; gap:24px; flex-wrap:wrap; }
.port-stat .s-label { font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:3px; }
.port-stat .s-val { font-size:15px; font-weight:600; font-family:'Space Grotesk',monospace; color:#fff; }

.news-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:18px 22px; margin-bottom:12px; }
.news-label { display:inline-block; font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; padding:3px 10px; border-radius:99px; margin-bottom:10px; }
.nl-insider { background:rgba(139,92,246,0.15); color:#a78bfa; border:1px solid rgba(139,92,246,0.2); }
.nl-rumour  { background:rgba(255,140,0,0.12);  color:#ff9a3c; border:1px solid rgba(255,140,0,0.2); }
.nl-event   { background:rgba(255,77,106,0.12); color:#FF4D6A; border:1px solid rgba(255,77,106,0.2); }
.nl-custom  { background:rgba(255,200,0,0.12);  color:#ffd93d; border:1px solid rgba(255,200,0,0.2); }
.news-text  { font-size:15px; color:rgba(255,255,255,0.88); line-height:1.65; }

.loan-card { background:#0d0f1a; border:1px solid rgba(139,92,246,0.25); border-radius:12px; padding:18px 22px; margin-bottom:16px; }
.loan-title { font-size:13px; font-weight:600; color:#a78bfa; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:10px; }
.bank-grid { display:grid; grid-template-columns:1fr; gap:10px; margin-bottom:20px; }
.bank-card { background:#0d0f1a; border-radius:12px; padding:18px 20px; cursor:pointer; transition:all 0.2s; }
.bank-safe  { border:1px solid rgba(0,200,150,0.3); }
.bank-mid   { border:1px solid rgba(255,200,0,0.3); }
.bank-risky { border:1px solid rgba(255,77,106,0.3); }
.bank-card:hover { transform:translateY(-1px); box-shadow:0 4px 20px rgba(0,0,0,0.3); }
.bank-card .bk-name { font-size:14px; font-weight:700; color:#fff; margin-bottom:4px; }
.bank-card .bk-rate { font-size:22px; font-weight:700; font-family:'Space Grotesk',monospace; margin-bottom:6px; }
.bank-safe  .bk-rate { color:#00C896; }
.bank-mid   .bk-rate { color:#ffd93d; }
.bank-risky .bk-rate { color:#FF4D6A; }
.bank-card .bk-limit { font-size:12px; color:rgba(255,255,255,0.4); }
.bank-card .bk-note  { font-size:11px; color:rgba(255,255,255,0.25); margin-top:8px; font-style:italic; }
.bank-accordion { overflow:hidden; max-height:0; transition:max-height 0.4s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease; opacity:0; border-radius:0 0 12px 12px; margin-top:-4px; }
.bank-accordion.open { max-height:300px; opacity:1; }
.bank-accordion-inner { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-top:none; border-radius:0 0 12px 12px; padding:16px 20px; }
.bk-chevron { float:right; font-size:16px; transition:transform 0.3s; color:rgba(255,255,255,0.3); }
.bk-chevron.open { transform:rotate(180deg); color:rgba(255,255,255,0.6); }
.loan-btn   button { background:rgba(139,92,246,0.12) !important; border:1px solid rgba(139,92,246,0.3) !important; color:#a78bfa !important; font-weight:600 !important; }
.repay-btn  button { background:rgba(255,77,106,0.08) !important; border:1px solid rgba(255,77,106,0.25) !important; color:#FF4D6A !important; font-weight:600 !important; }

/* Settings gear button — handled inside st.components.v1.html */

.short-btn button { background:rgba(255,140,0,0.1) !important; border:1px solid rgba(255,140,0,0.35) !important; color:#ff9a3c !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.cover-btn button { background:rgba(56,189,248,0.1) !important; border:1px solid rgba(56,189,248,0.35) !important; color:#38bdf8 !important; font-weight:700 !important; font-size:14px !important; height:42px !important; }
.short-badge { display:inline-block; font-size:10px; font-weight:700; padding:2px 8px; border-radius:99px; background:rgba(255,140,0,0.12); color:#ff9a3c; border:1px solid rgba(255,140,0,0.25); margin-left:6px; letter-spacing:0.5px; text-transform:uppercase; }

.lb-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:16px 20px; margin-bottom:10px; display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
.lb-rank { font-size:26px; font-weight:900; font-family:'Space Grotesk',sans-serif; min-width:40px; color:rgba(255,255,255,0.15); }
.lb-rank.gold { color:#ffd700; } .lb-rank.silver { color:#c0c0c0; } .lb-rank.bronze { color:#cd7f32; }
.lb-name { font-size:16px; font-weight:700; color:#fff; flex:1; min-width:100px; }
.lb-stats { display:flex; gap:20px; flex-wrap:wrap; }
.lb-stat .ls2-label { font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:3px; }
.lb-stat .ls2-val   { font-size:15px; font-weight:600; font-family:'Space Grotesk',monospace; color:#fff; }
.lb-nw { font-size:18px; font-weight:700; font-family:'Space Grotesk',monospace; color:#00C896; white-space:nowrap; }

.rule-card { background:#0d0f1a; border:1px solid #1e2535; border-radius:12px; padding:20px 24px; margin-bottom:12px; display:flex; gap:18px; align-items:flex-start; }
.rule-num { font-size:28px; font-weight:900; color:rgba(0,200,150,0.25); font-family:'Space Grotesk',sans-serif; min-width:36px; line-height:1; }
.rule-content h4 { font-size:14px; font-weight:600; color:#fff; margin-bottom:4px; }
.rule-content p { font-size:13px; color:rgba(255,255,255,0.45); line-height:1.6; }

/* FIX 4: Game over screen */
.gameover-screen { text-align:center; padding:80px 20px 40px; }
.gameover-screen h1 { font-family:'Space Grotesk',sans-serif; font-size:64px; font-weight:900; color:#fff; letter-spacing:-3px; margin-bottom:16px; }
.gameover-screen h1 span { color:#00C896; }
.gameover-screen p { font-size:18px; color:rgba(255,255,255,0.4); max-width:500px; margin:0 auto; line-height:1.7; }

/* ═══════════════════════════════════════════════════════
   LIGHT MODE — warm cream, slate accents, proper contrast
   ═══════════════════════════════════════════════════════ */
body.light-mode,
body.light-mode [data-testid="stAppViewContainer"],
body.light-mode [data-testid="stAppViewBlockContainer"],
body.light-mode section.main,
body.light-mode .block-container,
body.light-mode [data-testid="column"],
body.light-mode [data-testid="stVerticalBlock"],
body.light-mode [data-testid="stHorizontalBlock"],
body.light-mode [data-testid="stElementContainer"],
body.light-mode [data-testid="stMarkdownContainer"],
body.light-mode .stApp,
body.light-mode .main {
  background: #f5f2ed !important; color: #1c2b1c !important;
}
/* Streamlit native widget overrides */
body.light-mode [data-testid="stNumberInput"] input,
body.light-mode [data-testid="stTextInput"] input,
body.light-mode [data-testid="stTextArea"] textarea {
  background: #fffef9 !important; color: #1c2b1c !important;
  border-color: #ddd5c8 !important;
}
body.light-mode [data-testid="stForm"],
body.light-mode [data-testid="stExpander"] {
  background: #fffef9 !important; border-color: #ddd5c8 !important;
}
/* Force all plain text in light mode to be dark */
body.light-mode p, body.light-mode span, body.light-mode div,
body.light-mode label, body.light-mode h1, body.light-mode h2,
body.light-mode h3, body.light-mode h4 {
  color: #1c2b1c;
}

/* Ticker */
body.light-mode .ticker-wrap { background:#ece6dd; border-color:#d5cdc3; }
body.light-mode .ticker-item { color:#3d3328; }
body.light-mode .ticker-item .sym { color:#1c2b1c; font-weight:800; }
body.light-mode .ticker-item .up   { color:#0a6640; }
body.light-mode .ticker-item .down { color:#b83232; }

/* Phase banners */
body.light-mode .phase-lobby   { background:rgba(140,100,0,0.08);  border-color:rgba(140,100,0,0.28);  color:#6b4c00; }
body.light-mode .phase-trading { background:rgba(0,100,55,0.07);   border-color:rgba(0,100,55,0.25);   color:#004d28; }
body.light-mode .phase-between { background:rgba(150,65,0,0.07);   border-color:rgba(150,65,0,0.25);   color:#6b2d00; }
body.light-mode .phase-ended   { background:rgba(140,0,25,0.06);   border-color:rgba(140,0,25,0.2);    color:#730015; }

/* All cards — warm white with subtle warm shadow */
body.light-mode .metric-card,
body.light-mode .company-card,
body.light-mode .news-card,
body.light-mode .loan-card,
body.light-mode .port-card,
body.light-mode .lb-card,
body.light-mode .rule-card {
  background: #fffef9 !important;
  border-color: #ddd5c8 !important;
  box-shadow: 0 2px 8px rgba(60,40,0,0.07) !important;
}

/* Bank panels — light mode */
body.light-mode .bkp-s .bkp-head  { background:linear-gradient(135deg,#edfff7,#d8f5ec) !important; border-color:rgba(0,130,80,0.32) !important; }
body.light-mode .bkp-m .bkp-head  { background:linear-gradient(135deg,#fffbe8,#f5f0c8) !important; border-color:rgba(140,100,0,0.32) !important; }
body.light-mode .bkp-r .bkp-head  { background:linear-gradient(135deg,#fff0f3,#fde0e6) !important; border-color:rgba(160,0,30,0.32) !important; }
body.light-mode .bkp-s .bkp-body  { background:#f0fff8 !important; border-color:rgba(0,130,80,0.18) !important; }
body.light-mode .bkp-m .bkp-body  { background:#fdfde8 !important; border-color:rgba(140,100,0,0.18) !important; }
body.light-mode .bkp-r .bkp-body  { background:#fde8ed !important; border-color:rgba(160,0,30,0.18) !important; }
body.light-mode .bkp-name  { color:#1c2b1c !important; }
body.light-mode .bkp-meta,
body.light-mode .bkp-bar-lbl { color:#5a6a5a !important; }
body.light-mode .bkp-note  { color:#8a9a8a !important; }
body.light-mode .bkp-s .bkp-rate-num { color:#006b40 !important; }
body.light-mode .bkp-m .bkp-rate-num { color:#7a5c00 !important; }
body.light-mode .bkp-r .bkp-rate-num { color:#a0001e !important; }
body.light-mode .bkp-rate-lbl  { color:#8a9a8a !important; }
body.light-mode .bkp-chev      { color:rgba(0,40,0,0.22) !important; }
body.light-mode .bkp-bar-bg    { background:rgba(0,40,0,0.07) !important; }
body.light-mode .bkp-body-lbl  { color:rgba(0,40,0,0.32) !important; }
body.light-mode .bkp-summary   { background:linear-gradient(135deg,#f0ebff,#e8e0ff) !important; border-color:rgba(100,60,200,0.25) !important; }
body.light-mode .bkp-summary-left .s-tag { color:rgba(80,40,180,0.5) !important; }
body.light-mode .bkp-summary-left .s-amt { color:#4a28a0 !important; }
body.light-mode .bkp-summary-right { color:rgba(0,0,0,0.25) !important; }

/* Text */
body.light-mode .section-hdr           { color:#1c2b1c !important; border-color:#ddd5c8 !important; }
body.light-mode .company-name,
body.light-mode .port-name,
body.light-mode .lb-name,
body.light-mode .rule-content h4       { color:#1c2b1c !important; }
body.light-mode .company-meta,
body.light-mode .company-trait,
body.light-mode .port-qty,
body.light-mode .rule-content p        { color:#5a6a5a !important; }
body.light-mode .company-bio           { color:#3a4a3a !important; background:rgba(0,80,40,0.04) !important; border-left-color:#c0d8c0 !important; }
body.light-mode .news-text             { color:#1c2b1c !important; }
body.light-mode .price-main            { color:#1c2b1c !important; }
body.light-mode .metric-card .label   { color:#5a6a5a !important; }
body.light-mode .metric-card .value,
body.light-mode .port-stat .s-val,
body.light-mode .lb-stat .ls2-val      { color:#1c2b1c !important; }
body.light-mode .metric-card .delta.delta-neutral { color:#8a9a8a !important; }
body.light-mode .lb-stat .ls2-label,
body.light-mode .port-stat .s-label    { color:#8a9a8a !important; }
body.light-mode .lb-nw                 { color:#006b40 !important; }
body.light-mode .lb-rank               { color:rgba(0,50,0,0.12) !important; }
body.light-mode .lb-rank.gold          { color:#b8860b !important; }
body.light-mode .lb-rank.silver        { color:#708090 !important; }
body.light-mode .lb-rank.bronze        { color:#8b5e3c !important; }
body.light-mode .rule-num              { color:rgba(0,100,50,0.14) !important; }

/* Nav */
body.light-mode .nav-btn { border-right-color:#ddd5c8 !important; }
body.light-mode .nav-market  { background:rgba(0,100,55,0.06);  color:rgba(0,80,40,0.42); }
body.light-mode .nav-intel   { background:rgba(140,100,0,0.06); color:rgba(110,75,0,0.42); }
body.light-mode .nav-banks   { background:rgba(80,50,180,0.05); color:rgba(60,35,160,0.42); }
body.light-mode .nav-portf   { background:rgba(20,70,190,0.05); color:rgba(15,55,170,0.42); }
body.light-mode .nav-market.nav-active  { background:rgba(0,100,55,0.12);  color:#004d28; border-color:rgba(0,100,55,0.28); }
body.light-mode .nav-intel.nav-active   { background:rgba(140,100,0,0.12); color:#6b4c00; border-color:rgba(140,100,0,0.28); }
body.light-mode .nav-banks.nav-active   { background:rgba(80,50,180,0.1);  color:#3c20a0; border-color:rgba(80,50,180,0.28); }
body.light-mode .nav-portf.nav-active   { background:rgba(20,70,190,0.1);  color:#0f3794; border-color:rgba(20,70,190,0.28); }
body.light-mode .nav-row { border-color:#ddd5c8 !important; }

/* Buttons */
body.light-mode .buy-btn  button { background:#d6f0e6 !important; border-color:#0a6640 !important; color:#004d28 !important; }
body.light-mode .sell-btn button { background:#fde6e6 !important; border-color:#b83232 !important; color:#8b1a1a !important; }
body.light-mode .max-btn  button { background:#fef5e0 !important; border-color:#a07800 !important; color:#6b5000 !important; }
body.light-mode .loan-btn button { background:#ede8ff !important; border-color:#5b3fa0 !important; color:#4a28a0 !important; }
body.light-mode .repay-btn button{ background:#fde6e6 !important; border-color:#b83232 !important; color:#8b1a1a !important; }

/* Hide Altair chart toolbar */
.vega-embed summary,
.vega-embed .vega-actions,
.vega-embed details { display:none !important; }
.vega-embed { padding:0 !important; }
body.light-mode .risk-low         { background:rgba(0,120,70,0.1);  color:#006b3c; border-color:rgba(0,120,70,0.3); }
body.light-mode .risk-medium      { background:rgba(160,120,0,0.1); color:#7a5c00; border-color:rgba(160,120,0,0.3); }
body.light-mode .risk-high        { background:rgba(160,0,30,0.08); color:#a0001e; border-color:rgba(160,0,30,0.25); }
body.light-mode .risk-medium-high { background:rgba(160,80,0,0.08); color:#8b4000; border-color:rgba(160,80,0,0.25); }

/* News labels */
body.light-mode .nl-insider { background:rgba(80,40,180,0.1); color:#4a24b0; border-color:rgba(80,40,180,0.25); }
body.light-mode .nl-rumour  { background:rgba(160,80,0,0.1);  color:#8b4000; border-color:rgba(160,80,0,0.25); }
body.light-mode .nl-event   { background:rgba(160,0,30,0.08); color:#a0001e; border-color:rgba(160,0,30,0.2); }
body.light-mode .nl-custom  { background:rgba(160,120,0,0.1); color:#7a5c00; border-color:rgba(160,120,0,0.25); }

/* Header text in light mode */
body.light-mode #mm-gear-btn { background:rgba(0,60,0,0.07) !important; border-color:rgba(0,60,0,0.2) !important; color:#1a3a1a !important; }

/* Override ALL inline white/grey text in the header area */
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:#fff"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color: #fff"] { color:#0d2e0d !important; }
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.3)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.25)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.35)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.45)"],
body.light-mode [data-testid="stMarkdownContainer"] div[style*="color:rgba(255,255,255,0.4)"],
body.light-mode [data-testid="stMarkdownContainer"] span[style*="color:rgba(255,255,255"] { color:#4a6a4a !important; }

/* Team name specifically */
body.light-mode [style*="font-size:26px"][style*="font-weight:700"] { color:#0d2e0d !important; }
body.light-mode [style*="font-size:12px"][style*="color:rgba(255,255,255,0.3)"] { color:#4a6a4a !important; }
body.light-mode [style*="font-size:12px"][style*="color:rgba(255,255,255,0.25)"] { color:#4a6a4a !important; }

/* "Trading is closed" and similar status text */
body.light-mode [style*="color:rgba(255,255,255,0.3)"] { color:#5a7a5a !important; }

/* Buy/sell panel backgrounds in light mode */
body.light-mode [style*="background:#0d0f1a"][style*="border:1px solid #1e2535"] {
  background:#f8fbf8 !important; border-color:#c2d9c2 !important;
}
body.light-mode [style*="font-size:10px"][style*="color:rgba(255,255,255,0.3)"] { color:#4a6a4a !important; }
body.light-mode [style*="font-size:11px"][style*="color:rgba(255,255,255"] { color:#4a6a4a !important; }

/* Streamlit-injected elements */
body.light-mode [data-testid="stMarkdownContainer"] p { color:#1a2e1a; }
body.light-mode div[data-testid="stHorizontalBlock"] { background:transparent !important; }
body.light-mode [data-baseweb="base-input"] { background:#fff !important; border-color:#c2d9c2 !important; color:#0d2e0d !important; }
body.light-mode [data-baseweb="base-input"] input { color:#0d2e0d !important; }
body.light-mode button[kind="secondary"] { background:#fff !important; border-color:#c2d9c2 !important; color:#0d2e0d !important; }

/* Settings panel in light mode */
body.light-mode #mm-spanel { background:#f5faf5 !important; border-color:#c2d9c2 !important; }
body.light-mode .mm-sph-title { color:#0d2e0d !important; }
body.light-mode .mm-slbl { color:#4a6a4a !important; }
body.light-mode .mm-stog { background:rgba(0,80,40,0.05) !important; border-color:#c2d9c2 !important; }
body.light-mode .mm-stog-txt { color:#1a2e1a !important; }
body.light-mode .mm-svlbl { color:#1a2e1a !important; }
body.light-mode .mm-svval { color:#4a6a4a !important; }

div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: #0a4a35 !important; border: 1px solid #00C896 !important;
    color: #00C896 !important; font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

BANKS = {
    "rbi_safe":     {"name":"RBI Trustbank",     "rate":0.07,  "cap":50000,  "css":"bank-safe",  "rate_label":"7% / round",  "note":"Regulated. Stable. Low ceiling but fair rates.",             "borrow_options":[5000,10000,25000,50000]},
    "axis_mid":     {"name":"Axis Capital",       "rate":0.12,  "cap":100000, "css":"bank-mid",   "rate_label":"12% / round", "note":"Mid-tier lender. Decent limit for growing teams.",           "borrow_options":[10000,25000,50000,75000,100000]},
    "hawala_risky": {"name":"BlackRock Ventures", "rate":0.18,  "cap":200000, "css":"bank-risky", "rate_label":"18% / round", "note":"High credit line. Aggressive interest. Not for the faint-hearted.", "borrow_options":[25000,50000,100000,150000,200000]},
}

def fmt(n): return f"₹{int(n):,}"
def risk_class(risk): return "risk-" + risk.lower().replace(" ", "-")
def news_label_class(ntype):
    return {"insider":"nl-insider","rumour":"nl-rumour","event":"nl-event"}.get(ntype,"nl-custom")
def should_show_news(n, current_phase):
    ntype = n.get("type", "custom")
    if ntype in ("event", "positive"): return current_phase in ("trading", "ended")
    if ntype == "rumour":              return current_phase in ("between", "ended")
    return True  # insider, custom — always visible

state = load_state()
tid = st.session_state.get("team_id") or st.query_params.get("tid")
if tid and not st.session_state.get("team_id"):
    st.session_state["team_id"] = tid
if tid and tid not in state["teams"]:
    st.session_state.clear(); st.rerun()
team = state["teams"].get(tid) if tid else None

# ── Ticker ────────────────────────────────────────────────────────────────────
ticker_items = ""
for cid, c in state["companies"].items():
    chg = c["price"] - c.get("prev_price", c["price"])
    chg_pct = (chg / c["prev_price"] * 100) if c.get("prev_price") else 0
    direction = "up" if chg >= 0 else "down"
    arrow = "▲" if chg >= 0 else "▼"
    ticker_items += f'<span class="ticker-item"><span class="sym">{cid.upper()[:4]}</span><span class="{direction}">{fmt(c["price"])} {arrow} {abs(chg_pct):.1f}%</span></span>'
st.markdown(f'<div class="ticker-wrap"><div class="ticker">{ticker_items * 4}</div></div>', unsafe_allow_html=True)

# ── Registration ──────────────────────────────────────────────────────────────
if not team:
    st.markdown("""
    <div class="hero">
        <div class="hero-tag">Inceptia</div>
        <h1>Market <span>Mayhem</span></h1>
        <p>The floor is open. Only the sharpest portfolio wins.</p>
    </div>""", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.form("register"):
            st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.35);letter-spacing:2px;text-transform:uppercase;font-weight:600;margin-bottom:4px">Enter the market</p>', unsafe_allow_html=True)
            team_name = st.text_input("Team name", placeholder="e.g. Delhi", label_visibility="collapsed")
            st.markdown('<p style="font-size:11px;color:rgba(255,255,255,0.2);margin:-6px 0 12px 2px">City name</p>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.35);letter-spacing:2px;text-transform:uppercase;font-weight:600;margin-bottom:4px">Participant number</p>', unsafe_allow_html=True)
            participant_num = st.number_input("Participant number", min_value=1, max_value=4, value=1, label_visibility="collapsed")
            st.markdown('<p style="font-size:11px;color:rgba(255,255,255,0.2);margin:-6px 0 12px 2px">Player 1–4 in your team</p>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Enter the Market", type="primary", use_container_width=True)
            if submitted:
                if not team_name.strip():
                    st.error("Enter a team name to continue.")
                else:
                    state = load_state()
                    new_tid = str(uuid.uuid4())[:8]
                    state["teams"][new_tid] = {
                        "name": team_name.strip(),
                        "participant_num": int(participant_num),
                        "cash": 0, "loan_balance": 0,
                        "loan_rbi_safe": 0, "loan_axis_mid": 0, "loan_hawala_risky": 0,
                        "holdings": {cid: 0 for cid in state["companies"]},
                        "avg_cost": {cid: 0 for cid in state["companies"]},
                        "price_history": {cid: [c["price"]] for cid, c in state["companies"].items()},
                    }
                    save_state(state)
                    st.session_state["team_id"] = new_tid
                    st.query_params["tid"] = new_tid
                    st.rerun()
    st.markdown('<h2 style="font-family:Space Grotesk,sans-serif;font-size:28px;font-weight:700;color:#fff;margin:48px 0 20px;letter-spacing:-0.5px">How it works</h2>', unsafe_allow_html=True)
    rules = [
        ("Register", "Enter your city name. You start with ₹0 — take a loan to begin trading."),
        ("Pick your bank", "3 banks to borrow from. Each has its own terms, limits, and interest rates. Choose wisely."),
        ("Read the market", "9 companies across sectors. Each has a personality, risk level, and backstory."),
        ("Trade in rounds", "4 rounds of live trading. Buy, sell, or short before each round closes."),
        ("Navigate the news", "News drops throughout the game. Some is real. Some is noise. You decide."),
        ("Win by net worth", "Cash + portfolio − loan balance at the end of the final round. Highest wins."),
    ]
    for i, (title, desc) in enumerate(rules, 1):
        st.markdown(f'<div class="rule-card"><div class="rule-num">{str(i).zfill(2)}</div><div class="rule-content"><h4>{title}</h4><p>{desc}</p></div></div>', unsafe_allow_html=True)
    st.stop()

# ── Main dashboard ────────────────────────────────────────────────────────────
state = load_state()
team = state["teams"].get(tid)
phase = state["phase"]

# ── Music — loaded once into session state, played via JS in parent frame ─────
_MUSIC_PHASES = {"lobby", "between", "ended"}
_music_vol   = st.session_state.get("music_volume", 50)
_should_play = phase in _MUSIC_PHASES
_vol_f       = max(0.0, min(1.0, _music_vol / 100))

# Load MP3 as base64 once per session (not stored in .py source, loaded at runtime)
if "mm_music_src" not in st.session_state:
    import base64 as _b64
    _tried = [
        Path(__file__).parent.parent / "static" / "music.mp3",
        Path(__file__).parent / "music.mp3",
        Path(__file__).parent.parent / "music.mp3",
    ]
    st.session_state["mm_music_src"] = ""
    for _mp in _tried:
        if _mp.exists():
            _enc = _b64.b64encode(_mp.read_bytes()).decode()
            st.session_state["mm_music_src"] = f"data:audio/mpeg;base64,{_enc}"
            break

_music_src = st.session_state.get("mm_music_src", "")

import streamlit.components.v1 as _stc_music
_stc_music.html(f"""<script>
(function(){{
  var P = window.parent.document;
  var shouldPlay = {'true' if _should_play else 'false'};
  var vol = {_vol_f:.3f};
  var src = {repr(_music_src)};
  var FADE_STEPS = 52, FADE_INTERVAL = 25; // 1.3s fade

  function fade(a, to, cb) {{
    clearInterval(a._ft);
    var from = a.volume, step = 0;
    a._ft = setInterval(function() {{
      step++;
      a.volume = Math.max(0, Math.min(1, from + (to - from) * (step / FADE_STEPS)));
      if (step >= FADE_STEPS) {{ a.volume = to; clearInterval(a._ft); if (cb) cb(); }}
    }}, FADE_INTERVAL);
  }}

  function getOrCreateAudio() {{
    var a = P.getElementById('mm-bg-audio');
    if (!a && src) {{
      a = P.createElement('audio');
      a.id = 'mm-bg-audio';
      a.loop = true; a.preload = 'auto'; a.style.display = 'none';
      a.src = src;
      P.body.appendChild(a);
    }}
    return a;
  }}

  function tryPlay(a) {{
    if (!a) return;
    a.volume = 0;
    a.play().then(function() {{ fade(a, vol); }}).catch(function() {{
      var handler = function() {{
        a.play().then(function() {{ fade(a, vol); }}).catch(function(){{}});
        P.removeEventListener('click', handler);
        var hint = P.getElementById('mm-play-hint');
        if (hint) hint.remove();
      }};
      P.addEventListener('click', handler);
      if (!P.getElementById('mm-play-hint')) {{
        var hint = P.createElement('div');
        hint.id = 'mm-play-hint';
        hint.textContent = '🎵 Tap anywhere to enable music';
        hint.style.cssText = 'position:fixed;bottom:14px;left:50%;transform:translateX(-50%);' +
          'background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.3);' +
          'color:#00C896;font-size:13px;font-family:Inter,sans-serif;font-weight:500;' +
          'padding:8px 18px;border-radius:99px;z-index:9997;pointer-events:none;';
        P.body.appendChild(hint);
      }}
    }});
  }}

  function sync() {{
    var a = getOrCreateAudio();
    if (!a) return;
    if (shouldPlay) {{
      if (a.paused) {{ tryPlay(a); }}
      else {{ fade(a, vol); }}
    }} else {{
      if (!a.paused) {{ fade(a, 0, function() {{ a.pause(); }}); }}
    }}
    // Keep volume in sync with slider
    a._targetVol = vol;
  }}

  setTimeout(sync, 200);
}})();
</script>""", height=0)

# ── Live micro-fluctuation engine ────────────────────────────────────────────
# Real prices only change at round start (host). This adds visual micro-ticks
# every ~3s during trading so charts show live movement. Stored in session state
# only — never written to game_state.json, so it doesn't affect real prices.
import random as _random

MICRO_VOL = {  # per-tick max % move (purely visual) — kept conservative
    "zora":0.003, "streamvx":0.010, "freshco":0.002, "voltex":0.008,
    "mediq":0.009, "skylink":0.012, "swifthaul":0.005, "crownmart":0.009, "shieldgen":0.003,
}

if "micro_prices" not in st.session_state or st.session_state.get("micro_phase") != phase:
    # Initialise from real prices
    st.session_state["micro_prices"] = {cid: c["price"] for cid, c in state["companies"].items()}
    st.session_state["micro_phase"] = phase
    st.session_state["micro_tick"] = 0

# Sync if real price drifts far from micro price (e.g. after round start)
for cid, c in state["companies"].items():
    mp = st.session_state["micro_prices"].get(cid, c["price"])
    if abs(mp - c["price"]) / c["price"] > 0.08:  # >8% drift → resync
        st.session_state["micro_prices"][cid] = c["price"]

if phase == "trading":
    st.session_state["micro_tick"] = st.session_state.get("micro_tick", 0) + 1
    tick = st.session_state["micro_tick"]
    if tick % 3 == 0:  # fluctuate every 3 refreshes (~3s)
        for cid in state["companies"]:
            mp = st.session_state["micro_prices"][cid]
            vol = MICRO_VOL.get(cid, 0.008)
            direction = 1 if _random.random() > 0.5 else -1
            change = direction * _random.uniform(vol * 0.3, vol)
            st.session_state["micro_prices"][cid] = max(10, round(mp * (1 + change), 1))

# Build display_hist: real price history lives in game_state; micro ticks in session only
if "price_history" not in team:
    team["price_history"] = {cid: [c["price"]] for cid, c in state["companies"].items()}

# Accumulate micro ticks in session state only — never written to disk
if "micro_hist" not in st.session_state or st.session_state.get("micro_hist_phase") != phase:
    st.session_state["micro_hist"] = {cid: [] for cid in state["companies"]}
    st.session_state["micro_hist_phase"] = phase

if phase == "trading":
    for cid in state["companies"]:
        micro_p = st.session_state["micro_prices"].get(cid, state["companies"][cid]["price"])
        buf = st.session_state["micro_hist"].get(cid, [])
        buf.append(micro_p)
        if len(buf) > 60: buf = buf[-60:]
        st.session_state["micro_hist"][cid] = buf

# FIX 4: Game over screen — show immediately after ticker, no banner, no progress
if phase == "ended":
    port_val = sum(team["holdings"].get(cid,0) * state["companies"][cid]["price"] for cid in state["companies"])
    loan_balance = team.get("loan_balance", 0)
    net_worth = team["cash"] + port_val - loan_balance
    st.markdown(f"""
    <div class="gameover-screen">
      <h1>Thank <span>You</span></h1>
      <p>Results will be announced shortly by your event coordinator.</p>
      <p style="margin-top:24px;font-size:14px;color:rgba(255,255,255,0.2)">Your final net worth: <strong style="color:#00C896">{fmt(net_worth)}</strong></p>
    </div>""", unsafe_allow_html=True)
    st.stop()  # Don't render anything else after game over

# ── Header + Settings (non-ended phases only) ────────────────────────────────
participant_tag = f' &nbsp;<span style="font-size:13px;font-weight:500;color:rgba(255,255,255,0.35)">· P{team.get("participant_num","")}</span>' if team.get("participant_num") else ""

# Settings state — read from query params so JS can write them without a rerun
_qp = st.query_params
if "music_volume" not in st.session_state:
    st.session_state["music_volume"] = int(_qp.get("vol", 50))
if "light_mode" not in st.session_state:
    st.session_state["light_mode"] = _qp.get("theme", "dark") == "light"
if "chart_type" not in st.session_state:
    st.session_state["chart_type"] = _qp.get("chart", "line")
if "intel_popup" not in st.session_state:
    st.session_state["intel_popup"] = _qp.get("intel_popup", "off") == "on"

# Handle query param updates from the JS settings panel
_qp_vol   = _qp.get("vol")
_qp_theme = _qp.get("theme")
_qp_chart = _qp.get("chart")
_qp_intel = _qp.get("intel_popup")
_qp_bank  = _qp.get("bank_open")
if _qp_vol is not None:
    try:
        st.session_state["music_volume"] = int(_qp_vol)
    except ValueError:
        pass
if _qp_theme is not None:
    st.session_state["light_mode"] = (_qp_theme == "light")
if _qp_chart is not None and _qp_chart in ("line", "candle", "bar"):
    st.session_state["chart_type"] = _qp_chart
if _qp_intel is not None:
    st.session_state["intel_popup"] = (_qp_intel == "on")
if _qp_bank is not None:
    if _qp_bank == "" or _qp_bank == st.session_state.get("bank_open"):
        st.session_state["bank_open"] = None
    else:
        st.session_state["bank_open"] = _qp_bank
    try:
        del st.query_params["bank_open"]
    except Exception:
        pass

_vol   = st.session_state["music_volume"]
_light = st.session_state["light_mode"]
_chart = st.session_state.get("chart_type", "line")
_intel_popup = st.session_state.get("intel_popup", False)

# Header (plain HTML — renders fine, no scripts needed here)
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin:14px 0 20px;flex-wrap:wrap;gap:10px">
  <div>
    <div style="font-family:Space Grotesk,sans-serif;font-size:26px;font-weight:700;color:#fff;letter-spacing:-0.5px">{team['name']}{participant_tag}</div>
    <div style="font-size:12px;color:rgba(255,255,255,0.3);margin-top:2px">Market Mayhem · Inceptia</div>
  </div>
  <div style="display:flex;align-items:center;gap:14px">
    <div style="font-size:12px;color:rgba(255,255,255,0.25);font-family:Space Grotesk,monospace">Round {state['round']} / 4</div>
    <div id="mm-gear-btn"
         style="width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,0.05);
                border:1px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.55);
                font-size:18px;cursor:pointer;display:flex;align-items:center;
                justify-content:center;user-select:none;transition:background 0.15s,color 0.15s"
         title="Settings">⚙</div>
  </div>
</div>
""", unsafe_allow_html=True)



# Settings panel — inject CSS + DOM + JS all into the PARENT document from the iframe
import streamlit.components.v1 as _stc
_stc.html(f"""
<!DOCTYPE html><html><body style="margin:0;padding:0;background:transparent">
<script>
(function(){{
  var P = window.parent.document;

  // ── Inject CSS into parent <head> once ──────────────────────────────────
  if (!P.getElementById('mm-settings-css')) {{
    var s = P.createElement('style');
    s.id = 'mm-settings-css';
    s.textContent = `
      #mm-soverlay {{
        display:none !important;position:fixed;inset:0;z-index:9998;
        background:rgba(0,0,0,0.45);
      }}
      #mm-soverlay.sp-open {{ display:block !important; }}
      #mm-spanel {{
        position:fixed;top:0;right:0;width:300px;height:100vh;
        background:#0d0f1a;border-left:1px solid #1e2535;
        z-index:9999;padding:28px 22px;overflow-y:auto;box-sizing:border-box;
        transform:translateX(100%);transition:transform 0.28s cubic-bezier(0.16,1,0.3,1);
      }}
      #mm-spanel.sp-open {{ transform:translateX(0); }}
      #mm-soverlay.sp-open {{ display:block; }}
      .mm-sph {{ display:flex;justify-content:space-between;align-items:center;margin-bottom:28px; }}
      .mm-sph-title {{ font-family:Space Grotesk,sans-serif;font-size:18px;font-weight:700;color:#fff;letter-spacing:-0.3px; }}
      .mm-sph-x {{ width:30px;height:30px;border-radius:50%;border:1px solid rgba(255,255,255,0.12);
                   background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.5);font-size:15px;
                   cursor:pointer;display:flex;align-items:center;justify-content:center;
                   transition:background .15s,color .15s,border-color .15s; }}
      .mm-sph-x:hover {{ background:rgba(255,77,106,0.15);color:#FF4D6A;border-color:rgba(255,77,106,0.3); }}
      .mm-ssec {{ margin-bottom:22px;padding-bottom:22px;border-bottom:1px solid rgba(255,255,255,0.05); }}
      .mm-slbl {{ font-size:11px;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:1.5px;font-weight:600;margin-bottom:12px; }}
      .mm-theme-row {{ display:flex;gap:10px; }}
      .mm-tbtn {{ flex:1;padding:14px 8px;border-radius:12px;border:1.5px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.04);cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:8px;transition:all 0.18s;user-select:none; }}
      .mm-tbtn:hover {{ background:rgba(255,255,255,0.08); }}
      .mm-tbtn.t-active-light {{ border-color:#ffd93d;background:rgba(255,211,61,0.1); }}
      .mm-tbtn.t-active-dark  {{ border-color:#a78bfa;background:rgba(167,139,250,0.1); }}
      .mm-tbtn.t-active-chart {{ border-color:#00C896;background:rgba(0,200,150,0.1); }}
      .mm-tbtn svg {{ width:28px;height:28px; }}
      .mm-tbtn span {{ font-size:12px;font-weight:600;color:rgba(255,255,255,0.45);letter-spacing:0.3px; }}
      .mm-tbtn.t-active-light span {{ color:#ffd93d; }}
      .mm-tbtn.t-active-dark  span {{ color:#a78bfa; }}
      .mm-tbtn.t-active-chart span {{ color:#00C896; }}
      .mm-svlbl {{ font-size:14px;color:rgba(255,255,255,0.8);font-weight:500;margin-bottom:12px; }}
      .mm-svrow {{ display:flex;align-items:center;gap:10px; }}
      .mm-svrow input[type=range] {{
        flex:1;-webkit-appearance:none;height:4px;border-radius:2px;
        background:rgba(255,255,255,0.12);outline:none;cursor:pointer;
      }}
      .mm-svrow input[type=range]::-webkit-slider-thumb {{
        -webkit-appearance:none;width:18px;height:18px;border-radius:50%;
        background:#00C896;cursor:pointer;box-shadow:0 0 0 3px rgba(0,200,150,0.2);
      }}
      .mm-svval {{ font-size:13px;color:rgba(255,255,255,0.4);min-width:28px;text-align:right;font-family:monospace; }}
      .mm-tog-row {{ display:flex;align-items:center;justify-content:space-between;gap:10px; }}
      .mm-tog-desc {{ font-size:13px;color:rgba(255,255,255,0.6);flex:1;line-height:1.4; }}
      .mm-tog {{ position:relative;width:44px;height:24px;flex-shrink:0; }}
      .mm-tog input {{ opacity:0;width:0;height:0; }}
      .mm-tog-sl {{ position:absolute;cursor:pointer;inset:0;background:rgba(255,255,255,0.1);border-radius:99px;transition:background 0.2s; }}
      .mm-tog-sl:before {{ content:"";position:absolute;height:18px;width:18px;left:3px;bottom:3px;background:rgba(255,255,255,0.4);border-radius:50%;transition:transform 0.2s,background 0.2s; }}
      .mm-tog input:checked + .mm-tog-sl {{ background:rgba(255,77,106,0.35); }}
      .mm-tog input:checked + .mm-tog-sl:before {{ transform:translateX(20px);background:#FF4D6A; }}
    `;
    P.head.appendChild(s);
  }}

  // ── Build overlay + panel DOM once ──────────────────────────────────────
  // ── Persistent settings state — survives iframe refreshes ──────────────────
  // Store on window.MM so values aren't re-declared to Python defaults every 3s
  if (!window.MM) window.MM = {{}};
  var MM = window.MM;

  // Only accept Python values if JS hasn't diverged (i.e. user hasn't changed them)
  // This prevents the 3s refresh from snapping settings back mid-interaction
  if (!MM._init) {{
    MM.isLight    = {'true' if _light else 'false'};
    MM.vol        = {_vol};
    MM.chartType  = '{_chart}';
    MM.intelPopup = {'true' if _intel_popup else 'false'};
    MM._init = true;
  }} else {{
    // Sync only if Python caught up to what JS set (avoids flicker)
    var pyLight = {'true' if _light else 'false'};
    var pyChart = '{_chart}';
    var pyIntel = {'true' if _intel_popup else 'false'};
    var pyVol   = {_vol};
    // Only override JS value if Python agrees with it (confirming the param was read)
    if (pyLight === MM.isLight) MM.isLight = pyLight;
    if (pyChart === MM.chartType) MM.chartType = pyChart;
    if (pyIntel === MM.intelPopup) MM.intelPopup = pyIntel;
    if (!MM._sliderDragging) MM.vol = pyVol;
  }}

  var SVG_SUN  = '<svg viewBox="0 0 24 24" fill="none" stroke="#ffd93d" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  var SVG_MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  var SVG_LINE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3,17 8,10 13,14 21,5"/></svg>';
  var SVG_CANDLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="7" y="8" width="4" height="10" rx="1"/><line x1="9" y1="4" x2="9" y2="8"/><line x1="9" y1="18" x2="9" y2="22"/><rect x="13" y="6" width="4" height="8" rx="1"/><line x1="15" y1="2" x2="15" y2="6"/><line x1="15" y1="14" x2="15" y2="20"/></svg>';
  var SVG_BAR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="12" width="4" height="9" rx="1"/><rect x="10" y="6" width="4" height="15" rx="1"/><rect x="17" y="9" width="4" height="12" rx="1"/></svg>';

  if (!P.getElementById('mm-spanel')) {{
    var ov = P.createElement('div'); ov.id = 'mm-soverlay';
    var pn = P.createElement('div'); pn.id = 'mm-spanel';
    pn.innerHTML =
      '<div class="mm-sph">' +
        '<span class="mm-sph-title">Settings</span>' +
        '<div class="mm-sph-x" id="mm-sclose">&#x2715;</div>' +
      '</div>' +
      '<div class="mm-ssec">' +
        '<div class="mm-slbl">Appearance</div>' +
        '<div class="mm-theme-row">' +
          '<div class="mm-tbtn" id="mm-btn-light">' + SVG_SUN + '<span>Light</span></div>' +
          '<div class="mm-tbtn" id="mm-btn-dark">'  + SVG_MOON + '<span>Dark</span></div>' +
        '</div>' +
      '</div>' +
      '<div class="mm-ssec">' +
        '<div class="mm-slbl">Chart Style</div>' +
        '<div class="mm-theme-row">' +
          '<div class="mm-tbtn" id="mm-chart-line">'   + SVG_LINE   + '<span>Line</span></div>' +
          '<div class="mm-tbtn" id="mm-chart-candle">' + SVG_CANDLE + '<span>Candle</span></div>' +
          '<div class="mm-tbtn" id="mm-chart-bar">'    + SVG_BAR    + '<span>Bar</span></div>' +
        '</div>' +
      '</div>' +
      '<div class="mm-ssec">' +
        '<div class="mm-slbl">Notifications</div>' +
        '<div class="mm-tog-row">' +
          '<span class="mm-tog-desc">Red popup when new Intel drops</span>' +
          '<label class="mm-tog"><input type="checkbox" id="mm-intel-tog"><span class="mm-tog-sl"></span></label>' +
        '</div>' +
      '</div>' +
      '<div class="mm-ssec" style="border-bottom:none">' +
        '<div class="mm-slbl">Music Volume</div>' +
        '<div class="mm-svlbl">Background music <span style="color:rgba(255,255,255,0.35);font-size:12px">(lobby &amp; breaks)</span></div>' +
        '<div class="mm-svrow">' +
          '<span style="font-size:15px">&#x1F508;</span>' +
          '<input type="range" id="mm-vol-sl" min="0" max="100">' +
          '<span style="font-size:15px">&#x1F50A;</span>' +
          '<span class="mm-svval" id="mm-vval"></span>' +
        '</div>' +
      '</div>';
    P.body.appendChild(ov);
    P.body.appendChild(pn);
  }}

  // ── Debounced rewire — prevent double-fire on rapid clicks ───────────────────
  clearTimeout(MM._rewireTimer);
  MM._rewireTimer = setTimeout(function() {{
    var pn  = P.getElementById('mm-spanel');
    var ov  = P.getElementById('mm-soverlay');
    if (!pn || !ov) return;

    // Replace overlay once to drop stale listeners — but preserve open state
    var wasOpen = ov.classList.contains('sp-open') || pn.classList.contains('sp-open');
    var ov2 = P.createElement('div');
    ov2.id = 'mm-soverlay';
    if (wasOpen) {{ ov2.classList.add('sp-open'); pn.classList.add('sp-open'); }}
    ov.parentNode.replaceChild(ov2, ov);

    function openPanel()  {{ pn.classList.add('sp-open'); ov2.classList.add('sp-open'); }}
    function closePanel() {{ pn.classList.remove('sp-open'); ov2.classList.remove('sp-open'); }}
    ov2.addEventListener('click', closePanel);

    function rewireEl(id, fn) {{
      var el = P.getElementById(id);
      if (!el) return null;
      var el2 = el.cloneNode(true);
      el.parentNode.replaceChild(el2, el);
      if (fn) fn(el2);
      return el2;
    }}

    rewireEl('mm-sclose', function(el) {{ el.addEventListener('click', closePanel); }});

    var g = P.getElementById('mm-gear-btn');
    if (g) g.onclick = openPanel;
    else setTimeout(function() {{ var g2=P.getElementById('mm-gear-btn'); if(g2) g2.onclick=openPanel; }}, 200);

    // ── Theme ───────────────────────────────────────────────────────────────
    function applyTheme(light) {{
      MM.isLight = light;
      var bl = P.getElementById('mm-btn-light');
      var bd = P.getElementById('mm-btn-dark');
      if (bl) bl.className = 'mm-tbtn' + (light  ? ' t-active-light' : '');
      if (bd) bd.className = 'mm-tbtn' + (!light ? ' t-active-dark'  : '');
      if (light) P.body.classList.add('light-mode');
      else       P.body.classList.remove('light-mode');
      var url = new URL(window.parent.location.href);
      url.searchParams.set('theme', light ? 'light' : 'dark');
      window.parent.location.href = url.toString();
    }}
    // Apply current state immediately (no flicker)
    applyTheme(MM.isLight);
    rewireEl('mm-btn-light', function(el) {{
      el.className = 'mm-tbtn' + (MM.isLight ? ' t-active-light' : '');
      el.addEventListener('click', function() {{ applyTheme(true); }});
    }});
    rewireEl('mm-btn-dark', function(el) {{
      el.className = 'mm-tbtn' + (!MM.isLight ? ' t-active-dark' : '');
      el.addEventListener('click', function() {{ applyTheme(false); }});
    }});

    // ── Chart style ─────────────────────────────────────────────────────────
    function applyChart(type) {{
      MM.chartType = type;
      ['line','candle','bar'].forEach(function(t) {{
        var el = P.getElementById('mm-chart-' + t);
        if (el) el.className = 'mm-tbtn' + (t === type ? ' t-active-chart' : '');
      }});
      // Navigate to same page with ?chart=type — Streamlit reads this on rerun
      var url = new URL(window.parent.location.href);
      url.searchParams.set('chart', type);
      window.parent.location.href = url.toString();
    }}
    applyChart(MM.chartType);
    ['line','candle','bar'].forEach(function(t) {{
      rewireEl('mm-chart-' + t, function(el) {{
        el.className = 'mm-tbtn' + (t === MM.chartType ? ' t-active-chart' : '');
        el.addEventListener('click', function() {{ applyChart(t); }});
      }});
    }});

    // ── Intel popup ─────────────────────────────────────────────────────────
    rewireEl('mm-intel-tog', function(el) {{
      el.checked = MM.intelPopup;
      el.addEventListener('change', function() {{
        MM.intelPopup = this.checked;
        var url = new URL(window.parent.location.href);
        url.searchParams.set('intel_popup', MM.intelPopup ? 'on' : 'off');
        window.parent.history.replaceState({{}}, '', url.toString());
        var popup = P.getElementById('mm-intel-popup');
        if (popup) popup.style.display = MM.intelPopup ? 'flex' : 'none';
      }});
    }});

    // ── Volume — protect mid-drag from rewire reset ──────────────────────
    rewireEl('mm-vol-sl', function(el) {{
      el.value = MM.vol;
      var vv = P.getElementById('mm-vval');
      if (vv) vv.textContent = MM.vol;
      el.addEventListener('mousedown', function() {{ MM._sliderDragging = true; }});
      el.addEventListener('touchstart', function() {{ MM._sliderDragging = true; }});
      el.addEventListener('mouseup',   function() {{ MM._sliderDragging = false; }});
      el.addEventListener('touchend',  function() {{ MM._sliderDragging = false; }});
      el.addEventListener('input', function() {{
        MM.vol = parseInt(this.value);
        var vv2 = P.getElementById('mm-vval');
        if (vv2) vv2.textContent = MM.vol;
        var audio = P.getElementById('mm-bg-audio');
        if (audio) audio.volume = MM.vol / 100;
        var url = new URL(window.parent.location.href);
        url.searchParams.set('vol', MM.vol);
        window.parent.history.replaceState({{}}, '', url.toString());
      }});
    }});
  }}, 80); // 80ms debounce — fast enough, prevents double-fire on rapid clicks

  if (MM.isLight) P.body.classList.add('light-mode');
}})();
</script>
</body></html>
""", height=0)

phase_map = {
    "lobby":   ("phase-lobby",   "WAITING FOR HOST",               "The trading floor opens shortly."),
    "trading": ("phase-trading", f"ROUND {state['round']} — LIVE", "Trading is open. Buy and sell before the round ends."),
    "between": ("phase-between", f"ROUND {state['round']} CLOSED", "Round ended. Host will start the next round shortly."),
}
p_class, p_title, p_sub = phase_map.get(phase, ("phase-lobby","—","—"))
st.markdown(f'<div class="phase-banner {p_class}"><strong>{p_title}</strong> &nbsp;—&nbsp; {p_sub}</div>', unsafe_allow_html=True)

# Python-driven countdown — reliable, same approach as host
if phase == "trading" and state.get("round_end_time"):
    remaining = max(0, state["round_end_time"] - time.time())
    if remaining > 0:
        mins, secs = divmod(int(remaining), 60)
        time_label = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        progress_val = max(0.0, min(1.0, 1.0 - (remaining / ROUND_DURATION)))
        bar_color = "#00C896" if progress_val < 0.5 else ("#ffd93d" if progress_val < 0.75 else "#FF4D6A")
        st.markdown(f'<p style="font-size:30px;color:rgba(255,255,255,0.7);margin-bottom:6px">⏱ Round closes in <strong style="color:#fff">{time_label}</strong></p>', unsafe_allow_html=True)
        st.markdown(f"""<style>div[data-testid="stProgress"]>div>div>div>div{{background:{bar_color}!important}}div[data-testid="stProgress"]>div>div{{background:rgba(255,255,255,0.08)!important}}</style>""", unsafe_allow_html=True)
        st.progress(progress_val)
    else:
        st.markdown('<p style="font-size:20px;color:#FF4D6A;margin-bottom:6px">⏰ Round time is up — waiting for host to close.</p>', unsafe_allow_html=True)
elif phase == "between" and state.get("break_end_time"):
    remaining = max(0, state["break_end_time"] - time.time())
    if remaining > 0:
        mins, secs = divmod(int(remaining), 60)
        time_label = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        progress_val = max(0.0, min(1.0, 1.0 - (remaining / BREAK_DURATION)))
        st.markdown(f'<p style="font-size:30px;color:rgba(255,255,255,0.7);margin-bottom:6px">☕ Break ends in <strong style="color:#fff">{time_label}</strong></p>', unsafe_allow_html=True)
        st.markdown(f"""<style>div[data-testid="stProgress"]>div>div>div>div{{background:#a78bfa!important}}div[data-testid="stProgress"]>div>div{{background:rgba(255,255,255,0.08)!important}}</style>""", unsafe_allow_html=True)
        st.progress(progress_val)

# Metrics
port_val = sum(team["holdings"].get(cid,0) * state["companies"][cid]["price"] for cid in state["companies"])
loan_balance = team.get("loan_balance", 0)
net_worth = team["cash"] + port_val - loan_balance
st.markdown(f"""
<div class="metric-row" style="grid-template-columns:repeat(4,1fr)">
  <div class="metric-card"><div class="label">Cash</div><div class="value" style="color:#00C896">{fmt(team['cash'])}</div><div class="delta" style="color:rgba(0,200,150,0.45)">Available</div></div>
  <div class="metric-card"><div class="label">Portfolio</div><div class="value" style="color:#ffd93d">{fmt(port_val)}</div><div class="delta" style="color:rgba(255,211,61,0.45)">Holdings value</div></div>
  <div class="metric-card"><div class="label">Loan Balance</div><div class="value" style="color:#a78bfa">{fmt(loan_balance)}</div><div class="delta" style="color:rgba(167,139,250,0.4)">Outstanding debt</div></div>
  <div class="metric-card"><div class="label">Net Worth</div><div class="value" style="color:#4f8ef7">{fmt(net_worth)}</div><div class="delta" style="color:rgba(79,142,247,0.45)">Cash + portfolio − loan</div></div>
</div>""", unsafe_allow_html=True)

can_trade = phase == "trading"
can_bank  = phase in ("trading", "between")

all_news = state.get("news", [])
visible_news = [n for n in all_news if should_show_news(n, phase)]
new_count = len(visible_news)
if "intel_seen_count" not in st.session_state:
    st.session_state["intel_seen_count"] = 0
unseen_intel = max(0, new_count - st.session_state["intel_seen_count"])

if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "market"
if st.session_state["active_panel"] == "news":
    st.session_state["intel_seen_count"] = new_count

# Nav tabs — pure Streamlit buttons styled to match metric tile colours
active = st.session_state["active_panel"]

nav_cols = st.columns(4)
panel_keys  = ["market",  "news",   "loans",  "portfolio"]
panel_labels = ["Market", "Intel", "Banks", "Portfolio"]
for i, (p, lbl) in enumerate(zip(panel_keys, panel_labels)):
    with nav_cols[i]:
        is_active = active == p
        color_map = {"market":"#00C896","news":"#ffd93d","loans":"#a78bfa","portfolio":"#4f8ef7"}
        bg_map    = {"market":"rgba(0,200,150","news":"rgba(255,211,61","loans":"rgba(167,139,250","portfolio":"rgba(79,142,247"}
        col = color_map[p]; bg = bg_map[p]
        opacity = "0.15" if is_active else "0.07"
        border_opacity = "0.5" if is_active else "0.2"
        st.markdown(f"""<style>
        div[data-testid="stHorizontalBlock"] > div:nth-child({i+1}) button {{
            background:{bg},{opacity}) !important;
            border:1px solid {bg},{border_opacity}) !important;
            color:{''+col+'' if is_active else bg+',0.6)'} !important;
            font-weight:{'700' if is_active else '500'} !important;
            font-size:13px !important;
            letter-spacing:0.5px !important;
            text-transform:uppercase !important;
            height:48px !important;
            position:relative !important;
        }}
        </style>""", unsafe_allow_html=True)
        if st.button(lbl, key=f"nav_{p}", use_container_width=True):
            st.session_state["active_panel"] = p
            if p == "news": st.session_state["intel_seen_count"] = new_count
            st.rerun()
        # Corner badge for Intel — overlaid via negative margin trick
        if p == "news" and unseen_intel > 0:
            st.markdown(f"""
            <div style="position:relative;height:0;overflow:visible">
              <div style="position:absolute;top:-46px;right:8px;
                background:#FF4D6A;color:#fff;
                font-size:11px;font-weight:800;font-family:Inter,sans-serif;
                min-width:20px;height:20px;border-radius:99px;
                display:flex;align-items:center;justify-content:center;
                padding:0 5px;
                box-shadow:0 0 0 2px #0d0f1a;
                pointer-events:none;z-index:999">
                {unseen_intel}
              </div>
            </div>""", unsafe_allow_html=True)

active = st.session_state["active_panel"]
if active == "news": st.session_state["intel_seen_count"] = new_count
st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

# ── Floating Intel popup (WhatsApp-style) ─────────────────────────────────────
if _intel_popup and unseen_intel > 0 and active != "news":
    st.markdown(f"""
    <div id="mm-intel-popup" style="
      position:fixed;bottom:28px;right:24px;z-index:9990;
      display:flex;align-items:center;gap:12px;
      background:#1a0a0e;border:1.5px solid rgba(255,77,106,0.5);
      border-radius:16px;padding:12px 18px;
      box-shadow:0 4px 24px rgba(255,77,106,0.25);
      font-family:Inter,sans-serif;cursor:pointer;
      animation:mm-pop-in 0.3s cubic-bezier(0.16,1,0.3,1)">
      <div style="background:#FF4D6A;color:#fff;font-size:13px;font-weight:800;
                  min-width:26px;height:26px;border-radius:99px;display:flex;
                  align-items:center;justify-content:center;padding:0 6px;flex-shrink:0">
        {unseen_intel}
      </div>
      <div>
        <div style="font-size:13px;font-weight:700;color:#fff">New Intel</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.45)">Tap to view market intelligence</div>
      </div>
    </div>
    <style>
    @keyframes mm-pop-in {{
      from {{ transform:translateY(20px);opacity:0; }}
      to   {{ transform:translateY(0);opacity:1; }}
    }}
    </style>""", unsafe_allow_html=True)

# ══ PANEL: MARKET ═════════════════════════════════════════════════════════════
if active == "market":
    if phase == "between":
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0d0f1a 0%,#0a1220 100%);border:1px solid rgba(56,189,248,0.2);border-radius:16px;padding:40px 48px;text-align:center;margin:0 0 24px">
          <h2 style="font-family:Space Grotesk,sans-serif;font-size:32px;font-weight:700;color:#fff;letter-spacing:-1px;margin-bottom:10px">Round Over</h2>
          <p style="font-size:15px;color:rgba(255,255,255,0.4)">Check Banks to repay loans · Check Intel for new rumours · Next round starts soon</p>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-hdr">Live Market</div>', unsafe_allow_html=True)
    if not can_trade:
        st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.3);margin-bottom:16px">Trading is closed. Study the companies below.</p>', unsafe_allow_html=True)

    for cid, c in state["companies"].items():
        price = c["price"]; prev = c.get("prev_price", price)
        chg = price - prev; chg_pct = (chg/prev*100) if prev else 0
        chg_class = "delta-up" if chg >= 0 else "delta-down"
        arrow = "▲" if chg >= 0 else "▼"
        held = team["holdings"].get(cid, 0)
        rclass = risk_class(c.get("risk","Medium"))
        br = "border-radius:12px;" if not can_trade else "border-radius:12px 12px 0 0;"
        left_col, right_col = st.columns([1.1, 1])
        with left_col:
            # Header + bio unified in left col
            st.markdown(f"""
            <div class="company-card" style="{br}margin-bottom:0">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:10px">
                <div>
                  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px">
                    <span class="company-name">{c['name']}</span>
                    <span class="risk-badge {rclass}">{c.get('risk','Medium')} risk</span>
                  </div>
                  <div class="company-meta">{c['sector']} · {c.get('age','—')} · {c.get('size','—')}</div>
                  <div class="company-trait">{c.get('trait','')}</div>
                </div>
                <div style="text-align:right">
                  <div class="price-main">{fmt(price)}</div>
                  <div class="price-chg {chg_class}">{arrow} {abs(chg):.0f} ({abs(chg_pct):.1f}%)</div>
                  <div style="font-size:11px;color:rgba(255,255,255,0.25);margin-top:4px">{held} held</div>
                </div>
              </div>
              <div class="company-bio" style="margin-bottom:0">{c.get('bio','')}</div>
            </div>""", unsafe_allow_html=True)
            if can_trade:
                max_buy  = max(1, int(team["cash"] // price)) if team["cash"] >= price else 1
                max_sell = max(1, held)
                bmax_key = f"_bmax_{cid}"; smax_key = f"_smax_{cid}"
                buy_qty_key = f"buy_qty_{cid}"; sell_qty_key = f"sell_qty_{cid}"
                # ── MAX flag: apply BEFORE widgets render so no re-entrancy ──
                if st.session_state.pop(bmax_key, False):
                    st.session_state[buy_qty_key]  = max(1, max_buy)
                if st.session_state.pop(smax_key, False):
                    st.session_state[sell_qty_key] = max(1, max_sell)
                st.markdown('<div style="background:#0d0f1a;border:1px solid #1e2535;border-top:none;border-radius:0 0 12px 12px;padding:14px 24px 18px">', unsafe_allow_html=True)
                buy_col, sell_col = st.columns(2)
                with buy_col:
                    st.markdown('<div style="font-size:10px;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Buy</div>', unsafe_allow_html=True)
                    b1,b2,b3 = st.columns([2,1,1])
                    with b1:
                        buy_qty = st.number_input("bq", min_value=1, max_value=max(1,max_buy), value=min(st.session_state.get(buy_qty_key,1),max(1,max_buy)), key=buy_qty_key, label_visibility="collapsed")
                    with b2:
                        st.markdown('<div class="max-btn">', unsafe_allow_html=True)
                        if st.button("MAX", key=f"bmax_btn_{cid}", use_container_width=True):
                            st.session_state[bmax_key] = True; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with b3:
                        st.markdown('<div class="buy-btn">', unsafe_allow_html=True)
                        if st.button("Buy", key=f"buy_{cid}", use_container_width=True):
                            cost = buy_qty * price; state = load_state(); team = state["teams"][tid]
                            if cost > team["cash"]: st.error("Not enough cash.")
                            else:
                                ph = team["holdings"].get(cid,0); pc = team["avg_cost"].get(cid,0)*ph
                                team["holdings"][cid] = ph+buy_qty
                                team["avg_cost"][cid] = (pc+cost)/team["holdings"][cid]
                                team["cash"] -= cost; state["teams"][tid] = team; save_state(state)
                                st.success(f"Bought {buy_qty} × {c['name']} @ {fmt(price)}"); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:11px;color:rgba(255,255,255,0.25);margin-top:4px">Cost: {fmt(buy_qty*price)}</div>', unsafe_allow_html=True)
                with sell_col:
                    st.markdown('<div style="font-size:10px;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Sell</div>', unsafe_allow_html=True)
                    s1,s2,s3 = st.columns([2,1,1])
                    with s1:
                        sell_qty = st.number_input("sq", min_value=1, max_value=max(1,max_sell), value=min(st.session_state.get(sell_qty_key,1),max(1,max_sell)), key=sell_qty_key, label_visibility="collapsed", disabled=(held==0))
                    with s2:
                        st.markdown('<div class="max-btn">', unsafe_allow_html=True)
                        if st.button("MAX", key=f"smax_btn_{cid}", use_container_width=True, disabled=(held==0)):
                            st.session_state[smax_key] = True; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with s3:
                        st.markdown('<div class="sell-btn">', unsafe_allow_html=True)
                        if st.button("Sell", key=f"sell_{cid}", use_container_width=True, disabled=(held==0)):
                            state = load_state(); team = state["teams"][tid]
                            fresh_price = state["companies"][cid]["price"]
                            hn = team["holdings"].get(cid,0); sq = min(sell_qty,hn)
                            team["holdings"][cid] = hn-sq; team["cash"] += sq*fresh_price
                            if team["holdings"][cid]==0: team["avg_cost"][cid]=0
                            state["teams"][tid] = team; save_state(state)
                            st.success(f"Sold {sq} × {c['name']} @ {fmt(fresh_price)}"); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:11px;color:rgba(255,255,255,0.25);margin-top:4px">{"Value: "+fmt(sell_qty*price) if held>0 else "None held"}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background:#0d0f1a;border:1px solid #1e2535;border-top:none;border-radius:0 0 12px 12px;height:4px"></div>', unsafe_allow_html=True)
        with right_col:
            real_hist = team.get("price_history", {}).get(cid, [])
            micro_buf = st.session_state.get("micro_hist", {}).get(cid, [])
            if phase == "trading":
                display_hist = (real_hist + micro_buf) if real_hist else micro_buf or [price]
            else:
                display_hist = real_hist if real_hist else [c.get("prev_price", price), price]
            if len(display_hist) == 1:
                display_hist = [display_hist[0], display_hist[0]]
            chart_color = "#00C896" if price >= c.get("prev_price", price) else "#FF4D6A"
            mn = min(display_hist); mx = max(display_hist)
            pad = max((mx - mn) * 0.6, price * 0.03)
            df = pd.DataFrame({"i": range(len(display_hist)), "Price": display_hist})
            _is_light = st.session_state.get("light_mode", False)
            _label_col = "rgba(30,60,30,0.7)"  if _is_light else "rgba(255,255,255,0.35)"
            _grid_col  = "rgba(0,80,0,0.08)"   if _is_light else "rgba(255,255,255,0.05)"
            _tick_col  = "rgba(30,60,30,0.5)"  if _is_light else "rgba(255,255,255,0.2)"
            _chart_type = st.session_state.get("chart_type", "line")
            _y = alt.Y("Price:Q", scale=alt.Scale(domain=[mn-pad, mx+pad]),
                       axis=alt.Axis(grid=True, gridColor=_grid_col, labelColor=_label_col,
                                     tickColor=_tick_col, domainColor=_tick_col,
                                     tickCount=4, format=",.0f",
                                     labelFont="Space Grotesk", labelFontSize=11))
            _x = alt.X("i:Q", axis=None)
            if _chart_type == "bar":
                chart = alt.Chart(df).mark_bar(color=chart_color, opacity=0.75).encode(x=_x, y=_y)
            elif _chart_type == "candle":
                _area = alt.Chart(df).mark_area(color=chart_color, opacity=0.15, interpolate="monotone").encode(x=_x, y=_y)
                _line = alt.Chart(df).mark_line(color=chart_color, strokeWidth=2, interpolate="monotone").encode(x=_x, y=_y)
                _tick = alt.Chart(df).mark_tick(color=chart_color, thickness=2, size=10).encode(x=_x, y=_y)
                chart = _area + _line + _tick
            else:
                chart = alt.Chart(df).mark_line(color=chart_color, strokeWidth=2, interpolate="monotone").encode(x=_x, y=_y)
            st.altair_chart(
                chart.properties(height=220, background="transparent").configure_view(strokeWidth=0),
                use_container_width=True,
                theme=None
            )
        st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)

elif active == "news":
    st.markdown('<div class="section-hdr">Market Intelligence</div>', unsafe_allow_html=True)
    if not visible_news:
        st.markdown('<div style="text-align:center;padding:60px 20px"><p style="font-size:28px;font-weight:700;color:#fff;font-family:Space Grotesk,sans-serif">Nothing yet</p><p style="color:rgba(255,255,255,0.4);margin-top:8px">Intelligence drops as the game progresses.</p></div>', unsafe_allow_html=True)
    else:
        ctx_text = {
            "trading": "📡 Live feed: <strong>market events</strong> and <strong>insider hints</strong> only. Rumours surface during the break.",
            "between": "🌙 Break feed: <strong>rumours</strong> and <strong>insider hints</strong>. Market events resume next round.",
        }.get(phase, "Some of this was real. Some was noise.")
        st.markdown(f'<p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:16px">{ctx_text}</p>', unsafe_allow_html=True)
        for n in reversed(visible_news):
            ntype = n.get("type","custom"); lclass = news_label_class(ntype)
            st.markdown(f'<div class="news-card"><span class="news-label {lclass}">{n.get("label","News")}</span><div class="news-text">{n["text"]}</div></div>', unsafe_allow_html=True)

elif active == "loans":
    st.markdown('<div class="section-hdr">Bank Loans</div>', unsafe_allow_html=True)

    if "bank_open" not in st.session_state:
        st.session_state["bank_open"] = None

    # ── Bank panel styles ──────────────────────────────────────────────────────
    st.markdown("""<style>
    /* ── Outer wrapper ── */
    .bkp-wrap { margin-bottom:16px; border-radius:18px; overflow:hidden; }

    /* ── Header panel ── */
    .bkp-head {
        display:flex; align-items:stretch; min-height:110px;
        cursor:pointer; transition:filter 0.18s;
        border-radius:18px; border:1px solid;
        overflow:hidden; position:relative;
    }
    .bkp-head:hover { filter:brightness(1.1); }
    .bkp-head.bkp-open { border-radius:18px 18px 0 0; }

    /* colour accent stripe on left */
    .bkp-stripe { width:6px; flex-shrink:0; }

    /* main content area */
    .bkp-content { flex:1; padding:18px 20px; display:flex; flex-direction:column; justify-content:center; gap:6px; }

    /* rate column on the right */
    .bkp-rate-col {
        width:130px; flex-shrink:0;
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        gap:4px; padding:18px 16px;
        border-left:1px solid rgba(255,255,255,0.06);
    }
    .bkp-rate-num { font-size:32px; font-weight:900; font-family:'Space Grotesk',monospace; line-height:1; }
    .bkp-rate-lbl { font-size:11px; font-weight:600; letter-spacing:1px; text-transform:uppercase; opacity:0.5; }

    /* chevron */
    .bkp-chev { position:absolute; top:14px; right:16px; font-size:16px; color:rgba(255,255,255,0.3); transition:transform 0.25s; }
    .bkp-open .bkp-chev { transform:rotate(180deg); color:rgba(255,255,255,0.6); }

    /* text inside header */
    .bkp-name  { font-size:17px; font-weight:800; font-family:'Space Grotesk',sans-serif; color:#fff; }
    .bkp-meta  { font-size:12px; color:rgba(255,255,255,0.4); }
    .bkp-note  { font-size:11px; color:rgba(255,255,255,0.22); font-style:italic; margin-top:2px; }
    .bkp-bar-wrap { display:flex; align-items:center; gap:8px; margin-top:4px; }
    .bkp-bar-bg   { flex:1; height:5px; border-radius:99px; background:rgba(255,255,255,0.08); overflow:hidden; max-width:220px; }
    .bkp-bar-fill { height:100%; border-radius:99px; transition:width 0.4s ease; }
    .bkp-bar-lbl  { font-size:11px; color:rgba(255,255,255,0.3); white-space:nowrap; }

    /* ── Per-bank colour themes ── */
    .bkp-s .bkp-head  { background:linear-gradient(135deg,#071a12 0%,#0d2018 100%); border-color:rgba(0,200,150,0.3); }
    .bkp-m .bkp-head  { background:linear-gradient(135deg,#181408 0%,#201a08 100%); border-color:rgba(255,217,61,0.3); }
    .bkp-r .bkp-head  { background:linear-gradient(135deg,#1a080d 0%,#220812 100%); border-color:rgba(255,77,106,0.3); }
    .bkp-s .bkp-stripe { background:linear-gradient(180deg,#00C896,#007a5a); }
    .bkp-m .bkp-stripe { background:linear-gradient(180deg,#ffd93d,#b89a00); }
    .bkp-r .bkp-stripe { background:linear-gradient(180deg,#FF4D6A,#aa1a30); }
    .bkp-s .bkp-rate-num { color:#00C896; }
    .bkp-m .bkp-rate-num { color:#ffd93d; }
    .bkp-r .bkp-rate-num { color:#FF4D6A; }
    .bkp-s .bkp-bar-fill  { background:#00C896; }
    .bkp-m .bkp-bar-fill  { background:#ffd93d; }
    .bkp-r .bkp-bar-fill  { background:#FF4D6A; }
    .bkp-s .bkp-rate-col  { background:rgba(0,200,150,0.05); }
    .bkp-m .bkp-rate-col  { background:rgba(255,217,61,0.05); }
    .bkp-r .bkp-rate-col  { background:rgba(255,77,106,0.05); }

    /* ── Accordion connector strip — sits flush under card as design element ── */
    .bkp-body {
        padding: 14px 24px 6px;
        border-left: 1px solid;
        border-right: 1px solid;
        border-bottom: none;
        border-top: none;
        margin-top: -4px;
        margin-bottom: 8px;
    }
    .bkp-s .bkp-body { background:linear-gradient(180deg,#071a12,transparent); border-color:rgba(0,200,150,0.2); }
    .bkp-m .bkp-body { background:linear-gradient(180deg,#181408,transparent); border-color:rgba(255,217,61,0.2); }
    .bkp-r .bkp-body { background:linear-gradient(180deg,#1a080d,transparent); border-color:rgba(255,77,106,0.2); }
    .bkp-body-lbl { font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:rgba(255,255,255,0.3); margin-bottom:14px; }

    /* ── Loan amount buttons — per-theme colours via class on the wrapper div ── */
    .loan-amt-btn button {
        border-radius:10px !important; font-weight:700 !important;
        font-size:14px !important; height:46px !important;
        font-family:'Space Grotesk',monospace !important;
        transition:transform 0.12s, box-shadow 0.12s !important;
    }
    .loan-amt-btn button:not(:disabled):hover { transform:translateY(-2px) !important; box-shadow:0 4px 14px rgba(0,0,0,0.4) !important; }
    .loan-amt-btn.theme-s button { background:rgba(0,200,150,0.1) !important; border:1px solid rgba(0,200,150,0.35) !important; color:#00C896 !important; }
    .loan-amt-btn.theme-m button { background:rgba(255,217,61,0.08) !important; border:1px solid rgba(255,217,61,0.35) !important; color:#ffd93d !important; }
    .loan-amt-btn.theme-r button { background:rgba(255,77,106,0.08) !important; border:1px solid rgba(255,77,106,0.35) !important; color:#FF4D6A !important; }
    /* 5th (max) button always pink — overrides theme */
    .loan-amt-btn.loan-max button { background:rgba(236,72,153,0.1) !important; border:1px solid rgba(236,72,153,0.4) !important; color:#ec4899 !important; }

    /* ── Repay buttons ── */
    .repay-btn button { background:rgba(255,77,106,0.08) !important; border:1px solid rgba(255,77,106,0.25) !important; color:#FF4D6A !important; font-weight:600 !important; border-radius:10px !important; height:46px !important; }

    /* ── Outstanding loan summary card ── */
    .bkp-summary {
        background:linear-gradient(135deg,#0d0a1a 0%,#130f22 100%);
        border:1px solid rgba(167,139,250,0.3);
        border-radius:16px; padding:20px 24px;
        display:flex; align-items:center; justify-content:space-between;
        margin-bottom:20px; flex-wrap:wrap; gap:12px;
    }
    .bkp-summary-left .s-tag { font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:rgba(167,139,250,0.6); margin-bottom:6px; }
    .bkp-summary-left .s-amt { font-size:34px; font-weight:900; font-family:'Space Grotesk',monospace; color:#a78bfa; line-height:1; }
    .bkp-summary-right { font-size:12px; color:rgba(255,255,255,0.25); font-style:italic; text-align:right; }

    /* light mode overrides */
    body.light-mode .bkp-s .bkp-head  { background:linear-gradient(135deg,#edfff7,#d8f7eb); border-color:rgba(0,150,90,0.4); }
    body.light-mode .bkp-m .bkp-head  { background:linear-gradient(135deg,#fefde8,#faf5c0); border-color:rgba(160,120,0,0.4); }
    body.light-mode .bkp-r .bkp-head  { background:linear-gradient(135deg,#fff0f3,#fde0e6); border-color:rgba(180,0,30,0.4); }
    body.light-mode .bkp-s .bkp-body  { background:#f0fff8; border-color:rgba(0,150,90,0.25); }
    body.light-mode .bkp-m .bkp-body  { background:#fefde0; border-color:rgba(160,120,0,0.25); }
    body.light-mode .bkp-r .bkp-body  { background:#fde8ed; border-color:rgba(180,0,30,0.25); }
    body.light-mode .bkp-name          { color:#0d2e0d; }
    body.light-mode .bkp-meta          { color:#4a6a4a; }
    body.light-mode .bkp-note          { color:#7a947a; }
    body.light-mode .bkp-chev          { color:rgba(0,60,0,0.3); }
    body.light-mode .bkp-bar-lbl       { color:rgba(0,60,0,0.4); }
    body.light-mode .bkp-bar-bg        { background:rgba(0,60,0,0.08); }
    body.light-mode .bkp-s .bkp-rate-num { color:#006b3c; }
    body.light-mode .bkp-m .bkp-rate-num { color:#7a5c00; }
    body.light-mode .bkp-r .bkp-rate-num { color:#a0001e; }
    body.light-mode .bkp-body-lbl      { color:rgba(0,60,0,0.4); }
    body.light-mode .bkp-summary { background:linear-gradient(135deg,#f5f0ff,#ede8ff); border-color:rgba(120,80,220,0.3); }
    body.light-mode .bkp-summary-left .s-tag { color:rgba(100,60,200,0.6); }
    body.light-mode .bkp-summary-left .s-amt { color:#5b3fa0; }
    body.light-mode .bkp-summary-right { color:rgba(0,0,0,0.3); }
    </style>""", unsafe_allow_html=True)

    # ── Outstanding loan summary ───────────────────────────────────────────────
    if loan_balance > 0:
        st.markdown(f"""
        <div class="bkp-summary">
          <div class="bkp-summary-left">
            <div class="s-tag">Outstanding Debt</div>
            <div class="s-amt">{fmt(loan_balance)}</div>
          </div>
          <div class="bkp-summary-right">Interest charged<br>per bank at round-end.</div>
        </div>""", unsafe_allow_html=True)

    BK_THEME = {
        "rbi_safe":     "bkp-s",
        "axis_mid":     "bkp-m",
        "hawala_risky": "bkp-r",
    }
    BK_ICONS = {
        "rbi_safe":     "🏛",
        "axis_mid":     "🏦",
        "hawala_risky": "💀",
    }

    for bk_id, bk in BANKS.items():
        bank_bal  = team.get(f"loan_{bk_id}", 0)
        used_pct  = int(bank_bal / bk["cap"] * 100) if bk["cap"] else 0
        available = max(0, bk["cap"] - bank_bal)
        is_open   = st.session_state.get("bank_open") == bk_id
        theme     = BK_THEME.get(bk_id, "bkp-s")
        icon      = BK_ICONS.get(bk_id, "🏦")
        open_cls  = "bkp-open" if is_open else ""
        chev      = "▾" if is_open else "▸"

        # Clean approach: full-width styled button IS the card
        # Use CSS to make the button look exactly like the card panel
        btn_themes = {
            "bkp-s": ("linear-gradient(135deg,#071a12 0%,#0d2018 100%)", "rgba(0,200,150,0.3)", "#00C896", "rgba(0,200,150,0.06)"),
            "bkp-m": ("linear-gradient(135deg,#181408 0%,#201a08 100%)", "rgba(255,217,61,0.3)",  "#ffd93d", "rgba(255,217,61,0.06)"),
            "bkp-r": ("linear-gradient(135deg,#1a080d 0%,#220812 100%)", "rgba(255,77,106,0.3)",  "#FF4D6A", "rgba(255,77,106,0.06)"),
        }
        bg, border, rc, rc_bg = btn_themes.get(theme, btn_themes["bkp-s"])
        # Stripe color for left border
        stripe = rc
        st.markdown(f"""<style>
        button[data-key="bk_tog_{bk_id}"] {{
            background:{bg} !important;
            border:1px solid {border} !important;
            border-left:6px solid {stripe} !important;
            border-radius:18px !important;
            padding:18px 20px 18px 20px !important;
            height:auto !important; min-height:120px !important;
            width:100% !important;
            text-align:left !important;
            margin-bottom:12px !important;
            cursor:pointer !important;
            transition:filter 0.18s !important;
        }}
        button[data-key="bk_tog_{bk_id}"]:hover {{ filter:brightness(1.12) !important; }}
        button[data-key="bk_tog_{bk_id}"] p {{
            font-family:'Space Grotesk',monospace !important;
            font-size:15px !important; font-weight:700 !important;
            color:#fff !important; text-align:left !important;
            white-space:pre-wrap !important; line-height:1.8 !important;
            margin:0 !important;
        }}
        </style>""", unsafe_allow_html=True)
        bar_filled = "█" * (used_pct // 10) + "░" * (10 - used_pct // 10)
        btn_label = f"{icon}  {bk['name']}  {chev}\n{int(bk['rate']*100)}% per round   |   Limit {fmt(bk['cap'])}   ·   Borrowed {fmt(bank_bal)} ({used_pct}%)\n{bk['note']}"
        if st.button(btn_label, key=f"bk_tog_{bk_id}", use_container_width=True):
            st.session_state["bank_open"] = None if is_open else bk_id
            st.rerun()

        # ── Accordion body ─────────────────────────────────────────────────────
        if is_open:
            st.markdown(f'<div class="bkp-body {theme}">', unsafe_allow_html=True)
            if not can_bank:
                st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.4);margin:0">Borrowing is only available during trading rounds and breaks.</p>', unsafe_allow_html=True)
            elif available <= 0:
                st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.3);margin:0">Credit limit reached.</p>', unsafe_allow_html=True)
            else:
                valid_amts = [a for a in bk["borrow_options"] if a <= available]
                if valid_amts:
                    st.markdown('<div class="bkp-body-lbl">Choose amount to borrow</div>', unsafe_allow_html=True)
                    bcols = st.columns(len(valid_amts))
                    # theme_short maps bkp-s/m/r → s/m/r for the button class
                    theme_short = theme.replace("bkp-", "")
                    for i, amt in enumerate(valid_amts):
                        is_max = (i == len(valid_amts) - 1) and len(valid_amts) > 1
                        max_cls = "loan-max" if is_max else ""
                        with bcols[i]:
                            st.markdown(f'<div class="loan-amt-btn theme-{theme_short} {max_cls}">', unsafe_allow_html=True)
                            if st.button(fmt(amt), key=f"borrow_{bk_id}_{amt}", use_container_width=True):
                                state = load_state(); team = state["teams"][tid]
                                team["cash"] = team.get("cash", 0) + amt
                                team["loan_balance"] = team.get("loan_balance", 0) + amt
                                team[f"loan_{bk_id}"] = team.get(f"loan_{bk_id}", 0) + amt
                                state["teams"][tid] = team; save_state(state)
                                st.session_state["bank_open"] = None
                                st.success(f"Borrowed {fmt(amt)} from {bk['name']}"); st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.3);margin:0">No valid amounts available.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Repay section (break only) ─────────────────────────────────────────────
    if phase == "between" and loan_balance > 0:
        st.markdown('<p style="font-size:13px;color:rgba(255,255,255,0.5);margin:24px 0 10px">Repay now to reduce interest before the next round:</p>', unsafe_allow_html=True)
        repay_options = []
        if loan_balance >= 4: repay_options.append(("Pay ¼", loan_balance//4))
        if loan_balance >= 2: repay_options.append(("Pay ½", loan_balance//2))
        repay_options.append(("Pay Full", loan_balance))
        rcols = st.columns(len(repay_options))
        for i, (label, amount) in enumerate(repay_options):
            with rcols[i]:
                st.markdown('<div class="repay-btn">', unsafe_allow_html=True)
                if st.button(f"{label}  {fmt(amount)}", key=f"repay_{i}", use_container_width=True, disabled=(team["cash"]<amount)):
                    state = load_state(); team = state["teams"][tid]
                    if team["cash"] >= amount:
                        team["cash"] -= amount; team["loan_balance"] = max(0,team.get("loan_balance",0)-amount)
                        rem = amount
                        for bk_id in ["hawala_risky","axis_mid","rbi_safe"]:
                            bk_bal = team.get(f"loan_{bk_id}",0); red = min(bk_bal,rem)
                            team[f"loan_{bk_id}"] = bk_bal-red; rem -= red
                            if rem <= 0: break
                        state["teams"][tid] = team; save_state(state)
                        st.success(f"Repaid {fmt(amount)}."); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

elif active == "portfolio":
    st.markdown('<div class="section-hdr">Your Portfolio</div>', unsafe_allow_html=True)
    has = any(team["holdings"].get(cid,0) > 0 for cid in state["companies"])
    if not has:
        st.markdown('<div style="text-align:center;padding:60px 20px"><p style="font-size:28px;font-weight:700;color:#fff;font-family:Space Grotesk,sans-serif">No holdings</p><p style="color:rgba(255,255,255,0.4);margin-top:8px">Buy stocks from the Market panel.</p></div>', unsafe_allow_html=True)
    else:
        for cid, c in state["companies"].items():
            qty = team["holdings"].get(cid,0)
            if qty == 0: continue
            cp = c["price"]; avg = team["avg_cost"].get(cid,0); cv = qty*cp; pl = cv-qty*avg
            plc = "delta-up" if pl>=0 else "delta-down"; pls = "+" if pl>=0 else ""
            st.markdown(f'<div class="port-card"><div><div class="port-name">{c["name"]}</div><div class="port-qty">{qty} shares · {c["sector"]}</div></div><div class="port-stats"><div class="port-stat"><div class="s-label">Avg cost</div><div class="s-val">{fmt(avg)}</div></div><div class="port-stat"><div class="s-label">Current</div><div class="s-val">{fmt(cp)}</div></div><div class="port-stat"><div class="s-label">Value</div><div class="s-val">{fmt(cv)}</div></div><div class="port-stat"><div class="s-label">P / L</div><div class="s-val {plc}">{pls}{fmt(pl)}</div></div></div></div>', unsafe_allow_html=True)

# Auto-refresh handled by st_autorefresh(interval=1000) at top of file
