import os
import re
import json
import datetime as dt
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="FinPilot AI", layout="wide", initial_sidebar_state="collapsed")

CACHE_DIR = "market_cache"
ACCOUNTS_DIR = "accounts"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(ACCOUNTS_DIR, exist_ok=True)

COLORS = ["#10B981", "#0EA5E9", "#8B5CF6", "#F59E0B", "#EF4444", "#14B8A6", "#6366F1", "#EC4899"]
GOALS = ["Retirement", "A home", "Education", "Building wealth"]
RISKS = ["Conservative", "Moderate", "Aggressive"]

# Curated universe the AI advisor is allowed to choose from (no hallucinated/penny tickers).
UNIVERSE = {
    "US broad market ETF": ["VTI", "VOO"],
    "US tech/growth ETF": ["QQQ"],
    "US large-cap stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "JPM", "JNJ", "PG", "V", "KO"],
    "Dividend ETF": ["SCHD", "VYM"],
    "International developed ETF": ["VEA", "VXUS"],
    "Emerging markets ETF": ["VWO"],
    "Aggregate bond ETF": ["BND", "AGG"],
    "Long-term treasury ETF": ["TLT"],
    "Short-term treasury / cash ETF": ["SHY", "BIL"],
    "Gold ETF": ["GLD"],
}
ALL_TICKERS = sorted({t for v in UNIVERSE.values() for t in v})


def _rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def toggle(label, key):
    try:
        return st.toggle(label, key=key)
    except Exception:
        return st.checkbox(label, key=key)


def card():
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def _safe(name):
    return "".join(c for c in str(name).lower() if c.isalnum() or c in ("-", "_")) or "user"


# ---------------- ACCOUNT PERSISTENCE ----------------

def account_path(name):
    return os.path.join(ACCOUNTS_DIR, f"{_safe(name)}.json")


def save_account(a):
    try:
        with open(account_path(a["name"]), "w") as f:
            json.dump(a, f, indent=2)
    except Exception:
        pass


def load_account(name):
    try:
        with open(account_path(name)) as f:
            return json.load(f)
    except Exception:
        return None


def list_accounts():
    out = []
    for fn in os.listdir(ACCOUNTS_DIR):
        if fn.endswith(".json"):
            a = load_account(fn[:-5])
            if a and "name" in a:
                out.append(a["name"])
    return sorted(set(out))


# ---------------- HELPERS ----------------

def money(v):
    return f"${float(v):,.0f}"


def money_short(v):
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def parse_weights(text, tickers):
    try:
        vals = [float(x) for x in str(text).split(",") if x.strip()]
    except Exception:
        vals = []
    if len(vals) == len(tickers) and sum(vals) > 0:
        w = np.array(vals, dtype=float)
        return w / w.sum()
    return np.array([1 / len(tickers)] * len(tickers))


# ---------------- DATA LAYER (auto-refreshing, 10-min cache) ----------------

def _price_path(ticker, period):
    return os.path.join(CACHE_DIR, f"px_{_safe(ticker)}_{period}.csv")


def _save_prices_to_cache(df, period):
    for col in df.columns:
        df[[col]].dropna().to_csv(_price_path(col, period))


def _load_prices_from_cache(tickers, period):
    frames = []
    for t in tickers:
        path = _price_path(t, period)
        if not os.path.exists(path):
            raise FileNotFoundError(t)
        s = pd.read_csv(path, index_col=0, parse_dates=True)
        s.columns = [t]
        frames.append(s)
    return pd.concat(frames, axis=1).dropna()


@st.cache_data(ttl=600, show_spinner=False)
def get_stock_data(tickers, period="1y", demo_mode=False):
    tickers = list(tickers)
    if demo_mode:
        try:
            return _load_prices_from_cache(tickers, period)
        except Exception:
            pass
    try:
        raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
        if isinstance(raw, pd.Series):
            raw = raw.to_frame(name=tickers[0])
        raw = raw.dropna()
        if raw.empty:
            raise ValueError("empty")
        _save_prices_to_cache(raw, period)
        return raw
    except Exception:
        return _load_prices_from_cache(tickers, period)


@st.cache_data(ttl=600, show_spinner=False)
def get_dividend_data(tickers, prices=None, demo_mode=False):
    tickers = list(tickers)
    rows = []
    for t in tickers:
        last_price = np.nan
        if prices is not None and t in prices.columns:
            s = prices[t].dropna()
            if not s.empty:
                last_price = float(s.iloc[-1])
        annual_dividend = 0.0
        try:
            divs = yf.Ticker(t).dividends
            if divs is not None and not divs.empty:
                cutoff = divs.index.max() - pd.DateOffset(years=1)
                annual_dividend = float(divs[divs.index >= cutoff].sum())
        except Exception:
            annual_dividend = 0.0
        dy = (annual_dividend / last_price) if (last_price and last_price > 0) else 0.0
        rows.append({"Ticker": t, "Dividend Yield": dy, "Estimated Price": last_price})
    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def market_conditions(demo_mode=False):
    try:
        spy = get_stock_data(["SPY"], "6mo", demo_mode)["SPY"].dropna()
        rets = spy.pct_change().dropna()
        ann_vol = float(rets.std() * np.sqrt(252))
        drawdown = float(spy.iloc[-1] / spy.cummax().iloc[-1] - 1)
    except Exception:
        return None
    if ann_vol < 0.13 and drawdown > -0.05:
        label, adj, mult = "Calm", 0.00, 1.00
    elif ann_vol < 0.20:
        label, adj, mult = "Normal", -0.01, 1.10
    elif ann_vol < 0.30:
        label, adj, mult = "Cautious", -0.03, 1.30
    else:
        label, adj, mult = "Stressed", -0.06, 1.60
    if drawdown < -0.12 and label in ("Calm", "Normal"):
        label, adj, mult = "Cautious", -0.03, 1.30
    return {"label": label, "ann_vol": ann_vol, "drawdown": drawdown, "return_adjustment": adj,
            "volatility_multiplier": mult,
            "explanation": f"Based on recent S&P 500 volatility of {ann_vol:.0%} and a {abs(drawdown):.0%} pullback from its high."}


# ---------------- FINANCE ----------------

def apply_clean_theme(fig):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0)",
                      font=dict(color="#102A43"), title_font=dict(size=19, color="#102A43"),
                      margin=dict(l=20, r=20, t=50, b=20), legend=dict(bgcolor="rgba(255,255,255,0)", borderwidth=0))
    return fig


def recommend_allocation(age, risk, horizon):
    if risk == "Conservative":
        equity = max(20, 100 - age - 20)
    elif risk == "Moderate":
        equity = max(30, 110 - age)
    else:
        equity = max(40, 120 - age)
    equity += 10 if horizon > 15 else (-20 if horizon < 5 else 0)
    equity = min(max(equity, 10), 90)
    bonds = max(0, 100 - equity - 5)
    return {"Equity": equity, "Bonds / Fixed Income": bonds, "Cash": 100 - equity - bonds}


def recommended_portfolio(allocation, equity_tickers):
    sleeves = {"Equity": list(equity_tickers) if equity_tickers else ["VTI"], "Bonds / Fixed Income": ["BND"], "Cash": ["BIL"]}
    w = {}
    for sleeve, pct in allocation.items():
        ts = sleeves.get(sleeve, [])
        if not ts or pct <= 0:
            continue
        share = (pct / 100.0) / len(ts)
        for t in ts:
            w[t] = w.get(t, 0.0) + share
    total = sum(w.values())
    return {t: x / total for t, x in w.items()} if total > 0 else w


def build_ai_portfolio(api_key, profile):
    """Ask the AI to build a SAMPLE portfolio from the curated universe. Returns
    {"summary":..., "holdings":[{ticker,weight,reason}]} or None on any failure."""
    if not api_key:
        return None
    prompt = f"""You are an educational robo-advisor building a SAMPLE diversified portfolio (this is NOT financial advice).
Choose 5 to 8 instruments ONLY from this approved list: {ALL_TICKERS}.
Investor: age {profile['age']}, {profile['risk']} risk tolerance, {profile['horizon']}-year horizon,
goal "{profile['goal']}", investing about ${profile['monthly']:,.0f}/month.
Rules: weights are percentages summing to 100; match the equity/bond/cash balance to the risk level and horizon
(more bonds/cash for conservative or short horizons, more equities for aggressive or long horizons); diversify across
asset types; pick nothing outside the list.
Return ONLY valid JSON (no markdown, no prose) in exactly this shape:
{{"summary":"one short paragraph on the strategy","holdings":[{{"ticker":"VTI","weight":40,"reason":"short reason"}}]}}"""
    try:
        from anthropic import Anthropic
        msg = Anthropic(api_key=api_key).messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=900,
            messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text
        match = re.search(r"\{.*\}", text, re.S)
        data = json.loads(match.group(0))
        valid = set(ALL_TICKERS)
        holdings = []
        for h in data.get("holdings", []):
            tk = str(h.get("ticker", "")).upper().strip()
            if tk in valid and float(h.get("weight", 0)) > 0:
                holdings.append({"ticker": tk, "weight": float(h["weight"]), "reason": str(h.get("reason", ""))[:160]})
        if not holdings:
            return None
        tot = sum(h["weight"] for h in holdings)
        for h in holdings:
            h["weight"] = round(h["weight"] / tot * 100, 1)
        return {"summary": str(data.get("summary", ""))[:600], "holdings": holdings}
    except Exception:
        return None


def build_smart_portfolio(profile):
    """Rule-based portfolio in the SAME shape as the AI one, so the experience shows
    even without an API key. Picks from the curated universe based on risk and horizon."""
    risk, horizon = profile["risk"], profile["horizon"]
    alloc = recommend_allocation(profile["age"], risk, horizon)
    eq, bd, csh = alloc["Equity"], alloc["Bonds / Fixed Income"], alloc["Cash"]
    if risk == "Aggressive":
        eq_split = [("VTI", 0.40, "Total US market core"), ("QQQ", 0.25, "Growth tilt for the long horizon"),
                    ("VXUS", 0.20, "International diversification"), ("NVDA", 0.15, "High-growth large-cap")]
    elif risk == "Moderate":
        eq_split = [("VTI", 0.50, "Total US market core"), ("SCHD", 0.25, "Quality dividend payers"),
                    ("VXUS", 0.25, "International diversification")]
    else:
        eq_split = [("VTI", 0.60, "Broad, steady core"), ("SCHD", 0.40, "Dividend stability")]
    holdings = [{"ticker": tk, "weight": round(eq * frac, 1), "reason": rs} for tk, frac, rs in eq_split]
    if bd > 0:
        holdings.append({"ticker": "BND", "weight": round(bd, 1), "reason": "Investment-grade bonds for stability"})
    if csh > 0:
        holdings.append({"ticker": "BIL", "weight": round(csh, 1), "reason": "T-bills for safety and liquidity"})
    tot = sum(h["weight"] for h in holdings) or 1
    for h in holdings:
        h["weight"] = round(h["weight"] / tot * 100, 1)
    summary = (f"A {risk.lower()} portfolio for a {horizon}-year horizon: about {eq}% equities, "
               f"{bd}% bonds and {csh}% cash, diversified across US, international, and defensive assets, "
               f"and rebalanced to these targets over time.")
    return {"summary": summary, "holdings": holdings}


def risk_score(age, risk, horizon, monthly, income):
    s = 50
    s += 15 if age < 30 else (-15 if age > 55 else 0)
    s += 20 if risk == "Aggressive" else (-20 if risk == "Conservative" else 0)
    s += 15 if horizon > 15 else (-15 if horizon < 5 else 0)
    sr = (monthly * 12) / income if income > 0 else 0
    s += 10 if sr > 0.25 else (-10 if sr < 0.10 else 0)
    return int(min(max(s, 0), 100))


def portfolio_metrics(prices, weights, rf=0.0):
    returns = prices.pct_change().dropna()
    er = np.dot(weights, returns.mean() * 252)
    vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    return er, vol, ((er - rf) / vol if vol != 0 else 0), returns


def health_score(n, vol, sharpe):
    s = 50
    s += 15 if n >= 5 else (-15 if n <= 2 else 0)
    s += 15 if vol < 0.20 else (-15 if vol > 0.35 else 0)
    s += 20 if sharpe > 1 else (-10 if sharpe < 0.3 else 0)
    return int(min(max(s, 0), 100))


def contribution_for_month(base, growth, month):
    return base * ((1 + growth) ** (month // 12))


def wealth_projection(start, monthly, annual_return, years, growth):
    mr = annual_return / 12
    value = start
    rows = []
    for m in range(years * 12 + 1):
        c = contribution_for_month(monthly, growth, m)
        rows.append({"Year": m / 12, "Monthly Contribution": c, "Projected Value": value})
        value = value * (1 + mr) + c
    return pd.DataFrame(rows)


def income_schedule(income, monthly, sg, cg, years):
    rows = []
    for y in range(years + 1):
        salary = income * ((1 + sg) ** y)
        mc = monthly * ((1 + cg) ** y)
        rows.append({"Year": y, "Projected Salary": salary, "Monthly Contribution": mc,
                     "Annual Contribution": mc * 12, "Contribution Rate": (mc * 12 / salary) if salary else 0})
    return pd.DataFrame(rows)


def random_portfolios(prices, n=3000):
    returns = prices.pct_change().dropna()
    ar = returns.mean() * 252
    cov = returns.cov() * 252
    res = []
    for _ in range(n):
        w = np.random.random(len(prices.columns))
        w /= w.sum()
        pr = np.dot(w, ar)
        pv = np.sqrt(np.dot(w.T, np.dot(cov, w)))
        res.append({"Return": pr, "Volatility": pv, "Sharpe": pr / pv if pv else 0, "Weights": w})
    return pd.DataFrame(res)


def monte_carlo(start, monthly, er, vol, years, growth, sims=500):
    mr = er / 12
    mv = vol / np.sqrt(12)
    paths = []
    for _ in range(sims):
        v = start
        p = []
        for m in range(years * 12 + 1):
            p.append(v)
            v = v * (1 + np.random.normal(mr, mv)) + contribution_for_month(monthly, growth, m)
        paths.append(p)
    return pd.DataFrame(paths).T


def portfolio_beta(prices, weights, period, demo_mode=False):
    bench = get_stock_data(["SPY"], period, demo_mode)
    combined = prices.join(bench, how="inner", rsuffix="_b")
    r = combined.pct_change().dropna()
    pr = r[prices.columns].dot(weights)
    bcol = "SPY_b" if "SPY_b" in r.columns else "SPY"
    var = np.var(r[bcol])
    return np.cov(pr, r[bcol])[0][1] / var if var else 0


def dividend_reinvest(start, monthly, er, dy, dg, cg, years):
    mpr = er / 12
    vw = vwo = start
    rows = []
    for m in range(years * 12 + 1):
        y = m / 12
        c = contribution_for_month(monthly, cg, m)
        rows.append({"Year": y, "With Reinvestment": vw, "Without Reinvestment": vwo})
        cdy = dy * ((1 + dg) ** y)
        vw = vw * (1 + mpr) + c + vw * (cdy / 12)
        vwo = vwo * (1 + mpr) + c
    return pd.DataFrame(rows)


def weighted_yield(ddf, tickers, weights):
    ys = []
    for t in tickers:
        row = ddf[ddf["Ticker"] == t]
        ys.append(float(row["Dividend Yield"].iloc[0]) if not row.empty else 0)
    return float(np.dot(weights, np.array(ys)))


def stress_test(weights):
    sc = {"COVID-style shock": -0.20, "2022 rate shock": -0.18, "Trade war": -0.16,
          "Geopolitical crisis": -0.22, "Mild recession": -0.10, "Strong bull market": 0.15}
    return pd.DataFrame({"Scenario": list(sc.keys()), "Estimated Impact": [f"{v * np.sum(weights):.2%}" for v in sc.values()]})


def recent_return(prices, weights, days=90):
    try:
        port = prices.pct_change().dropna().dot(weights)
        return float((1 + port.tail(days)).prod() - 1)
    except Exception:
        return 0.0


def advisor_bullets(risk, horizon, score, vol, sharpe, allocation, market_label, dy):
    r = [f"Your risk score is {score}/100 — a {risk.lower()} investor profile."]
    r.append("Your long horizon supports more equity since you can ride out volatility." if horizon >= 10 else "Your shorter horizon favors a more defensive mix.")
    r.append("Volatility is high; defensive assets could help." if vol > 0.30 else ("Volatility is low, limiting both risk and growth." if vol < 0.15 else "Volatility looks balanced."))
    r.append("Strong Sharpe ratio — good reward for the risk." if sharpe > 1 else ("Weak Sharpe ratio — the mix may not reward its risk well." if sharpe < 0.5 else "Reasonable Sharpe ratio."))
    r.append("Meaningful dividend income that compounds if reinvested." if dy > 0.03 else "Growth here comes mainly from price appreciation.")
    r.append(f"Markets are currently {market_label.lower()}, which the plan accounts for." if market_label else "Market-conditions data is unavailable right now.")
    r.append(f"Recommended balance: {allocation['Equity']}% equities, {allocation['Bonds / Fixed Income']}% bonds, {allocation['Cash']}% cash.")
    return r


# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg,#EAFBF2 0%,#FFFFFF 34%,#F4F8FC 100%); color:#102A43; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top:3.5rem; max-width:1180px; }
.land-hero { text-align:center; padding:18px 0 6px; }
.land-logo { font-size:18px; font-weight:900; color:#047857; letter-spacing:.3px; }
.land-title { font-size:42px; font-weight:900; color:#062E2E; line-height:1.08; margin-top:8px; }
.land-sub { font-size:17px; color:#42606A; margin-top:10px; }
.acct-bar { display:flex; align-items:center; justify-content:space-between; background:#FFFFFF; border:1px solid #E3EAF0; border-radius:18px; padding:12px 20px; box-shadow:0 8px 24px rgba(16,42,67,0.06); margin-bottom:14px; }
.acct-name { font-size:15px; font-weight:800; color:#102A43; }
.acct-val { font-size:14px; font-weight:800; color:#047857; }
.home-wrap { max-width:680px; margin:0 auto; }
.home-card { background:#FFFFFF; border:1px solid #E3EAF0; border-radius:28px; padding:30px; box-shadow:0 12px 32px rgba(16,42,67,0.07); margin-bottom:14px; }
.home-label { font-size:14px; color:#52616B; margin-bottom:6px; }
.value-big { font-size:48px; font-weight:900; color:#062E2E; letter-spacing:-1px; line-height:1; }
.gain-pos { color:#047857; font-weight:800; font-size:15px; }
.gain-neg { color:#B91C1C; font-weight:800; font-size:15px; }
.home-sub { font-size:14px; color:#52616B; margin-top:6px; }
.pill-ok { display:inline-block; background:#BBF7D0; color:#065F46; padding:5px 14px; border-radius:999px; font-size:13px; font-weight:800; }
.pill-warn { display:inline-block; background:#FED7AA; color:#9A3412; padding:5px 14px; border-radius:999px; font-size:13px; font-weight:800; }
.bar-track { height:10px; background:#EEF2F6; border-radius:999px; overflow:hidden; margin:14px 0 6px; }
.bar-fill { height:100%; background:linear-gradient(90deg,#10B981,#0EA5E9); border-radius:999px; }
.home-advisor { background:linear-gradient(135deg,#ECFDF5,#EFF6FF); border:1px solid #BBF7D0; border-radius:18px; padding:16px 18px; font-size:15px; line-height:1.55; color:#0F5132; margin-top:16px; }
.ai-tag { display:inline-block; background:#EDE9FE; color:#5B21B6; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:800; }
.hold { display:flex; align-items:center; gap:12px; padding:10px 0; border-bottom:1px solid #F0F3F7; }
.hold-tk { font-weight:900; color:#102A43; width:64px; }
.hold-bartrack { flex:1; height:8px; background:#EEF2F6; border-radius:999px; overflow:hidden; }
.hold-barfill { height:100%; background:linear-gradient(90deg,#10B981,#0EA5E9); border-radius:999px; }
.hold-w { width:48px; text-align:right; font-weight:800; color:#0EA5E9; }
.hold-reason { font-size:13px; color:#52616B; margin:0 0 8px 76px; }
.brand { font-size:15px; font-weight:800; color:#047857; }
.feature-card { background:#FFFFFF; padding:20px; border-radius:22px; border:1px solid #E3EAF0; box-shadow:0 12px 32px rgba(16,42,67,0.07); margin-bottom:14px; }
.card-title { font-size:20px; font-weight:850; color:#102A43; margin-bottom:4px; }
.card-text { font-size:14px; color:#52616B; }
.accent-box { background:linear-gradient(135deg,#ECFDF5,#EFF6FF); border:1px solid #D7F2E4; padding:16px; border-radius:18px; margin-bottom:12px; }
.advisor-box { background:linear-gradient(135deg,#ECFDF5,#EFF6FF); border:1px solid #BBF7D0; padding:22px; border-radius:22px; font-size:16px; line-height:1.6; }
div[data-testid="stMetric"] { background:#FFFFFF; border:1px solid #E3EAF0; padding:16px; border-radius:18px; box-shadow:0 10px 26px rgba(16,42,67,0.06); }
.stTabs [data-baseweb="tab-list"] { gap:10px; background:#FFFFFF; padding:8px; border-radius:999px; border:1px solid #E3EAF0; margin-bottom:18px; }
.stTabs [data-baseweb="tab"] { height:44px; padding:8px 26px; border-radius:999px; color:#102A43; font-weight:800; }
.stTabs [aria-selected="true"] { background:linear-gradient(135deg,#10B981,#0EA5E9) !important; color:white !important; }
.stButton > button { background:linear-gradient(135deg,#10B981,#0EA5E9); color:white; border:none; border-radius:999px; padding:0.6rem 1.3rem; font-weight:800; }
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
ss = st.session_state
ss.setdefault("user", None)
ss.setdefault("view", "home")
ss.setdefault("onb_active", False)
ss.setdefault("onb_step", 1)
for k in ("auto_deposit", "auto_rebalance", "auto_dividend", "auto_tlh"):
    ss.setdefault(k, True)
ANS_DEFAULTS = {"ans_name": "", "ans_goal": "Retirement", "ans_target": 1000000, "ans_age": 28,
                "ans_income": 60000, "ans_horizon": 30, "ans_monthly": 1000, "ans_risk": "Moderate",
                "ans_opening": 10000}
for k, v in ANS_DEFAULTS.items():
    ss.setdefault(k, v)

try:
    ANTHROPIC_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    ANTHROPIC_KEY = None


def seed_keys(a):
    ss["k_goal"] = a.get("goal", "Retirement")
    ss["k_target"] = int(a.get("target", 1000000))
    ss["k_age"] = int(a.get("age", 28))
    ss["k_income"] = int(a.get("income", 60000))
    ss["k_monthly"] = int(a.get("monthly", 1000))
    ss["k_risk"] = a.get("risk", "Moderate")
    ss["k_horizon"] = int(a.get("horizon", 30))
    ss["k_salary"] = int(a.get("salary_growth", 5))
    for k in ("auto_deposit", "auto_rebalance", "auto_dividend", "auto_tlh"):
        ss[k] = a.get(k, True)
    ss["use_own_tickers"] = a.get("use_own", False)
    ss["k_tickers"] = a.get("tickers", "AAPL, MSFT, NVDA, SPY, VYM")
    ss["k_weights"] = a.get("weights_text", "")


# ================= LOGIN / ONBOARDING =================
if ss.user is None:
    st.markdown("""
    <div class="land-hero">
        <div class="land-logo">FinPilot AI</div>
        <div class="land-title">Investing on autopilot.</div>
        <div class="land-sub">Answer a few questions and your AI advisor builds, funds, and tracks a portfolio for you.</div>
    </div>""", unsafe_allow_html=True)

    cl, cc, cr = st.columns([1, 4, 1])
    with cc:
        if not ss.onb_active:
            tab_start, tab_login = st.tabs(["Get started", "Log in"])
            with tab_start:
                with card():
                    st.write("New here? Open an account in under a minute and we'll build your portfolio.")
                    if st.button("Get started", use_container_width=True):
                        for wk in [k for k in ss.keys() if k.startswith("w_")]:
                            del ss[wk]
                        for k, v in ANS_DEFAULTS.items():
                            ss[k] = v
                        ss.onb_active = True
                        ss.onb_step = 1
                        _rerun()
            with tab_login:
                with card():
                    existing = list_accounts()
                    if existing:
                        st.write("Welcome back — choose your account.")
                        for nm in existing:
                            if st.button(f"Log in as {nm}", key=f"login_{nm}", use_container_width=True):
                                seed_keys(load_account(nm))
                                ss.user = nm
                                ss.view = "home"
                                _rerun()
                    else:
                        st.caption("No accounts yet — use Get started to create one.")
            st.caption("Educational prototype only. Not financial advice.")
            st.stop()

        # onboarding wizard: each input uses a stable w_ key seeded from the saved ans_ value,
        # so values don't lag and still survive moving between steps.
        step = ss.onb_step
        with card():
            st.caption(f"Step {step} of 4")
            if step == 1:
                st.subheader("Let's build your plan")
                ss.setdefault("w_name", ss.ans_name)
                ss.ans_name = st.text_input("What should we call you?", key="w_name", placeholder="Your name")
                ss.setdefault("w_goal", ss.ans_goal)
                ss.ans_goal = st.selectbox("What are you investing for?", GOALS, key="w_goal")
                ss.setdefault("w_target", int(ss.ans_target))
                ss.ans_target = st.number_input("Target amount ($)", min_value=0, step=50000, key="w_target")
            elif step == 2:
                st.subheader("A little about you")
                c1, c2 = st.columns(2)
                with c1:
                    ss.setdefault("w_age", int(ss.ans_age))
                    ss.ans_age = st.number_input("Age", 18, 100, key="w_age")
                    ss.setdefault("w_income", int(ss.ans_income))
                    ss.ans_income = st.number_input("Annual income ($)", min_value=0, step=5000, key="w_income")
                with c2:
                    ss.setdefault("w_horizon", int(ss.ans_horizon))
                    ss.ans_horizon = st.slider("Years until your goal", 1, 40, key="w_horizon")
                    ss.setdefault("w_monthly", int(ss.ans_monthly))
                    ss.ans_monthly = st.number_input("Monthly contribution ($)", min_value=0, step=100, key="w_monthly")
            elif step == 3:
                st.subheader("How do you feel about risk?")
                ss.setdefault("w_risk", ss.ans_risk)
                ss.ans_risk = st.radio("Pick what sounds most like you", RISKS, key="w_risk",
                                       captions=["Protect what I have — smaller swings", "A balance of growth and safety", "Grow as much as possible — I can handle big swings"])
            else:
                st.subheader("Fund your account")
                st.write("How much would you like to start with? You can add more anytime.")
                ss.setdefault("w_opening", int(ss.ans_opening))
                ss.ans_opening = st.number_input("Opening deposit ($)", min_value=0, step=1000, key="w_opening")

            b1, b2 = st.columns(2)
            with b1:
                if step > 1 and st.button("Back", use_container_width=True):
                    ss.onb_step -= 1
                    _rerun()
            with b2:
                if step < 4:
                    if st.button("Continue", use_container_width=True):
                        ss.onb_step += 1
                        _rerun()
                else:
                    if st.button("Build my portfolio", use_container_width=True):
                        name = ss.ans_name or "Investor"
                        opening = int(ss.ans_opening)
                        acct = {
                            "name": name, "created": dt.date.today().isoformat(),
                            "goal": ss.ans_goal, "target": int(ss.ans_target), "age": int(ss.ans_age),
                            "income": int(ss.ans_income), "monthly": int(ss.ans_monthly), "risk": ss.ans_risk,
                            "horizon": int(ss.ans_horizon), "salary_growth": 5, "invested": opening,
                            "transactions": [{"date": dt.date.today().isoformat(), "type": "Opening deposit", "amount": opening}],
                            "auto_deposit": True, "auto_rebalance": True, "auto_dividend": True, "auto_tlh": True,
                            "use_own": False, "tickers": "AAPL, MSFT, NVDA, SPY, VYM", "weights_text": "",
                        }
                        prof = {"age": acct["age"], "risk": acct["risk"], "horizon": acct["horizon"], "goal": acct["goal"], "monthly": acct["monthly"]}
                        with st.spinner("Your AI advisor is building your portfolio…"):
                            ai = build_ai_portfolio(ANTHROPIC_KEY, prof)
                        acct["portfolio_source"] = "ai" if ai else "model"
                        acct["ai_portfolio"] = ai if ai else build_smart_portfolio(prof)
                        acct["built_for"] = {"risk": acct["risk"], "horizon": acct["horizon"], "age": acct["age"]}
                        save_account(acct)
                        seed_keys(acct)
                        ss.user = name
                        ss.onb_active = False
                        ss.view = "home"
                        _rerun()
    st.caption("Educational prototype only. Not financial advice.")
    st.stop()


# ================= LOGGED IN =================
acct = load_account(ss.user) or {}
name = ss.user

st.sidebar.title("Settings")
st.sidebar.header("Goal")
goal_name = st.sidebar.selectbox("Investing for", GOALS, key="k_goal")
goal_target = int(st.sidebar.number_input("Target ($)", min_value=0, step=50000, key="k_target"))
st.sidebar.header("About you")
age = int(st.sidebar.number_input("Age", 18, 100, key="k_age"))
income = int(st.sidebar.number_input("Annual income ($)", min_value=0, step=5000, key="k_income"))
monthly = int(st.sidebar.number_input("Monthly contribution ($)", min_value=0, step=100, key="k_monthly"))
risk_tol = st.sidebar.selectbox("Risk comfort", RISKS, key="k_risk")
horizon = int(st.sidebar.slider("Years until goal", 1, 40, key="k_horizon"))
salary_growth = st.sidebar.slider("Annual salary growth (%)", 0, 20, key="k_salary") / 100
contribution_growth = salary_growth
with st.sidebar.expander("Advanced settings"):
    use_own = st.checkbox("Use my own tickers", key="use_own_tickers")
    ticker_input = st.text_input("Tickers", key="k_tickers") if use_own else "VTI, BND, BIL"
    weights_text = st.text_input("Weights % (optional)", key="k_weights") if use_own else ""
    period = st.selectbox("Market data period", ["6mo", "1y", "2y", "5y"], index=1)
    risk_free_rate = st.number_input("Risk-free rate (%)", 0.0, 10.0, 4.3, 0.1) / 100
    demo_mode = st.checkbox("Demo mode (saved data)", value=False)
if st.sidebar.button("Log out"):
    ss.user = None
    _rerun()

auto_deposit_on = ss.get("auto_deposit", True)
effective_monthly = monthly if auto_deposit_on else 0
assumed_return = {"Conservative": 0.05, "Moderate": 0.07, "Aggressive": 0.09}[risk_tol]
allocation = recommend_allocation(age, risk_tol, horizon)
score = risk_score(age, risk_tol, horizon, monthly, income)

acct.update({"goal": goal_name, "target": goal_target, "age": age, "income": income, "monthly": monthly,
             "risk": risk_tol, "horizon": horizon, "salary_growth": int(salary_growth * 100),
             "auto_deposit": ss.get("auto_deposit", True), "auto_rebalance": ss.get("auto_rebalance", True),
             "auto_dividend": ss.get("auto_dividend", True), "auto_tlh": ss.get("auto_tlh", True),
             "use_own": ss.get("use_own_tickers", False), "tickers": ss.get("k_tickers", ""), "weights_text": ss.get("k_weights", "")})
save_account(acct)

invested = float(acct.get("invested", 0))
transactions = acct.get("transactions", [])
ai_port = acct.get("ai_portfolio")
port_source = acct.get("portfolio_source", "model")

# Rebuild the portfolio when it's missing OR when the inputs that should drive it have changed.
profile_key = {"risk": risk_tol, "horizon": horizon, "age": age}
needs_build = (not ss.get("use_own_tickers", False)) and (ai_port is None or acct.get("built_for") != profile_key)
if needs_build:
    prof = {"age": age, "risk": risk_tol, "horizon": horizon, "goal": goal_name, "monthly": monthly}
    # Keep it AI-built if this account uses AI and a key is available; otherwise re-tilt instantly with the model.
    built = build_ai_portfolio(ANTHROPIC_KEY, prof) if (ANTHROPIC_KEY and port_source == "ai") else None
    port_source = "ai" if built else "model"
    ai_port = built if built else build_smart_portfolio(prof)
    acct["ai_portfolio"] = ai_port
    acct["portfolio_source"] = port_source
    acct["built_for"] = profile_key
    save_account(acct)

mc_read = market_conditions(demo_mode)
market_label = mc_read["label"] if mc_read else None

prices, weights, tickers, perf, portfolio_summary, ai_built = None, None, [], 0.0, "", False
try:
    if ss.use_own_tickers:
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
        prices = get_stock_data(tickers, period, demo_mode)
        tickers = list(prices.columns)
        weights = parse_weights(weights_text, tickers)
    elif ai_port and ai_port.get("holdings"):
        want = [h["ticker"] for h in ai_port["holdings"]]
        prices = get_stock_data(want, period, demo_mode)
        tickers = [t for t in want if t in prices.columns]
        prices = prices[tickers]
        wmap = {h["ticker"]: h["weight"] for h in ai_port["holdings"]}
        w = np.array([wmap[t] for t in tickers], dtype=float)
        weights = w / w.sum()
        portfolio_summary = ai_port.get("summary", "")
        ai_built = True
    else:
        rec = recommended_portfolio(allocation, ["VTI"])
        want = list(rec.keys())
        prices = get_stock_data(want, period, demo_mode)
        tickers = [t for t in want if t in prices.columns]
        prices = prices[tickers]
        w = np.array([rec[t] for t in tickers], dtype=float)
        weights = w / w.sum()
    perf = recent_return(prices, weights)
except Exception:
    prices = None

current_value = invested * (1 + perf)
gain = current_value - invested
home_proj = wealth_projection(current_value, effective_monthly, assumed_return, horizon, contribution_growth)
projected_value = float(home_proj["Projected Value"].iloc[-1])
on_track = projected_value >= goal_target
now_str = dt.datetime.now().strftime("%b %d, %I:%M %p")


# ================= HOME =================
if ss.view == "home":
    bar1, bar2 = st.columns([4, 1])
    with bar1:
        st.markdown(f'<div class="acct-bar"><span class="acct-name">{name}\'s account</span><span class="acct-val">Total value {money(current_value)}</span></div>', unsafe_allow_html=True)
    with bar2:
        if st.button("↻ Refresh", use_container_width=True):
            st.cache_data.clear()
            _rerun()

    pct = (projected_value / goal_target) if goal_target > 0 else 1.0
    bar_pct = min(max(pct, 0.0), 1.0) * 100
    gcls = "gain-pos" if gain >= 0 else "gain-neg"
    gsign = "+" if gain >= 0 else "−"
    pill = '<span class="pill-ok">On track</span>' if on_track else '<span class="pill-warn">Needs a nudge</span>'
    ai_chip = ('<span class="ai-tag">AI-built</span>' if port_source == "ai" else '<span class="ai-tag">Auto-built</span>') if ai_built else ''
    if on_track:
        adv = f"You're on track to reach your {goal_name.lower()} goal of {money_short(goal_target)}. Keeping your {money(monthly)}/month deposit going gets you there with room to spare."
    else:
        adv = f"You're projected to reach {money_short(projected_value)} — a little under your {money_short(goal_target)} goal. Raising your monthly deposit or extending your timeline closes the gap."

    st.markdown(f"""
    <div class="home-wrap"><div class="home-card">
      <div class="home-label">Portfolio value &nbsp; {ai_chip}</div>
      <div class="value-big">{money(current_value)}</div>
      <div class="{gcls}">{gsign}{money(abs(gain))} ({perf:+.1%}) on {money(invested)} invested</div>
      <div class="bar-track"><div class="bar-fill" style="width:{bar_pct:.0f}%;"></div></div>
      <div class="home-sub">{pill} &nbsp; Projected {money_short(projected_value)} toward your {money_short(goal_target)} goal in {horizon} years</div>
      <div class="home-advisor">{adv}</div>
    </div></div>""", unsafe_allow_html=True)

    fig_home = px.area(home_proj, x="Year", y="Projected Value", color_discrete_sequence=["#10B981"])
    fig_home.update_layout(height=240, showlegend=False, xaxis_title=None, yaxis_title=None, title=None)
    st.plotly_chart(apply_clean_theme(fig_home), use_container_width=True)
    st.caption(f"Prices refresh automatically every few minutes · last loaded {now_str}")

    ad1, ad2 = st.columns([2, 1])
    with ad1:
        dep = st.number_input("Add money to your account ($)", min_value=0, value=0, step=500, key="dep_amt")
    with ad2:
        st.write("")
        st.write("")
        if st.button("Deposit", use_container_width=True):
            if dep > 0:
                acct["invested"] = invested + dep
                acct.setdefault("transactions", []).append({"date": dt.date.today().isoformat(), "type": "Deposit", "amount": int(dep)})
                save_account(acct)
                st.success(f"Added {money(dep)} to your account.")
                _rerun()

    st.markdown("#### Automation — set it and forget it")
    a1, a2 = st.columns(2)
    with a1:
        toggle(f"Automatic deposits — {money(monthly)}/mo", "auto_deposit")
        toggle("Auto-rebalance — quarterly", "auto_rebalance")
    with a2:
        toggle("Reinvest dividends automatically", "auto_dividend")
        toggle("Tax-loss harvesting", "auto_tlh")
    notes = ["Deposits run automatically each month." if ss.auto_deposit else "Automatic deposits are paused."]
    if ss.auto_rebalance:
        notes.append("Rebalanced to target each quarter.")
    if ss.auto_tlh:
        notes.append(f"Tax-loss harvesting could save ~{money_short(current_value * 0.008)}/yr (rough estimate).")
    st.caption("  •  ".join(notes))

    if transactions:
        with st.expander("Recent activity"):
            tdf = pd.DataFrame(transactions)[::-1].head(10).copy()
            tdf["amount"] = tdf["amount"].apply(money)
            tdf.columns = ["Date", "Type", "Amount"]
            st.dataframe(tdf, use_container_width=True, hide_index=True)

    s1, s2, s3 = st.columns([1, 2, 1])
    with s2:
        if st.button("See detailed analytics →", use_container_width=True):
            ss.view = "advanced"
            _rerun()
    st.caption("Adjust your goal, deposit, and risk in Settings (top-left ›). Educational prototype only. Not financial advice.")
    st.stop()


# ================= ANALYTICS =================
bb1, bb2 = st.columns([4, 1])
with bb1:
    if st.button("← Back to home"):
        ss.view = "home"
        _rerun()
with bb2:
    if st.button("↻ Refresh", use_container_width=True):
        st.cache_data.clear()
        _rerun()

st.markdown(f'<div class="acct-bar"><span class="acct-name">{name}\'s account · detailed analytics</span><span class="acct-val">{money(current_value)}</span></div>', unsafe_allow_html=True)

if prices is None or prices.empty:
    st.warning("Market data is taking a moment to load. Hit Refresh, or switch on Demo mode in Settings → Advanced.")
    st.stop()

try:
    normalized = prices / prices.iloc[0] * 100
    er, vol, sharpe, returns = portfolio_metrics(prices, weights, risk_free_rate)
    adj = mc_read["return_adjustment"] if mc_read else 0.0
    mult = mc_read["volatility_multiplier"] if mc_read else 1.0
    adj_return, adj_vol = er + adj, vol * mult
    try:
        ddf = get_dividend_data(tickers, prices, demo_mode)
        port_dy = weighted_yield(ddf, tickers, weights)
    except Exception:
        ddf, port_dy = pd.DataFrame({"Ticker": tickers, "Dividend Yield": 0}), 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Account Value", money(current_value))
    m2.metric("Expected Return", f"{er:.2%}")
    m3.metric("Dividend Yield", f"{port_dy:.2%}")
    m4.metric("Market Conditions", market_label or "—")

    tab_plan, tab_invest, tab_track = st.tabs(["Plan", "Invest", "Track"])

    with tab_plan:
        st.markdown('<div class="feature-card"><div class="card-title">Your plan</div><div class="card-text">Target balance and projection for your goal.</div></div>', unsafe_allow_html=True)
        adf = pd.DataFrame({"Asset Class": list(allocation.keys()), "Allocation (%)": list(allocation.values())})
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(adf, use_container_width=True, hide_index=True)
        with c2:
            st.plotly_chart(apply_clean_theme(px.pie(adf, names="Asset Class", values="Allocation (%)", hole=0.55, title="Target Balance", color_discrete_sequence=COLORS)), use_container_width=True)
        pr = st.slider("Planning return assumption (%)", 1, 15, int(assumed_return * 100)) / 100
        proj = wealth_projection(current_value, effective_monthly, pr, horizon, contribution_growth)
        sched = income_schedule(income, monthly, salary_growth, contribution_growth, horizon)
        p1, p2, p3 = st.columns(3)
        p1.metric("Projected Value", money_short(proj['Projected Value'].iloc[-1]))
        p2.metric("Final Monthly Contribution", money(proj['Monthly Contribution'].iloc[-1]))
        p3.metric("Final Projected Salary", money_short(sched['Projected Salary'].iloc[-1]))
        st.plotly_chart(apply_clean_theme(px.area(proj, x="Year", y="Projected Value", title="Projected Wealth Growth", color_discrete_sequence=["#10B981"])), use_container_width=True)
        with st.expander("Income & contribution schedule"):
            d = sched.copy()
            for col in ["Projected Salary", "Monthly Contribution", "Annual Contribution"]:
                d[col] = d[col].apply(money)
            d["Contribution Rate"] = d["Contribution Rate"].apply(lambda x: f"{x:.1%}")
            st.dataframe(d, use_container_width=True, hide_index=True)

    with tab_invest:
        if ss.use_own_tickers:
            src = "your own tickers"
        elif port_source == "ai":
            src = "your AI advisor"
        else:
            src = "FinPilot's model"
        st.markdown(f'<div class="feature-card"><div class="card-title">Your portfolio</div><div class="card-text">Built by {src}.</div></div>', unsafe_allow_html=True)

        strategy_tag = "AI strategy" if port_source == "ai" else "Strategy"
        if ai_built and portfolio_summary:
            st.markdown(f'<div class="advisor-box"><span class="ai-tag">{strategy_tag}</span><br><br>{portfolio_summary}</div>', unsafe_allow_html=True)

        if ai_built and ai_port.get("holdings"):
            st.write("")
            for h in ai_port["holdings"]:
                if h["ticker"] in tickers:
                    st.markdown(f'<div class="hold"><div class="hold-tk">{h["ticker"]}</div><div class="hold-bartrack"><div class="hold-barfill" style="width:{min(h["weight"],100):.0f}%"></div></div><div class="hold-w">{h["weight"]:.0f}%</div></div><div class="hold-reason">{h.get("reason","")}</div>', unsafe_allow_html=True)
        else:
            wdf = pd.DataFrame({"Holding": tickers, "Weight": [f"{w:.1%}" for w in weights]})
            st.dataframe(wdf, use_container_width=True, hide_index=True)

        rebuild_label = "↻ Regenerate portfolio with AI" if ANTHROPIC_KEY else "↻ Rebuild my portfolio"
        if not ss.use_own_tickers and st.button(rebuild_label):
            prof = {"age": age, "risk": risk_tol, "horizon": horizon, "goal": goal_name, "monthly": monthly}
            with st.spinner("Rebuilding your portfolio…"):
                ai = build_ai_portfolio(ANTHROPIC_KEY, prof)
            acct["portfolio_source"] = "ai" if ai else "model"
            acct["ai_portfolio"] = ai if ai else build_smart_portfolio(prof)
            acct["built_for"] = {"risk": risk_tol, "horizon": horizon, "age": age}
            save_account(acct)
            _rerun()
        if not ANTHROPIC_KEY:
            st.caption("Add an Anthropic API key in secrets to have a live AI build this instead of the rule-based model.")

        im1, im2, im3, im4 = st.columns(4)
        im1.metric("Expected Return", f"{er:.2%}")
        im2.metric("Volatility", f"{vol:.2%}")
        im3.metric("Sharpe Ratio", f"{sharpe:.2f}")
        im4.metric("Health Score", f"{health_score(len(tickers), vol, sharpe)}/100")

        fig_g = go.Figure()
        for i, tk in enumerate(normalized.columns):
            fig_g.add_trace(go.Scatter(x=normalized.index, y=normalized[tk], mode="lines", name=tk, line=dict(width=3, color=COLORS[i % len(COLORS)])))
        try:
            bn = get_stock_data(["SPY"], period, demo_mode)
            bn = bn / bn.iloc[0] * 100
            fig_g.add_trace(go.Scatter(x=bn.index, y=bn["SPY"], mode="lines", name="S&P 500", line=dict(width=3, dash="dash", color="#111827")))
        except Exception:
            pass
        fig_g.update_layout(title="Growth of $100 vs S&P 500", xaxis_title="Date", yaxis_title="Indexed Value")
        st.plotly_chart(apply_clean_theme(fig_g), use_container_width=True)

        if len(tickers) >= 2:
            with st.expander("How your holdings move together"):
                st.plotly_chart(apply_clean_theme(px.imshow(returns.corr(), text_auto=True, title="Correlation Matrix", color_continuous_scale=["#10B981", "#FFFFFF", "#EF4444"])), use_container_width=True)
            with st.expander("Optimize this portfolio"):
                if st.button("Run optimization"):
                    ports = random_portfolios(prices)
                    best = ports.loc[ports["Sharpe"].idxmax()]
                    st.dataframe(pd.DataFrame({"Ticker": prices.columns, "Max Sharpe (%)": (best["Weights"] * 100).round(1)}), use_container_width=True, hide_index=True)
                    fig_f = px.scatter(ports, x="Volatility", y="Return", color="Sharpe", title="Efficient Frontier", color_continuous_scale="Viridis")
                    fig_f.add_trace(go.Scatter(x=[best["Volatility"]], y=[best["Return"]], mode="markers", marker=dict(size=18, symbol="star", color="#F59E0B"), name="Max Sharpe"))
                    st.plotly_chart(apply_clean_theme(fig_f), use_container_width=True)

    with tab_track:
        st.markdown('<div class="feature-card"><div class="card-title">Are you on track?</div><div class="card-text">Progress, market conditions, income, and protection.</div></div>', unsafe_allow_html=True)
        tk1, tk2, tk3 = st.columns(3)
        tk1.metric("Projected at Goal", money_short(projected_value))
        tk2.metric("Your Target", money_short(goal_target))
        tk3.metric("Status", "On track" if on_track else "Needs a nudge")
        if mc_read:
            st.markdown(f'<div class="accent-box"><b>Market conditions: {mc_read["label"]}.</b> {mc_read["explanation"]} Read automatically — nothing to set.</div>', unsafe_allow_html=True)
        with st.expander("Project future outcomes (Monte Carlo)"):
            if st.button("Run simulation"):
                mc = monte_carlo(current_value, effective_monthly, adj_return, adj_vol, horizon, contribution_growth, sims=500)
                fv = mc.iloc[-1]
                s1, s2, s3 = st.columns(3)
                s1.metric("Pessimistic (10th)", money_short(np.percentile(fv, 10)))
                s2.metric("Expected (median)", money_short(np.percentile(fv, 50)))
                s3.metric("Optimistic (90th)", money_short(np.percentile(fv, 90)))
                fig_mc = go.Figure()
                for i in range(min(50, mc.shape[1])):
                    fig_mc.add_trace(go.Scatter(y=mc.iloc[:, i], mode="lines", opacity=0.22, line=dict(color="#10B981"), showlegend=False))
                fig_mc.update_layout(title="Possible paths (adjusted for market conditions)", xaxis_title="Months", yaxis_title="Value")
                st.plotly_chart(apply_clean_theme(fig_mc), use_container_width=True)
        with st.expander("Dividend income"):
            di1, di2 = st.columns(2)
            di1.metric("Portfolio Yield", f"{port_dy:.2%}")
            di2.metric("Est. Annual Income", money_short(current_value * port_dy))
            if ss.auto_dividend:
                dg = st.slider("Assumed dividend growth (%)", 0, 10, 3) / 100
                dp = dividend_reinvest(current_value, effective_monthly, er, port_dy, dg, contribution_growth, horizon)
                fig_d = go.Figure()
                fig_d.add_trace(go.Scatter(x=dp["Year"], y=dp["With Reinvestment"], mode="lines", name="Reinvested", line=dict(width=4, color="#10B981")))
                fig_d.add_trace(go.Scatter(x=dp["Year"], y=dp["Without Reinvestment"], mode="lines", name="Not reinvested", line=dict(width=4, dash="dash", color="#0EA5E9")))
                fig_d.update_layout(title="Reinvesting dividends vs not", xaxis_title="Year", yaxis_title="Value")
                st.plotly_chart(apply_clean_theme(fig_d), use_container_width=True)
            else:
                st.caption("Dividend reinvestment is off in your automation settings.")
        with st.expander("Downside protection"):
            try:
                beta = portfolio_beta(prices, weights, period, demo_mode)
                bp1, bp2 = st.columns(2)
                bp1.metric("Beta vs S&P 500", f"{beta:.2f}")
                bp2.metric("Volatility", f"{vol:.2%}")
            except Exception:
                st.caption("Beta unavailable right now.")
            st.dataframe(stress_test(weights), use_container_width=True, hide_index=True)

    st.markdown('<div class="feature-card"><div class="card-title">AI Advisor Summary</div><div class="card-text">A plain-English read on your plan.</div></div>', unsafe_allow_html=True)
    recs = advisor_bullets(risk_tol, horizon, score, vol, sharpe, allocation, market_label, port_dy)
    for r in recs:
        st.markdown(f"- {r}")

except Exception:
    st.warning("Something went wrong loading the analytics. Hit Refresh, or switch on Demo mode in Settings → Advanced.")

st.divider()
st.caption("Built with Streamlit, yfinance, pandas, numpy, and plotly. Educational prototype only. Not financial advice.")
