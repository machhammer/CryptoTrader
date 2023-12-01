import os
import sys
import backtrader as bt
from pprint import pprint
import credentials
import ccxt  # noqa: E402
import backtrader.feeds as btfeeds
from decimal import Decimal


api_key = credentials.provider_1.get("key")
api_secret = credentials.provider_1.get("secret")


exchange = ccxt.coinbase({
    'apiKey': api_key,
    'secret': api_secret,
    # 'verbose': True,  # for debug output
})

print(exchange)

symbol = 'XRP-USDC'
order_type = 'limit'
side = 'sell'
amount = 1
order_price = 0.7
#stop_params = {
#    'triggerPrice': 0.700
#}

limit_order = exchange.create_order(symbol, order_type, side, amount, order_price)

#limit_order = exchange.create_order(symbol, order_type, side, amount, order_price)

#order = exchange.create_order(symbol, order_type, side, amount)

pprint(limit_order)
