import sqlite3
import pandas as pd

DB_NAME = "portfolio.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_transaction(ticker: str, action: str, price: float, quantity: int, timestamp: str = None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if timestamp:
        cursor.execute('''
            INSERT INTO transactions (ticker, action, price, quantity, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticker, action, price, quantity, timestamp))
    else:
        cursor.execute('''
            INSERT INTO transactions (ticker, action, price, quantity)
            VALUES (?, ?, ?, ?)
        ''', (ticker, action, price, quantity))
    conn.commit()
    conn.close()

# MAKE SURE THIS FUNCTION EXISTS AND IS SAVED:
def get_portfolio_summary() -> pd.DataFrame:
    conn = sqlite3.connect(DB_NAME)
    # Fetch all trade transactions ordered chronologically
    df_tx = pd.read_sql_query("SELECT * FROM transactions WHERE action IN ('BUY', 'SELL') ORDER BY timestamp ASC, id ASC", conn)
    conn.close()
    
    portfolio = []
    
    # Calculate holdings using a chronological Weighted Average Cost approach
    for ticker, group in df_tx.groupby('ticker'):
        total_shares = 0
        total_cost = 0.0
        realized_pl = 0.0
        
        for _, row in group.iterrows():
            if row['action'] == 'BUY':
                total_shares += row['quantity']
                total_cost += row['price'] * row['quantity']
            elif row['action'] == 'SELL':
                if total_shares > 0:
                    # Calculate current avg price before selling
                    avg_price = total_cost / total_shares
                    
                    # Calculate realized P/L for the shares actually sold
                    shares_sold = min(row['quantity'], total_shares)
                    realized_pl += (row['price'] - avg_price) * shares_sold
                    
                    # Remove the sold shares
                    total_shares -= shares_sold
                    # Reduce cost basis proportionally
                    total_cost -= shares_sold * avg_price
                
                # If we sold everything, completely reset the cost basis to avoid dragging old prices
                if total_shares <= 0:
                    total_shares = 0
                    total_cost = 0.0
                    
        # Include tickers that are currently held OR have a realized P/L history
        if total_shares > 0 or realized_pl != 0.0:
            portfolio.append({
                'ticker': ticker,
                'total_shares': total_shares,
                'avg_price': total_cost / total_shares if total_shares > 0 else 0.0,
                'total_cost': total_cost,
                'realized_pl': realized_pl
            })
            
    if not portfolio:
        return pd.DataFrame(columns=['ticker', 'total_shares', 'avg_price', 'total_cost', 'realized_pl'])
        
    return pd.DataFrame(portfolio)

def get_cash_balance() -> float:
    conn = sqlite3.connect(DB_NAME)
    df_tx = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    
    cash = 0.0
    for _, row in df_tx.iterrows():
        action = row['action']
        amount = row['price'] * row['quantity']
        if action == 'DEPOSIT':
            cash += amount
        elif action == 'WITHDRAWAL':
            cash -= amount
        elif action == 'BUY':
            cash -= amount
        elif action == 'SELL':
            cash += amount
        elif action == 'DIVIDEND':
            cash += amount
    return cash

def get_net_deposits() -> float:
    conn = sqlite3.connect(DB_NAME)
    df_tx = pd.read_sql_query("SELECT * FROM transactions WHERE action IN ('DEPOSIT', 'WITHDRAWAL')", conn)
    conn.close()
    
    net = 0.0
    for _, row in df_tx.iterrows():
        amount = row['price'] * row['quantity']
        if row['action'] == 'DEPOSIT':
            net += amount
        elif row['action'] == 'WITHDRAWAL':
            net -= amount
    return net

def get_all_transactions() -> pd.DataFrame:
    conn = sqlite3.connect(DB_NAME)
    df_tx = pd.read_sql_query("SELECT * FROM transactions ORDER BY timestamp DESC, id DESC", conn)
    conn.close()
    return df_tx

def delete_transaction(tx_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()

def reset_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    # Also reset the auto-increment counter to avoid massive IDs
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
    conn.commit()
    conn.close()