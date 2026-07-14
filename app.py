import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from data_fetcher import get_stock_info, get_historical_data, get_market_data, get_sp500_dataframe
from database import init_db, add_transaction, get_portfolio_summary, get_cash_balance, get_net_deposits, get_all_transactions, delete_transaction, reset_database
from analytics import build_portfolio_history

# Initialize database on startup
init_db()

# --- UI Setup ---
st.set_page_config(page_title="Portfolio Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for Premium Look ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #1e1e2d;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    /* MAGIC TABS: Turn horizontal radio into premium tabs */
    div[data-testid="stRadio"] > div {
        border-bottom: 1px solid #333;
        gap: 0px !important;
    }
    
    /* Hide the radio button circles */
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }
    
    /* Style the text containers to look like tabs */
    div[data-testid="stRadio"] label > div:last-child {
        padding: 10px 16px;
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
        margin-right: 5px;
        border-radius: 5px 5px 0 0;
    }
    
    /* Target the text itself */
    div[data-testid="stRadio"] label > div:last-child p {
        font-weight: 600 !important;
        font-size: 15px !important;
        color: #8c8c94;
        transition: color 0.2s;
        margin: 0;
    }
    
    /* Hover effect */
    div[data-testid="stRadio"] label:hover > div:last-child {
        background-color: rgba(255, 255, 255, 0.05);
    }
    div[data-testid="stRadio"] label:hover > div:last-child p {
        color: #ffffff;
    }
    
    /* Active tab style */
    div[data-testid="stRadio"] label:has(input:checked) > div:last-child {
        border-bottom: 3px solid #00d26a;
    }
    div[data-testid="stRadio"] label:has(input:checked) > div:last-child p {
        color: #00d26a;
    }
</style>
""", unsafe_allow_html=True)

if 'ticker_search_input' not in st.session_state:
    st.session_state['ticker_search_input'] = ""

# Handle Market Explorer selection BEFORE sidebar renders to avoid st.rerun() tab resets
if 'explorer_table' in st.session_state and getattr(st.session_state.explorer_table, 'selection', None):
    rows = getattr(st.session_state.explorer_table.selection, 'rows', [])
    if rows:
        try:
            temp_df = get_sp500_dataframe()
            idx = rows[0]
            st.session_state['ticker_search_input'] = temp_df.iloc[idx]['Symbol']
        except Exception:
            pass

st.title("Stock Portfolio Dashboard")

# ==========================================
# SIDEBAR (Part 1): Inputs
# ==========================================
with st.sidebar:
    st.header("Control Center")
    st.subheader("Market Research")
    ticker_input = st.text_input("Enter Stock Ticker:", key="ticker_search_input").upper()

# ==========================================
# MAIN CONTENT: Portfolio Data
# ==========================================
portfolio_df = get_portfolio_summary()
cash_balance = get_cash_balance()
net_deposits = get_net_deposits()

# 1. Fetch live prices & calculate metrics
if not portfolio_df.empty:
    tickers = portfolio_df['ticker'].tolist()
    with st.spinner("Updating market data and Forex rates..."):
        market_data = get_market_data(tickers)
        
    portfolio_df['live_price'] = portfolio_df['ticker'].map(lambda x: market_data.get(x, {}).get('price', 0.0))
    portfolio_df['previous_close'] = portfolio_df['ticker'].map(lambda x: market_data.get(x, {}).get('previousClose', 0.0))
    portfolio_df['sector'] = portfolio_df['ticker'].map(lambda x: market_data.get(x, {}).get('sector', 'Unknown'))
    portfolio_df['currency'] = portfolio_df['ticker'].map(lambda x: market_data.get(x, {}).get('currency', 'USD'))
    portfolio_df['exchange_rate'] = portfolio_df['ticker'].map(lambda x: market_data.get(x, {}).get('exchange_rate', 1.0))
    portfolio_df['dividendYield'] = portfolio_df['ticker'].map(lambda x: market_data.get(x, {}).get('dividendYield', 0.0))
    
    # Forex normalization to USD
    portfolio_df['native_current_value'] = portfolio_df['total_shares'] * portfolio_df['live_price']
    portfolio_df['current_value'] = portfolio_df['native_current_value'] * portfolio_df['exchange_rate']
    
    portfolio_df['unrealized_pl'] = portfolio_df['current_value'] - portfolio_df['total_cost']
    portfolio_df['total_pl'] = portfolio_df['unrealized_pl'] + portfolio_df['realized_pl']
    portfolio_df['day_pl'] = portfolio_df['total_shares'] * (portfolio_df['live_price'] - portfolio_df['previous_close']) * portfolio_df['exchange_rate']
    portfolio_df['expected_dividend'] = portfolio_df['current_value'] * portfolio_df['dividendYield']

    stock_value = portfolio_df['current_value'].sum()
    total_unrealized_pl = portfolio_df['unrealized_pl'].sum()
    total_realized_pl = portfolio_df['realized_pl'].sum()
    total_day_pl = portfolio_df['day_pl'].sum()
    total_net_pl = portfolio_df['total_pl'].sum()
    total_expected_dividend = portfolio_df['expected_dividend'].sum()
    total_portfolio_cost = portfolio_df['total_cost'].sum()
else:
    stock_value = 0.0
    total_unrealized_pl = 0.0
    total_realized_pl = 0.0
    total_day_pl = 0.0
    total_net_pl = 0.0
    total_expected_dividend = 0.0
    total_portfolio_cost = 0.0

total_portfolio_value = stock_value + cash_balance

# 2. Top-Level Metric Banner
st.subheader("Executive Summary")
col1, col2, col3, col4, col5, col6 = st.columns(6)

if total_day_pl > 0:
    day_pl_str = f"${total_day_pl:,.2f} Today"
    d_color = "normal"
elif total_day_pl < 0:
    day_pl_str = f"-${abs(total_day_pl):,.2f} Today"
    d_color = "normal"
else:
    day_pl_str = "0.00 Today"
    d_color = "off"

unrealized_pct = (total_unrealized_pl / total_portfolio_cost * 100) if total_portfolio_cost > 0 else 0.0
if unrealized_pct > 0:
    unreal_str = f"+{unrealized_pct:,.2f}%"
    u_color = "normal"
elif unrealized_pct < 0:
    unreal_str = f"-{abs(unrealized_pct):,.2f}%"
    u_color = "normal"
else:
    unreal_str = "0.00%"
    u_color = "off"

if total_portfolio_value > 0:
    cash_pct = (cash_balance / total_portfolio_value) * 100
    div_yield = (total_expected_dividend / total_portfolio_value) * 100
else:
    cash_pct = 0.0
    div_yield = 0.0

cash_str = f"{cash_pct:.1f}% of Portfolio"
div_str = f"{div_yield:.2f}% Avg Yield"

if total_net_pl > 0:
    net_pl_str = f"+${total_net_pl:,.2f} All-time P/L"
    n_color = "normal"
elif total_net_pl < 0:
    net_pl_str = f"-${abs(total_net_pl):,.2f} All-time P/L"
    n_color = "normal"
else:
    net_pl_str = "0.00 All-time P/L"
    n_color = "off"

all_tx_metric = get_all_transactions()
num_sells = len(all_tx_metric[all_tx_metric['action'] == 'SELL']) if not all_tx_metric.empty else 0
realized_str = f"{num_sells} Closed Trades"

col1.metric("Total Portfolio Value", f"${total_portfolio_value:,.2f}", day_pl_str, delta_color=d_color)
col2.metric("Net Invested", f"${net_deposits:,.2f}", net_pl_str, delta_color=n_color)
col3.metric("Cash Balance", f"${cash_balance:,.2f}", cash_str, delta_color="off")
col4.metric("Unrealized P/L", f"${total_unrealized_pl:,.2f}", unreal_str, delta_color=u_color)
col5.metric("Realized P/L", f"${total_realized_pl:,.2f}", realized_str, delta_color="off")
col6.metric("Annual Dividend Income", f"${total_expected_dividend:,.2f}", div_str, delta_color="off")

st.divider()

# 3. Robust Navigation (Replacing buggy st.tabs)
tab_options = ["🚀 Overview", "📊 Holdings", "📈 Analytics", "🌍 Market Explorer", "🔍 Market Chart", "📜 History", "💵 Cash Hub", "⚙️ Settings"]
current_tab = st.radio("Navigation", tab_options, horizontal=True, label_visibility="collapsed")

if current_tab == "🚀 Overview":
    st.subheader("Historical Portfolio Performance")
    if portfolio_df.empty and cash_balance == 0:
        st.info("Your portfolio is empty. Make a Deposit or Log a Trade to begin.")
    else:
        with st.spinner("Building historical chart..."):
            hist_df = build_portfolio_history()
            
        if not hist_df.empty:
            fig_area = px.area(hist_df, x='Date', y='Total Value', template="plotly_dark")
            fig_area.update_traces(line_color='#00d26a', fillcolor='rgba(0, 210, 106, 0.2)')
            fig_area.update_layout(xaxis_title="", yaxis_title="Total Value ($)", margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("Not enough historical data to chart yet.")

elif current_tab == "📊 Holdings":
    if portfolio_df.empty:
        st.info("You don't hold any assets yet.")
    else:
        def format_yield(val):
            return f"{val*100:.2f}%" if pd.notna(val) else "0.00%"
            
        def color_profit(val):
            if isinstance(val, (int, float)):
                if val > 0: return 'color: #00d26a; font-weight: bold;'
                elif val < 0: return 'color: #f8485e; font-weight: bold;'
            return ''
        
        # Format dataframe for display
        display_df = portfolio_df.copy()
        display_df['dividendYield'] = display_df['dividendYield'].apply(format_yield)
        styled_df = display_df.style.map(color_profit, subset=['day_pl', 'unrealized_pl', 'realized_pl', 'total_pl']).format(precision=2)
        
        st.dataframe(
            styled_df,
            column_config={
                "ticker": "Ticker",
                "sector": "Sector",
                "currency": "Native Cur.",
                "total_shares": "Shares",
                "avg_price": st.column_config.NumberColumn("Avg Price ($)", format="$%.2f"),
                "live_price": st.column_config.NumberColumn("Live Price (Native)", format="%.2f"),
                "exchange_rate": None,
                "previous_close": None,
                "native_current_value": None,
                "expected_dividend": None,
                "current_value": st.column_config.NumberColumn("Current Value ($)", format="$%.2f"),
                "total_cost": None,
                "dividendYield": "Div Yield",
                "day_pl": st.column_config.NumberColumn("Day P/L ($)", format="$%.2f"),
                "unrealized_pl": st.column_config.NumberColumn("Unrealized P/L ($)", format="$%.2f"),
                "realized_pl": st.column_config.NumberColumn("Realized P/L ($)", format="$%.2f"),
                "total_pl": st.column_config.NumberColumn("Total P/L ($)", format="$%.2f")
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
elif current_tab == "📈 Analytics":
    if portfolio_df.empty:
        st.info("Not enough data for analytics.")
    else:
        col_pie, col_bar = st.columns(2)
        with col_pie:
            st.subheader("Allocation by Sector")
            active_holdings = portfolio_df[portfolio_df['current_value'] > 0]
            if not active_holdings.empty:
                fig_pie = px.pie(active_holdings, values='current_value', names='sector', hole=0.4, template="plotly_dark")
                fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#0e1117', width=2)))
                fig_pie.update_layout(margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No active holdings for allocation chart.")
            
        with col_bar:
            st.subheader("Total P/L by Asset")
            fig_bar = px.bar(portfolio_df, x='ticker', y='total_pl', template="plotly_dark", color='total_pl', color_continuous_scale=[(0, '#f8485e'), (1, '#00d26a')])
            fig_bar.update_layout(margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.subheader("Performance Leaders & Laggards")
        col_win, col_lose = st.columns(2)
        with col_win:
            st.markdown("### 🏆 Top 3 Winners")
            winners = portfolio_df.nlargest(3, 'total_pl')
            for _, row in winners.iterrows():
                if row['total_pl'] > 0:
                    pct = (row['total_pl'] / row['total_cost'] * 100) if row['total_cost'] > 0 else 0
                    st.metric(row['ticker'], f"${row['total_pl']:,.2f}", f"+{pct:.2f}%")
                
        with col_lose:
            st.markdown("### 📉 Top 3 Losers")
            losers = portfolio_df.nsmallest(3, 'total_pl')
            for _, row in losers.iterrows():
                if row['total_pl'] < 0:
                    pct = (row['total_pl'] / row['total_cost'] * 100) if row['total_cost'] > 0 else 0
                    st.metric(row['ticker'], f"${row['total_pl']:,.2f}", f"{pct:.2f}%")

elif current_tab == "🌍 Market Explorer":
    st.subheader("S&P 500 Market Explorer")
    st.write("Browse the 500 largest US companies. **Click a row to instantly select the ticker for trading.**")
    with st.spinner("Loading market data..."):
        sp500_df = get_sp500_dataframe()
    if not sp500_df.empty:
        st.dataframe(
            sp500_df, 
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row",
            key="explorer_table"
        )

elif current_tab == "🔍 Market Chart":
    if ticker_input:
        st.subheader(f"{ticker_input} 6-Month History")
        history_df = get_historical_data(ticker_input)
        if not history_df.empty:
            fig_line = px.line(history_df, x=history_df.index, y='Close', template="plotly_dark")
            fig_line.update_traces(line_color='#2962ff', line_width=3)
            fig_line.update_layout(xaxis_title="", yaxis_title="", margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Historical data unavailable.")
    else:
        st.info("Search for a ticker in the sidebar to view its chart.")

elif current_tab == "📜 History":
    st.subheader("Transaction Ledger")
    all_tx = get_all_transactions()
    if not all_tx.empty:
        # Prettify the dataframe for display
        display_tx = all_tx.copy()
        display_tx['action'] = display_tx['action'].str.capitalize()
        display_tx = display_tx.rename(columns={
            'id': 'ID',
            'ticker': 'Asset',
            'action': 'Action',
            'price': 'Price / Amount',
            'quantity': 'Quantity',
            'timestamp': 'Date'
        })
        
        st.dataframe(
            display_tx,
            column_config={
                "Price / Amount": st.column_config.NumberColumn("Price / Amount", format="$%.2f")
            },
            hide_index=True, 
            use_container_width=True
        )
        
        st.markdown("### Delete Transaction")
        with st.form("delete_form", clear_on_submit=True):
            tx_to_delete = st.selectbox("Select Transaction ID to delete:", all_tx['id'].tolist())
            del_submit = st.form_submit_button("Delete", type="primary")
            if del_submit:
                delete_transaction(tx_to_delete)
                st.success(f"Deleted transaction {tx_to_delete}")
                st.rerun()
    else:
        st.info("No transactions logged yet.")

elif current_tab == "💵 Cash Hub":
    st.subheader("Cash & Dividends Management")
    with st.form("cash_form", clear_on_submit=True):
        cash_action = st.selectbox("Operation Type", ["DEPOSIT", "WITHDRAWAL", "DIVIDEND"])
        amount = st.number_input("Amount ($)", min_value=0.0, step=100.0, value=0.0)
        
        cash_ticker = "CASH"
        if cash_action == "DIVIDEND":
            cash_ticker = st.text_input("Ticker that paid dividend", value=ticker_input).upper()
            
        cash_date = st.date_input("Date")
        cash_submitted = st.form_submit_button("Process", use_container_width=True)
        
        if cash_submitted:
            if amount <= 0:
                st.error("Amount must be greater than $0.")
            elif cash_action == "DIVIDEND" and not cash_ticker:
                st.error("Ticker is required for dividends.")
            else:
                current_time = datetime.datetime.now().time()
                full_datetime = datetime.datetime.combine(cash_date, current_time).strftime("%Y-%m-%d %H:%M:%S")

                if cash_action == "WITHDRAWAL":
                    if amount > cash_balance:
                        st.error(f"Cannot withdraw ${amount:,.2f}. You only have ${cash_balance:,.2f}.")
                        st.stop()

                target_ticker = cash_ticker if cash_action == "DIVIDEND" else "CASH"
                add_transaction(target_ticker, cash_action, amount, 1, full_datetime)
                st.success(f"Logged {cash_action} of ${amount:,.2f}!")
                st.rerun()

elif current_tab == "⚙️ Settings":
    st.subheader("Advanced Settings")
    st.warning("These operations affect your entire database.")
    
    all_tx_settings = get_all_transactions()
    if not all_tx_settings.empty:
        csv = all_tx_settings.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Ledger to CSV",
            data=csv,
            file_name='portfolio_transactions.csv',
            mime='text/csv',
            use_container_width=True
        )
        
    if st.button("🚨 Wipe Entire Portfolio", type="primary", use_container_width=True):
        reset_database()
        st.success("Database wiped.")
        st.rerun()

# ==========================================
# SIDEBAR (Part 2): Dynamic Stock Card & Terminal
# ==========================================
with st.sidebar:
    stock_data = {}
    if ticker_input:
        with st.spinner(f"Fetching {ticker_input}..."):
            stock_data = get_stock_info(ticker_input)
            
    # Stable UI layout for Company Card
    if ticker_input and "error" not in stock_data and "shortName" in stock_data:
        current_price = stock_data.get('currentPrice') or stock_data.get('regularMarketPrice') or stock_data.get('previousClose', 0.0)
        
        st.markdown(f"### {stock_data.get('shortName', ticker_input)}")
        col_a, col_b = st.columns(2)
        col_a.metric("Price", f"${current_price}")
        col_b.metric("Currency", stock_data.get('currency', 'USD'))
        
        st.caption(f"**Sector**: {stock_data.get('sector', 'N/A')} | **Industry**: {stock_data.get('industry', 'N/A')}")
    else:
        st.markdown("### No Ticker Selected")
        col_a, col_b = st.columns(2)
        col_a.metric("Price", "-")
        col_b.metric("Currency", "-")
        
        st.caption("**Sector**: - | **Industry**: -")
        
        if ticker_input:
            st.error("Data unavailable or invalid ticker.")
    
    st.divider()
    
    # 2. Trading Terminal
    st.subheader("Trading Terminal")
    with st.form("trade_form", clear_on_submit=True):
        action_input = st.selectbox("Action", ["BUY", "SELL"])
        
        current_price = 0.0
        if stock_data and "error" not in stock_data:
            current_price = stock_data.get('currentPrice') or stock_data.get('regularMarketPrice') or stock_data.get('previousClose', 0.0)
            
        price_input = st.number_input("Price per Share (in Base Currency)", min_value=0.01, step=0.01, value=float(current_price) if current_price > 0 else 1.0)
        
        if current_price > 0:
            import math
            max_shares = math.floor(cash_balance / current_price)
            st.caption(f"💰 Max Affordable: **{max_shares} shares**")
            
        buy_max = st.checkbox("Buy Max (Ignores Manual Quantity)", value=False)
        quantity = st.number_input("Number of Shares", min_value=1, step=1)
        
        date_input = st.date_input("Transaction Date")
        submitted = st.form_submit_button("Log Transaction", use_container_width=True)
        
        if submitted:
            if ticker_input:
                if price_input > 0:
                    if action_input == "BUY" and buy_max:
                        import math
                        max_shares = math.floor(cash_balance / price_input)
                        if max_shares < 1:
                            st.error(f"Insufficient cash to buy even 1 share. You only have ${cash_balance:,.2f}.")
                            st.stop()
                        quantity = max_shares

                    current_time = datetime.datetime.now().time()
                    full_datetime = datetime.datetime.combine(date_input, current_time).strftime("%Y-%m-%d %H:%M:%S")

                    if action_input == "BUY":
                        cost = price_input * quantity
                        if cost > cash_balance:
                            st.error(f"Insufficient cash! Cost is ${cost:,.2f} but you only have ${cash_balance:,.2f}. Please make a Deposit.")
                            st.stop()

                    if action_input == "SELL":
                        current_shares = 0
                        if not portfolio_df.empty and ticker_input in portfolio_df['ticker'].values:
                            current_shares = portfolio_df.loc[portfolio_df['ticker'] == ticker_input, 'total_shares'].values[0]
                        if quantity > current_shares:
                            st.error(f"Cannot sell {quantity}. You own {current_shares} shares.")
                            st.stop()
                    
                    add_transaction(ticker_input, action_input, price_input, quantity, full_datetime)
                    st.success(f"Logged {action_input} of {quantity} {ticker_input}!")
                    st.rerun() 
                else:
                    st.error("Price must be > 0.")
            else:
                st.warning("Enter a ticker first.")