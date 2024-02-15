import credentials
import json
import ccxt
import pandas as pd
from models import V2
import yfinance as yf
from yahoo_fin import stock_info as sf

coin = "ETH"


#data = pd.DataFrame( sf.get_data("LPT-USD", interval='30m'))
data = pd.DataFrame(yf.download(f"INJ-USD", period="1d", interval="30m", progress=False))
data = data.rename(columns={"Close": "close", "High": "high", "Low": "low"})
data = V2.apply_indicators(data)

print(data)

exit()

coins = {
    "XRP": {"product": "XRP/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "SOL": {"product": "SOL/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "XLM": {"product": "XLM/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "CRO": {"product": "CRO/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "NEAR": {"product": "NEAR/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
}

api_key = credentials.provider_2.get("key")
api_secret = credentials.provider_2.get("secret")

config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.cryptocom(
    {
        "apiKey": api_key,
        "secret": api_secret,
        #'verbose': True
    }
)

bars = exchange.fetch_ohlcv(
    "SOL/USDT", timeframe="30m", limit=50
)
data = pd.DataFrame(
    bars, columns=["timestamp", "open", "high", "low", "close", "volume"]
)
data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")

data = pd.DataFrame(
    data,
    columns=["timestamp", "open", "high", "low", "close", "volume"],
)

data = V2.apply_indicators(data)

print(data)