
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(
    page_title="Zenstar024 | PSX Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
.stApp {
    background: linear-gradient(135deg, #081510, #10251d, #151b17);
    color: #f4f0e7;
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #10251d, #09130f);
    border-right: 1px solid #345542;
}
h1, h2, h3 { color: #f0d7a0 !important; }
.hero {
    padding: 28px;
    border: 1px solid #46674f;
    border-radius: 22px;
    background: linear-gradient(120deg, #173b2a, #18251e);
    margin-bottom: 22px;
}
.hero h1 {
    font-family: 'Playfair Display', serif;
    font-size: 42px;
    margin: 0;
}
.hero p { color: #d4cbb8; }
div.stButton > button, div.stDownloadButton > button {
    background: #d9b777;
    color: #132018;
    border: 0;
    border-radius: 10px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

DEFAULT_SYMBOLS = ["OGDC", "LUCK", "HBL", "UBL", "MCB", "FFC", "PSO"]


@st.cache_data(ttl=900, show_spinner=False)
def load_tickers():
    import psxdata
    result = psxdata.tickers()

    if isinstance(result, pd.DataFrame):
        df = result.copy()
        symbol_col = next(
            (c for c in df.columns if str(c).lower() in
             ["symbol", "ticker", "code", "stock_symbol"]),
            None
        )
        values = (
            df[symbol_col].astype(str).tolist()
            if symbol_col else df.index.astype(str).tolist()
        )
    elif isinstance(result, (list, tuple, pd.Series, np.ndarray)):
        values = [str(item) for item in result]
    else:
        values = []

    return sorted({
        value.strip().upper()
        for value in values
        if value and value.strip() and value.lower() != "nan"
    })


def calculate_rsi(series, period=14):
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(
        alpha=1 / period, min_periods=period, adjust=False
    ).mean()
    avg_loss = losses.ewm(
        alpha=1 / period, min_periods=period, adjust=False
    ).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


@st.cache_data(ttl=900, show_spinner=False)
def load_history(symbol, start_date, end_date):
    import psxdata
    raw = psxdata.stocks(symbol, start=start_date, end=end_date)

    if raw is None:
        return pd.DataFrame()

    df = raw.copy() if isinstance(raw, pd.DataFrame) else pd.DataFrame(raw)
    if df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip().lower() for c in df.columns]

    if not any(c in df.columns for c in ["date", "datetime", "time"]):
        df = df.reset_index()
        df.columns = [str(c).strip().lower() for c in df.columns]

    date_col = next(
        (c for c in df.columns if c in ["date", "datetime", "time", "index"]),
        None
    )
    if date_col is None:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["date"])

    aliases = {
        "open": ["open", "opening", "open_price"],
        "high": ["high", "highest", "high_price"],
        "low": ["low", "lowest", "low_price"],
        "close": ["close", "closing", "close_price", "price"],
        "volume": ["volume", "vol", "shares"],
    }

    rename = {}
    for standard, alternatives in aliases.items():
        found = next((c for c in alternatives if c in df.columns), None)
        if found:
            rename[found] = standard
    df = df.rename(columns=rename)

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "close" not in df.columns:
        return pd.DataFrame()

    for col in ["open", "high", "low"]:
        if col not in df.columns:
            df[col] = df["close"]
        else:
            df[col] = df[col].fillna(df["close"])

    if "volume" not in df.columns:
        df["volume"] = 0
    df["volume"] = df["volume"].fillna(0)

    df = (
        df.dropna(subset=["close"])
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )
    df = df[df["close"] > 0].copy()

    df["SMA 20"] = df["close"].rolling(20).mean()
    df["SMA 50"] = df["close"].rolling(50).mean()
    df["Daily Change %"] = df["close"].pct_change() * 100
    df["RSI 14"] = calculate_rsi(df["close"])
    return df


def money(value):
    return "—" if pd.isna(value) else f"PKR {value:,.2f}"


# Sidebar
st.sidebar.markdown("## 📈 Zenstar024")
st.sidebar.caption("PAKISTAN STOCK EXCHANGE")

try:
    tickers = load_tickers()
    ticker_error = False
except Exception:
    tickers = []
    ticker_error = True

options = sorted(set(tickers + DEFAULT_SYMBOLS))
symbol = st.sidebar.selectbox(
    "Select stock symbol",
    options,
    index=options.index("OGDC") if "OGDC" in options else 0,
)

period = st.sidebar.selectbox(
    "Historical period",
    ["3 months", "6 months", "1 year", "2 years", "3 years", "5 years"],
    index=2,
)
days = {
    "3 months": 90,
    "6 months": 182,
    "1 year": 365,
    "2 years": 730,
    "3 years": 1095,
    "5 years": 1825,
}
end_date = date.today()
start_date = end_date - timedelta(days=days[period])

st.markdown("""
<div class="hero">
    <h1>ZENSTAR024</h1>
    <p>PSX MARKET INTELLIGENCE · STOCK ANALYTICS · PRICE TRACKING</p>
    <p>Explore historical prices, trends, momentum and trading activity.</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Educational dashboard. Data may be delayed, incomplete, or unavailable. "
    "Verify prices with official PSX sources."
)

if ticker_error:
    st.sidebar.warning("The live ticker list could not be loaded.")

try:
    with st.spinner(f"Loading historical data for {symbol}..."):
        history = load_history(
            symbol, start_date.isoformat(), end_date.isoformat()
        )
except Exception:
    history = pd.DataFrame()
    st.error(
        "The data provider could not return stock history. Try another symbol "
        "or check Manage app → Logs."
    )

if history.empty:
    st.warning(
        f"No usable historical data was returned for {symbol}. "
        "Try another stock or historical period."
    )
    st.stop()

latest = history.iloc[-1]
previous = history.iloc[-2]["close"] if len(history) > 1 else latest["close"]
change_pct = (
    (latest["close"] - previous) / previous * 100 if previous else np.nan
)
first_close = history.iloc[0]["close"]
period_return = (
    (latest["close"] / first_close - 1) * 100 if first_close else np.nan
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest available close", money(latest["close"]), f"{change_pct:+.2f}%")
c2.metric("Period return", f"{period_return:+.2f}%")
c3.metric("Period high", money(history["high"].max()))
c4.metric("Period low", money(history["low"].min()))

st.caption(
    f"{len(history):,} records · {history['date'].min().date()} to "
    f"{history['date'].max().date()} · Symbol: {symbol}"
)

# Price chart
st.subheader(f"📊 {symbol} — Price History")
chart_type = st.radio(
    "Chart type", ["Candlestick", "Closing price"], horizontal=True
)
fig = go.Figure()

if chart_type == "Candlestick":
    fig.add_trace(go.Candlestick(
        x=history["date"],
        open=history["open"],
        high=history["high"],
        low=history["low"],
        close=history["close"],
        name="OHLC",
    ))
else:
    fig.add_trace(go.Scatter(
        x=history["date"], y=history["close"],
        mode="lines", name="Closing price",
    ))

fig.add_trace(go.Scatter(
    x=history["date"], y=history["SMA 20"],
    mode="lines", name="SMA 20",
))
fig.add_trace(go.Scatter(
    x=history["date"], y=history["SMA 50"],
    mode="lines", name="SMA 50",
))

fig.update_layout(
    template="plotly_dark",
    height=510,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,21,16,0.5)",
    font=dict(color="#f4f0e7"),
    xaxis_title="Date",
    yaxis_title="Price (PKR)",
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(fig, use_container_width=True)

# RSI and volume
left, right = st.columns(2)

with left:
    st.subheader("📉 RSI — Momentum")
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(
        x=history["date"], y=history["RSI 14"],
        mode="lines", name="RSI 14",
    ))
    rsi_fig.add_hline(y=70, line_dash="dash")
    rsi_fig.add_hline(y=30, line_dash="dash")
    rsi_fig.update_layout(
        template="plotly_dark",
        height=300,
        yaxis=dict(range=[0, 100], title="RSI"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,21,16,0.5)",
    )
    st.plotly_chart(rsi_fig, use_container_width=True)

with right:
    st.subheader("📦 Trading Volume")
    volume_fig = go.Figure()
    volume_fig.add_trace(go.Bar(
        x=history["date"], y=history["volume"], name="Volume"
    ))
    volume_fig.update_layout(
        template="plotly_dark",
        height=300,
        yaxis_title="Shares",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,21,16,0.5)",
    )
    st.plotly_chart(volume_fig, use_container_width=True)

# Data table and download
st.subheader("📋 Historical Data")
show_cols = [
    "date", "open", "high", "low", "close", "volume",
    "Daily Change %", "SMA 20", "SMA 50", "RSI 14",
]
table = history[[c for c in show_cols if c in history.columns]].copy()
table["date"] = table["date"].dt.strftime("%Y-%m-%d")
st.dataframe(
    table.tail(100).iloc[::-1],
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "⬇️ Download historical data (CSV)",
    data=history.to_csv(index=False).encode("utf-8"),
    file_name=f"zenstar024_{symbol.lower()}_history.csv",
    mime="text/csv",
)

with st.expander("About the indicators"):
    st.write(
        "**SMA 20 / SMA 50:** rolling averages of closing prices. "
        "**RSI 14:** a momentum indicator often viewed with 30 and 70 reference levels. "
        "These indicators are informational, not trading advice."
    )

st.markdown("---")
st.caption(
    "ZENSTAR024 · Built with Streamlit, Plotly, pandas and psxdata. "
    "Not investment advice."
)
