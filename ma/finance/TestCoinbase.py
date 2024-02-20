import credentials
import json
import ccxt
import time
import numpy as np
import exchanges
import pandas as pd
from models import V2
import yfinance as yf
from yahoo_fin import stock_info as sf
from datetime import datetime, timedelta

coin = "ETH"

exchange = exchanges.cryptocom()

#data = pd.DataFrame( sf.get_data("LPT-USD", interval='30m'))
data = pd.DataFrame(yf.download(f"INJ-USD", period="1d", interval="30m", progress=False))
data = data.rename(columns={"Close": "close", "High": "high", "Low": "low"})
data = V2.apply_indicators(data)


def fetch_data():
    bars = exchange.fetch_ohlcv(
        "SOL/USDT", timeframe="30m", limit=35
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    
    return data

def get_highest_price(data, timestamp):
    if len(data) > 0:
        data = pd.DataFrame(
            data[:],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
    timestamp = datetime.utcfromtimestamp(timestamp / 1e3)
    print(timestamp)
    data = data[(data['timestamp'] >= timestamp)]

    return data["high"].max()

if __name__ == "__main__":
    data = fetch_data()
    print(data)
    timestamp = data.iloc[-1, 0]
    print(timestamp)
    timestamp = int(timestamp.timestamp() * 1e3)
    print(timestamp)
    print(get_highest_price(data, timestamp))