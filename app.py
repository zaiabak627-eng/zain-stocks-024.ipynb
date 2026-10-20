
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Zenstar024 | PSX Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# PREMIUM DASHBOARD DESIGN
# --------------------------------------------------
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
h1, h2, h3 {
    color: #e5c887 !important;
    font-family: 'Playfair Display', serif !important;
}
p, label, span {
    color: #f4f0e7;
}
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #1b3528, #102219);
    border: 1px solid #41644b;
    padding: 18px;
    border-radius: 15px;
    box-shadow: 0 5px 18px rgba(0,0,0,0.22);
}
div[data-testid="stMetricLabel"] {
    color: #c9d7c9 !important;
}
div[data-testid="stMetricValue"] {
    color: #e5c887 !important;
}
div.stButton > button, div.stDownloadButton > button {
    background: linear-gradient(90deg, #d7b56d, #f0d99e);
    color: #102018;
    border: none;
    border-radius: 10px;
    font-weight: 700;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background: #f7e7b5;
    color: #081510;
    border: none;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    background-color: #16291f;
    border-color: #41644b;
}
hr {
    border-color: #345542;
}
.hero {
    padding: 28px 30px;
    border: 1px solid #45664b;
    border-radius: 20px;
    background: linear-gradient(115deg, #193b29, #102219 65%, #352c18);
    margin-bottom: 24px;
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 42px;
    font-weight: 700;
    color: #e5c887;
    margin-bottom: 5px;
}
.hero-subtitle {
    color: #d4dfd2;
    font-size: 15px;
    letter-spacing: 2px;
}
.small-note {
    color: #aebcaf;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="hero-title">ZENSTAR024</div>
    <div class="hero-subtitle">PSX STOCK DASHBOARD · MARKET INSIGHTS</div>
    <p style="margin-top:18px; margin-bottom:0;">
        Explore stock prices, monitor performance, and analyze market trends.
    </p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# SIDEBAR CONTROLS
# --------------------------------------------------
st.sidebar.markdown("## 📊 Dashboard Controls")
st.sidebar.markdown("Customize your stock analysis below.")

today = date.today()
default_start = today - timedelta(days=365)

start_date = st.sidebar.date_input(
    "Start date",
    value=default_start,
    max_value=today
)
end_date = st.sidebar.date_input(
    "End date",
    value=today,
    max_value=today
)

# Common PSX symbols. Availability depends on the data provider.
default_symbols = [
    "OGDC", "PPL", "LUCK", "HBL", "UBL",
    "MEBL", "MCB", "FFC", "ENGRO", "PSO",
    "SYS", "TRG", "HUBC", "KEL", "POL"
]

# --------------------------------------------------
# LOAD PSX DATA
# --------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def load_tickers():
    import psxdata
    result = psxdata.tickers()

    if isinstance(result, pd.DataFrame):
        if "symbol" in result.columns:
            symbols = result["symbol"].astype(str).tolist()
        elif "ticker" in result.columns:
            symbols = result["ticker"].astype(str).tolist()
        else:
            symbols = result.iloc[:, 0].astype(str).tolist()
    elif isinstance(result, dict):
        symbols = list(result.keys())
    else:
        symbols = list(result)

    return sorted(set(s.strip().upper() for s in symbols if str(s).strip()))


@st.cache_data(ttl=900, show_spinner=False)
def load_stock_data(symbol, start_string, end_string):
    import psxdata

    data = psxdata.stocks(
        symbol,
        start=start_string,
        end=end_string
    )

    if data is None:
        return pd.DataFrame()

    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)

    data = data.copy()
    data.columns = [str(c).strip().lower().replace(" ", "_") for c in data.columns]

    # Find a date column if the provider did not use the index.
    possible_dates = ["date", "datetime", "timestamp", "time"]
    date_column = next((c for c in possible_dates if c in data.columns), None)

    if date_column:
        data[date_column] = pd.to_datetime(data[date_column], errors="coerce")
        data = data.set_index(date_column)
    else:
        data.index = pd.to_datetime(data.index, errors="coerce")

    data = data.loc[~data.index.isna()].sort_index()

    # Normalize common column names.
    aliases = {
        "close_price": "close",
        "closing_price": "close",
        "adj_close": "close",
        "adjusted_close": "close",
        "open_price": "open",
        "high_price": "high",
        "low_price": "low",
        "traded_volume": "volume"
    }
    data = data.rename(columns=aliases)

    # Keep numeric market columns numeric.
    for col in ["open", "high", "low", "close", "volume"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    if "close" not in data.columns:
        raise ValueError(
            "The data provider did not return a 'close' price column. "
            "Please check the provider's returned data format."
        )

    data = data.dropna(subset=["close"])
    data = data[~data.index.duplicated(keep="last")]

    return data


# --------------------------------------------------
# SELECT STOCK
# --------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏢 Select a Stock")

try:
    available_symbols = load_tickers()
    if not available_symbols:
        available_symbols = default_symbols
except Exception:
    available_symbols = default_symbols
    st.sidebar.warning(
        "Could not retrieve the live ticker list. Using common PSX symbols."
    )

preferred_defaults = [
    s for s in default_symbols if s in available_symbols
]
initial_symbol = preferred_defaults[0] if preferred_defaults else available_symbols[0]

symbol = st.sidebar.selectbox(
    "PSX symbol",
    options=available_symbols,
    index=available_symbols.index(initial_symbol)
)

show_sma = st.sidebar.checkbox("Show moving averages", value=True)
show_volume = st.sidebar.checkbox("Show volume chart", value=True)
show_rsi = st.sidebar.checkbox("Show RSI indicator", value=True)

st.sidebar.markdown("---")
st.sidebar.caption("Zenstar024 · Stock analysis dashboard")
st.sidebar.caption("Market data may be delayed or unavailable.")

# --------------------------------------------------
# VALIDATE DATES
# --------------------------------------------------
if start_date >= end_date:
    st.error("Please choose a start date earlier than the end date.")
    st.stop()

# --------------------------------------------------
# FETCH SELECTED STOCK
# --------------------------------------------------
try:
    with st.spinner(f"Loading market data for {symbol}..."):
        df = load_stock_data(
            symbol,
            start_date.isoformat(),
            end_date.isoformat()
        )
except Exception as exc:
    st.error(f"Could not load data for {symbol}.")
    st.warning(
        "The market-data provider may be unavailable, the symbol may not "
        "be supported, or its response format may have changed."
    )
    with st.expander("Technical error details"):
        st.code(str(exc))
    st.info(
        "Check that `requirements.txt` is in your repository root and "
        "contains streamlit, pandas, numpy, plotly, and psxdata."
    )
    st.stop()

if df.empty:
    st.warning(
        f"No price data was returned for {symbol} in the selected date range. "
        "Try another symbol or a wider date range."
    )
    st.stop()

# --------------------------------------------------
# CALCULATE INDICATORS
# --------------------------------------------------
df["daily_change"] = df["close"].diff()
df["daily_return"] = df["close"].pct_change() * 100
df["SMA 20"] = df["close"].rolling(window=20).mean()
df["SMA 50"] = df["close"].rolling(window=50).mean()

gain = df["daily_change"].clip(lower=0)
loss = -df["daily_change"].clip(upper=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
relative_strength = avg_gain / avg_loss.replace(0, np.nan)
df["RSI"] = 100 - (100 / (1 + relative_strength))

latest_price = float(df["close"].iloc[-1])
first_price = float(df["close"].iloc[0])
price_change = latest_price - first_price
percentage_change = (
    (latest_price / first_price - 1) * 100
    if first_price else 0
)
high_price = float(df["close"].max())
low_price = float(df["close"].min())
latest_rsi = df["RSI"].dropna().iloc[-1] if df["RSI"].notna().any() else np.nan

# --------------------------------------------------
# SUMMARY METRICS
# --------------------------------------------------
st.markdown(f"## 📈 {symbol} Market Overview")
st.caption(
    f"Period: {start_date.strftime('%d %b %Y')} – "
    f"{end_date.strftime('%d %b %Y')} · "
    f"{len(df):,} price records"
)

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Latest Close",
    f"PKR {latest_price:,.2f}",
    f"{price_change:+,.2f} PKR"
)
m2.metric(
    "Period Return",
    f"{percentage_change:+.2f}%"
)
m3.metric(
    "Period High",
    f"PKR {high_price:,.2f}"
)
m4.metric(
    "Period Low",
    f"PKR {low_price:,.2f}"
)

st.markdown("---")

# --------------------------------------------------
# PRICE CHART
# --------------------------------------------------
st.markdown("### 📉 Historical Price Analysis")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["close"],
        mode="lines",
        name="Closing Price",
        line=dict(color="#e5c887", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(229,200,135,0.08)"
    )
)

if show_sma:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA 20"],
            mode="lines",
            name="20-day SMA",
            line=dict(color="#65c7a2", width=1.6, dash="dot")
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA 50"],
            mode="lines",
            name="50-day SMA",
            line=dict(color="#d98b66", width=1.6, dash="dash")
        )
    )

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(12,28,20,0.8)",
    font=dict(color="#f4f0e7", family="DM Sans"),
    height=480,
    margin=dict(l=15, r=15, t=30, b=15),
    hovermode="x unified",
    legend=dict(orientation="h", y=1.12),
    xaxis_title="Date",
    yaxis_title="Price (PKR)"
)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(gridcolor="rgba(180,200,180,0.12)")

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# VOLUME CHART
# --------------------------------------------------
if show_volume and "volume" in df.columns:
    st.markdown("### 📊 Trading Volume")

    volume_fig = go.Figure()
    volume_fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["volume"],
            name="Volume",
            marker_color="#65a982"
        )
    )
    volume_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,28,20,0.8)",
        font=dict(color="#f4f0e7"),
        height=280,
        margin=dict(l=15, r=15, t=20, b=15),
        xaxis_title="Date",
        yaxis_title="Volume"
    )
    st.plotly_chart(volume_fig, use_container_width=True)

# --------------------------------------------------
# RSI INDICATOR
# --------------------------------------------------
if show_rsi:
    st.markdown("### ⚖️ Relative Strength Index (RSI)")

    rsi_fig = go.Figure()
    rsi_fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI"],
            mode="lines",
            name="RSI",
            line=dict(color="#d8b56a", width=2)
        )
    )
    rsi_fig.add_hline(
        y=70,
        line_dash="dash",
        line_color="#e87979",
        annotation_text="Potentially overbought (70)"
    )
    rsi_fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="#65c7a2",
        annotation_text="Potentially oversold (30)"
    )
    rsi_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,28,20,0.8)",
        font=dict(color="#f4f0e7"),
        height=280,
        margin=dict(l=15, r=15, t=20, b=15),
        yaxis=dict(range=[0, 100], title="RSI"),
        xaxis_title="Date"
    )
    st.plotly_chart(rsi_fig, use_container_width=True)

    if pd.notna(latest_rsi):
        if latest_rsi >= 70:
            st.warning(
                f"Latest RSI is {latest_rsi:.1f}. This is often described "
                "as an overbought zone, but it is not a guaranteed sell signal."
            )
        elif latest_rsi <= 30:
            st.info(
                f"Latest RSI is {latest_rsi:.1f}. This is often described "
                "as an oversold zone, but it is not a guaranteed buy signal."
            )
        else:
            st.success(
                f"Latest RSI is {latest_rsi:.1f}, within the commonly "
                "observed 30–70 range."
            )

# --------------------------------------------------
# DAILY RETURNS
# --------------------------------------------------
st.markdown("### 📅 Daily Price Changes")

returns = df[["close", "daily_change", "daily_return"]].copy()
returns = returns.rename(
    columns={
        "close": "Closing Price (PKR)",
        "daily_change": "Change (PKR)",
        "daily_return": "Daily Return (%)"
    }
)
returns.index.name = "Date"

st.dataframe(
    returns.sort_index(ascending=False),
    use_container_width=True,
    height=320
)

# --------------------------------------------------
# DOWNLOAD DATA
# --------------------------------------------------
st.markdown("### ⬇️ Export Data")

download_df = df.copy()
download_df.index.name = "Date"
csv_data = download_df.to_csv().encode("utf-8")

st.download_button(
    label="Download Stock Data as CSV",
    data=csv_data,
    file_name=f"zenstar024_{symbol.lower()}_stock_data.csv",
    mime="text/csv"
)

st.markdown("---")
st.markdown(
    "<p class='small-note'>"
    "Zenstar024 · PSX Stock Dashboard. For educational and informational "
    "purposes only. Market data may be delayed, incomplete, or inaccurate. "
    "This dashboard does not provide financial advice."
    "</p>",
    unsafe_allow_html=True
)
