from pathlib import Path
import json, os, time, tempfile

# Constants
STARTING_CASH   = 0
ROUND_DURATION  = 1200
BREAK_DURATION  = 300

STATE_FILE = Path(__file__).parent / "game_state.json"

# ── Atomic load: retries if file is mid-write ─────────────────────────────────
def load_state(retries: int = 8, delay: float = 0.05):
    for attempt in range(retries):
        try:
            if STATE_FILE.exists():
                text = STATE_FILE.read_text(encoding="utf-8").strip()
                if text:
                    return json.loads(text)
        except (json.JSONDecodeError, OSError):
            if attempt < retries - 1:
                time.sleep(delay)
            continue
    # File is corrupt or missing — reinitialise
    return init_state()

# ── Atomic save: write to temp then rename (single syscall, no partial writes) ─
def save_state(state):
    dir_ = STATE_FILE.parent
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            # Atomic on POSIX; best-effort on Windows
            os.replace(tmp_path, STATE_FILE)
        except Exception:
            try: os.unlink(tmp_path)
            except OSError: pass
            raise
    except Exception:
        # Hard fallback — at least try a normal write
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

def init_state():
    state = {
        "phase": "lobby",
        "round": 0,
        "round_end_time": None,
        "break_end_time": None,
        "companies": {
            "zora":      {"name":"Zora Industries",      "sector":"Manufacturing",    "price":420,  "prev_price":420,  "profile":"stable",   "age":"52 years","size":"Large-cap","bio":"A 52-year-old industrial giant. Builds everything from steel pipes to defence components. Boring but bulletproof — has never missed a dividend in 30 years. Trusted by the government, hated by competitors.","trait":"Old money. Steady as a rock.","risk":"Low"},
            "streamvx":  {"name":"StreamVerse",           "sector":"Media / OTT",      "price":310,  "prev_price":310,  "profile":"volatile",  "age":"8 years", "size":"Mid-cap", "bio":"India's fastest-growing OTT platform with 62 million subscribers. Burning cash on original content but subscriber numbers keep Wall Street happy. One hit show away from profitability — or one flop away from a funding crisis.","trait":"Binge-worthy. Wallet-draining.","risk":"High"},
            "freshco":   {"name":"FreshCo",              "sector":"FMCG",             "price":185,  "prev_price":185,  "profile":"stable",   "age":"38 years","size":"Large-cap","bio":"India's most trusted household brand. Makes everything from biscuits to shampoo. Rural India runs on FreshCo. Slow growth, predictable returns, and the kind of stock your grandparents would approve of.","trait":"Every Indian home has one.","risk":"Low"},
            "voltex":    {"name":"Voltex Energy",        "sector":"Renewable Energy", "price":560,  "prev_price":560,  "profile":"growth",   "age":"9 years", "size":"Mid-cap", "bio":"Riding the green energy wave hard. Solar parks across 6 states, two wind farm contracts pending. Government darling right now. Still unprofitable but growing at 60% YoY.","trait":"Future is bright. Profits, not yet.","risk":"Medium-High"},
            "mediq":     {"name":"MediQ",                "sector":"Pharma",           "price":275,  "prev_price":275,  "profile":"growth",   "age":"24 years","size":"Mid-cap", "bio":"A pharma company sitting on a potential blockbuster drug in clinical trials. If approved, this stock 5x's overnight. If rejected, it tanks 40%. Everyone knows it, nobody is sure which way it goes.","trait":"One approval away from the moon.","risk":"Medium"},
            "skylink":   {"name":"SkyLink Tech",         "sector":"Technology",       "price":890,  "prev_price":890,  "profile":"volatile",  "age":"7 years", "size":"Large-cap","bio":"India's answer to every Silicon Valley giant. Overvalued by most metrics, but investor sentiment keeps it flying. Founded by a 28-year-old. One bad earnings call away from a crash.","trait":"Overhyped. Overpriced. Irresistible.","risk":"High"},
            "swifthaul": {"name":"SwiftHaul Logistics",  "sector":"Logistics",        "price":340,  "prev_price":340,  "profile":"growth",   "age":"11 years","size":"Mid-cap", "bio":"Built on the back of India's e-commerce explosion. Delivers 2.4 million packages a day across 18,000 pin codes. Profitable since Year 6. Currently undercutting every competitor on pricing.","trait":"The backbone of online India.","risk":"Medium"},
            "crownmart": {"name":"CrownMart Retail",     "sector":"Retail",           "price":210,  "prev_price":210,  "profile":"volatile",  "age":"15 years","size":"Mid-cap", "bio":"India's third-largest retail chain with 800+ stores. Loved by tier-2 city shoppers, struggling against quick commerce apps. Has been 'about to turn profitable' for three years. Activist investors are circling.","trait":"Great stores, messy books.","risk":"High"},
            "shieldgen": {"name":"ShieldGen Defence",    "sector":"Defence",          "price":780,  "prev_price":780,  "profile":"stable",   "age":"31 years","size":"Large-cap","bio":"One of only three private defence manufacturers licensed by the Ministry of Defence. Makes radar systems, armoured vehicles, and drone components. Geopolitical tensions are its best friend.","trait":"The quietest money-maker on the board.","risk":"Low"},
        },
        "loan_cap": 150000,
        "loan_interest_per_round": 0.10,
        "teams": {},
        "news": [],
        "news_used": [],
        "leaderboard": [],
        "prev_holdings": {},
    }
    save_state(state)
    return state

NEWS_POOL = [
    # ── Zora ──────────────────────────────────────────────────────────────────
    {"type":"insider",  "label":"Insider Hint",      "affects":"zora",      "direction": 1,  "real":True,  "text":"Insider tip: Zora Industries is in final discussions for a ₹2,800 crore government infrastructure contract. Sources close to the Ministry confirm the announcement is imminent."},
    {"type":"event",    "label":"Market Event",      "affects":"zora",      "direction":-1,  "real":True,  "text":"BREAKING: National union calls a 3-day strike at manufacturing hubs across 5 states. Zora Industries' Pune plant among those affected."},
    {"type":"event",    "label":"Market Event",      "affects":"zora",      "direction": 1,  "real":True,  "text":"Zora Industries posts its 30th consecutive year of dividend payouts. Institutional investors increase stake by 4.2% this quarter."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"zora",      "direction":-1,  "real":False, "text":"Rumour: An anonymous whistleblower claims Zora Industries used substandard materials in a recent government project. Company denies all allegations."},
    # ── StreamVerse ───────────────────────────────────────────────────────────
    {"type":"event",    "label":"Market Event",      "affects":"streamvx",  "direction":-1,  "real":True,  "text":"BREAKING: StreamVerse reports a 14% spike in subscriber churn after hiking subscription prices by ₹100/month. Analysts cut price targets citing retention risk."},
    {"type":"event",    "label":"Market Event",      "affects":"streamvx",  "direction": 1,  "real":True,  "text":"StreamVerse's latest original series crosses 200 million watch hours in its first week — the biggest debut on any Indian OTT platform. Subscriber adds expected to surge."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"streamvx",  "direction":-1,  "real":False, "text":"Rumour: A former StreamVerse exec claims the platform inflates subscriber counts to attract advertisers. Internal audit allegedly underway. Company denies any wrongdoing."},
    {"type":"insider",  "label":"Insider Hint",      "affects":"streamvx",  "direction": 1,  "real":True,  "text":"Insider tip: StreamVerse is close to signing an exclusive cricket streaming deal covering 3 IPL seasons — a contract worth ₹4,200 crore that would lock in tens of millions of subscribers."},
    # ── FreshCo ───────────────────────────────────────────────────────────────
    {"type":"event",    "label":"Market Event",      "affects":"freshco",   "direction": 1,  "real":True,  "text":"FMCG sector hits record rural demand. FreshCo's distribution network of 6 million kirana stores gives it unmatched last-mile advantage. Analysts upgrade to Strong Buy."},
    {"type":"event",    "label":"Market Event",      "affects":"freshco",   "direction":-1,  "real":True,  "text":"BREAKING: Cyclone warning across eastern coast. FreshCo's largest manufacturing cluster in Odisha faces potential shutdown for 5–7 days."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"freshco",   "direction":-1,  "real":False, "text":"Rumour: A viral social media post claims FreshCo's popular biscuit brand contains banned additives. Company calls it fabricated."},
    {"type":"insider",  "label":"Insider Hint",      "affects":"freshco",   "direction": 1,  "real":True,  "text":"Insider tip: FreshCo is about to launch its first premium skincare line targeting urban millennials — analysts say it could add ₹1,200 crore to revenues."},
    # ── Voltex ────────────────────────────────────────────────────────────────
    {"type":"event",    "label":"Market Event",      "affects":"voltex",    "direction": 1,  "real":True,  "text":"BREAKING: Government announces ₹4,200 crore renewable energy subsidy expansion. Voltex Energy named explicitly in the policy document as a primary beneficiary."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"voltex",    "direction": 1,  "real":False, "text":"Rumour: Voltex Energy allegedly in advanced merger talks with a UAE sovereign wealth fund. Could value the company at 3x current market cap. Unconfirmed."},
    {"type":"event",    "label":"Market Event",      "affects":"voltex",    "direction":-1,  "real":True,  "text":"BREAKING: Two Voltex solar parks in Rajasthan fail safety inspections. Ministry of New Energy suspends project clearances pending review."},
    {"type":"event",    "label":"Market Event",      "affects":"voltex",    "direction": 1,  "real":True,  "text":"Voltex Energy signs its largest contract yet — a 900MW solar park for a state electricity board. Analysts revise price target upward by 35%."},
    # ── MediQ ─────────────────────────────────────────────────────────────────
    {"type":"insider",  "label":"Insider Hint",      "affects":"mediq",     "direction": 1,  "real":True,  "text":"Insider tip: MediQ's Phase 3 drug trial results are being submitted to DCGI this week. Internal sources describe results as 'exceptionally strong'. Approval expected within 30 days."},
    {"type":"event",    "label":"Market Event",      "affects":"mediq",     "direction":-1,  "real":True,  "text":"BREAKING: DCGI rejects MediQ's blockbuster drug application citing insufficient long-term safety data. Additional trials required — timeline pushed back 18 months."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"mediq",     "direction": 1,  "real":False, "text":"Rumour: A global pharma giant is reportedly in talks to acquire MediQ at a 60% premium. Neither company has confirmed. Treat as speculation."},
    {"type":"event",    "label":"Market Event",      "affects":"mediq",     "direction": 1,  "real":True,  "text":"MediQ quietly files 4 new patents for next-generation oncology drugs. Patent filings signal a robust pipeline the market hasn't priced in."},
    # ── SkyLink ───────────────────────────────────────────────────────────────
    {"type":"event",    "label":"Market Event",      "affects":"skylink",   "direction": 1,  "real":True,  "text":"SkyLink Tech posts 34% YoY revenue growth in Q2, beating analyst consensus by ₹420 crore. Founder announces entry into Southeast Asian markets."},
    {"type":"event",    "label":"Market Event",      "affects":"skylink",   "direction":-1,  "real":True,  "text":"BREAKING: A massive data breach at SkyLink Tech exposes 11 million user records. Government issues show-cause notice. Fines expected to exceed ₹800 crore."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"skylink",   "direction":-1,  "real":False, "text":"Rumour: Three senior SkyLink engineers have resigned en masse over a dispute with the founder. Anonymous posts describe 'toxic leadership'. Unverified."},
    {"type":"insider",  "label":"Insider Hint",      "affects":"skylink",   "direction": 1,  "real":True,  "text":"Insider tip: SkyLink is set to announce an AI product partnership with a top US tech firm next week — a deal that could fundamentally change its valuation story."},
    # ── SwiftHaul ─────────────────────────────────────────────────────────────
    {"type":"event",    "label":"Market Event",      "affects":"swifthaul", "direction": 1,  "real":True,  "text":"SwiftHaul Logistics reports a 28% surge in same-day delivery volume as festive season kicks off. Signs exclusive 3-year contract with India's largest e-commerce platform."},
    {"type":"event",    "label":"Market Event",      "affects":"swifthaul", "direction":-1,  "real":True,  "text":"BREAKING: Fuel prices rise 12% following global crude oil surge. SwiftHaul's fleet of 18,000 vehicles faces immediate margin compression."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"swifthaul", "direction":-1,  "real":False, "text":"Rumour: SwiftHaul allegedly under-reporting delivery failure rates to maintain contract metrics. An internal audit is said to be underway."},
    {"type":"insider",  "label":"Insider Hint",      "affects":"swifthaul", "direction": 1,  "real":True,  "text":"Insider tip: SwiftHaul is finalising a cold-chain logistics venture for pharmaceutical distribution — a high-margin segment that could significantly diversify revenues."},
    # ── CrownMart ─────────────────────────────────────────────────────────────
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"crownmart", "direction": 1,  "real":False, "text":"Rumour: A major private equity firm is building a stake in CrownMart ahead of an alleged management buyout. Unusual after-hours trading activity spotted."},
    {"type":"event",    "label":"Market Event",      "affects":"crownmart", "direction":-1,  "real":True,  "text":"BREAKING: Quick commerce platform Blinkit announces 10-minute grocery delivery expansion to 50 new cities — directly attacking CrownMart's core customer base."},
    {"type":"event",    "label":"Market Event",      "affects":"crownmart", "direction": 1,  "real":True,  "text":"CrownMart's new CEO unveils a restructuring plan: closing 120 loss-making stores and doubling down on high-margin private label products. Analysts react positively."},
    {"type":"insider",  "label":"Insider Hint",      "affects":"crownmart", "direction":-1,  "real":True,  "text":"Insider tip: CrownMart's Q3 same-store sales data, not yet public, shows a 9% decline. Results due next week. Insiders are quietly reducing positions."},
    # ── ShieldGen ─────────────────────────────────────────────────────────────
    {"type":"event",    "label":"Market Event",      "affects":"shieldgen", "direction": 1,  "real":True,  "text":"BREAKING: Escalating border tensions prompt government to fast-track ₹18,000 crore in emergency defence procurement. ShieldGen is the primary domestic supplier for 3 of 5 categories."},
    {"type":"event",    "label":"Market Event",      "affects":"shieldgen", "direction": 1,  "real":True,  "text":"ShieldGen Defence receives export clearance to supply radar systems to two allied nations — India's defence export push directly benefits its order book."},
    {"type":"rumour",   "label":"Unverified Rumour", "affects":"shieldgen", "direction":-1,  "real":False, "text":"Rumour: A parliamentary committee is allegedly reviewing ShieldGen's pricing on a recent armoured vehicle contract. Overpricing allegations. Government has not confirmed any probe."},
    {"type":"insider",  "label":"Insider Hint",      "affects":"shieldgen", "direction": 1,  "real":True,  "text":"Insider tip: ShieldGen has secured a 7-year maintenance contract for a classified drone programme. Value estimated at ₹6,000 crore. Announcement expected post budget session."},
]
