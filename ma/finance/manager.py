import os
import json
import trader
import exchanges
import threading
from TraderClass import TraderClass
import time

exchange = exchanges.cryptocom()

position_file = "positions.json"

coins = {"XRP": 0.25, "XLM": 0.25, "STX": 0.25, "SOL": 0.25}


traders = []
threads = []

for coin in coins:
    traders.append(TraderClass(
    trading_mode="live",
    coin=coin,
    coin_distribution=coins,
    frequency="15m",
    exchange=exchange,
    ))
    

for trader in traders:
    threads.append(threading.Thread(target=trader.run, daemon=True))

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()
