from pdb import run
from exchanges import Exchange
import numpy as np
import pandas as pd
import random
import time
import math
from datetime import datetime
from pandas_datareader import data as pdr
import time
import matplotlib.pyplot as plt
from tqdm import tqdm
from ta.trend import AroonIndicator, EMAIndicator
from scipy.signal import argrelextrema


base_currency = "USD"

amount_coins = 500

wait_time_next_asset_selection_minutes = 15
wait_time_next_buy_selection_seconds = 60
buy_attempts_nr = 30
move_increase_threshold = 0.2
move_increase_period_threshold = 2
volume_increase_threshold = 1.5
difference_to_maximum_max = -1
difference_to_resistance_min = 0.005



def get_tickers(exchange):
    tickers = exchange.fetch_tickers()
    tickers = pd.DataFrame(tickers)
    tickers = tickers.T
    tickers = tickers[tickers["symbol"].str.endswith("/" + base_currency)].head(amount_coins)
    market_movement = tickers["percentage"].mean() * 100
    print("market_movement: ", market_movement)
    tickers = tickers["symbol"].to_list()
    random.shuffle(tickers)
    return tickers, market_movement


def get_market_factor(pos_neg_mean):
    if pos_neg_mean > 3:
        return 0.95
    elif pos_neg_mean >1 and pos_neg_mean <=3:
        return 0.8
    elif pos_neg_mean >0 and pos_neg_mean <=1:
        return 0.6
    elif pos_neg_mean >-2 and pos_neg_mean <=0:
        return 0.4
    else:
        return 0.2


def wait(period):
    if period == "short":
        wait_time = get_wait_time_1()
    if period == "long":
        wait_time = get_wait_time()
    print("wait: ", wait_time)
    time.sleep(wait_time)

def get_wait_time():
        minute = datetime.now().minute
        wait_time = (wait_time_next_asset_selection_minutes - (minute % wait_time_next_asset_selection_minutes)) * 60
        return wait_time

def get_wait_time_1():
        seconds = datetime.now().second
        wait_time = (wait_time_next_buy_selection_seconds - (seconds % wait_time_next_buy_selection_seconds))
        return wait_time

def print_time():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("Current Time =", current_time)


def get_USD_balance(exchange):
    return exchange.fetch_balance()[base_currency]["free"]

def get_Ticker_balance(exchange, ticker):
    ticker = ticker.replace("/" + base_currency, "")
    return exchange.fetch_balance()[ticker]["free"]

def get_funding(usd, market_movement):
    return usd * get_market_factor(market_movement)

def convert_to_precision(size, precision):
    return math.floor(size/precision) * precision

def get_precision(exchange, ticker):
    markets = exchange.exchange.load_markets()
    return float((markets[ticker]['precision']['amount']))

def buy_order(exchange, usd, ticker, price, funding):
    print("BUY")
    print_time()
    precision = get_precision(exchange, ticker)
    size = convert_to_precision(funding / price, precision)
    print("size: ", size)
    order_id = exchange.create_buy_order(ticker, size, price)
    return order_id

def sell_order(exchange, ticker, size, stopLossPrice):
    print("SELL ORDER")
    print_time()
    exchange.cancel_orders(ticker)
    time.sleep(10)
    return exchange.create_stop_loss_order(ticker, size, stopLossPrice)

def get_data(exchange, ticker, interval, limit):
    bars = exchange.fetch_ohlcv(
            ticker, interval, limit=limit
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data

def save_to_file(data, filename):
    data.to_csv(filename, header=True, index=None, sep=';', mode='w')

def read_from_file(filename):
    return pd.read_csv(filename, sep=';')

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

def add_ema(data):
        indicator_EMA_9 = EMAIndicator(close=data["close"], window=9)
        data["ema_9"] = indicator_EMA_9.ema_indicator()
        indicator_EMA_20 = EMAIndicator(close=data["close"], window=20)
        data["ema_20"] = indicator_EMA_20.ema_indicator()
        return data

def get_ticker_with_bigger_moves(exchange, tickers):
    limit = 4
    bigger_moves = []
    iterations = len(tickers)
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for ticker in tickers:
        data = get_data(exchange, ticker, "5m", limit)
        data["change"] = ((data["close"] - data["open"]) / data["open"]) * 100
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
        print(ticker)
        print(data.tail(3)["aroon_up"])
        if (100 in data.tail(3)["aroon_up"].to_list()):
            buy_signals.append(ticker)
    return buy_signals


def get_ticker_with_increased_volume(exchange, tickers):
    increased_volumes = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1d", limit=10)
        last_mean = data.head(9)["volume"].mean()
        current_mean = data.tail(1)["volume"].mean()
        print(ticker)
        print("volume ratio: ", current_mean / last_mean)
        if (current_mean / last_mean) >= volume_increase_threshold:
            increased_volumes.append(ticker)
    return increased_volumes


def get_lowest_difference_to_maximum(excheange, tickers):
    lowest_difference_to_maximum = None
    for ticker in tickers:
        data = get_data(excheange, ticker, "1m", limit=90)
        data = add_min_max(data)
        local_max = data['max'].max()
        current_close = data.iloc[-1, 4]
        print(ticker)
        print("maximum: ", local_max)
        print("current close: ", current_close)
        ratio = ((current_close - local_max) * 100) / local_max
        print("ratio: ", ratio)
        if ratio > difference_to_maximum_max:
            lowest_difference_to_maximum = ticker
    return lowest_difference_to_maximum


def is_buy_decision(exchange, ticker):
    data = get_data(exchange, ticker, "1m", limit=90)
    data = add_min_max(data)
    data = add_aroon(data)

    max_column = data['max'].dropna().drop_duplicates().sort_values()
    print(max_column)    
    current_close = data.iloc[-1, 4]
    print("current close: ", current_close)
    last_max = (max_column.values)[-1]
    print("last max: ", last_max)
    previous_max = (max_column.values)[-2]
    print("previous max: ", previous_max)
    
    if current_close < last_max:
        return [False, None]
    elif current_close >= last_max and current_close >= previous_max:
        return [True, current_close]
    else:
        return [False, None]


def set_sell_trigger(exchange, isInitial, ticker, size, highest_value):
    print("***********************")
    data = get_data(exchange, ticker, "1m", limit=90)
    data = add_min_max(data)
    min_column = data['min'].dropna().drop_duplicates().sort_values()
    print(min_column)
    print(len(min_column))
    print("highest_value: ", highest_value)
    print("current: ", data.iloc[-1, 4])
    if isInitial or (highest_value < data.iloc[-1, 4]):
        print("new highest value")
        highest_value = data.iloc[-1, 4]
        resistance_found = False
        row = -1
        while not resistance_found:
            if row >= (-1) * len(min_column):
                resistance = min_column.iloc[row]
                diff = (abs(data.iloc[-1, 4] - resistance)) / data.iloc[-1, 4]
                print("resistance: ", resistance)
                print("diff: ", diff)
                if (diff >= difference_to_resistance_min):
                    print("set new sell triger: ", resistance)
                    sell_order(exchange, ticker, size, resistance)
                    resistance_found = True
                else:
                    row -= 1
            else:
                resistance = min_column.iloc[(-1) * len(min_column)]
                sell_order(exchange, ticker, size, resistance)
                resistance_found = True
    return highest_value

def plot(data):
    plt.figure(figsize=(14, 7))
    plt.plot(data['close'], label='close Price', color='black')
    plt.scatter(data.index, data['min'], label='Local Minima', color='green', marker='^', alpha=1)
    plt.scatter(data.index, data['max'], label='Local Maxima', color='red', marker='v', alpha=1)
    plt.plot(data.index, data['ema_9'], label='EMA 9', color='red', alpha=1)
    plt.plot(data.index, data['ema_20'], label='EMA 20', color='blue', alpha=1)
    minima = data.dropna(subset=['min'])
    maxima = data.dropna(subset=['max'])
    for i in range(len(minima) - 1):
        plt.plot([minima.index[i], minima.index[i + 1]], [minima['min'].iloc[i], minima['min'].iloc[i + 1]], label='Support Line', color='green', linestyle='--')
    

    for i in range(len(maxima) - 1):
        plt.plot([maxima.index[i], maxima.index[i + 1]], [maxima['max'].iloc[i], maxima['max'].iloc[i + 1]], label='Resistance Line', color='red', linestyle='--')

    plt.title('Stock Support and Resistance Levels')
    plt.show()


def get_candidate(exchange):
    tickers, market_movement = get_tickers(exchange)
    major_move = get_ticker_with_bigger_moves(exchange, tickers)
    print("major move: ", major_move)
    increased_volume = get_ticker_with_increased_volume(exchange, major_move)
    print("increased volume: ", increased_volume)
    buy_signals = get_ticker_with_aroon_buy_signals(exchange, increased_volume)
    print("buy signals", buy_signals)
    selected_Ticker = get_lowest_difference_to_maximum(exchange, buy_signals)
    return selected_Ticker, market_movement

def still_has_postion(size, price):
    return (size * price) > 5


def run_trader():

    exchange = Exchange("cryptocom")

    running = True

    while running:
        
        print_time()

        usd_balance = get_USD_balance(exchange)

        selected_Ticker, market_movement = get_candidate(exchange)
        
        if selected_Ticker:
            print("selected: ", selected_Ticker)
            buy_attempts = 1

            #observe selected Ticker
            price = None
            buy_decision = False
        
            is_buy_info = [True, 0]
            while not buy_decision and buy_attempts <= buy_attempts_nr:
                print("attempt: ", buy_attempts)
                is_buy_info = is_buy_decision(exchange, selected_Ticker)
                if not is_buy_info[0]:
                    buy_attempts += 1
                    wait("short")
                else:
                    price = is_buy_info[1]
                    buy_decision = True
            print("buy decision: ", buy_decision)    
            
            if buy_decision:

                #buy sleected Ticker
                funding = get_funding(usd_balance, market_movement)
                print("funding: ", funding)
                order = buy_order(exchange, usd_balance, selected_Ticker, price, funding)
                time.sleep(10)

                #adjust sell order
                adjust_sell_trigger = True
                isInitial = True
                highest_value = price
                while adjust_sell_trigger:
                    size = get_Ticker_balance(exchange, selected_Ticker)
                    if still_has_postion(size, highest_value):
                        highest_value = set_sell_trigger(exchange, isInitial, selected_Ticker, size, highest_value)
                        isInitial = False
                        wait("short")
                    else:
                        adjust_sell_trigger = False
                        print("Stopping.")
        else:  
            wait("long")



if __name__ == "__main__":
    
    run_trader()
    


