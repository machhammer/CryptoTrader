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


order_id = '5debc3ed-e5f7-464c-8757-41fa6c4a68f0'
# order_ids = ['04204eaf-94d6-444a-b9b7-2f8a485311f6', '7c13a059-d235-46e1-ab43-6794a5836db9']

try:
    cancel_order = exchange.cancel_order(order_id)
    # cancel_orders = exchange.cancel_orders(order_ids)
    pprint(cancel_order)
    # pprint(cancel_orders)
except Exception as err:
    print(err)
