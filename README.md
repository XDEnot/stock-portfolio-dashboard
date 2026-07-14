# Stock Portfolio Dashboard

A real-time stock portfolio tracking application built with Python and Streamlit. This application allows users to monitor their investments, fetch live market data, and analyze their asset allocation.

## Key Features

* **Live Market Data:** Integrates with `yfinance` to fetch real-time stock prices, previous closes, and dividend yields.
* **Multi-Currency Support:** Automatically converts native stock currencies into USD using live forex exchange rates.
* **Trading Terminal:** Log 'Buy' and 'Sell' transactions with automatic cash balance management.
* **Analytics:** Interactive Plotly charts (pie charts for sector allocation, area charts for historical performance).
* **S&P 500 Market Explorer:** Browse and select from the 500 largest US companies directly within the app.
* **Persistent Storage:** Uses SQLite to store all transactions, deposits, and portfolio history locally.

## Tech Stack

* **Frontend/Framework:** Streamlit
* **Data Processing:** Pandas, NumPy
* **Data Visualization:** Plotly Express, Plotly Graph Objects
* **Market Data API:** yfinance (Yahoo Finance)
* **Database:** SQLite3

## How to Run Locally

1. Clone this repository to your local machine.
2. Create a virtual environment and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   streamlit run app.py
   ```
   *(Alternatively, Windows users can double-click the `start.bat` file).*

## App Structure

* `app.py`: Main Streamlit application and UI routing.
* `data_fetcher.py`: Handles all external API calls to Yahoo Finance.
* `database.py`: Manages SQLite connections and SQL queries.
* `analytics.py`: Computes historical portfolio performance over time.
