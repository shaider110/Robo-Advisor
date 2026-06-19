import os
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="FinPilot AI", layout="wide")

# Folder where market data is cached to disk (auto-created). Acts as a safety net:
# if the network fails, the app falls back to the last good data instead of crashing.
CACHE_DIR = "market_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def _rerun():
    # Works on both new and older Streamlit versions.
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #F1FBF6 0%, #FFFFFF 38%, #F6F8FB 100%);
    color: #102A43;
}
.block-container { padding-top: 1.5rem; max-width: 1250px; }
.hero {
    background: linear-gradient(135deg, #DFF7EA 0%, #EAF4FF 55%, #FFFFFF 100%);
    padding: 42px; border-radius: 32px; border: 1px solid #D8EEE4;
    box-shadow: 0 18px 45px rgba(16, 42, 67, 0.08); margin-bottom: 24px;
}
.pill {
    display: inline-block; background: #BFF4D2; color: #065F46; padding: 8px 16px;
    border-radius: 999px; font-size: 14px; font-weight: 800; margin-bottom: 14px;
}
.hero-title { font-size: 48px; font-weight: 900; color: #062E2E; line-height: 1.05; max-width: 850px; }
.hero-subtitle { font-size: 18px; color: #42606A; max-width: 820px; margin-top: 15px; }
.feature-card {
    background: #FFFFFF; padding: 24px; border-radius: 26px; border: 1px solid #E3EAF0;
    box-shadow: 0px 12px 32px rgba(16, 42, 67, 0.07); margin-bottom: 18px;
}
.card-title { font-size: 22px; font-weight: 850; color: #102A43; margin-bottom: 6px; }
.card-text { font-size: 15px; color: #52616B; }
.accent-box {
    background: linear-gradient(135deg, #ECFDF5, #EFF6FF); border: 1px solid #D7F2E4;
    padding: 18px; border-radius: 22px; margin-bottom: 16px;
}
.advisor-box {
    background: linear-gradient(135deg, #ECFDF5, #EFF6FF); border: 1px solid #BBF7D0;
    padding: 26px; border-radius: 26px; margin-bottom: 16px; font-size: 16px; line-height: 1.6;
}
.risk-box {
    background: linear-gradient(135deg, #FFF7ED, #FEF2F2); border: 1px solid #FED7AA;
    padding: 18px; border-radius: 22px; margin-bottom: 16px;
}
/* ----- Calm goal-first Home view ----- */
.home-wrap { max-width: 620px; margin: 0 auto; }
.home-brand { font-size: 15px; font-weight: 800; color: #047857; margin-bottom: 2px; }
.home-welcome { font-size: 28px; font-weight: 900; color: #062E2E; line-height: 1.1; }
.home-tag { font-size: 14px; color: #52616B; margin-bottom: 12px; }
.home-card {
    background: #FFFFFF; border: 1px solid #E3EAF0; border-radius: 28px; padding: 30px;
    box-shadow: 0 12px 32px rgba(16, 42, 67, 0.07); margin-bottom: 18px;
}
.home-goal { font-size: 14px; color: #52616B; margin-bottom: 8px; }
.home-hero { font-size: 46px; font-weight: 900; color: #062E2E; letter-spacing: -1px; line-height: 1; }
.home-herosub { font-size: 14px; color: #52616B; margin-top: 4px; }
.pill-ok { display: inline-block; background: #BBF7D0; color: #065F46; padding: 5px 14px; border-radius: 999px; font-size: 13px; font-weight: 800; }
.pill-warn { display: inline-block; background: #FED7AA; color: #9A3412; padding: 5px 14px; border-radius: 999px; font-size: 13px; font-weight: 800; }
.home-bar-track { height: 10px; background: #EEF2F6; border-radius: 999px; overflow: hidden; margin: 14px 0 6px; }
.home-bar-fill { height: 100%; background: linear-gradient(90deg, #10B981, #0EA5E9); border-radius: 999px; }
.home-deposit { display: flex; align-items: center; gap: 10px; border-top: 1px solid #EEF2F6; border-bottom: 1px solid #EEF2F6; padding: 14px 0; margin: 16px 0; }
.home-advisor { background: linear-gradient(135deg, #ECFDF5, #EFF6FF); border: 1px solid #BBF7D0; border-radius: 18px; padding: 16px 18px; font-size: 15px; line-height: 1.55; color: #0F5132; }
div[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E3EAF0; padding: 18px; border-radius: 22px;
    box-shadow: 0px 10px 26px rgba(16, 42, 67, 0.06);
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-3px); box-shadow: 0px 16px 34px rgba(16, 42, 67, 0.12); transition: 0.25s ease;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 12px; background: #FFFFFF; padding: 10px; border-radius: 999px; border: 1px solid #E3EAF0;
    box-shadow: 0px 10px 30px rgba(16, 42, 67, 0.07); margin-bottom: 24px;
}
.stTabs [data-baseweb="tab"] {
    height: 50px; padding: 10px 22px; border-radius: 999px; color: #102A43; font-weight: 800;
    background: transparent; transition: all 0.25s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    background: #ECFDF5; color: #047857; transform: translateY(-2px); box-shadow: inset 0 0 0 1px #A7F3D0;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #10B981, #0EA5E9) !important; color: white !important;
    box-shadow: 0px 10px 24px rgba(16, 185, 129, 0.35);
}
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E3EAF0; }
.stButton > button {
    background: linear-gradient(135deg, #10B981, #0EA5E9); color: white; border: none;
    border-radius: 999px; padding: 0.7rem 1.4rem; font-weight: 800;
}
.stButton > button:hover {
    transform: translateY(-2px); box-shadow: 0px 12px 25px rgba(14, 165, 233, 0.25); transition: 0.25s ease;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATA LAYER (hardened) ----------------
# Caches every successful download to disk, one file per ticker. Normally fetches live;
# if a fetch fails it falls back to the cache so the app never crashes on a network blip.

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
        series = pd.read_csv(path, index_col=0, parse_dates=True)
        series.columns = [t]
        frames.append(series)
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
            series = prices[t].dropna()
            if not series.empty:
                last_price = float(series.iloc[-1])
        annual_dividend = 0.0
        try:
            dividends = yf.Ticker(t).dividends
            if dividends is not None and not dividends.empty:
                one_year_ago = dividends.index.max() - pd.DateOffset(years=1)
                annual_dividend = float(dividends[dividends.index >= one_year_ago].sum())
        except Exception:
            annual_dividend = 0.0
        dividend_yield = (annual_dividend / last_price) if (last_price and last_price > 0) else 0.0
        rows.append({
            "Ticker": t, "Last Annual Dividend": annual_dividend,
            "Estimated Price": last_price, "Dividend Yield": dividend_yield
        })
    return pd.DataFrame(rows)


# ---------------- FUNCTIONS ----------------

def money_short(v):
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def apply_clean_theme(fig):
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#102A43"), title_font=dict(size=22, color="#102A43"),
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(bgcolor="rgba(255,255,255,0)", borderwidth=0)
    )
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
    sleeves = {
        "Equity": list(equity_tickers) if equity_tickers else ["VTI"],
        "Bonds / Fixed Income": ["BND"],
        "Cash": ["BIL"],
    }
    weights = {}
    for sleeve, pct in allocation.items():
        tickers = sleeves.get(sleeve, [])
        if not tickers or pct <= 0:
            continue
        share = (pct / 100.0) / len(tickers)
        for t in tickers:
            weights[t] = weights.get(t, 0.0) + share
    total = sum(weights.values())
    if total > 0:
        weights = {t: w / total for t, w in weights.items()}
    return weights


def risk_score(age, risk_tolerance, horizon, monthly_savings, annual_income):
    score = 50
    if age < 30:
        score += 15
    elif age > 55:
        score -= 15
    if risk_tolerance == "Aggressive":
        score += 20
    elif risk_tolerance == "Conservative":
        score -= 20
    if horizon > 15:
        score += 15
    elif horizon < 5:
        score -= 15
    savings_rate = (monthly_savings * 12) / annual_income if annual_income > 0 else 0
    if savings_rate > 0.25:
        score += 10
    elif savings_rate < 0.10:
        score -= 10
    return int(min(max(score, 0), 100))


def portfolio_metrics(prices, weights, risk_free_rate=0.0):
    returns = prices.pct_change().dropna()
    annual_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    expected_return = np.dot(weights, annual_returns)
    volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    sharpe = (expected_return - risk_free_rate) / volatility if volatility != 0 else 0
    return expected_return, volatility, sharpe, returns


def portfolio_health_score(num_assets, volatility, sharpe):
    score = 50
    if num_assets >= 5:
        score += 15
    elif num_assets <= 2:
        score -= 15
    if volatility < 0.20:
        score += 15
    elif volatility > 0.35:
        score -= 15
    if sharpe > 1:
        score += 20
    elif sharpe < 0.3:
        score -= 10
    return int(min(max(score, 0), 100))


def contribution_for_month(base_monthly_savings, contribution_growth_rate, month):
    year_number = month // 12
    return base_monthly_savings * ((1 + contribution_growth_rate) ** year_number)


def wealth_projection_with_growth(current_savings, monthly_savings, annual_return, years, contribution_growth_rate):
    months = years * 12
    monthly_return = annual_return / 12
    portfolio_value = current_savings
    values = []
    for month in range(months + 1):
        current_contribution = contribution_for_month(monthly_savings, contribution_growth_rate, month)
        values.append({
            "Month": month, "Year": month / 12,
            "Monthly Contribution": current_contribution, "Projected Value": portfolio_value
        })
        portfolio_value = portfolio_value * (1 + monthly_return) + current_contribution
    return pd.DataFrame(values)


def income_growth_schedule(annual_income, monthly_savings, salary_growth_rate, contribution_growth_rate, years):
    rows = []
    for year in range(years + 1):
        salary = annual_income * ((1 + salary_growth_rate) ** year)
        monthly_contribution = monthly_savings * ((1 + contribution_growth_rate) ** year)
        annual_contribution = monthly_contribution * 12
        contribution_rate = annual_contribution / salary if salary > 0 else 0
        rows.append({
            "Year": year, "Projected Salary": salary, "Monthly Contribution": monthly_contribution,
            "Annual Contribution": annual_contribution, "Contribution Rate": contribution_rate
        })
    return pd.DataFrame(rows)


def random_portfolios(prices, num_portfolios=3000):
    returns = prices.pct_change().dropna()
    annual_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    results = []
    for _ in range(num_portfolios):
        weights = np.random.random(len(prices.columns))
        weights = weights / np.sum(weights)
        port_return = np.dot(weights, annual_returns)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = port_return / port_vol if port_vol != 0 else 0
        results.append({"Return": port_return, "Volatility": port_vol, "Sharpe": sharpe, "Weights": weights})
    return pd.DataFrame(results)


def monte_carlo_simulation(start_value, monthly_savings, expected_return, volatility, years, contribution_growth_rate, simulations=500):
    months = years * 12
    monthly_return = expected_return / 12
    monthly_volatility = volatility / np.sqrt(12)
    all_paths = []
    for _ in range(simulations):
        value = start_value
        path = []
        for month in range(months + 1):
            path.append(value)
            current_contribution = contribution_for_month(monthly_savings, contribution_growth_rate, month)
            random_return = np.random.normal(monthly_return, monthly_volatility)
            value = value * (1 + random_return) + current_contribution
        all_paths.append(path)
    return pd.DataFrame(all_paths).T


def calculate_var(returns, weights, portfolio_value, confidence=0.95):
    portfolio_returns = returns.dot(weights)
    var_percent = np.percentile(portfolio_returns, (1 - confidence) * 100)
    var_amount = portfolio_value * abs(var_percent)
    return var_percent, var_amount


def calculate_portfolio_beta(prices, weights, period, demo_mode=False):
    benchmark = get_stock_data(["SPY"], period, demo_mode)
    combined = prices.join(benchmark, how="inner", rsuffix="_benchmark")
    returns = combined.pct_change().dropna()
    portfolio_returns = returns[prices.columns].dot(weights)
    benchmark_col = "SPY_benchmark" if "SPY_benchmark" in returns.columns else "SPY"
    benchmark_returns = returns[benchmark_col]
    covariance = np.cov(portfolio_returns, benchmark_returns)[0][1]
    variance = np.var(benchmark_returns)
    return covariance / variance if variance != 0 else 0


def hedge_portfolio_analysis(prices, weights, portfolio_value, period, risk_free_rate=0.0, demo_mode=False):
    current_return, current_vol, current_sharpe, returns = portfolio_metrics(prices, weights, risk_free_rate)
    hedge_assets = [a for a in ["BND", "GLD"] if a not in prices.columns]
    if not hedge_assets:
        return None
    hedge_data = get_stock_data(hedge_assets, period, demo_mode)
    combined_prices = prices.join(hedge_data, how="inner")
    if combined_prices.empty:
        return None
    base = list(np.array(weights) * 0.80)
    add = [0.20 / len(hedge_assets)] * len(hedge_assets)
    hedge_weights = np.array(base + add)
    hedge_weights = hedge_weights / hedge_weights.sum()
    hedged_return, hedged_vol, hedged_sharpe, hedged_returns = portfolio_metrics(combined_prices, hedge_weights, risk_free_rate)
    _, current_var_amount = calculate_var(returns, weights, portfolio_value)
    _, hedged_var_amount = calculate_var(hedged_returns, hedge_weights, portfolio_value)
    comparison = pd.DataFrame({
        "Metric": ["Expected Annual Return", "Annual Volatility", "Sharpe Ratio", "Daily 95% VaR"],
        "Current Portfolio": [f"{current_return:.2%}", f"{current_vol:.2%}", f"{current_sharpe:.2f}", f"${current_var_amount:,.0f}"],
        "Hedged Portfolio": [f"{hedged_return:.2%}", f"{hedged_vol:.2%}", f"{hedged_sharpe:.2f}", f"${hedged_var_amount:,.0f}"]
    })
    hedge_weights_df = pd.DataFrame({
        "Asset": list(prices.columns) + hedge_assets, "Hedged Weight (%)": hedge_weights * 100
    })
    return comparison, hedge_weights_df


def macro_scenario_assumptions(scenario):
    scenarios = {
        "Normal Market Environment": {"return_adjustment": 0.00, "volatility_multiplier": 1.00, "risk_label": "Low", "explanation": "Markets are assumed to behave near historical averages."},
        "Elevated Policy Uncertainty": {"return_adjustment": -0.02, "volatility_multiplier": 1.25, "risk_label": "Moderate", "explanation": "Higher policy uncertainty may reduce risk appetite and increase volatility."},
        "Trade War / Tariff Shock": {"return_adjustment": -0.04, "volatility_multiplier": 1.45, "risk_label": "High", "explanation": "Trade uncertainty can pressure global supply chains, margins, and equity valuations."},
        "Geopolitical Crisis": {"return_adjustment": -0.06, "volatility_multiplier": 1.70, "risk_label": "Very High", "explanation": "Geopolitical stress may create sharp market moves and demand for defensive assets."},
        "Recession Stress": {"return_adjustment": -0.08, "volatility_multiplier": 1.90, "risk_label": "Severe", "explanation": "A recession scenario assumes weak returns, higher volatility, and elevated drawdown risk."}
    }
    return scenarios[scenario]


def macro_uncertainty_score(epu, tpu, gpr):
    epu_score = min(epu / 500, 1) * 40
    tpu_score = min(tpu / 5000, 1) * 30
    gpr_score = min(gpr / 500, 1) * 30
    total = epu_score + tpu_score + gpr_score
    if total < 35:
        label = "Low Macro Risk"
    elif total < 60:
        label = "Moderate Macro Risk"
    elif total < 80:
        label = "High Macro Risk"
    else:
        label = "Extreme Macro Risk"
    return int(total), label


def weighted_dividend_yield(dividend_df, tickers, weights):
    yields = []
    for ticker in tickers:
        row = dividend_df[dividend_df["Ticker"] == ticker]
        yields.append(float(row["Dividend Yield"].iloc[0]) if not row.empty else 0)
    return float(np.dot(weights, np.array(yields)))


def dividend_reinvestment_projection(starting_value, monthly_savings, expected_return, dividend_yield, dividend_growth_rate, contribution_growth_rate, years):
    months = years * 12
    monthly_price_return = expected_return / 12
    value_with_reinvestment = starting_value
    value_without_reinvestment = starting_value
    annual_dividend_income = starting_value * dividend_yield
    rows = []
    for month in range(months + 1):
        year = month / 12
        current_contribution = contribution_for_month(monthly_savings, contribution_growth_rate, month)
        rows.append({
            "Year": year, "Monthly Contribution": current_contribution,
            "With Dividend Reinvestment": value_with_reinvestment,
            "Without Dividend Reinvestment": value_without_reinvestment,
            "Estimated Annual Dividend Income": annual_dividend_income
        })
        current_dividend_yield = dividend_yield * ((1 + dividend_growth_rate) ** year)
        monthly_dividend = value_with_reinvestment * (current_dividend_yield / 12)
        value_with_reinvestment = value_with_reinvestment * (1 + monthly_price_return) + current_contribution + monthly_dividend
        value_without_reinvestment = value_without_reinvestment * (1 + monthly_price_return) + current_contribution
        annual_dividend_income = value_with_reinvestment * current_dividend_yield
    return pd.DataFrame(rows)


def enhanced_ai_recommendation(age, risk_tolerance, horizon, score, expected_return, volatility, sharpe, allocation, macro_label, dividend_yield, salary_growth_rate, contribution_growth_rate):
    recs = []
    recs.append(f"Your risk score is {score}/100, placing you in a {risk_tolerance.lower()} investor profile.")
    if horizon >= 10:
        recs.append("Your long time horizon supports higher equity exposure because you have more time to absorb volatility.")
    else:
        recs.append("Your shorter horizon means capital protection matters more, so the model favors a more defensive allocation.")
    if contribution_growth_rate > 0:
        recs.append(f"Your contributions are assumed to grow by {contribution_growth_rate:.1%} annually, which can meaningfully improve long-term wealth accumulation.")
    if salary_growth_rate > 0:
        recs.append(f"Your salary is assumed to grow by {salary_growth_rate:.1%} annually, allowing the model to create a more realistic planning path.")
    if volatility > 0.30:
        recs.append("Your current portfolio volatility is high. Adding defensive assets such as bonds, gold, or broad ETFs may help.")
    elif volatility < 0.15:
        recs.append("Your portfolio volatility is low, which reduces risk but may limit long-term growth.")
    else:
        recs.append("Your portfolio volatility appears balanced for a diversified strategy.")
    if sharpe > 1:
        recs.append("Your Sharpe ratio is strong, meaning the portfolio is producing attractive return relative to risk.")
    elif sharpe < 0.5:
        recs.append("Your Sharpe ratio is weak, meaning the portfolio may not be efficiently rewarding you for the risk taken.")
    else:
        recs.append("Your Sharpe ratio is reasonable, but optimization may improve risk-adjusted returns.")
    if dividend_yield > 0.03:
        recs.append("Your portfolio has meaningful dividend income potential, which can improve compounding if reinvested.")
    elif dividend_yield > 0:
        recs.append("Your portfolio has some dividend exposure, but most expected growth may still come from capital appreciation.")
    else:
        recs.append("Your portfolio has little dividend income exposure, so projected growth mainly depends on price appreciation.")
    if "High" in macro_label or "Extreme" in macro_label:
        recs.append("Macro uncertainty is elevated, so the model recommends stronger downside protection and lower concentration risk.")
    elif "Moderate" in macro_label:
        recs.append("Macro uncertainty is moderate, so the model recommends balanced exposure with some defensive allocation.")
    else:
        recs.append("Macro uncertainty is low, so the model does not require major defensive adjustments.")
    recs.append(f"The recommended strategic allocation is {allocation['Equity']}% equities, {allocation['Bonds / Fixed Income']}% fixed income, and {allocation['Cash']}% cash.")
    return recs


def generate_ai_advisor_note(api_key, profile, metrics, allocation, macro):
    prompt = f"""You are FinPilot, an educational robo-advisor. Write a short, plain-English
advisory note (about 130-180 words) for the investor below. Use ONLY the numbers given;
do not invent figures. No bullet lists or headers, just clear flowing prose. End with one
sentence noting this is educational and not personalised financial advice.

Profile: age {profile['age']}, {profile['risk_tolerance']} risk tolerance,
{profile['horizon']}-year horizon, income ${profile['annual_income']:,.0f},
current savings ${profile['current_savings']:,.0f}, monthly contribution
${profile['monthly_savings']:,.0f}, risk score {profile['risk_score']}/100.

Recommended allocation: {allocation['Equity']}% equity, {allocation['Bonds / Fixed Income']}%
bonds, {allocation['Cash']}% cash.

Portfolio metrics: expected return {metrics['expected_return']:.2%}, volatility
{metrics['volatility']:.2%}, Sharpe {metrics['sharpe']:.2f} (net of a
{metrics['risk_free_rate']:.2%} risk-free rate), dividend yield {metrics['dividend_yield']:.2%}.

Macro backdrop: {macro['label']} ({macro['score']}/100), active scenario {macro['scenario']}.

Explain what the risk profile implies, why the allocation suits the horizon, what the Sharpe
and volatility say about efficiency, and how the macro backdrop should shape caution."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception:
        return None


def stress_test(weights):
    scenarios = {
        "COVID-style market shock": -0.20, "2022 inflation and rate shock": -0.18,
        "Trade war shock": -0.16, "Geopolitical crisis": -0.22,
        "Mild recession": -0.10, "Strong bull market": 0.15
    }
    return pd.DataFrame({
        "Scenario": list(scenarios.keys()),
        "Estimated Portfolio Impact": [f"{shock * np.sum(weights):.2%}" for shock in scenarios.values()]
    })


# ---------------- VIEW STATE ----------------
# "home" = calm goal-first screen (default). "advanced" = full analytics dashboard.
if "view" not in st.session_state:
    st.session_state.view = "home"
view = st.session_state.view

# ---------------- SIDEBAR ----------------
st.sidebar.title("FinPilot Controls")

st.sidebar.header("Your Goal")
goal_name = st.sidebar.selectbox("I'm investing for", ["Retirement", "A home", "Education", "Building wealth"])
goal_target = st.sidebar.number_input("Target amount ($)", min_value=0, value=1000000, step=50000)
extra_deposit = st.sidebar.number_input("One-time deposit now ($)", min_value=0, value=0, step=1000)

st.sidebar.header("Investor Profile")
age = st.sidebar.number_input("Age", min_value=18, max_value=100, value=25)
annual_income = st.sidebar.number_input("Annual Income", min_value=0, value=60000, step=5000)
current_savings = st.sidebar.number_input("Current Savings", min_value=0, value=10000, step=1000)
monthly_savings = st.sidebar.number_input("Monthly Contribution", min_value=0, value=1000, step=100)
risk_tolerance = st.sidebar.selectbox("Risk Tolerance", ["Conservative", "Moderate", "Aggressive"])
horizon = st.sidebar.slider("Investment Horizon (years)", 1, 40, 10)

st.sidebar.header("Income Growth")
salary_growth_rate = st.sidebar.slider("Expected Annual Salary Growth (%)", 0, 20, 5) / 100
link_contribution_to_salary = st.sidebar.checkbox("Increase contributions with salary growth", value=True)
if link_contribution_to_salary:
    contribution_growth_rate = salary_growth_rate
else:
    contribution_growth_rate = st.sidebar.slider("Annual Contribution Growth (%)", 0, 20, 5) / 100

# Advanced-only controls appear only in the analytics view, keeping the Home view calm.
if view == "advanced":
    st.sidebar.header("Portfolio")
    ticker_input = st.sidebar.text_input("Tickers", "AAPL, MSFT, NVDA, SPY, VYM")
    period = st.sidebar.selectbox("Market Data Period", ["6mo", "1y", "2y", "5y"], index=1)
    risk_free_rate = st.sidebar.number_input("Risk-free rate (%)", 0.0, 10.0, 4.3, 0.1) / 100
    analyze_recommended = st.sidebar.checkbox("Analyze my recommended portfolio instead of typed tickers", value=False)

    st.sidebar.header("Reliability")
    demo_mode = st.sidebar.checkbox("Demo mode (use saved data, skip live fetch)", value=False)

    st.sidebar.header("Macro Risk")
    macro_scenario = st.sidebar.selectbox("Macro Scenario", [
        "Normal Market Environment", "Elevated Policy Uncertainty",
        "Trade War / Tariff Shock", "Geopolitical Crisis", "Recession Stress"
    ])
    epu_input = st.sidebar.slider("Economic Policy Uncertainty Index", 50, 700, 200)
    tpu_input = st.sidebar.slider("Trade Policy Uncertainty Index", 100, 6000, 1500)
    gpr_input = st.sidebar.slider("Geopolitical Risk Index", 50, 700, 180)

# Always-available figures (used by both views).
assumed_return = {"Conservative": 0.05, "Moderate": 0.07, "Aggressive": 0.09}[risk_tolerance]
allocation = recommend_allocation(age, risk_tolerance, horizon)
score = risk_score(age, risk_tolerance, horizon, monthly_savings, annual_income)


# ================= HOME VIEW =================
if view == "home":
    goal_label = {"Retirement": "Retirement", "A home": "Buying a home",
                  "Education": "Education", "Building wealth": "Building wealth"}[goal_name]
    goal_phrase = {"Retirement": "retirement", "A home": "home",
                   "Education": "education", "Building wealth": "wealth"}[goal_name]

    proj = wealth_projection_with_growth(
        current_savings=current_savings + extra_deposit, monthly_savings=monthly_savings,
        annual_return=assumed_return, years=horizon, contribution_growth_rate=contribution_growth_rate
    )
    projected_value = float(proj["Projected Value"].iloc[-1])
    on_track = projected_value >= goal_target
    pct = (projected_value / goal_target) if goal_target > 0 else 1.0
    bar_pct = min(max(pct, 0.0), 1.0) * 100

    if on_track:
        pill_html = '<span class="pill-ok">On track</span>'
        pass_note = " — projected to pass it"
        advisor_line = (f"You're on track to reach your {goal_phrase} goal of {money_short(goal_target)}. "
                        f"Keeping your ${monthly_savings:,.0f}/month deposit going gets you there with room to spare.")
    else:
        pill_html = '<span class="pill-warn">Needs a nudge</span>'
        pass_note = ""
        advisor_line = (f"You're projected to reach {money_short(projected_value)} — a little under your "
                        f"{money_short(goal_target)} goal. Raising your monthly deposit or extending your "
                        f"timeline closes the gap.")

    st.markdown("""
    <div class="home-wrap">
        <div class="home-brand">FinPilot AI</div>
        <div class="home-welcome">Welcome back</div>
        <div class="home-tag">Here's where your plan stands.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="home-wrap">
      <div class="home-card">
        <div class="home-goal">{goal_label} · in {horizon} years</div>
        <div style="display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;">
          <span class="home-hero">{money_short(projected_value)}</span>
          {pill_html}
        </div>
        <div class="home-herosub">projected balance</div>
        <div class="home-bar-track"><div class="home-bar-fill" style="width:{bar_pct:.0f}%;"></div></div>
        <div class="home-herosub">Goal {money_short(goal_target)}{pass_note}</div>
        <div class="home-deposit">
          <div style="flex:1;">
            <div style="font-weight:800; color:#102A43; font-size:16px;">${monthly_savings:,.0f} / month</div>
            <div style="font-size:13px; color:#52616B;">automatic deposit</div>
          </div>
        </div>
        <div class="home-advisor">{advisor_line}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    fig_home = px.area(proj, x="Year", y="Projected Value", color_discrete_sequence=["#10B981"])
    fig_home.update_layout(height=260, showlegend=False, xaxis_title=None, yaxis_title=None, title=None)
    st.plotly_chart(apply_clean_theme(fig_home), use_container_width=True)

    spacer_l, mid, spacer_r = st.columns([1, 2, 1])
    with mid:
        if st.button("See detailed analytics →", use_container_width=True):
            st.session_state.view = "advanced"
            _rerun()
    st.caption("Adjust your goal, deposit, timeline, and risk level in the sidebar.")
    st.caption("Educational prototype only. Not financial advice.")
    st.stop()


# ================= ADVANCED VIEW =================
if st.button("← Back to home"):
    st.session_state.view = "home"
    _rerun()

st.markdown("""
<div class="hero">
    <div class="pill">AI-powered wealth management prototype</div>
    <div class="hero-title">Detailed portfolio analytics.</div>
    <div class="hero-subtitle">
        Track portfolios, project salary and contribution growth, simulate future wealth, analyze dividends,
        optimize allocations, and stress-test portfolios under macro uncertainty.
    </div>
</div>
""", unsafe_allow_html=True)
st.caption("Educational prototype only. Not financial advice.")

tickers = [ticker.strip().upper() for ticker in ticker_input.split(",") if ticker.strip()]
macro_score, macro_label = macro_uncertainty_score(epu_input, tpu_input, gpr_input)
scenario_data = macro_scenario_assumptions(macro_scenario)

try:
    ANTHROPIC_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    ANTHROPIC_KEY = None

try:
    if not tickers:
        st.error("Please enter at least one ticker symbol in the sidebar.")
        st.stop()

    if analyze_recommended:
        rec = recommended_portfolio(allocation, equity_tickers=tickers)
        requested = list(rec.keys())
        prices = get_stock_data(requested, period, demo_mode)
        available = [t for t in requested if t in prices.columns]
        prices = prices[available]
        tickers = available
        weights = np.array([rec[t] for t in tickers], dtype=float)
        weights = weights / weights.sum()
        st.sidebar.caption("Portfolio set to your recommended allocation (equity sleeve = your tickers, plus BND and BIL).")
    else:
        prices = get_stock_data(tickers, period, demo_mode)
        if prices.empty:
            st.error("No market data found. Please check the ticker symbols.")
            st.stop()
        tickers = list(prices.columns)

        st.sidebar.header("Portfolio Weights")
        use_custom_weights = st.sidebar.checkbox("Use custom weights", value=False)
        if use_custom_weights:
            raw_weights = []
            for ticker in tickers:
                raw_weights.append(st.sidebar.number_input(
                    f"{ticker} weight (%)", min_value=0.0, max_value=100.0,
                    value=round(100 / len(tickers), 2), step=1.0
                ))
            if sum(raw_weights) == 0:
                weights = np.array([1 / len(tickers)] * len(tickers))
            else:
                weights = np.array(raw_weights) / sum(raw_weights)
        else:
            weights = np.array([1 / len(tickers)] * len(tickers))

    if prices.empty:
        st.error("No market data found. Please check the ticker symbols.")
        st.stop()

    normalized = prices / prices.iloc[0] * 100
    expected_return, volatility, sharpe, returns = portfolio_metrics(prices, weights, risk_free_rate)
    adjusted_return = expected_return + scenario_data["return_adjustment"]
    adjusted_volatility = volatility * scenario_data["volatility_multiplier"]

    try:
        dividend_df = get_dividend_data(tickers, prices, demo_mode)
        portfolio_dividend_yield = weighted_dividend_yield(dividend_df, tickers, weights)
    except Exception:
        dividend_df = pd.DataFrame({"Ticker": tickers, "Last Annual Dividend": 0, "Estimated Price": np.nan, "Dividend Yield": 0})
        portfolio_dividend_yield = 0.0

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Risk Score", f"{score}/100")
    top2.metric("Expected Return", f"{expected_return:.2%}")
    top3.metric("Dividend Yield", f"{portfolio_dividend_yield:.2%}")
    top4.metric("Macro Risk", macro_label)

    tab_plan, tab_invest, tab_income, tab_analyze, tab_optimize, tab_macro, tab_protect = st.tabs([
        "Plan", "Invest", "Income", "Analyze", "Optimize", "Macro Risk", "Protect"
    ])

    with tab_plan:
        st.markdown("""
        <div class="feature-card"><div class="card-title">Your personalized wealth plan</div>
        <div class="card-text">Create a long-term investment path using savings, income growth, contribution growth, and risk profile.</div></div>
        """, unsafe_allow_html=True)

        allocation_df = pd.DataFrame({"Asset Class": list(allocation.keys()), "Allocation (%)": list(allocation.values())})
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(allocation_df, use_container_width=True)
        with col2:
            fig_alloc = px.pie(allocation_df, names="Asset Class", values="Allocation (%)", hole=0.55,
                               title="Recommended Allocation", color="Asset Class",
                               color_discrete_sequence=["#10B981", "#0EA5E9", "#F59E0B"])
            st.plotly_chart(apply_clean_theme(fig_alloc), use_container_width=True)

        st.markdown("""
        <div class="accent-box"><b>Salary and contribution growth:</b> The projection increases monthly contributions each year based on the selected growth assumption.</div>
        """, unsafe_allow_html=True)

        assumed_return_adv = st.slider("Planning Return Assumption (%)", 1, 15, 7) / 100
        projection = wealth_projection_with_growth(current_savings, monthly_savings, assumed_return_adv, horizon, contribution_growth_rate)
        income_schedule = income_growth_schedule(annual_income, monthly_savings, salary_growth_rate, contribution_growth_rate, horizon)

        p1, p2, p3 = st.columns(3)
        p1.metric("Projected Portfolio Value", f"${projection['Projected Value'].iloc[-1]:,.0f}")
        p2.metric("Final Monthly Contribution", f"${projection['Monthly Contribution'].iloc[-1]:,.0f}")
        p3.metric("Final Projected Salary", f"${income_schedule['Projected Salary'].iloc[-1]:,.0f}")

        fig_projection = px.area(projection, x="Year", y="Projected Value", title="Projected Wealth Growth With Rising Contributions", color_discrete_sequence=["#10B981"])
        st.plotly_chart(apply_clean_theme(fig_projection), use_container_width=True)

        st.markdown("### Income and Contribution Schedule")
        dsch = income_schedule.copy()
        dsch["Projected Salary"] = dsch["Projected Salary"].apply(lambda x: f"${x:,.0f}")
        dsch["Monthly Contribution"] = dsch["Monthly Contribution"].apply(lambda x: f"${x:,.0f}")
        dsch["Annual Contribution"] = dsch["Annual Contribution"].apply(lambda x: f"${x:,.0f}")
        dsch["Contribution Rate"] = dsch["Contribution Rate"].apply(lambda x: f"{x:.1%}")
        st.dataframe(dsch, use_container_width=True)

        fig_contribution = go.Figure()
        fig_contribution.add_trace(go.Scatter(x=income_schedule["Year"], y=income_schedule["Projected Salary"], mode="lines+markers", name="Projected Salary", line=dict(width=4, color="#0EA5E9")))
        fig_contribution.add_trace(go.Scatter(x=income_schedule["Year"], y=income_schedule["Annual Contribution"], mode="lines+markers", name="Annual Contribution", line=dict(width=4, color="#10B981")))
        fig_contribution.update_layout(title="Projected Salary vs Annual Contributions", xaxis_title="Year", yaxis_title="Amount")
        st.plotly_chart(apply_clean_theme(fig_contribution), use_container_width=True)

    with tab_invest:
        st.markdown("""
        <div class="feature-card"><div class="card-title">Market and portfolio tracking</div>
        <div class="card-text">Track selected stocks and ETFs against a broad market benchmark.</div></div>
        """, unsafe_allow_html=True)
        st.dataframe(prices.tail(), use_container_width=True)

        fig_prices = go.Figure()
        colors = ["#10B981", "#0EA5E9", "#8B5CF6", "#F59E0B", "#EF4444", "#14B8A6", "#6366F1"]
        for i, ticker in enumerate(normalized.columns):
            fig_prices.add_trace(go.Scatter(x=normalized.index, y=normalized[ticker], mode="lines", name=ticker, line=dict(width=3, color=colors[i % len(colors)])))
        try:
            benchmark = get_stock_data(["SPY"], period, demo_mode)
            benchmark_norm = benchmark / benchmark.iloc[0] * 100
            fig_prices.add_trace(go.Scatter(x=benchmark_norm.index, y=benchmark_norm["SPY"], mode="lines", name="Benchmark: SPY", line=dict(width=3, dash="dash", color="#111827")))
        except Exception:
            st.caption("Benchmark (SPY) data unavailable right now.")
        fig_prices.update_layout(title="Growth of $100 vs S&P 500 ETF", xaxis_title="Date", yaxis_title="Indexed Value")
        st.plotly_chart(apply_clean_theme(fig_prices), use_container_width=True)

    with tab_income:
        st.markdown("""
        <div class="feature-card"><div class="card-title">Dividend income engine</div>
        <div class="card-text">Estimate dividend yield, annual income, dividend growth, and the long-term impact of reinvesting dividends.</div></div>
        """, unsafe_allow_html=True)

        ddf = dividend_df.copy()
        ddf["Dividend Yield"] = ddf["Dividend Yield"].apply(lambda x: f"{x:.2%}")
        ddf["Last Annual Dividend"] = ddf["Last Annual Dividend"].apply(lambda x: f"${x:.2f}")
        ddf["Estimated Price"] = ddf["Estimated Price"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        st.dataframe(ddf, use_container_width=True)

        estimated_annual_income = current_savings * portfolio_dividend_yield
        d1, d2, d3 = st.columns(3)
        d1.metric("Portfolio Dividend Yield", f"{portfolio_dividend_yield:.2%}")
        d2.metric("Estimated Annual Dividend Income", f"${estimated_annual_income:,.0f}")
        d3.metric("Monthly Dividend Income", f"${estimated_annual_income / 12:,.0f}")

        fig_div_yield = px.bar(dividend_df, x="Ticker", y="Dividend Yield", title="Estimated Dividend Yield by Asset", color="Ticker", color_discrete_sequence=colors)
        fig_div_yield.update_yaxes(tickformat=".2%")
        st.plotly_chart(apply_clean_theme(fig_div_yield), use_container_width=True)

        st.markdown("""
        <div class="accent-box"><b>Dividend reinvestment simulator:</b> Compare portfolio growth when dividends are reinvested versus not reinvested.</div>
        """, unsafe_allow_html=True)

        dividend_growth_rate = st.slider("Assumed Annual Dividend Growth Rate (%)", 0, 10, 3) / 100
        dividend_projection = dividend_reinvestment_projection(current_savings, monthly_savings, expected_return, portfolio_dividend_yield, dividend_growth_rate, contribution_growth_rate, horizon)

        fwr = dividend_projection["With Dividend Reinvestment"].iloc[-1]
        fwor = dividend_projection["Without Dividend Reinvestment"].iloc[-1]
        r1, r2, r3 = st.columns(3)
        r1.metric("With Reinvestment", f"${fwr:,.0f}")
        r2.metric("Without Reinvestment", f"${fwor:,.0f}")
        r3.metric("Reinvestment Benefit", f"${fwr - fwor:,.0f}")

        fig_reinvest = go.Figure()
        fig_reinvest.add_trace(go.Scatter(x=dividend_projection["Year"], y=dividend_projection["With Dividend Reinvestment"], mode="lines", name="With Dividend Reinvestment", line=dict(width=4, color="#10B981")))
        fig_reinvest.add_trace(go.Scatter(x=dividend_projection["Year"], y=dividend_projection["Without Dividend Reinvestment"], mode="lines", name="Without Dividend Reinvestment", line=dict(width=4, dash="dash", color="#0EA5E9")))
        fig_reinvest.update_layout(title="Portfolio Growth: Dividends Reinvested vs Not Reinvested", xaxis_title="Year", yaxis_title="Portfolio Value")
        st.plotly_chart(apply_clean_theme(fig_reinvest), use_container_width=True)

        fig_income_growth = px.area(dividend_projection, x="Year", y="Estimated Annual Dividend Income", title="Projected Annual Dividend Income Growth", color_discrete_sequence=["#F59E0B"])
        st.plotly_chart(apply_clean_theme(fig_income_growth), use_container_width=True)
        st.info("Dividend estimates use recent dividend history and user-selected dividend growth. Actual dividends can change depending on company earnings, ETF distributions, and market conditions.")

    with tab_analyze:
        st.markdown("""
        <div class="feature-card"><div class="card-title">Portfolio analytics dashboard</div>
        <div class="card-text">Analyze return, volatility, Sharpe ratio, diversification, and correlations using the selected portfolio weights.</div></div>
        """, unsafe_allow_html=True)

        health_score = portfolio_health_score(len(tickers), volatility, sharpe)
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Expected Return", f"{expected_return:.2%}")
        a2.metric("Volatility", f"{volatility:.2%}")
        a3.metric("Sharpe Ratio", f"{sharpe:.2f}")
        a4.metric("Health Score", f"{health_score}/100")

        weights_df = pd.DataFrame({"Ticker": tickers, "Portfolio Weight": weights})
        weights_df["Portfolio Weight"] = weights_df["Portfolio Weight"].apply(lambda x: f"{x:.2%}")
        st.markdown("### Current Portfolio Weights")
        st.dataframe(weights_df, use_container_width=True)

        if len(tickers) >= 2:
            corr = returns.corr()
            fig_corr = px.imshow(corr, text_auto=True, title="Asset Correlation Matrix", color_continuous_scale=["#10B981", "#FFFFFF", "#EF4444"])
            st.plotly_chart(apply_clean_theme(fig_corr), use_container_width=True)
        else:
            st.caption("Add two or more tickers to see a correlation matrix.")

    with tab_optimize:
        st.markdown("""
        <div class="feature-card"><div class="card-title">Optimization studio</div>
        <div class="card-text">Run Monte Carlo simulations and find portfolios with stronger risk-adjusted performance.</div></div>
        """, unsafe_allow_html=True)

        if len(tickers) < 2:
            st.caption("Add two or more tickers to run the optimizer.")
        elif st.button("Run Portfolio Optimization"):
            portfolios = random_portfolios(prices)
            best_portfolio = portfolios.loc[portfolios["Sharpe"].idxmax()]
            min_vol_portfolio = portfolios.loc[portfolios["Volatility"].idxmin()]
            opt_weights = pd.DataFrame({
                "Ticker": prices.columns,
                "Max Sharpe Weight (%)": best_portfolio["Weights"] * 100,
                "Min Volatility Weight (%)": min_vol_portfolio["Weights"] * 100
            })
            st.dataframe(opt_weights, use_container_width=True)
            fig_frontier = px.scatter(portfolios, x="Volatility", y="Return", color="Sharpe", title="Efficient Frontier Simulation", color_continuous_scale="Viridis")
            fig_frontier.add_trace(go.Scatter(x=[best_portfolio["Volatility"]], y=[best_portfolio["Return"]], mode="markers", marker=dict(size=18, symbol="star", color="#F59E0B"), name="Max Sharpe"))
            fig_frontier.add_trace(go.Scatter(x=[min_vol_portfolio["Volatility"]], y=[min_vol_portfolio["Return"]], mode="markers", marker=dict(size=15, symbol="diamond", color="#0EA5E9"), name="Min Volatility"))
            st.plotly_chart(apply_clean_theme(fig_frontier), use_container_width=True)

        if st.button("Run Standard Monte Carlo Simulation"):
            mc = monte_carlo_simulation(current_savings, monthly_savings, expected_return, volatility, horizon, contribution_growth_rate, simulations=500)
            final_values = mc.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("10th Percentile", f"${np.percentile(final_values, 10):,.0f}")
            m2.metric("Median", f"${np.percentile(final_values, 50):,.0f}")
            m3.metric("90th Percentile", f"${np.percentile(final_values, 90):,.0f}")
            fig_mc = go.Figure()
            for i in range(min(50, mc.shape[1])):
                fig_mc.add_trace(go.Scatter(y=mc.iloc[:, i], mode="lines", opacity=0.22, line=dict(color="#10B981"), showlegend=False))
            fig_mc.update_layout(title="Standard Monte Carlo Portfolio Paths With Rising Contributions", xaxis_title="Months", yaxis_title="Portfolio Value")
            st.plotly_chart(apply_clean_theme(fig_mc), use_container_width=True)

    with tab_macro:
        st.markdown("""
        <div class="feature-card"><div class="card-title">Macro Risk Simulator</div>
        <div class="card-text">Stress-test the portfolio under policy uncertainty, trade uncertainty, geopolitical risk, and recession-style scenarios.</div></div>
        """, unsafe_allow_html=True)

        mm1, mm2, mm3, mm4 = st.columns(4)
        mm1.metric("Macro Score", f"{macro_score}/100")
        mm2.metric("Macro Regime", macro_label)
        mm3.metric("Scenario", macro_scenario)
        mm4.metric("Scenario Risk", scenario_data["risk_label"])

        st.markdown(f"""<div class="risk-box"><b>Scenario explanation:</b> {scenario_data["explanation"]}</div>""", unsafe_allow_html=True)

        macro_inputs_df = pd.DataFrame({
            "Indicator": ["Economic Policy Uncertainty", "Trade Policy Uncertainty", "Geopolitical Risk"],
            "Input Value": [epu_input, tpu_input, gpr_input]
        })
        fig_macro = px.bar(macro_inputs_df, x="Indicator", y="Input Value", color="Indicator", title="Macro Uncertainty Indicators", color_discrete_sequence=["#10B981", "#0EA5E9", "#EF4444"])
        st.plotly_chart(apply_clean_theme(fig_macro), use_container_width=True)

        scenario_df = pd.DataFrame({
            "Metric": ["Base Expected Return", "Macro-Adjusted Return", "Base Volatility", "Macro-Adjusted Volatility"],
            "Value": [f"{expected_return:.2%}", f"{adjusted_return:.2%}", f"{volatility:.2%}", f"{adjusted_volatility:.2%}"]
        })
        st.dataframe(scenario_df, use_container_width=True)

        if st.button("Run Macro-Adjusted Monte Carlo Simulation"):
            macro_mc = monte_carlo_simulation(current_savings, monthly_savings, adjusted_return, adjusted_volatility, horizon, contribution_growth_rate, simulations=500)
            final_values = macro_mc.iloc[-1]
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Stress Case 10th Percentile", f"${np.percentile(final_values, 10):,.0f}")
            mc2.metric("Median Outcome", f"${np.percentile(final_values, 50):,.0f}")
            mc3.metric("Upside Case 90th Percentile", f"${np.percentile(final_values, 90):,.0f}")
            fig_macro_mc = go.Figure()
            for i in range(min(50, macro_mc.shape[1])):
                fig_macro_mc.add_trace(go.Scatter(y=macro_mc.iloc[:, i], mode="lines", opacity=0.22, line=dict(color="#EF4444"), showlegend=False))
            fig_macro_mc.update_layout(title=f"Macro-Adjusted Monte Carlo Simulation: {macro_scenario}", xaxis_title="Months", yaxis_title="Portfolio Value")
            st.plotly_chart(apply_clean_theme(fig_macro_mc), use_container_width=True)

        st.info("This module uses scenario-based assumptions rather than a formal econometric model. It is designed to be explainable and useful for a class project.")

    with tab_protect:
        st.markdown("""
        <div class="feature-card"><div class="card-title">Protection and hedging lab</div>
        <div class="card-text">Estimate beta, downside risk, hedged allocation, and stress-test portfolio performance.</div></div>
        """, unsafe_allow_html=True)

        try:
            beta = calculate_portfolio_beta(prices, weights, period, demo_mode)
            pp1, pp2, pp3 = st.columns(3)
            pp1.metric("Beta vs SPY", f"{beta:.2f}")
            pp2.metric("Current Volatility", f"{volatility:.2%}")
            if beta > 1.2:
                hedge_signal = "High Market Risk"
            elif beta < 0.8:
                hedge_signal = "Defensive"
            else:
                hedge_signal = "Moderate Risk"
            pp3.metric("Hedge Signal", hedge_signal)

            hedge_result = hedge_portfolio_analysis(prices, weights, current_savings, period, risk_free_rate, demo_mode)
            if hedge_result is not None:
                hedge_comparison, hedge_weights_df = hedge_result
                st.markdown("""<div class="accent-box">The hedge simulation shifts 20% of the portfolio into defensive assets (BND and GLD).</div>""", unsafe_allow_html=True)
                st.dataframe(hedge_comparison, use_container_width=True)
                fig_hedge = px.bar(hedge_weights_df, x="Asset", y="Hedged Weight (%)", title="Suggested Hedged Allocation", color="Asset", color_discrete_sequence=colors)
                st.plotly_chart(apply_clean_theme(fig_hedge), use_container_width=True)
            else:
                st.caption("Your portfolio already contains the hedge assets, so no extra hedge is added.")
        except Exception:
            st.warning("Beta and hedging analysis is unavailable right now (benchmark data could not load).")

        st.markdown("### Stress Test Scenarios")
        st.dataframe(stress_test(weights), use_container_width=True)
        st.info("This hedging module is simplified for educational purposes. A real platform would use live options data, liquidity, taxes, and regulatory suitability checks.")

    # ---------- AI ADVISOR SUMMARY ----------
    st.markdown("""
    <div class="feature-card"><div class="card-title">AI Advisor Summary</div>
    <div class="card-text">A recommendation engine explains risk profile, contribution growth, dividend potential, portfolio efficiency, allocation suitability, and macro-risk exposure.</div></div>
    """, unsafe_allow_html=True)

    ai_recs = enhanced_ai_recommendation(age, risk_tolerance, horizon, score, expected_return, volatility, sharpe, allocation, macro_label, portfolio_dividend_yield, salary_growth_rate, contribution_growth_rate)

    if ANTHROPIC_KEY:
        if st.button("Generate AI advisor note"):
            profile = {"age": age, "risk_tolerance": risk_tolerance, "horizon": horizon,
                       "annual_income": annual_income, "current_savings": current_savings,
                       "monthly_savings": monthly_savings, "risk_score": score}
            metrics = {"expected_return": expected_return, "volatility": volatility, "sharpe": sharpe,
                       "dividend_yield": portfolio_dividend_yield, "risk_free_rate": risk_free_rate}
            macro = {"label": macro_label, "score": macro_score, "scenario": macro_scenario}
            note = generate_ai_advisor_note(ANTHROPIC_KEY, profile, metrics, allocation, macro)
            if note:
                st.markdown(f'<div class="advisor-box">{note}</div>', unsafe_allow_html=True)
            else:
                st.caption("AI note unavailable right now — showing the rule-based summary below.")

    for rec in ai_recs:
        st.markdown(f"- {rec}")

except Exception:
    st.warning("Market data is taking a moment to load. Try again, check your ticker symbols, or switch on Demo mode in the sidebar to use saved data.")

st.divider()
st.caption("Built with Streamlit, yfinance, pandas, numpy, and plotly.")
