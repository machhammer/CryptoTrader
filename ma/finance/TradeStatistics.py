import ccxt
import credentials
import pandas as pd
from pprint import pprint

api_key = credentials.provider_2.get("key")
api_secret = credentials.provider_2.get("secret")

config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.cryptocom(
    {
        "apiKey": api_key,
        "secret": api_secret,
        # 'verbose': True,  # for debug output
    }
)

current_balance = exchange.fetch_balance()["USDT"]["free"]
current_price = exchange.fetch_ticker("XLM/USDT")["last"]

print(current_balance)
print(current_price)
