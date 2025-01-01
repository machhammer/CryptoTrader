from ta.trend import AroonIndicator, EMAIndicator, MACD
from ta.volume import VolumeWeightedAveragePrice
from scipy.signal import argrelextrema
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("screener")

# ************************************ Get Ticker Data
def get_data(exchange, ticker, interval, limit):
    bars = exchange.fetch_ohlcv(ticker, interval, limit=limit)
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data


# ************************************ add Indicators
def add_min_max(data):
    order = 3
    data["min"] = data.iloc[
        argrelextrema(data["close"].values, np.less_equal, order=order)[0]
    ]["close"]
    data["max"] = data.iloc[
        argrelextrema(data["close"].values, np.greater_equal, order=order)[0]
    ]["close"]
    return data


def add_aroon(data):
    indicator_AROON = AroonIndicator(high=data["high"], low=data["low"], window=14)
    data["aroon_up"] = indicator_AROON.aroon_up()
    data["aroon_down"] = indicator_AROON.aroon_down()
    return data


def add_vwap(data):
    indicator_vwap = VolumeWeightedAveragePrice(
        high=data["high"], low=data["low"], close=data["close"], volume=data["volume"]
    )
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
