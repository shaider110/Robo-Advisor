import os
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="FinPilot AI", layout="wide")

CACHE_DIR = "market_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

COLORS = ["#10B981", "#0EA5E9", "#8B5CF6", "#F59E0B", "#EF4444", "#14B8A6", "#6366F1"]
GOALS = ["Retirement", "A home", "Education", "Building wealth"]


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


# ---------------- SESSION DEFAULTS ----------------
ss = st.session_state
ss.setdefault("onboarded", False)
ss.setdefault("onb_step", 1)
ss.setdefault("view", "home")
ss.setdefault("k_name", "")
ss.setdefault("k_goal", "Retirement")
ss.setdefault("k_target", 1000000)
ss.setdefault("k_extra", 0)
ss.setdefault("k_age", 28)
ss.setdefault("k_income", 60000)
ss.setdefault("k_savings", 10000)
ss.setdefault("k_monthly", 1000)
ss.setdefault("k_risk", "Moderate")
ss.setdefault("k_horizon", 30)
ss.setdefault("auto_deposit", True)
ss.setdefault("auto_rebalance", True)
ss.setdefault("auto_dividend", True)
ss.setdefault("auto_tlh", True)
ss.setdefault("use_own_tickers", False)

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #F1FBF6 0%, #FFFFFF 38%, #F6F8FB 100%); color: #102A43; }
.block-container { padding-top: 1.5rem; max-width: 1250px; }
.hero { background: linear-gradient(135deg, #DFF7EA 0%, #EAF4FF 55%, #FFFFFF 100%); padding: 38px; border-radius: 30px; border: 1px solid #D8EEE4; box-shadow: 0 18px 45px rgba(16,42,67,0.08); margin-bottom: 22px; }
.pill { display:inline-block; background:#BFF4D2; color:#065F46; padding:8px 16px; border-radius:999px; font-size:14px; font-weight:800; margin-bottom:14px; }
.hero-title { font-size:40px; font-weight:900; color:#062E2E; line-height:1.05; }
.hero-subtitle { font-size:17px; color:#42606A; max-width:820px; margin-top:14px; }
.feature-card { background:#FFFFFF; padding:22px; border-radius:24px; border:1px solid #E3EAF0; box-shadow:0 12px 32px rgba(16,42,67,0.07); margin-bottom:16px; }
.card-title { font-size:21px; font-weight:850; color:#102A43; margin-bottom:6px; }
.card-text { font-size:15px; color:#52616B; }
.accent-box { background:linear-gradient(135deg,#ECFDF5,#EFF6FF); border:1px solid #D7F2E4; padding:16px; border-radius:20px; margin-bottom:14px; }
.advisor-box { background:linear-gradient(135deg,#ECFDF5,#EFF6FF); border:1px solid #BBF7D0; padding:24px; border-radius:24px; margin-bottom:16px; font-size:16px; line-height:1.6; }
.onb-card { background:#FFFFFF; border:1px solid #E3EAF0; border-radius:28px; padding:34px; box-shadow:0 14px 36px rgba(16,42,67,0.08); }
.home-wrap { max-width:640px; margin:0 auto; }
.home-brand { font-size:15px; font-weight:800; color:#047857; margin-bottom:2px; }
.home-welcome { font-size:28px; font-weight:900; color:#062E2E; line-height:1.1; }
.home-tag { font-size:14px; color:#52616B; margin-bottom:12px; }
.home-card { background:#FFFFFF; border:1px solid #E3EAF0; border-radius:28px; padding:30px; box-shadow:0 12px 32px rgba(16,42,67,0.07); margin-bottom:16px; }
.home-goal { font-size:14px; color:#52616B; margin-bottom:8px; }
.home-hero { font-size:46px; font-weight:900; color:#062E2E; letter-spacing:-1px; line-height:1; }
.home-herosub { font-size:14px; color:#52616B; margin-top:4px; }
.chip { display:inline-block; background:#E0F2FE; color:#075985; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:800; margin-left:6px; }
.pill-ok { display:inline-block; background:#BBF7D0; color:#065F46; padding:5px 14px; border-radius:999px; font-size:13px; font-weight:800; }
.pill-warn { display:inline-block; background:#FED7AA; color:#9A3412; padding:5px 14px; border-radius:999px; font-size:13px; font-weight:800; }
.home-bar-track { height:10px; background:#EEF2F6; border-radius:999px; overflow:hidden; margin:14px 0 6px; }
.home-bar-fill { height:100%; background:linear-gradient(90deg,#10B981,#0EA5E9); border-radius:999px; }
.home-deposit { display:flex; align-items:center; gap:10px; border-top:1px solid #EEF2F6; border-bottom:1px solid #EEF2F6; padding:14px 0; margin:16px 0; }
.home-advisor { background:linear-gradient(135deg,#ECFDF5,#EFF6FF); border:1px solid #BBF7D0; border-radius:18px; padding:16px 18px; font-size:15px; line-height:1.55; color:#0F5132; }
div[data-testid="stMetric"] { background:#FFFFFF; border:1px solid #E3EAF0; padding:18px; border-radius:20px; box-shadow:0 10px 26px rgba(16,42,67,0.06); }
.stTabs [data-baseweb="tab-list"] { gap:12px; background:#FFFFFF; padding:10px; border-radius:999px; border:1px solid #E3EAF0; box-shadow:0 10px 30px rgba(16,42,67,0.07); margin-bottom:22px; }
.stTabs [data-baseweb="tab"] { height:48px; padding:10px 24px; border-radius:999px; color:#102A43; font-weight:800; background:transparent; }
.stTabs [aria-selected="true"] { background:linear-gradient(135deg,#10B981,#0EA5E9) !important; color:white !important; box-shadow:0 10px 24px rgba(16,185,129,0.35); }
[data-testid="stSidebar"] { background:#FFFFFF; border-right:1px solid #E3EAF0; }
.stButton > button { background:linear-gradient(135deg,#10B981,#0EA5E9); color:white; border:none; border-radius:999px; padding:0.7rem 1.4rem; font-weight:800; }
</style>
""", unsafe_allow_html=True)

# ---------------- DATA LAYER ----------------

def _safe_name(name):
    return str(name).replace("/", "_").replace("\\", "_").replace(" ", "_")


def _price_path(ticker, period):
    return os.path.join(CACHE_DIR, f"px_{_safe_name(ticker)}_{period}.csv")


def _save_prices_to_cache(df, period):
    for col in df.columns:
        df[[col]].dropna().to_csv(_price_path(col, period))


def _load_prices_from_cache(tickers, period):
    frames = []
    for t in tickers:
        path = _price_path(t, period)
        if not os.path.exists(path):
            raise FileNotFoundError(f"No cached data for {t} ({period}).")
        s = pd.read_csv(path, index_col=0, parse_dates=True)
        s.columns = [t]
        frames.append(s)
    return pd.concat(frames, axis=1).dropna()


@st.cache_data(ttl=3600, show_spinner="Loading market data…")
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
            raise ValueError("Empty download")
        _save_prices_to_cache(raw, period)
        return raw
    except Exception:
        return _load_prices_from_cache(tickers, period)


@st.cache_data(ttl=3600, show_spinner=False)
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
                one_year_ago = divs.index.max() - pd.DateOffset(years=1)
                annual_dividend = float(divs[divs.index >= one_year_ago].sum())
        except Exception:
            annual_dividend = 0.0
        dy = (annual_dividend / last_price) if (last_price and last_price > 0) else 0.0
        rows.append({"Ticker": t, "Last Annual Dividend": annual_dividend, "Estimated Price": last_price, "Dividend Yield": dy})
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def market_conditions(demo_mode=False):
    # Reads current market conditions automatically from the S&P 500 (no manual inputs).
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
    return {"label": label, "ann_vol": ann_vol, "drawdown": drawdown,
            "return_adjustment": adj, "volatility_multiplier": mult,
            "explanation": f"Based on recent S&P 500 volatility of {ann_vol:.0%} and a {abs(drawdown):.0%} pullback from its recent high."}


# ---------------- HELPERS ----------------

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


def apply_clean_theme(fig):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0)",
                      font=dict(color="#102A43"), title_font=dict(size=20, color="#102A43"),
                      margin=dict(l=20, r=20, t=55, b=20), legend=dict(bgcolor="rgba(255,255,255,0)", borderwidth=0))
    return fig


def recommend_allocation(age, risk_tolerance, horizon):
    if risk_tolerance == "Conservative":
        equity = max(20, 100 - age - 20)
    elif risk_tolerance == "Moderate":
        equity = max(30, 110 - age)
    else:
        equity = max(40, 120 - age)
    if horizon < 5:
        equity -= 20
    elif horizon > 15:
        equity += 10
    equity = min(max(equity, 10), 90)
    bonds = max(0, 100 - equity - 5)
    cash = 100 - equity - bonds
    return {"Equity": equity, "Bonds / Fixed Income": bonds, "Cash": cash}


def recommended_portfolio(allocation, equity_tickers):
    sleeves = {"Equity": list(equity_tickers) if equity_tickers else ["VTI"],
               "Bonds / Fixed Income": ["BND"], "Cash": ["BIL"]}
    weights = {}
    for sleeve, pct in allocation.items():
        ts = sleeves.get(sleeve, [])
        if not ts or pct <= 0:
            continue
        share = (pct / 100.0) / len(ts)
        for t in ts:
            weights[t] = weights.get(t, 0.0) + share
    total = sum(weights.values())
    if total > 0:
        weights = {t: w / total for t, w in weights.items()}
    return weights


def risk_score(age, risk_tolerance, horizon, monthly_savings, annual_income):
    score = 50
    score += 15 if age < 30 else (-15 if age > 55 else 0)
    score += 20 if risk_tolerance == "Aggressive" else (-20 if risk_tolerance == "Conservative" else 0)
    score += 15 if horizon > 15 else (-15 if horizon < 5 else 0)
    sr = (monthly_savings * 12) / annual_income if annual_income > 0 else 0
    score += 10 if sr > 0.25 else (-10 if sr < 0.10 else 0)
    return int(min(max(score, 0), 100))


def portfolio_metrics(prices, weights, risk_free_rate=0.0):
    returns = prices.pct_change().dropna()
    annual_returns = returns.mean() * 252
    cov = returns.cov() * 252
    er = np.dot(weights, annual_returns)
    vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
    sharpe = (er - risk_free_rate) / vol if vol != 0 else 0
    return er, vol, sharpe, returns


def portfolio_health_score(num_assets, volatility, sharpe):
    score = 50
    score += 15 if num_assets >= 5 else (-15 if num_assets <= 2 else 0)
    score += 15 if volatility < 0.20 else (-15 if volatility > 0.35 else 0)
    score += 20 if sharpe > 1 else (-10 if sharpe < 0.3 else 0)
    return int(min(max(score, 0), 100))


def contribution_for_month(base, growth, month):
    return base * ((1 + growth) ** (month // 12))


def wealth_projection_with_growth(current_savings, monthly_savings, annual_return, years, contribution_growth_rate):
    months = years * 12
    mr = annual_return / 12
    value = current_savings
    rows = []
    for m in range(months + 1):
        c = contribution_for_month(monthly_savings, contribution_growth_rate, m)
        rows.append({"Month": m, "Year": m / 12, "Monthly Contribution": c, "Projected Value": value})
        value = value * (1 + mr) + c
    return pd.DataFrame(rows)


def income_growth_schedule(annual_income, monthly_savings, salary_growth_rate, contribution_growth_rate, years):
    rows = []
    for y in range(years + 1):
        salary = annual_income * ((1 + salary_growth_rate) ** y)
        mc = monthly_savings * ((1 + contribution_growth_rate) ** y)
        ac = mc * 12
        rows.append({"Year": y, "Projected Salary": salary, "Monthly Contribution": mc,
                     "Annual Contribution": ac, "Contribution Rate": ac / salary if salary > 0 else 0})
    return pd.DataFrame(rows)


def random_portfolios(prices, num_portfolios=3000):
    returns = prices.pct_change().dropna()
    ar = returns.mean() * 252
    cov = returns.cov() * 252
    results = []
    for _ in range(num_portfolios):
        w = np.random.random(len(prices.columns))
        w = w / np.sum(w)
        pr = np.dot(w, ar)
        pv = np.sqrt(np.dot(w.T, np.dot(cov, w)))
        results.append({"Return": pr, "Volatility": pv, "Sharpe": pr / pv if pv != 0 else 0, "Weights": w})
    return pd.DataFrame(results)


def monte_carlo_simulation(start_value, monthly_savings, expected_return, volatility, years, contribution_growth_rate, simulations=500):
    months = years * 12
    mr = expected_return / 12
    mv = volatility / np.sqrt(12)
    paths = []
    for _ in range(simulations):
        value = start_value
        path = []
        for m in range(months + 1):
            path.append(value)
            c = contribution_for_month(monthly_savings, contribution_growth_rate, m)
            value = value * (1 + np.random.normal(mr, mv)) + c
        paths.append(path)
    return pd.DataFrame(paths).T


def calculate_var(returns, weights, portfolio_value, confidence=0.95):
    pr = returns.dot(weights)
    var_pct = np.percentile(pr, (1 - confidence) * 100)
    return var_pct, portfolio_value * abs(var_pct)


def calculate_portfolio_beta(prices, weights, period, demo_mode=False):
    benchmark = get_stock_data(["SPY"], period, demo_mode)
    combined = prices.join(benchmark, how="inner", rsuffix="_benchmark")
    returns = combined.pct_change().dropna()
    pr = returns[prices.columns].dot(weights)
    bcol = "SPY_benchmark" if "SPY_benchmark" in returns.columns else "SPY"
    br = returns[bcol]
    var = np.var(br)
    return np.cov(pr, br)[0][1] / var if var != 0 else 0


def hedge_portfolio_analysis(prices, weights, portfolio_value, period, risk_free_rate=0.0, demo_mode=False):
    cr, cv, cs, returns = portfolio_metrics(prices, weights, risk_free_rate)
    hedge_assets = [a for a in ["BND", "GLD"] if a not in prices.columns]
    if not hedge_assets:
        return None
    hedge_data = get_stock_data(hedge_assets, period, demo_mode)
    combined = prices.join(hedge_data, how="inner")
    if combined.empty:
        return None
    base = list(np.array(weights) * 0.80)
    add = [0.20 / len(hedge_assets)] * len(hedge_assets)
    hw = np.array(base + add)
    hw = hw / hw.sum()
    hr, hv, hs, hret = portfolio_metrics(combined, hw, risk_free_rate)
    _, cva = calculate_var(returns, weights, portfolio_value)
    _, hva = calculate_var(hret, hw, portfolio_value)
    comparison = pd.DataFrame({
        "Metric": ["Expected Annual Return", "Annual Volatility", "Sharpe Ratio", "Daily 95% VaR"],
        "Current": [f"{cr:.2%}", f"{cv:.2%}", f"{cs:.2f}", f"${cva:,.0f}"],
        "Hedged": [f"{hr:.2%}", f"{hv:.2%}", f"{hs:.2f}", f"${hva:,.0f}"]})
    hw_df = pd.DataFrame({"Asset": list(prices.columns) + hedge_assets, "Hedged Weight (%)": hw * 100})
    return comparison, hw_df


def dividend_reinvestment_projection(starting_value, monthly_savings, expected_return, dividend_yield, dividend_growth_rate, contribution_growth_rate, years):
    months = years * 12
    mpr = expected_return / 12
    vw = starting_value
    vwo = starting_value
    adi = starting_value * dividend_yield
    rows = []
    for m in range(months + 1):
        y = m / 12
        c = contribution_for_month(monthly_savings, contribution_growth_rate, m)
        rows.append({"Year": y, "With Dividend Reinvestment": vw, "Without Dividend Reinvestment": vwo, "Estimated Annual Dividend Income": adi})
        cdy = dividend_yield * ((1 + dividend_growth_rate) ** y)
        md = vw * (cdy / 12)
        vw = vw * (1 + mpr) + c + md
        vwo = vwo * (1 + mpr) + c
        adi = vw * cdy
    return pd.DataFrame(rows)


def weighted_dividend_yield(dividend_df, tickers, weights):
    yields = []
    for t in tickers:
        row = dividend_df[dividend_df["Ticker"] == t]
        yields.append(float(row["Dividend Yield"].iloc[0]) if not row.empty else 0)
    return float(np.dot(weights, np.array(yields)))


def stress_test(weights):
    scenarios = {"COVID-style shock": -0.20, "2022 inflation/rate shock": -0.18, "Trade war shock": -0.16,
                 "Geopolitical crisis": -0.22, "Mild recession": -0.10, "Strong bull market": 0.15}
    return pd.DataFrame({"Scenario": list(scenarios.keys()),
                         "Estimated Impact": [f"{s * np.sum(weights):.2%}" for s in scenarios.values()]})


def advisor_bullets(risk_tolerance, horizon, score, volatility, sharpe, allocation, market_label, dividend_yield):
    recs = [f"Your risk score is {score}/100, a {risk_tolerance.lower()} investor profile."]
    recs.append("Your long horizon supports more equity exposure since you can ride out volatility." if horizon >= 10
                else "Your shorter horizon favors a more defensive, capital-protective mix.")
    recs.append("Volatility looks high — defensive assets like bonds or gold could help." if volatility > 0.30
                else ("Volatility is low, which limits risk but also long-term growth." if volatility < 0.15
                      else "Volatility looks balanced for a diversified strategy."))
    recs.append("Your Sharpe ratio is strong — good return for the risk taken." if sharpe > 1
                else ("Your Sharpe ratio is weak — the mix may not reward its risk efficiently." if sharpe < 0.5
                      else "Your Sharpe ratio is reasonable; optimization could still improve it."))
    recs.append("Meaningful dividend income that compounds well if reinvested." if dividend_yield > 0.03
                else "Most expected growth here comes from price appreciation, not dividends.")
    recs.append(f"Markets are currently {market_label.lower()}, which the plan accounts for in its risk view." if market_label
                else "Market-conditions data is unavailable right now.")
    recs.append(f"Recommended mix: {allocation['Equity']}% equities, {allocation['Bonds / Fixed Income']}% bonds, {allocation['Cash']}% cash.")
    return recs


def generate_ai_advisor_note(api_key, profile, metrics, allocation, market_label):
    prompt = f"""You are FinPilot, an educational robo-advisor. Write a short plain-English advisory note
(130-180 words) using ONLY these numbers; invent nothing. Flowing prose, no lists or headers. End with one
sentence that this is educational, not personalised financial advice.

Profile: age {profile['age']}, {profile['risk_tolerance']} risk, {profile['horizon']}-year horizon,
income ${profile['annual_income']:,.0f}, savings ${profile['current_savings']:,.0f}, ${profile['monthly_savings']:,.0f}/mo, risk score {profile['risk_score']}/100.
Allocation: {allocation['Equity']}% equity, {allocation['Bonds / Fixed Income']}% bonds, {allocation['Cash']}% cash.
Metrics: expected return {metrics['expected_return']:.2%}, volatility {metrics['volatility']:.2%},
Sharpe {metrics['sharpe']:.2f} (net of {metrics['risk_free_rate']:.2%} risk-free), dividend yield {metrics['dividend_yield']:.2%}.
Market conditions: {market_label}."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=600,
                                     messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text
    except Exception:
        return None


# ================= ONBOARDING =================
if not ss.onboarded:
    step = ss.onb_step
    st.markdown('<div class="home-wrap"><div class="home-brand">FinPilot AI</div></div>', unsafe_allow_html=True)
    with st.container():
        cl, cc, cr = st.columns([1, 4, 1])
        with cc:
            st.markdown('<div class="onb-card">', unsafe_allow_html=True)
            st.caption(f"Step {step} of 3")

            if step == 1:
                st.subheader("Welcome — let's build your plan")
                st.write("A few quick questions and we'll handle the investing for you.")
                st.text_input("What should we call you?", key="k_name", placeholder="Your name")
                st.selectbox("What are you investing for?", GOALS, key="k_goal")
                st.number_input("How much do you want to reach? ($)", min_value=0, step=50000, key="k_target")

            elif step == 2:
                hi = f", {ss.k_name}" if ss.k_name else ""
                st.subheader(f"A little about you{hi}")
                c1, c2 = st.columns(2)
                with c1:
                    st.number_input("Your age", min_value=18, max_value=100, key="k_age")
                    st.number_input("Current savings ($)", min_value=0, step=1000, key="k_savings")
                    st.number_input("Annual income ($)", min_value=0, step=5000, key="k_income")
                with c2:
                    st.slider("Years until you need it", 1, 40, key="k_horizon")
                    st.number_input("Amount you can invest monthly ($)", min_value=0, step=100, key="k_monthly")

            else:
                st.subheader("How do you feel about risk?")
                st.write("This sets how much of your money goes into stocks versus safer assets.")
                st.radio("Pick what sounds most like you", GOALS[:0] + ["Conservative", "Moderate", "Aggressive"],
                         key="k_risk",
                         captions=["Protect what I have — smaller ups and downs",
                                   "A balance of growth and safety",
                                   "Grow as much as possible — I can handle big swings"])

            b1, b2 = st.columns(2)
            with b1:
                if step > 1 and st.button("Back", use_container_width=True):
                    ss.onb_step -= 1
                    _rerun()
            with b2:
                if step < 3:
                    if st.button("Continue", use_container_width=True):
                        ss.onb_step += 1
                        _rerun()
                else:
                    if st.button("Build my plan", use_container_width=True):
                        ss.onboarded = True
                        ss.view = "home"
                        _rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.caption("Educational prototype only. Not financial advice.")
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.title("FinPilot")

st.sidebar.header("Your Goal")
goal_name = st.sidebar.selectbox("I'm investing for", GOALS, key="k_goal")
goal_target = st.sidebar.number_input("Target amount ($)", min_value=0, step=50000, key="k_target")
extra_deposit = st.sidebar.number_input("One-time deposit now ($)", min_value=0, step=1000, key="k_extra")

st.sidebar.header("About You")
age = st.sidebar.number_input("Age", 18, 100, key="k_age")
annual_income = st.sidebar.number_input("Annual income ($)", min_value=0, step=5000, key="k_income")
current_savings = st.sidebar.number_input("Current savings ($)", min_value=0, step=1000, key="k_savings")
monthly_savings = st.sidebar.number_input("Monthly contribution ($)", min_value=0, step=100, key="k_monthly")
risk_tolerance = st.sidebar.selectbox("Risk comfort", ["Conservative", "Moderate", "Aggressive"], key="k_risk")
horizon = st.sidebar.slider("Years until goal", 1, 40, key="k_horizon")

st.sidebar.header("Income Growth")
salary_growth_rate = st.sidebar.slider("Annual salary growth (%)", 0, 20, 5) / 100
link_contrib = st.sidebar.checkbox("Grow contributions with salary", value=True)
contribution_growth_rate = salary_growth_rate if link_contrib else st.sidebar.slider("Annual contribution growth (%)", 0, 20, 5) / 100

# --- Advanced settings (tickers + custom weights live here) ---
use_own = False
ticker_input = "VTI, BND, BIL"
weights_text = ""
period = "1y"
risk_free_rate = 0.043
demo_mode = False
if ss.view == "advanced":
    with st.sidebar.expander("Advanced settings"):
        use_own = st.checkbox("Use my own tickers", key="use_own_tickers")
        if use_own:
            ticker_input = st.text_input("Tickers", "AAPL, MSFT, NVDA, SPY, VYM")
            weights_text = st.text_input("Weights % (optional, comma-separated)", "")
        period = st.selectbox("Market data period", ["6mo", "1y", "2y", "5y"], index=1)
        risk_free_rate = st.number_input("Risk-free rate (%)", 0.0, 10.0, 4.3, 0.1) / 100
        demo_mode = st.checkbox("Demo mode (use saved data)", value=False)

# ---------------- SHARED FIGURES ----------------
auto_deposit_on = ss.get("auto_deposit", True)
effective_monthly = monthly_savings if auto_deposit_on else 0
assumed_return = {"Conservative": 0.05, "Moderate": 0.07, "Aggressive": 0.09}[risk_tolerance]
allocation = recommend_allocation(age, risk_tolerance, horizon)
score = risk_score(age, risk_tolerance, horizon, monthly_savings, annual_income)

goal_label = {"Retirement": "Retirement", "A home": "Buying a home", "Education": "Education", "Building wealth": "Building wealth"}[goal_name]
goal_phrase = {"Retirement": "retirement", "A home": "home", "Education": "education", "Building wealth": "wealth"}[goal_name]

home_proj = wealth_projection_with_growth(current_savings + extra_deposit, effective_monthly, assumed_return, horizon, contribution_growth_rate)
projected_value = float(home_proj["Projected Value"].iloc[-1])
on_track = projected_value >= goal_target


# ================= HOME VIEW =================
if ss.view == "home":
    pct = (projected_value / goal_target) if goal_target > 0 else 1.0
    bar_pct = min(max(pct, 0.0), 1.0) * 100
    if on_track:
        pill_html, pass_note = '<span class="pill-ok">On track</span>', " — projected to pass it"
        advisor_line = f"You're on track to reach your {goal_phrase} goal of {money_short(goal_target)}. Keeping your ${monthly_savings:,.0f}/month deposit going gets you there with room to spare."
    else:
        pill_html, pass_note = '<span class="pill-warn">Needs a nudge</span>', ""
        advisor_line = f"You're projected to reach {money_short(projected_value)} — a little under your {money_short(goal_target)} goal. Raising your monthly deposit or extending your timeline closes the gap."

    hi = f", {ss.k_name}" if ss.k_name else ""
    st.markdown(f"""
    <div class="home-wrap">
      <div class="home-brand">FinPilot AI</div>
      <div class="home-welcome">Welcome back{hi}</div>
      <div class="home-tag">Here's where your plan stands.</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="home-wrap"><div class="home-card">
      <div class="home-goal">{goal_label} · in {horizon} years</div>
      <div style="display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;">
        <span class="home-hero">{money_short(projected_value)}</span>{pill_html}
      </div>
      <div class="home-herosub">projected balance</div>
      <div class="home-bar-track"><div class="home-bar-fill" style="width:{bar_pct:.0f}%;"></div></div>
      <div class="home-herosub">Goal {money_short(goal_target)}{pass_note}</div>
      <div class="home-deposit"><div style="flex:1;">
        <div style="font-weight:800; color:#102A43; font-size:16px;">${monthly_savings:,.0f} / month</div>
        <div style="font-size:13px; color:#52616B;">automatic deposit</div></div></div>
      <div class="home-advisor">{advisor_line}</div>
    </div></div>""", unsafe_allow_html=True)

    fig_home = px.area(home_proj, x="Year", y="Projected Value", color_discrete_sequence=["#10B981"])
    fig_home.update_layout(height=250, showlegend=False, xaxis_title=None, yaxis_title=None, title=None)
    st.plotly_chart(apply_clean_theme(fig_home), use_container_width=True)

    st.markdown("#### Automation — set it and forget it")
    a1, a2 = st.columns(2)
    with a1:
        toggle(f"Automatic deposits — ${monthly_savings:,.0f}/mo", "auto_deposit")
        toggle("Auto-rebalance — quarterly", "auto_rebalance")
    with a2:
        toggle("Reinvest dividends automatically", "auto_dividend")
        toggle("Tax-loss harvesting", "auto_tlh")

    notes = []
    notes.append("Deposits run automatically each month." if ss.auto_deposit else "Automatic deposits are paused — your projection assumes no new contributions.")
    if ss.auto_rebalance:
        notes.append("Your mix is rebalanced back to target each quarter so it never drifts.")
    if ss.auto_tlh:
        tlh = current_savings * 0.008
        notes.append(f"Tax-loss harvesting could save roughly {money_short(tlh)}/yr (rough estimate, varies with your tax situation).")
    st.caption("  •  ".join(notes))

    sl, sm, sr = st.columns([1, 2, 1])
    with sm:
        if st.button("See detailed analytics →", use_container_width=True):
            ss.view = "advanced"
            _rerun()
    st.caption("Adjust your goal, deposit, timeline, and risk level in the sidebar.")
    st.caption("Educational prototype only. Not financial advice.")
    st.stop()


# ================= ADVANCED (ANALYTICS) VIEW =================
if st.button("← Back to home"):
    ss.view = "home"
    _rerun()

st.markdown("""
<div class="hero"><div class="pill">Detailed analytics</div>
<div class="hero-title">Under the hood of your plan.</div>
<div class="hero-subtitle">Your plan, your portfolio, and how it's tracking — with the market read automatically.</div></div>
""", unsafe_allow_html=True)
st.caption("Educational prototype only. Not financial advice.")

try:
    ANTHROPIC_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    ANTHROPIC_KEY = None

mc_read = market_conditions(demo_mode)
market_label = mc_read["label"] if mc_read else None

try:
    # --- Resolve the portfolio: recommended by default, or your own tickers (Advanced) ---
    if use_own:
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
        if not tickers:
            st.error("Enter at least one ticker in Advanced settings.")
            st.stop()
        prices = get_stock_data(tickers, period, demo_mode)
        tickers = list(prices.columns)
        weights = parse_weights(weights_text, tickers)
    else:
        rec = recommended_portfolio(allocation, equity_tickers=["VTI"])
        requested = list(rec.keys())
        prices = get_stock_data(requested, period, demo_mode)
        tickers = [t for t in requested if t in prices.columns]
        prices = prices[tickers]
        weights = np.array([rec[t] for t in tickers], dtype=float)
        weights = weights / weights.sum()

    if prices.empty:
        st.error("No market data found.")
        st.stop()

    normalized = prices / prices.iloc[0] * 100
    expected_return, volatility, sharpe, returns = portfolio_metrics(prices, weights, risk_free_rate)
    adj = mc_read["return_adjustment"] if mc_read else 0.0
    mult = mc_read["volatility_multiplier"] if mc_read else 1.0
    adjusted_return, adjusted_volatility = expected_return + adj, volatility * mult

    try:
        dividend_df = get_dividend_data(tickers, prices, demo_mode)
        portfolio_dividend_yield = weighted_dividend_yield(dividend_df, tickers, weights)
    except Exception:
        dividend_df = pd.DataFrame({"Ticker": tickers, "Last Annual Dividend": 0, "Estimated Price": np.nan, "Dividend Yield": 0})
        portfolio_dividend_yield = 0.0

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Risk Score", f"{score}/100")
    t2.metric("Expected Return", f"{expected_return:.2%}")
    t3.metric("Dividend Yield", f"{portfolio_dividend_yield:.2%}")
    t4.metric("Market Conditions", market_label or "—")

    tab_plan, tab_invest, tab_track = st.tabs(["Plan", "Invest", "Track"])

    # ---------- PLAN ----------
    with tab_plan:
        st.markdown('<div class="feature-card"><div class="card-title">Your plan</div><div class="card-text">Recommended mix and long-term projection for your goal.</div></div>', unsafe_allow_html=True)
        adf = pd.DataFrame({"Asset Class": list(allocation.keys()), "Allocation (%)": list(allocation.values())})
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(adf, use_container_width=True)
        with c2:
            fig_alloc = px.pie(adf, names="Asset Class", values="Allocation (%)", hole=0.55, title="Recommended Allocation", color_discrete_sequence=COLORS)
            st.plotly_chart(apply_clean_theme(fig_alloc), use_container_width=True)

        planning_return = st.slider("Planning return assumption (%)", 1, 15, int(assumed_return * 100)) / 100
        projection = wealth_projection_with_growth(current_savings + extra_deposit, effective_monthly, planning_return, horizon, contribution_growth_rate)
        income_schedule = income_growth_schedule(annual_income, monthly_savings, salary_growth_rate, contribution_growth_rate, horizon)

        p1, p2, p3 = st.columns(3)
        p1.metric("Projected Value", money_short(projection['Projected Value'].iloc[-1]))
        p2.metric("Final Monthly Contribution", f"${projection['Monthly Contribution'].iloc[-1]:,.0f}")
        p3.metric("Final Projected Salary", money_short(income_schedule['Projected Salary'].iloc[-1]))

        fig_proj = px.area(projection, x="Year", y="Projected Value", title="Projected Wealth Growth", color_discrete_sequence=["#10B981"])
        st.plotly_chart(apply_clean_theme(fig_proj), use_container_width=True)

        with st.expander("Income & contribution schedule"):
            disp = income_schedule.copy()
            for col in ["Projected Salary", "Monthly Contribution", "Annual Contribution"]:
                disp[col] = disp[col].apply(lambda x: f"${x:,.0f}")
            disp["Contribution Rate"] = disp["Contribution Rate"].apply(lambda x: f"{x:.1%}")
            st.dataframe(disp, use_container_width=True)
            fig_c = go.Figure()
            fig_c.add_trace(go.Scatter(x=income_schedule["Year"], y=income_schedule["Projected Salary"], mode="lines", name="Salary", line=dict(width=4, color="#0EA5E9")))
            fig_c.add_trace(go.Scatter(x=income_schedule["Year"], y=income_schedule["Annual Contribution"], mode="lines", name="Annual Contribution", line=dict(width=4, color="#10B981")))
            fig_c.update_layout(title="Salary vs Annual Contributions", xaxis_title="Year", yaxis_title="Amount")
            st.plotly_chart(apply_clean_theme(fig_c), use_container_width=True)

    # ---------- INVEST ----------
    with tab_invest:
        src = "your own tickers" if use_own else "your recommended allocation (VTI / BND / BIL)"
        st.markdown(f'<div class="feature-card"><div class="card-title">Your portfolio</div><div class="card-text">Built from {src}. Change this in Advanced settings.</div></div>', unsafe_allow_html=True)

        wdf = pd.DataFrame({"Holding": tickers, "Weight": weights})
        wdf["Weight"] = wdf["Weight"].apply(lambda x: f"{x:.1%}")
        cc1, cc2 = st.columns([1, 1])
        with cc1:
            st.dataframe(wdf, use_container_width=True)
        with cc2:
            fig_w = px.pie(pd.DataFrame({"Holding": tickers, "Weight": weights}), names="Holding", values="Weight", hole=0.55, title="Holdings", color_discrete_sequence=COLORS)
            st.plotly_chart(apply_clean_theme(fig_w), use_container_width=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Expected Return", f"{expected_return:.2%}")
        m2.metric("Volatility", f"{volatility:.2%}")
        m3.metric("Sharpe Ratio", f"{sharpe:.2f}")
        m4.metric("Health Score", f"{portfolio_health_score(len(tickers), volatility, sharpe)}/100")

        fig_g = go.Figure()
        for i, tk in enumerate(normalized.columns):
            fig_g.add_trace(go.Scatter(x=normalized.index, y=normalized[tk], mode="lines", name=tk, line=dict(width=3, color=COLORS[i % len(COLORS)])))
        try:
            bench = get_stock_data(["SPY"], period, demo_mode)
            bn = bench / bench.iloc[0] * 100
            fig_g.add_trace(go.Scatter(x=bn.index, y=bn["SPY"], mode="lines", name="S&P 500", line=dict(width=3, dash="dash", color="#111827")))
        except Exception:
            pass
        fig_g.update_layout(title="Growth of $100 vs S&P 500", xaxis_title="Date", yaxis_title="Indexed Value")
        st.plotly_chart(apply_clean_theme(fig_g), use_container_width=True)

        if len(tickers) >= 2:
            with st.expander("How your holdings move together (correlation)"):
                fig_corr = px.imshow(returns.corr(), text_auto=True, title="Correlation Matrix", color_continuous_scale=["#10B981", "#FFFFFF", "#EF4444"])
                st.plotly_chart(apply_clean_theme(fig_corr), use_container_width=True)
            with st.expander("Optimize this portfolio"):
                if st.button("Run optimization"):
                    ports = random_portfolios(prices)
                    best = ports.loc[ports["Sharpe"].idxmax()]
                    minv = ports.loc[ports["Volatility"].idxmin()]
                    st.dataframe(pd.DataFrame({"Ticker": prices.columns, "Max Sharpe (%)": best["Weights"] * 100, "Min Volatility (%)": minv["Weights"] * 100}), use_container_width=True)
                    fig_f = px.scatter(ports, x="Volatility", y="Return", color="Sharpe", title="Efficient Frontier", color_continuous_scale="Viridis")
                    fig_f.add_trace(go.Scatter(x=[best["Volatility"]], y=[best["Return"]], mode="markers", marker=dict(size=18, symbol="star", color="#F59E0B"), name="Max Sharpe"))
                    st.plotly_chart(apply_clean_theme(fig_f), use_container_width=True)

    # ---------- TRACK ----------
    with tab_track:
        st.markdown('<div class="feature-card"><div class="card-title">Are you on track?</div><div class="card-text">Your progress, current market conditions, income, and protection.</div></div>', unsafe_allow_html=True)

        tk1, tk2, tk3 = st.columns(3)
        tk1.metric("Projected at Goal", money_short(projected_value))
        tk2.metric("Your Target", money_short(goal_target))
        tk3.metric("Status", "On track" if on_track else "Needs a nudge")

        if mc_read:
            st.markdown(f'<div class="accent-box"><b>Market conditions: {mc_read["label"]}.</b> {mc_read["explanation"]} This is read automatically — nothing to set.</div>', unsafe_allow_html=True)
        else:
            st.caption("Market-conditions data is unavailable right now.")

        with st.expander("Project future outcomes (Monte Carlo)"):
            if st.button("Run simulation"):
                mc = monte_carlo_simulation(current_savings + extra_deposit, effective_monthly, adjusted_return, adjusted_volatility, horizon, contribution_growth_rate, simulations=500)
                fv = mc.iloc[-1]
                s1, s2, s3 = st.columns(3)
                s1.metric("Pessimistic (10th)", money_short(np.percentile(fv, 10)))
                s2.metric("Expected (median)", money_short(np.percentile(fv, 50)))
                s3.metric("Optimistic (90th)", money_short(np.percentile(fv, 90)))
                fig_mc = go.Figure()
                for i in range(min(50, mc.shape[1])):
                    fig_mc.add_trace(go.Scatter(y=mc.iloc[:, i], mode="lines", opacity=0.22, line=dict(color="#10B981"), showlegend=False))
                fig_mc.update_layout(title="Possible paths (adjusted for current market conditions)", xaxis_title="Months", yaxis_title="Value")
                st.plotly_chart(apply_clean_theme(fig_mc), use_container_width=True)

        with st.expander("Dividend income"):
            est_income = current_savings * portfolio_dividend_yield
            di1, di2 = st.columns(2)
            di1.metric("Portfolio Yield", f"{portfolio_dividend_yield:.2%}")
            di2.metric("Est. Annual Income", money_short(est_income))
            if ss.auto_dividend:
                dgr = st.slider("Assumed dividend growth (%)", 0, 10, 3) / 100
                dp = dividend_reinvestment_projection(current_savings + extra_deposit, effective_monthly, expected_return, portfolio_dividend_yield, dgr, contribution_growth_rate, horizon)
                fig_d = go.Figure()
                fig_d.add_trace(go.Scatter(x=dp["Year"], y=dp["With Dividend Reinvestment"], mode="lines", name="Reinvested", line=dict(width=4, color="#10B981")))
                fig_d.add_trace(go.Scatter(x=dp["Year"], y=dp["Without Dividend Reinvestment"], mode="lines", name="Not reinvested", line=dict(width=4, dash="dash", color="#0EA5E9")))
                fig_d.update_layout(title="Reinvesting dividends vs not", xaxis_title="Year", yaxis_title="Value")
                st.plotly_chart(apply_clean_theme(fig_d), use_container_width=True)
            else:
                st.caption("Dividend reinvestment is turned off in your automation settings.")

        with st.expander("Downside protection"):
            try:
                beta = calculate_portfolio_beta(prices, weights, period, demo_mode)
                dp1, dp2 = st.columns(2)
                dp1.metric("Beta vs S&P 500", f"{beta:.2f}")
                dp2.metric("Volatility", f"{volatility:.2%}")
                hedge = hedge_portfolio_analysis(prices, weights, current_savings, period, risk_free_rate, demo_mode)
                if hedge is not None:
                    comp, hwdf = hedge
                    st.caption("A defensive version shifts 20% into bonds (BND) and gold (GLD):")
                    st.dataframe(comp, use_container_width=True)
            except Exception:
                st.caption("Protection analysis unavailable right now.")
            st.dataframe(stress_test(weights), use_container_width=True)

    # ---------- ADVISOR ----------
    st.markdown('<div class="feature-card"><div class="card-title">AI Advisor Summary</div><div class="card-text">A plain-English read on your plan.</div></div>', unsafe_allow_html=True)
    recs = advisor_bullets(risk_tolerance, horizon, score, volatility, sharpe, allocation, market_label, portfolio_dividend_yield)
    if ANTHROPIC_KEY and st.button("Generate AI advisor note"):
        profile = {"age": age, "risk_tolerance": risk_tolerance, "horizon": horizon, "annual_income": annual_income,
                   "current_savings": current_savings, "monthly_savings": monthly_savings, "risk_score": score}
        metrics = {"expected_return": expected_return, "volatility": volatility, "sharpe": sharpe,
                   "dividend_yield": portfolio_dividend_yield, "risk_free_rate": risk_free_rate}
        note = generate_ai_advisor_note(ANTHROPIC_KEY, profile, metrics, allocation, market_label or "unavailable")
        if note:
            st.markdown(f'<div class="advisor-box">{note}</div>', unsafe_allow_html=True)
    for r in recs:
        st.markdown(f"- {r}")

except Exception:
    st.warning("Market data is taking a moment to load. Try again, or switch on Demo mode in Advanced settings.")

st.divider()
st.caption("Built with Streamlit, yfinance, pandas, numpy, and plotly.")
