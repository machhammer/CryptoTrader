import os
import sys
import backtrader as bt
from pprint import pprint
import credentials
import ccxt  # noqa: E402
import backtrader.feeds as btfeeds
from decimal import Decimal


api_key = credentials.provider_2.get("key")
api_secret = credentials.provider_2.get("secret")


exchange = ccxt.cryptocom({
    'apiKey': api_key,
    'secret': api_secret,
    # 'verbose': True,  # for debug output
})

print(exchange)
usdt = exchange.fetch_balance()["USDT"]["free"]
print(usdt)

print("**************** create order")

symbol = 'XRP/USDT'
order_type = 'market'
side = 'sell'
amount = 2
order_price = 0.576
#stop_params = {
#    'triggerPrice': 0.700
#}

limit_order = exchange.create_order(symbol, order_type, side, amount, order_price)

#limit_order = exchange.create_order(symbol, order_type, side, amount, order_price)

#order = exchange.create_order(symbol, order_type, side, amount)

pprint(limit_order)
