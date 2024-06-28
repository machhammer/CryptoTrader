from exchanges import Exchange
import numpy as np
import pandas as pd
import random
import time
from datetime import datetime
from pandas_datareader import data as pdr
import pprint
import time
from tqdm import tqdm
from ta.trend import AroonIndicator
from scipy.signal import argrelextrema


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
    limit = 4
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
        data["is_change_relevant"] = data["change"] >= 0.2

        ticker_check = {}
        ticker_check['ticker'] = ticker
        ticker_check['change'] = data["change"].to_list()
        ticker_check['relevant'] = data["is_change_relevant"].to_list()
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
            ticker, "1m", limit=20
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
        print(ticker)
        print(data.tail(3)["aroon_up"])
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
        last_mean = data.head(9)["volume"].mean()
        current_mean = data.tail(1)["volume"].mean()
        print(ticker)
        print("volume ratio: ", current_mean / last_mean)
        if (current_mean / last_mean) >= 1:
            increased_volumes.append(ticker)
    return increased_volumes

def get_lowest_difference_to_maximum(tickers):
    lowest_difference_to_maximum = None
    order = 2
    for ticker in tickers:
        bars = exchange.fetch_ohlcv(
            ticker, "1m", limit=90
        )
        data = pd.DataFrame(
            bars[:], columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"]
        )
        data["Timestamp"] = pd.to_datetime(data["Timestamp"], unit="ms")
        data['min'] = data.iloc[argrelextrema(data['Close'].values, np.less_equal, order=order)[0]]['Close']
        data['max'] = data.iloc[argrelextrema(data['Close'].values, np.greater_equal, order=order)[0]]['Close']
        local_max = data['max'].max()
        current_close = data.iloc[-1, 4]
        print(ticker)
        print("maximum: ", local_max)
        print("current close: ", current_close)
        ratio = ((current_close - local_max) * 100) / local_max
        print("ratio: ", ratio)
        if ratio > -1:
            lowest_difference_to_maximum = ticker
    return lowest_difference_to_maximum

def is_buy(ticker):
    order = 5
    bars = exchange.fetch_ohlcv(
        ticker, "1m", limit=90
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
    
    data['min'] = data.iloc[argrelextrema(data['close'].values, np.less_equal, order=order)[0]]['close']
    data['max'] = data.iloc[argrelextrema(data['close'].values, np.greater_equal, order=order)[0]]['close']

    max_column = data['max'].dropna().sort_values()
    min_column = data['min'].dropna().sort_values()
    
    current_close = data.iloc[-1, 4]
    last_max = (max_column.values)[-1]
    previous_max = (max_column.values)[-2]
    
    if current_close < last_max:
        print('dont buy')
    if current_close == last_max and current_close > previous_max:
        print('buy')
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print("**** Current Time =", current_time)
        print('****', data.iloc[-1, 4])

def get_wait_time():
        minute = datetime.now().minute
        wait_time = (10 - (minute % 10)) * 60
        return wait_time

def get_wait_time_1():
        seconds = datetime.now().second
        wait_time = (60 - (seconds % 60))
        return wait_time


if __name__ == "__main__":
    
    running = True
    candidate_not_found = True
    observed = False

    count = 0

    while running:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print("Current Time =", current_time)
        tickers = get_tickers()
        major_move = get_ticker_with_bigger_moves(tickers)
        print("major move: ", major_move)
        increased_volume = get_ticker_with_increased_volume(major_move)
        print("increased volume: ", increased_volume)
        buy_signals = get_ticker_with_aroon_buy_signals(increased_volume)
        print("buy signals", buy_signals)
        selected_Ticker = get_lowest_difference_to_maximum(buy_signals)
        if selected_Ticker:
            print("selected: ", selected_Ticker)
            observed = True
            count = 0
            while observed:
                print("check if buyable")
                is_buy(selected_Ticker)
                wait_time = get_wait_time_1()
                print("wait: ", wait_time)                
                time.sleep(wait_time)
                count += 1
                if count >= 10:
                    observed = False
        else:  
            print("Wait for next check.")  
            time.sleep(get_wait_time())

