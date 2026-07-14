import pandas as pd
import sqlite3
import yfinance as yf
import streamlit as st
import datetime
from database import DB_NAME

@st.cache_data(ttl=3600)
def build_portfolio_history() -> pd.DataFrame:
    """
    Reconstructs the daily historical value of the portfolio.
    Returns a DataFrame with columns: ['Date', 'Stock Value', 'Cash Balance', 'Total Value']
    """
    conn = sqlite3.connect(DB_NAME)
    df_tx = pd.read_sql_query("SELECT * FROM transactions ORDER BY timestamp ASC, id ASC", conn)
    conn.close()
    
    if df_tx.empty:
        return pd.DataFrame()
        
    df_tx['timestamp'] = pd.to_datetime(df_tx['timestamp'], format='mixed')
    if df_tx['timestamp'].dt.tz is not None:
        df_tx['timestamp'] = df_tx['timestamp'].dt.tz_localize(None)
    start_date = df_tx['timestamp'].min().floor('D')
    end_date = pd.Timestamp.now().floor('D')
    
    # Generate business days
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # Get all unique tickers that are stocks (from BUY/SELL)
    trade_tx = df_tx[df_tx['action'].isin(['BUY', 'SELL'])]
    tickers = trade_tx['ticker'].unique().tolist()
    
    # Download historical prices for all tickers
    historical_prices = pd.DataFrame()
    if tickers:
        try:
            # yf.download returns a MultiIndex DataFrame if len(tickers) > 1
            hist_data = yf.download(tickers, start=start_date, end=end_date + datetime.timedelta(days=1))
            if 'Close' in hist_data:
                historical_prices = hist_data['Close']
                if len(tickers) == 1:
                    historical_prices = pd.DataFrame({tickers[0]: historical_prices})
        except Exception:
            pass
            
    history_records = []
    
    # Reconstruct portfolio day by day
    for current_date in date_range:
        # Transactions up to the end of this day
        mask = df_tx['timestamp'].dt.floor('D') <= current_date
        past_tx = df_tx[mask]
        
        cash_balance = 0.0
        shares = {t: 0 for t in tickers}
        
        for _, row in past_tx.iterrows():
            action = row['action']
            amount = row['price'] * row['quantity']
            ticker = row['ticker']
            
            if action == 'DEPOSIT':
                cash_balance += amount
            elif action == 'WITHDRAWAL':
                cash_balance -= amount
            elif action == 'DIVIDEND':
                cash_balance += amount
            elif action == 'BUY':
                cash_balance -= amount
                shares[ticker] += row['quantity']
            elif action == 'SELL':
                cash_balance += amount
                shares[ticker] -= row['quantity']
                
        stock_value = 0.0
        # Calculate stock value for this day using historical prices
        if not historical_prices.empty and current_date in historical_prices.index:
            day_prices = historical_prices.loc[current_date]
            for ticker, count in shares.items():
                if count > 0 and ticker in day_prices and pd.notna(day_prices[ticker]):
                    stock_value += count * day_prices[ticker]
        elif not historical_prices.empty:
            # If market was closed or missing data, forward fill from last available
            try:
                day_prices = historical_prices.asof(current_date)
                for ticker, count in shares.items():
                    if count > 0 and ticker in day_prices and pd.notna(day_prices[ticker]):
                        stock_value += count * day_prices[ticker]
            except Exception:
                pass
                
        history_records.append({
            'Date': current_date,
            'Stock Value': stock_value,
            'Cash Balance': cash_balance,
            'Total Value': stock_value + cash_balance
        })
        
    df_hist = pd.DataFrame(history_records)
    return df_hist
