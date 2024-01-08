import credentials
import json
import ccxt
import pandas as pd

coin = "XRP"

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

tickers = exchange.fetch_tickers()


df = pd.DataFrame(tickers)

df = df.T

df = df[df["symbol"].str.contains("USDT")]


looser = df[df["percentage"] <= 0]
print(len(looser))

winner = df[df["percentage"] > 0]
print(len(winner))

overall = df["percentage"].sum()
print(overall)
