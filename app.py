
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(
    page_title="Zenstar024 | PSX Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- PREMIUM DASHBOARD DESIGN ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

.stApp {
    background: linear-gradient(135deg, #081510 0%, #10251d 55%, #151b17 100%);
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
    background: linear-gradient(120deg, #173b2a, #18251e 75%);
    margin-bottom: 22px;
}
.hero h1 {
    font-family: 'Playfair Display', serif;
    font-size: 42px;
    margin: 0;
}
.hero p { color: #d4cbb8; margin-bottom: 0; }
.metric {
    background: rgba(35, 61, 45, 0.75);
    border: 1px solid #46674f;
    border-radius: 15px;
    padding: 16px;
}
.small-note { color: #b7c5b9; font-size: 13px; }
div.stButton > button {
    background: #d9b777;
    color: #132018;
    border: 0;
    border-radius: 10px;
    font-weight: 700;
}
div.stButton > button:hover {
    background: #f0d7a0;
    color: #132018;
}
</style>
""", unsafe_allow_html=True)

# ---------- DATA HELPERS ----------
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
        if symbol_col:
            symbols = df[symbol_col].astype(str).tolist()
        else:
            symbols = df.index.astype(str).tolist()
    elif isinstance(result, (list, tuple, pd.Series, np.ndarray)):
        symbols = [str(x) for x in result]
    else:
        symbols = []

    return sorted(set(
        s.strip().upper() for s in symbols
        if s and str(s).strip() and str(s).lower() != "nan"
    ))


@st.cache_data(ttl=900, show_spinner=False)
def load_history(symbol, start_date, end_date):
    import psxdata

    data = psxdata.stocks(
        symbol,
        start=start_date,
        end=end_date
    )

    if data is None:
        return pd.DataFrame()

    df = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if df.empty:
        return df

    df.columns = [str(c).strip().lower() for c in df.columns]

    # Move a date-like index into a column when necessary.
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

    # Normalize common column names.
    aliases = {
        "open": ["open", "opening", "open_price"],
        "high": ["high", "highest", "high_price"],
        "low": ["low", "lowest", "low_price"],
        "close": ["close", "closing", "close_price", "price"],
        "volume": ["volume", "vol", "shares"],
    }

    rename = {}
    for standard, choices in aliases.items():
        found = next((c for c in choices if c in df.columns), None)
        if found:
            rename[found] = standard
    df = df.rename(columns=rename)

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "close" not in df.columns:
        return pd.DataFrame()

    # Provide usable chart columns if the provider omits OHLC fields.
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


def money(value):
    if pd.isna(value):
        return "—"
    return f"PKR {value:,.2f}"


# ---------- SIDEBAR ----------
st.sidebar.markdown("## 📈 Zenstar024")
st.sidebar.caption("PAKISTAN STOCK EXCHANGE")

try:
    available_symbols = load_tickers()
except Exception as exc:
    available_symbols = []
    st.sidebar.error(
        "Could not load the PSX ticker list. Check the app logs and internet connection."
    )

default_options = ["OGDC", "LUCK", "HBL", "UBL", "MCB", "FFC", "PSO"]
symbols = sorted(set(available_symbols + default_options))

selected_symbol = st.sidebar.selectbox(
    "Select stock symbol",
    symbols,
    index=symbols.index("OGDC") if "OGDC" in symbols else 0,
)

period_label = st.sidebar.selectbox(
    "Historical period",
    ["3 months", "6 months", "1 year", "2 years", "3 years", "5 years"],
    index=2,
)
period_days = {
    "3 months": 90,
    "6 months": 182,
    "1 year": 365,
    "2 years": 730,
    "3 years": 1095,
    "5 years": 1825,
}
end_date = date.today()
start_date = end_date - timedelta(days=period_days[period_label])

st.sidebar.markdown("---")
st.sidebar.caption("Data provider: psxdata")
st.sidebar.caption("Prices and availability may vary by symbol.")

# ---------- HERO ----------
st.markdown("""
<div class="hero">
    <h1>ZENSTAR024</h1>
    <p>PSX MARKET INTELLIGENCE · STOCK ANALYTICS · PRICE TRACKING</p>
    <p>Explore historical prices, trends and trading activity.</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Educational analytics dashboard. Historical data is supplied by a third-party "
    "data library and may be delayed, incomplete, or unavailable."
)

# ---------- LOAD SELECTED STOCK ----------
try:
    with st.spinner(f"Loading historical data for {selected_symbol}..."):
        history = load_history(
            selected_symbol,
            start_date.isoformat(),
            end_date.isoformat(),
        )
except Exception as exc:
    history = pd.DataFrame()
    st.error(
        "The PSX data provider could not return this stock's history. "
        "Try another symbol or check the Streamlit app logs."
    )

if history.empty:
    st.warning(
        f"No usable historical data was returned for {selected_symbol}. "
        "Try another symbol or a different historical period."
    )
    st.info(
        "If this happens for every symbol, check that psxdata is installed "
        "and that the provider is reachable."
    )
    st.stop()

# ---------- SUMMARY METRICS ----------
latest = history.iloc[-1]
previous_close = (
    history.iloc[-2]["close"] if len(history) > 1 else latest["close"]
)
change = latest["close"] - previous_close
change_pct = (
    change / previous_close * 100 if previous_close else np.nan
)
first_close = history.iloc[0]["close"]
period_return = (
    (latest["close"] / first_close - 1) * 100 if first_close else np.nan
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Latest available close", money(latest["close"]), f"{change_pct:+.2f}%")
m2.metric("Period return", f"{period_return:+.2f}%")
m3.metric("Period high", money(history["high"].max()))
m4.metric("Period low", money(history["low"].min()))

st.caption(
    f"Showing {len(history):,} trading records · "
    f"{history['date'].min().date()} to {history['date'].max().date()} · "
    f"Selected symbol: {selected_symbol}"
)

# ---------- PRICE CHART ----------
st.subheader(f"📊 {selected_symbol} — Price History")

chart_mode = st.radio(
    "Chart type",
    ["Candlestick", "Closing price"],
    horizontal=True,
)

fig = go.Figure()

if chart_mode == "Candlestick":
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
        x=history["date"],
        y=history["close"],
        mode="lines",
        name="Closing price",
        line=dict(width=2),
    ))

fig.add_trace(go.Scatter(
    x=history["date"], y=history["SMA 20"],
    mode="lines", name="SMA 20",
    line=dict(width=1.5, dash="dot"),
))
fig.add_trace(go.Scatter(
    x=history["date"], y=history["SMA 50"],
    mode="lines", name="SMA 50",
    line=dict(width=1.5, dash="dash"),
))

fig.update_layout(
    template="plotly_dark",
    height=520,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(8,21,16,0.5)",
    font=dict(color="#f4f0e7"),
    xaxis_title="Date",
    yaxis_title="Price (PKR)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(l=10, r=10, t=50, b=10),
    xaxis_rangeslider_visible=False,
)
st.plotly_chart(fig, use_container_width=True)

# ---------- INDICATORS ----------
left, right = st.columns(2)

with left:
    st.subheader("📉 RSI — Momentum")
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(
        x=history["date"],
        y=history["RSI 14"],
        mode="lines",
        name="RSI 14",
    ))
    rsi_fig.add_hline(y=70, line_dash="dash")
    rsi_fig.add_hline(y=30, line_dash="dash")
    rsi_fig.update_layout(
        template="plotly_dark",
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,21,16,0.5)",
        yaxis=dict(range=[0, 100], title="RSI"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(rsi_fig, use_container_width=True)

with right:
    st.subheader("📦 Trading Volume")
    volume_fig = go.Figure()
    volume_fig.add_trace(go.Bar(
        x=history["date"],
        y=history["volume"],
        name="Volume",
    ))
    volume_fig.update_layout(
        template="plotly_dark",
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,21,16,0.5)",
        yaxis_title="Shares",
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(volume_fig, use_container_width=True)

# ---------- DATA TABLE + DOWNLOAD ----------
st.subheader("📋 Historical Data")
show_columns = [
    "date", "open", "high", "low", "close", "volume",
    "Daily Change %", "SMA 20", "SMA 50", "RSI 14"
]
table = history[[c for c in show_columns if c in history.columns]].copy()
table["date"] = table["date"].dt.strftime("%Y-%m-%d")

st.dataframe(table.tail(100).iloc[::-1], use_container_width=True, hide_index=True)

csv_data = history.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download historical data (CSV)",
    data=csv_data,
    file_name=f"zenstar024_{selected_symbol.lower()}_history.csv",
    mime="text/csv",
)

with st.expander("About the indicators"):
    st.write(
        "**SMA 20 / SMA 50:** rolling averages of closing prices. "
        "**RSI 14:** a momentum indicator commonly interpreted using 30 and 70 "
        "reference levels. These indicators are informational, not trading advice."
    )

st.markdown("---")
st.caption(
    "ZENSTAR024 · Built with Streamlit, Plotly, pandas and psxdata. "
    "Not investment advice. Verify prices with official PSX sources before trading."
)
