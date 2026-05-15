import streamlit as st
import json, random, time
from pathlib import Path
from utils import load_state, save_state, ROUND_DURATION
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_state, save_state, init_state, NEWS_POOL, STARTING_CASH, ROUND_DURATION
from streamlit_autorefresh import st_autorefresh
st.set_page_config(page_title="Host Panel — Market Mayhem", page_icon="🎛️", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=1400, key="datarefresh")
st.markdown("""
<style>
#MainMenu, header, footer { visibility: hidden; }
[data-testid="stSidebarNav"],[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stToolbar"],.stDeployButton,div[data-testid="stDecoration"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        div[data-testid="stProgress"] > div > div > div > div {
            background-color: #00C896 !important;
        }
        div[data-testid="stProgress"] > div > div {
            background-color: rgba(255, 255, 255, 0.1) !important;
        }
    </style>
""", unsafe_allow_html=True)
# ── Password gate ─────────────────────────────────────────────────────────────
HOST_PASSWORD = "RasnaKaGuavaJuice"
if "host_auth" not in st.session_state:
    st.session_state["host_auth"] = False

if not st.session_state["host_auth"]:
    st.markdown("<h1 style='color:white'>Host Access</h1>", unsafe_allow_html=True)
    st.caption("Restricted to event organisers only.")
    pwd = st.text_input("Password", type="password", placeholder="Enter host password")
    if st.button("Unlock", type="primary"):
        if pwd == HOST_PASSWORD:
            st.session_state["host_auth"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

BREAK_DURATION = 300   # keep in sync with trade.py

def render_host_progress(progress: float, phase: str):
    """Colour-shifting progress bar — no native st.progress dependency."""
    if phase == "trading":
        if   progress < 0.50: bar_color = "#00C896"
        elif progress < 0.75: bar_color = "#ffd93d"
        else:                  bar_color = "#FF4D6A"
    else:
        if   progress < 0.50: bar_color = "#a78bfa"
        elif progress < 0.75: bar_color = "#38bdf8"
        else:                  bar_color = "#00C896"
    pct = int(progress * 100)
    st.markdown(f"""
    <div style="margin-bottom:16px">
      <div style="background:rgba(255,255,255,0.08);border-radius:99px;height:14px;overflow:hidden">
        <div style="width:{pct}%;height:100%;background:{bar_color};border-radius:99px;transition:width 0.4s ease,background 0.6s ease"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Progress bar + alert banners ──────────────────────────────────────────────
state = load_state()
phase = state["phase"]

if phase == "trading":
    end_time = state.get("round_end_time")
    if end_time:
        remaining = end_time - time.time()
        if remaining > 0:
            progress_val = max(0.0, min(1.0, 1.0 - (remaining / ROUND_DURATION)))
            mins, secs = divmod(int(remaining), 60)
            time_label = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
            st.markdown(f'<p style="font-size:28px;color:rgba(255,255,255,0.8);margin-bottom:8px">⏱ Round closes in <strong style="color:#fff">{time_label}</strong></p>', unsafe_allow_html=True)
            render_host_progress(progress_val, "trading")
        else:
            # ── ALERT: round timer expired ────────────────────────────────────
            st.markdown("""
            <div style="background:rgba(255,77,106,0.15);border:2px solid #FF4D6A;border-radius:12px;padding:18px 24px;margin-bottom:16px;display:flex;align-items:center;gap:14px">
              <span style="font-size:28px">🚨</span>
              <div>
                <div style="font-size:18px;font-weight:700;color:#FF4D6A">Round time is up!</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:2px">Click <strong style="color:#fff">⏸️ End Current Round</strong> below to close trading and move to the break.</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            render_host_progress(1.0, "trading")

elif phase == "between":
    break_end_time = state.get("break_end_time")
    if break_end_time:
        remaining = break_end_time - time.time()
        if remaining > 0:
            progress_val = max(0.0, min(1.0, 1.0 - (remaining / BREAK_DURATION)))
            mins, secs = divmod(int(remaining), 60)
            time_label = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
            st.markdown(f'<p style="font-size:28px;color:rgba(255,255,255,0.8);margin-bottom:8px">☕ Break ends in <strong style="color:#fff">{time_label}</strong></p>', unsafe_allow_html=True)
            render_host_progress(progress_val, "between")
        else:
            # ── ALERT: break timer expired ────────────────────────────────────
            next_rnd = state["round"] + 1
            st.markdown(f"""
            <div style="background:rgba(56,189,248,0.12);border:2px solid #38bdf8;border-radius:12px;padding:18px 24px;margin-bottom:16px;display:flex;align-items:center;gap:14px">
              <span style="font-size:28px">🔔</span>
              <div>
                <div style="font-size:18px;font-weight:700;color:#38bdf8">Break over!</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:2px">Click <strong style="color:#fff">▶️ Start Round {next_rnd}</strong> below to resume trading.</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            render_host_progress(1.0, "between")
            
# ── Price engine ──────────────────────────────────────────────────────────────
def fluctuate_prices(state, round_news):
    companies = state["companies"]
    COMPANY_VOL = {
        "zora":      {"range": (0.005, 0.018), "bias": 0.48},
        "streamvx":  {"range": (0.030, 0.080), "bias": 0.45},
        "freshco":   {"range": (0.004, 0.016), "bias": 0.49},
        "voltex":    {"range": (0.020, 0.060), "bias": 0.44},
        "mediq":     {"range": (0.020, 0.070), "bias": 0.46},
        "skylink":   {"range": (0.035, 0.090), "bias": 0.44},
        "swifthaul": {"range": (0.012, 0.040), "bias": 0.46},
        "crownmart": {"range": (0.025, 0.075), "bias": 0.44},
        "shieldgen": {"range": (0.005, 0.020), "bias": 0.49},
    }
    prev_holdings = state.get("prev_holdings", {cid: 0 for cid in companies})
    FLOAT_SIZE = 10000

    for cid, c in companies.items():
        c["prev_price"] = c["price"]
        vol = COMPANY_VOL.get(cid, {"range": (0.020, 0.060), "bias": 0.45})
        vol_magnitude = random.uniform(vol["range"][0], vol["range"][1])
        direction = 1 if random.random() > vol["bias"] else -1
        change = direction * vol_magnitude

        # Buy/sell pressure
        current_held = sum(t["holdings"].get(cid, 0) for t in state["teams"].values())
        prev_held = prev_holdings.get(cid, 0)
        net_bought = current_held - prev_held
        pressure = (net_bought / FLOAT_SIZE) * 2.5
        pressure = max(-0.12, min(0.12, pressure))
        change += pressure

        # News impact
        for n in round_news:
            if n["affects"] == cid:
                impact = random.uniform(0.06, 0.14) if n["real"] else random.uniform(0.01, 0.03)
                change += n["direction"] * impact

        c["price"] = max(10, round(c["price"] * (1 + change)))

    state["prev_holdings"] = {
        cid: sum(t["holdings"].get(cid, 0) for t in state["teams"].values())
        for cid in companies
    }
    return state

def pick_round_news(state, count=3):
    used = state.get("news_used", [])
    pool = [n for n in NEWS_POOL if n["text"] not in used]
    picked = random.sample(pool, min(count, len(pool)))
    state["news_used"] = used + [n["text"] for n in picked]
    return picked

def fmt(n):
    return f"₹{int(n):,}"

# ── UI ────────────────────────────────────────────────────────────────────────
state = load_state()

st.markdown("<h1 style='color:white;margin-bottom:4px'>Host Control Panel</h1>", unsafe_allow_html=True)
st.caption("Market Mayhem · Inceptia")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Phase", state["phase"].upper())
c2.metric("Round", f"{state['round']} / 4")
c3.metric("Teams", len(state["teams"]))
c4.metric("News released", len(state.get("news", [])))

st.divider()

# ── Game controls ─────────────────────────────────────────────────────────────
st.subheader("Game controls")
col_a, col_b, col_c = st.columns(3)

with col_a:
    if state["phase"] == "lobby":
        if st.button("▶️ Start Round 1", type="primary", use_container_width=True):
            state["round"] = 1
            state["phase"] = "trading"
            state["round_end_time"] = time.time() + ROUND_DURATION
            new_news = pick_round_news(state, 2)
            state["news"] = new_news
            state = fluctuate_prices(state, new_news)
            save_state(state)
            st.success("Round 1 started!")
            st.rerun()
    elif state["phase"] == "trading":
        if st.button("⏸️ End Current Round", use_container_width=True):
            state["phase"] = "between"
            state["round_end_time"] = None
            state["break_end_time"] = time.time() + BREAK_DURATION
            # Apply per-bank interest on each team's per-bank balances
            BANK_RATES = {"rbi_safe": 0.05, "axis_mid": 0.10, "hawala_risky": 0.20}
            for tid, team in state["teams"].items():
                new_total = 0
                for bk_id, rate in BANK_RATES.items():
                    bk_bal = team.get(f"loan_{bk_id}", 0)
                    if bk_bal > 0:
                        bk_bal = round(bk_bal * (1 + rate))
                        team[f"loan_{bk_id}"] = bk_bal
                    new_total += bk_bal
                # Fallback for teams that didn't use per-bank tracking
                if new_total == 0 and team.get("loan_balance", 0) > 0:
                    default_rate = state.get("loan_interest_per_round", 0.10)
                    new_total = round(team["loan_balance"] * (1 + default_rate))
                team["loan_balance"] = new_total
                state["teams"][tid] = team
            save_state(state)
            st.success(f"Round {state['round']} ended. Break timer started. Per-bank interest applied.")
            st.rerun()
    elif state["phase"] == "between":
        next_round = state["round"] + 1
        if next_round <= 4:
            if st.button(f"▶️ Start Round {next_round}", type="primary", use_container_width=True):
                state["round"] = next_round
                state["phase"] = "trading"
                state["round_end_time"] = time.time() + ROUND_DURATION
                state["break_end_time"] = None
                new_news = pick_round_news(state, 3)
                state["news"] = state.get("news", []) + new_news
                state = fluctuate_prices(state, new_news)
                save_state(state)
                st.success(f"Round {next_round} started!")
                st.rerun()
        else:
            if st.button("🏁 End Game & Show Results", type="primary", use_container_width=True):
                state["phase"] = "ended"
                lb = []
                for tid, team in state["teams"].items():
                    pv = sum(team["holdings"].get(cid, 0) * state["companies"][cid]["price"] for cid in state["companies"])
                    loan_balance = team.get("loan_balance", 0)
                    nw = team["cash"] + pv - loan_balance
                    lb.append({"name": team["name"], "net_worth": nw, "cash": team["cash"], "portfolio": pv, "loan": loan_balance})
                lb.sort(key=lambda x: x["net_worth"], reverse=True)
                state["leaderboard"] = lb
                save_state(state)
                st.success("Game over! Leaderboard is live.")
                st.rerun()

with col_b:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

with col_c:
    if st.button("⚠️ Reset entire game", use_container_width=True):
        init_state()
        st.success("Game reset.")
        st.rerun()

st.divider()

# ── Custom news injection ─────────────────────────────────────────────────────
st.subheader("Inject a custom news event")
st.caption("Drops immediately and affects prices in real time.")

with st.form("inject_news"):
    news_type = st.selectbox("Type", ["Market event", "Insider hint", "Unverified rumour", "Positive news"])
    news_text = st.text_area("News text", placeholder="e.g. BREAKING: RBI freezes all transactions above ₹50,000...")
    affects = st.selectbox("Primarily affects", list(state["companies"].keys()), format_func=lambda x: state["companies"][x]["name"])
    direction = st.radio("Price direction", ["Up ↑", "Down ↓"], horizontal=True)
    is_real = st.checkbox("Is this real? (real events move price strongly)", value=True)
    submitted = st.form_submit_button("Inject event", type="primary")

    if submitted and news_text.strip():
        custom_news = {
            "type": "custom",
            "label": news_type,
            "text": news_text.strip(),
            "affects": affects,
            "direction": 1 if "Up" in direction else -1,
            "real": is_real,
        }
        state["news"].append(custom_news)
        c = state["companies"][affects]
        c["prev_price"] = c["price"]
        strength = random.uniform(0.07, 0.15) if is_real else random.uniform(0.01, 0.03)
        direction_val = 1 if "Up" in direction else -1
        c["price"] = max(10, round(c["price"] * (1 + direction_val * strength)))
        save_state(state)
        st.success(f"Event injected! {state['companies'][affects]['name']} price updated.")
        st.rerun()

st.divider()

# ── Live prices ───────────────────────────────────────────────────────────────
st.subheader("Live market prices")
price_cols = st.columns(len(state["companies"]))
for i, (cid, c) in enumerate(state["companies"].items()):
    chg = c["price"] - c["prev_price"]
    chg_pct = (chg / c["prev_price"] * 100) if c["prev_price"] else 0
    price_cols[i].metric(c["name"], fmt(c["price"]), delta=f"{chg:+.0f} ({chg_pct:+.1f}%)")

st.divider()

# ── Team management ───────────────────────────────────────────────────────────
st.subheader("Team portfolios")
if not state["teams"]:
    st.info("No teams registered yet.")
else:
    rows = []
    for tid, team in state["teams"].items():
        pv = sum(team["holdings"].get(cid, 0) * state["companies"][cid]["price"] for cid in state["companies"])
        loan = team.get("loan_balance", 0)
        nw = team["cash"] + pv - loan
        rows.append({"tid": tid, "name": team["name"], "player": team.get("player_num","?"), "cash": team["cash"], "portfolio": pv, "loan": loan, "net_worth": nw})
    rows.sort(key=lambda x: x["net_worth"], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    # Header
    hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([0.4, 2.2, 1.2, 1.2, 1.2, 0.8])
    hc2.caption("Team · Player"); hc3.caption("Cash"); hc4.caption("Portfolio"); hc5.caption("Net Worth"); hc6.caption("")
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        col1, col2, col3, col4, col5, col6 = st.columns([0.4, 2.2, 1.2, 1.2, 1.2, 0.8])
        col1.write(medal)
        col2.write(f"**{row['name']}** · P{row['player']}")
        col3.write(fmt(row["cash"]))
        col4.write(fmt(row["portfolio"]))
        col5.write(f"**{fmt(row['net_worth'])}**")
        if col6.button("Kick", key=f"kick_{row['tid']}"):
            del state["teams"][row["tid"]]
            save_state(state)
            st.warning(f"Removed {row['name']}")
            st.rerun()

st.divider()

# ── News feed (with truth revealed) ──────────────────────────────────────────
st.subheader("News released — truth revealed")
if not state.get("news"):
    st.caption("No news released yet.")
else:
    for n in reversed(state["news"]):
        real_tag = "✅ Real" if n.get("real") else "❌ False rumour"
        st.markdown(f"**{n.get('label','News')}** — {n['text']}  \n_{real_tag} · Affects: {state['companies'].get(n['affects'],{}).get('name', n['affects'])}_")
        st.divider()
