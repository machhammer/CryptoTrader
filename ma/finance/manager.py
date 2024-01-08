import os
import json
import trader
import exchanges
import threading
from TraderClass import TraderClass
import time

exchange = exchanges.cryptocom()

position_file = "positions.json"

coins = {"XRP": 0.2, "XLM": 0.2, "GMT": 0.2, "SOL": 0.2, "STX": 0.2}

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
