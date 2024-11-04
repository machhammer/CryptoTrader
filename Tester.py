from math import isnan, nan, floor, ceil
from Exchange import Exchange
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
from Helper import Helper


difference_to_maximum_max = -2
move_increase_threshold = 0.003
move_increase_period_threshold = 1
volume_increase_threshold = 2

symbol = "ETH/USDT"
startDate = "2023-10-07 03:00:00+00:00"
startDate = datetime.strptime(startDate, "%Y-%m-%d %H:%M:%S%z")
startDate = datetime.timestamp(startDate)
startDate = int(startDate) * 1000

wait_time_next_asset_selection_minutes = 15
wait_time_next_buy_selection_seconds = 60

helper = Helper(None, wait_time_next_asset_selection_minutes, wait_time_next_buy_selection_seconds)

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


def write_to_database(now, assets, level):
    for asset in assets:
        database.insert_coin_select_table(now, asset, level)


def all_selected_tickers():
    tickers = database.execute_select("select distinct asset from coin_select order by asset")
    return tickers.squeeze().tolist()




def get_candidate(exchange):
    
    tickers = get_tickers(exchange)
    tickers = get_tickers_as_list(tickers)

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    major_move = get_ticker_with_bigger_moves(exchange, tickers)
    #write_to_database(now, major_move, "bm")
    #print("major move: ", major_move)

    expected_results = get_top_ticker_expected_results(exchange, major_move)
    #print("expected: ", expected_results)
    
    close_to_high = get_close_to_high(exchange, major_move)
    #print("close to high: ", close_to_high)
    
    relevant_tickers = expected_results + close_to_high
    relevant_tickers = list(set(relevant_tickers))
    #write_to_database(now, relevant_tickers, "rt")
    #print("relevant: ", relevant_tickers)
    
    increased_volume = get_ticker_with_increased_volume(exchange, relevant_tickers)
    write_to_database(now, increased_volume, "iv")
    #print("increased volume: ", increased_volume)

    buy_signals = get_ticker_with_aroon_buy_signals(exchange, increased_volume)
    write_to_database(now, buy_signals, "bs")
    #print("buy signals: ", buy_signals)

    sufficient_variance = get_with_sufficient_variance(exchange, buy_signals)
    write_to_database(now, sufficient_variance, "sv")
    #print("sufficient variance: ", sufficient_variance)
    
    diff_to_maximum = get_lowest_difference_to_maximum(exchange, sufficient_variance)
    write_to_database(now, diff_to_maximum, "df")
    print("Selected: ", diff_to_maximum)
    
    return diff_to_maximum

def get_ticker_with_bigger_moves(exchange, tickers):
    limit = 4
    bigger_moves = []
    iterations = len(tickers)
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit)
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
        data = get_data(exchange, ticker, "1m", limit=20)
        data = add_aroon(data)
        if (100 in data.tail(3)["aroon_up"].to_list()):
            buy_signals.append(ticker)
    return buy_signals


def get_ticker_with_increased_volume(exchange, tickers):
    increased_volumes = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "15m", limit=28)
        last_mean = data.head(24)["volume"].mean()
        current_mean = data.tail(4)["volume"].mean()
        if (current_mean / last_mean) >= volume_increase_threshold:
            increased_volumes.append(ticker)
    return increased_volumes


def get_top_ticker_expected_results(exchange, tickers):
    accepted_expected_results = {}
    for ticker in tickers:
        data = get_data(exchange, ticker, "5m", limit=120)
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
        data = get_data(exchange, ticker, "1h", limit=48)
        max = data['close'].max()
        if data.iloc[-1, 4] >= max:
            close_to_high.append(ticker)
    return close_to_high


def get_lowest_difference_to_maximum(exchange, tickers):
    lowest_difference_to_maximum = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit=90)
        data = add_min_max(data)
        local_max = data['max'].max()
        current_close = data.iloc[-1, 4]
        ratio = ((current_close - local_max) * 100) / local_max
        if ratio > difference_to_maximum_max:
            lowest_difference_to_maximum.append(ticker)
    return lowest_difference_to_maximum


def get_with_sufficient_variance(exchange, tickers):
    sufficient_variance = []
    duplicate_data = 99
    for ticker in tickers:
        if ticker:
            data = get_data(exchange, ticker, "1m", limit=5)
            data = data.duplicated(subset=["close"])
            data = data.loc[lambda x : x == True]
            duplicate_data = len(data)
        if duplicate_data==0:
            sufficient_variance.append(ticker)
    return sufficient_variance


def get_data(exchange, ticker, interval, limit):
    bars = exchange.fetch_ohlcv(
            ticker, interval, limit=limit
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data


def download_ticker_data(exchange):
    tickers = all_selected_tickers()
    now = datetime.now()
    posttext = "_" + str(now.year) + str(now.month) + str(now.minute)
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", 1000)
        name = ticker.replace("/USDT", "") + posttext + ".csv"
        print(name)
        data.to_csv(name)


if __name__ == "__main__":

    database.initialize_coin_select()

    exchange = Exchange("bitget")
    running = True

    while running:
        now = datetime.now()
        if now.hour >= 3 and now.hour <= 15:
            print("Selected: ", get_candidate(exchange))
            helper.wait("long")
        if now.hour >= 22:
            download_ticker_data(exchange)
            running = False

    
    

    