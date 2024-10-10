from math import isnan, nan, floor, ceil

import random
import numpy as np
import credentials
import pandas as pd
from tqdm import tqdm
import Database as database
from ta.trend import AroonIndicator, EMAIndicator, MACD
from ta.volume import VolumeWeightedAveragePrice
from scipy.signal import argrelextrema
from datetime import datetime
import ccxt


difference_to_maximum_max = -2
move_increase_threshold = 0.003
move_increase_period_threshold = 1
volume_increase_threshold = 1.3

symbol = "ETH/USDT"
startDate = "2023-10-07 03:00:00+00:00"
startDate = datetime.strptime(startDate, "%Y-%m-%d %H:%M:%S%z")
startDate = datetime.timestamp(startDate)
startDate = int(startDate) * 1000


def coinbase():
    api_key = credentials.provider_1.get("key")
    api_secret = credentials.provider_1.get("secret")

    return ccxt.coinbase(
        {
            "apiKey": api_key,
            "secret": api_secret,
            #'verbose': True
        }
    )

def bitget():
    api_key = credentials.provider_3.get("key")
    api_secret = credentials.provider_3.get("secret")
    password = credentials.provider_3.get("password")
    passphrase = credentials.provider_3.get("passphrase")

    return ccxt.bitget(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "password": passphrase

            #'verbose': True
        }
    )

def get_tickers(exchange):
    tickers = exchange.fetch_tickers()
    tickers = pd.DataFrame(tickers)
    tickers = tickers.T
    tickers = tickers[tickers["symbol"].str.endswith("/USDT")].head(1000)
    return tickers

def get_tickers_as_list(tickers):
    tickers = tickers["symbol"].to_list()
    random.shuffle(tickers)
    return tickers

def get_data(exchange, ticker, interval, since, limit):
    bars = exchange.fetch_ohlcv(
            ticker, interval, since=since, limit=limit
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data

def add_min_max(data):
    order = 3
    data['min'] = data.iloc[argrelextrema(data['close'].values, np.less_equal, order=order)[0]]['close']
    data['max'] = data.iloc[argrelextrema(data['close'].values, np.greater_equal, order=order)[0]]['close']
    return data


def add_aroon(data):
    indicator_AROON = AroonIndicator(
        high=data["high"], low=data["low"], window=14
    )
    data["aroon_up"] = indicator_AROON.aroon_up()
    data["aroon_down"] = indicator_AROON.aroon_down()
    return data


def get_candidate(exchange):

    tickers = get_tickers(exchange)
    tickers = get_tickers_as_list(tickers)
    major_move = get_ticker_with_bigger_moves(exchange, tickers)
    print("major move: ", major_move)
    expected_results = get_top_ticker_expected_results(exchange, major_move)
    print("expected: ", expected_results)
    close_to_high = get_close_to_high(exchange, major_move)
    print("close to high: ", close_to_high)
    relevant_tickers = expected_results + close_to_high
    print("relevant: ", relevant_tickers)
    increased_volume = get_ticker_with_increased_volume(exchange, relevant_tickers)
    print("increased volume: ", increased_volume)
    buy_signals = get_ticker_with_aroon_buy_signals(exchange, increased_volume)
    selected_Ticker = get_lowest_difference_to_maximum(exchange, buy_signals)
    selected_Ticker = get_with_sufficient_variance(exchange, selected_Ticker)
    return selected_Ticker

def get_ticker_with_bigger_moves(exchange, tickers):
    limit = 4
    bigger_moves = []
    iterations = len(tickers)
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", startDate, limit)
        #data["change"] = ((data["close"] - data["open"]) / data["open"]) * 100
        if not data.empty:
            data["change"] = data["close"].pct_change()
            data["is_change_relevant"] = data["change"] >= move_increase_threshold
            ticker_check = {}
            ticker_check['ticker'] = ticker
            ticker_check['change'] = data["change"].to_list()
            ticker_check['relevant'] = data["is_change_relevant"].to_list()
            ticker_check['data'] = data
            if ticker_check['relevant'].count(True) >= move_increase_period_threshold:
                bigger_moves.append(ticker)
        try:
            next(progress_bar)
        except:
            pass
    return bigger_moves


def get_ticker_with_aroon_buy_signals(exchange, tickers):
    buy_signals = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", startDate, limit=20)
        data = add_aroon(data)
        if (100 in data.tail(3)["aroon_up"].to_list()):
            buy_signals.append(ticker)
    return buy_signals


def get_ticker_with_increased_volume(exchange, tickers):
    increased_volumes = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "15m", startDate, limit=28)
        last_mean = data.head(24)["volume"].mean()
        current_mean = data.tail(4)["volume"].mean()
        if (current_mean / last_mean) >= volume_increase_threshold:
            increased_volumes.append(ticker)
    return increased_volumes


def get_top_ticker_expected_results(exchange, tickers):
    accepted_expected_results = {}
    for ticker in tickers:
        data = get_data(exchange, ticker, "5m", startDate, limit=120)
        data['pct_change'] = data['close'].pct_change(periods=3)
        min = data['pct_change'].min()
        if min > -0.005:
            accepted_expected_results[ticker] = min
    df = pd.DataFrame(accepted_expected_results.items(), columns=['ticker', 'min'])
    df = df.sort_values(by='min')   
    df = df.tail(5)['ticker'].to_list()
    return df


def get_close_to_high(exchange, tickers):
    close_to_high = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1h", startDate, limit=48)
        max = data['close'].max()
        if data.iloc[-1, 4] >= max:
            close_to_high.append(ticker)
    return close_to_high


def get_lowest_difference_to_maximum(exchange, tickers):
    lowest_difference_to_maximum = None
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", startDate, limit=90)
        data = add_min_max(data)
        local_max = data['max'].max()
        current_close = data.iloc[-1, 4]
        ratio = ((current_close - local_max) * 100) / local_max
        if ratio > difference_to_maximum_max:
            lowest_difference_to_maximum = ticker
    return lowest_difference_to_maximum

def get_with_sufficient_variance(exchange, ticker):
    duplicate_data = 99
    if ticker:
        data = get_data(exchange, ticker, "1m", startDate, limit=5)
        data = data.duplicated(subset=["close"])
        data = data.loc[lambda x : x == True]
        duplicate_data = len(data)
    if duplicate_data>0:
        return None
    else:
        return ticker



if __name__ == "__main__":
    
    #exchange = Exchange("bitget")

    #get_candidate(exchange)

    exchange = bitget()

    data = get_candidate(exchange)

    print(data)

    