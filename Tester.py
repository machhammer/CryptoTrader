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
    for ticker in tickers:
        data = get_data(exchange, ticker, "4h", limit=12)
        print(data)
        last_mean = data.head(11)["volume"].mean()
        current_mean = data.tail(1)["volume"].mean()
        #print(ticker, current_mean, last_mean, current_mean / last_mean)
        quot = current_mean / last_mean
        print("Ticker: {}, \t\tcurrent mean: {}, \t\t\tlast_mean: {}, \t\tquit: {}".format(ticker, current_mean, last_mean, quot))
        if (current_mean / last_mean) >= 1:
            increased_volumes.append(ticker)
    return increased_volumes


if __name__ == "__main__":
    
    exchange = Exchange("bitget")

    #tickers = get_tickers(exchange)
    #tickers = get_tickers_as_list(tickers)

    print(get_ticker_with_increased_volume(exchange, ['DGI/USDT']))

    
    