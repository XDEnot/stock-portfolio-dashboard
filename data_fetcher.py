import yfinance as yf
import pandas as pd
import streamlit as st
from typing import Dict, Any

@st.cache_data(ttl=900)
def get_stock_info(ticker_symbol: str) -> Dict[str, Any]:
    """
    Fetches basic company information for a given stock ticker.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        return info
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600)
def get_historical_data(ticker_symbol: str, period: str = "6mo") -> pd.DataFrame:
    """
    Fetches historical price data for charting.
    Returns a Pandas DataFrame.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        return hist
    except Exception:
        return pd.DataFrame()
    
def get_market_data(tickers: list) -> dict:
    """
    Takes a list of tickers and returns a dictionary of their market data
    including current price, previous close, sector, currency, exchange rate to USD, and dividend yield.
    """
    data = {}
    for ticker in tickers:
        info = get_stock_info(ticker)
        
        # fallback if currentPrice is missing
        price = info.get('currentPrice')
        if not price:
            price = info.get('regularMarketPrice')
        if not price:
            price = info.get('previousClose')
            
        final_price = price if price else 0.0
        
        # Forex Engine
        currency = info.get('currency', 'USD')
        exchange_rate = 1.0
        if currency and currency != 'USD':
            pair_ticker = f"{currency}USD=X"
            pair_info = get_stock_info(pair_ticker)
            rate = pair_info.get('currentPrice') or pair_info.get('regularMarketPrice') or pair_info.get('previousClose')
            if rate:
                exchange_rate = float(rate)
                
        data[ticker] = {
            'price': final_price,
            'previousClose': info.get('previousClose', final_price),
            'sector': info.get('sector', 'Unknown'),
            'currency': currency,
            'exchange_rate': exchange_rate,
            'dividendYield': info.get('dividendYield', 0.0) or 0.0
        }
    return data

@st.cache_data(ttl=86400) # Cache for 24 hours
def get_sp500_dataframe() -> pd.DataFrame:
    """
    Scrapes the S&P 500 list from Wikipedia and returns a clean DataFrame.
    """
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        df = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0'})[0]
        df['Symbol'] = df['Symbol'].str.replace('.', '-', regex=False)
        cols = ['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location', 'Founded']
        return df[cols]
    except Exception:
        return pd.DataFrame(columns=['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location', 'Founded'])