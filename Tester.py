from math import isnan, nan
from Exchange import Exchange
import random
import pandas as pd


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
    limit = 24
    print("Ticker;Current Mean;Last Mean;Quot")
    for ticker in tickers:
        data = get_data(exchange, ticker, "1h", limit)
        last_mean = data.head(limit-1)["volume"].mean()
        current_mean = data.tail(1)["volume"].mean()
        print(ticker, current_mean, last_mean, current_mean / last_mean)
        if not pd.isna(current_mean) and not pd.isna(last_mean) and last_mean != 0:
            quot = current_mean / last_mean
            if (current_mean / last_mean) >= 1.5:
                print("{};{};{};{}".format(ticker, current_mean, last_mean, quot))
                increased_volumes.append(ticker)
    return increased_volumes


if __name__ == "__main__":
    
    exchange = Exchange("bitget")

    #tickers = get_tickers(exchange)
    #tickers = get_tickers_as_list(tickers)

    print(get_ticker_with_increased_volume(exchange, ['PORTO/USDT', 'APT/USDT', 'CAKE/USDT', 'NYM/USDT', 'ICX/USDT', 'APT/USDT', 'CAKE/USDT', 'NYM/USDT', 'ICX/USDT']))

    
    