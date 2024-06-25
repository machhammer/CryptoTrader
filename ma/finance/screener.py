from exchanges import Exchange
import pandas as pd
import random
import time
from datetime import datetime
from pandas_datareader import data as pdr
import pprint
import time
from tqdm import tqdm
from ta.trend import AroonIndicator
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

base_currency = "USD"

amount_coins = 500

exchange = Exchange("cryptocom")


def get_tickers():
    tickers = exchange.fetch_tickers()
    tickers = pd.DataFrame(tickers)
    tickers = tickers.T
    tickers = tickers[tickers["symbol"].str.endswith("/" + base_currency)].head(amount_coins)

    tickers = tickers["symbol"].to_list()
    random.shuffle(tickers)

    return tickers


def get_ticker_with_bigger_moves(tickers):
    limit = 3
    bigger_moves = []
    iterations = len(tickers)
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for ticker in tickers:
        bars = exchange.fetch_ohlcv(
            ticker, "5m", limit=limit
        )
        data = pd.DataFrame(
            bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        data["change"] = ((data["close"] - data["open"]) / data["open"]) * 100
        data["is_change_relevant"] = data["change"] >= 0.8

        ticker_check = {}
        ticker_check['ticker'] = ticker
        ticker_check['change'] = data.tail(limit)["change"].to_list()
        ticker_check['relevant'] = data.tail(limit)["is_change_relevant"].to_list()
        ticker_check['data'] = data
        if ticker_check['relevant'].count(True) >=2:
            bigger_moves.append(ticker)
        try:
            next(progress_bar)
        except:
            pass
    return bigger_moves


def get_ticker_with_aroon_buy_signals(tickers):
    buy_signals = []
    for ticker in tickers:
        bars = exchange.fetch_ohlcv(
            ticker, "5m", limit=20
        )
        data = pd.DataFrame(
            bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        indicator_AROON = AroonIndicator(
            high=data["high"], low=data["low"], window=14
        )
        data["aroon_up"] = indicator_AROON.aroon_up()
        data["aroon_down"] = indicator_AROON.aroon_down()
        if (100 in data.tail(3)["aroon_up"].to_list()):
            buy_signals.append(ticker)
    return buy_signals

def get_ticker_with_increased_volume(tickers):
    increased_volumes = []
    for ticker in tickers:
        bars = exchange.fetch_ohlcv(
            ticker, "1d", limit=10
        )
        data = pd.DataFrame(
            bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        last_mean = data.head(19)["volume"].median()
        current_mean = data.tail(1)["volume"].mean()
        if (current_mean / last_mean) >= 1:
            increased_volumes.append(ticker)
    return increased_volumes



if __name__ == "__main__":
    
    run = True
    
    while run:
        tickers = get_tickers()
        major_move = get_ticker_with_bigger_moves(tickers)
        increased_volume = get_ticker_with_increased_volume(major_move)
        buy_signals = get_ticker_with_aroon_buy_signals(increased_volume)
        print("buy signals", buy_signals)
        time.sleep(900)

    #send_email("Test Betreff", "Das ist der E-Mail-Text.", "machhammer@gmx.net")