import credentials
import json
import ccxt
import time
import numpy as np
import exchanges
import pandas as pd
from models import V2
import yfinance as yf
from yahoo_fin import stock_info as sf
from datetime import datetime, timedelta

coin = "SOL"

exchange = exchanges.cryptocom()

current_assets = exchange.fetch_balance()["free"]
print(current_assets)

balance = 0
for asset in current_assets:
    if not asset =="USD":
        price = exchange.fetch_ticker(asset + "/USD")["last"] * current_assets[asset]
    else:
        price = current_assets['USD']        
    balance = balance + price

print(balance)

