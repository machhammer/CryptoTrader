from math import isnan, nan
from Exchange import Exchange
import random
import numpy as np
import pandas as pd
from ta.trend import AroonIndicator, EMAIndicator, MACD
from ta.volume import VolumeWeightedAveragePrice
from scipy.signal import argrelextrema

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

def get_data(exchange, ticker, interval, limit):
    bars = exchange.fetch_ohlcv(
            ticker, interval, limit=limit
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data

def get_ticker_with_increased_volume(exchange, tickers):
    increased_volumes = []
    limit = 48
    print("Ticker;Current Mean;Last Mean;Quot")
    for ticker in tickers:
        data = get_data(exchange, ticker, "15m", limit)
        last_mean = data.head(limit-4)["volume"].mean()
        current_mean = data.tail(4)["volume"].mean()
        print(ticker, current_mean, last_mean, current_mean / last_mean)
        if not pd.isna(current_mean) and not pd.isna(last_mean) and last_mean != 0:
            quot = current_mean / last_mean
            if (current_mean / last_mean) >= 1.5:
                print("{};{};{};{}".format(ticker, current_mean, last_mean, quot))
                increased_volumes.append(ticker)
    return increased_volumes


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


def add_vwap(data):
    indicator_vwap = VolumeWeightedAveragePrice(high=data["high"], low=data["low"], close=data["close"], volume=data["volume"])
    data["vwap"] = indicator_vwap.volume_weighted_average_price()
    return data


def add_macd(data):
    indicator_macd = MACD(close=data["close"])
    data["macd"] = indicator_macd.macd()
    data["macd_diff"] = indicator_macd.macd_diff()
    data["macd_signal"] = indicator_macd.macd_signal()
    return data


def add_ema(data):
        indicator_EMA_9 = EMAIndicator(close=data["close"], window=9)
        data["ema_9"] = indicator_EMA_9.ema_indicator()
        indicator_EMA_20 = EMAIndicator(close=data["close"], window=20)
        data["ema_20"] = indicator_EMA_20.ema_indicator()
        return data


def is_buy_test(exchange, ticker):
    data = get_data(exchange, ticker, "1m", limit=120)
    data = add_min_max(data)
    data = add_aroon(data)
    data = add_vwap(data)
    data = add_macd(data)
    data.to_csv("output.txt")
    
    max_column = data['max'].dropna().drop_duplicates().sort_values()
    current_close = data.iloc[-1, 4]
    last_max = (max_column.values)[-1]
    previous_max = (max_column.values)[-2]
    
    is_buy = False

    if current_close < last_max:
        is_buy = False
    elif current_close >= last_max and current_close > previous_max:
        is_buy = True
    else:
        is_buy = False


    aroon_up = data.iloc[-1, 8]
    if is_buy:
        if isinstance(aroon_up, float):
            if aroon_up == 100:
                is_buy = True
            else:
                is_buy = False


    vwap = data.iloc[-1, 10]
    if is_buy:
        if isinstance(current_close, float) and isinstance(vwap, float):
            if vwap < current_close:
                is_buy = True
            else:
                is_buy = False


    macd = data.iloc[-1, 11]
    macd_diff = data.iloc[-1, 12]
    macd_signal = data.iloc[-1, 13]
    if is_buy:
        if isinstance(macd, float) and isinstance(macd_signal, float) and isinstance(macd_diff, float):
            if macd > macd_signal and macd_diff > 0:
                is_buy = True
            else:
                is_buy = False


if __name__ == "__main__":
    
    exchange = Exchange("bitget")

    #tickers = get_tickers(exchange)
    #tickers = get_tickers_as_list(tickers)

    print(is_buy_test(exchange, 'COREUM/USDT'))

    
    