import os
import json
import trader
import exchanges
import threading
from TraderClass import TraderClass
import time

exchange = exchanges.cryptocom()

position_file = "positions.json"

coins = {"XRP": 0.25, "XLM": 0.25, "GMT": 0.25, "SOL": 0.25}

trader1 = TraderClass(
    trading_mode="live",
    coin="XLM",
    coin_distribution={"XRP": 0.25, "FITFI": 0.25, "GMT": 0.25, "SOL": 0.25},
    frequency="1m",
    exchange=exchange,
)

trader2 = TraderClass(
    trading_mode="live",
    coin="XRP",
    coin_distribution={"XRP": 0.25, "FITFI": 0.25, "GMT": 0.25, "SOL": 0.25},
    frequency="1m",
    exchange=exchange,
)

x = threading.Thread(target=trader1.run, daemon=True)
y = threading.Thread(target=trader2.run, daemon=True)

x.start()
y.start()

x.join()
y.join()

print("wait")

time.wait(15)

print("stop")


trader1.stop_running()
trader2.stop_running()

print("stopped")