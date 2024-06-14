from exchanges import Exchange
import pandas as pd
from pandas_datareader import data as pdr
import pprint

base_currency = "USD"

amount_coins = 500


exchange = Exchange("cryptocom")
tickers = exchange.fetch_tickers()
tickers = pd.DataFrame(tickers)
tickers = tickers.T
tickers = tickers[tickers["symbol"].str.endswith("/" + base_currency)].head(amount_coins)


long_list_relevant_tickers = []
short_list_relevant_tickers = []

tickers = tickers["symbol"].to_list()

print(len(tickers))

limit = 10

for ticker in tickers:
    bars = exchange.fetch_ohlcv(
        ticker, "5m", limit=limit
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    data["change"] = ((data["close"] - data["open"]) / data["open"]) * 100
    data["is_change_relevant"] = data["change"] >= 1

    ticker_check = {}
    ticker_check['ticker'] = ticker
    ticker_check['change'] = data.tail(3)["change"].to_list()
    ticker_check['relevant'] = data.tail(3)["is_change_relevant"].to_list()
    if ticker_check['relevant'].count(True) >=1:
        long_list_relevant_tickers.append(ticker_check)
    
pprint.pprint(long_list_relevant_tickers)

for ticker in long_list_relevant_tickers:
    print(ticker["ticker"])
    bars = exchange.fetch_ohlcv(
        ticker["ticker"], "1d", limit=20
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    last_mean = data.head(19)["volume"].median()
    current_mean = data.tail(1)["volume"].mean()
    print(" *** last mean: {}\t current mean: {}\t Ratio: {}".format(last_mean, current_mean, current_mean / last_mean))
    short_list_relevant_tickers.append(ticker["ticker"])