import os
import sys
import backtrader as bt
from pprint import pprint
import credentials
import ccxt  # noqa: E402
import backtrader.feeds as btfeeds


api_key = credentials.provider_1.get("key")
api_secret = credentials.provider_1.get("secret")


exchange = ccxt.coinbase({
    'apiKey': api_key,
    'secret': api_secret,
    # 'verbose': True,  # for debug output
})

symbol = 'TRB/USDC'
order_type = 'limit'
side = 'sell'
amount = 0.1
order_price = 86.5
stop_params = {
    'triggerPrice': 15000
}

#market_order = exchange.create_market_sell_order(symbol, amount)
#order = exchange.create_limit_order(symbol, order_type, side, amount, order_price)
order = exchange.create_order(symbol, order_type, side, amount, order_price)
pprint(order)
# pprint(stop_order)

