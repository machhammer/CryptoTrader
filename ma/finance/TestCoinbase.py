from datetime import datetime, timedelta
import credentials
from dateutil.relativedelta import relativedelta
import data_provider.DataReader as data_provider
import backtrader as bt
from backtrader import Order
from backtrader import Position

from ccxtbt import CCXTStore
import ccxt
import warnings

coin = "XLM"

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

def get_funding():
    total = 0
    coin_keys = coins.keys()
    for key in coin_keys:
        print(key)
        try:
            current_balance = exchange.fetch_balance()[key]["free"]
        except:
            current_balance = 0
        current_price = exchange.fetch_ticker(coins[key]["product"])["last"]
        if current_balance * current_price < 1:
            total = total + float(coins[key]["dist_ratio"]) * 10

    ratio = (coins[coin]["dist_ratio"] * 10) / total
    return (exchange.fetch_balance()["USDT"]["free"] * ratio) - 1


print(exchange.fetch_balance()["USDT"]["free"])

print (get_funding())

