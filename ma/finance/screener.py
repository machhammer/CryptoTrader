from pdb import run
from exchanges import Exchange
import numpy as np
import pandas as pd
import random
import time
from datetime import datetime
from pandas_datareader import data as pdr
import time
import matplotlib.pyplot as plt
from tqdm import tqdm
from ta.trend import AroonIndicator, EMAIndicator
from scipy.signal import argrelextrema


base_currency = "USD"

amount_coins = 500


def get_tickers(exchange):
    tickers = exchange.fetch_tickers()
    tickers = pd.DataFrame(tickers)
    tickers = tickers.T
    tickers = tickers[tickers["symbol"].str.endswith("/" + base_currency)].head(amount_coins)
    tickers = tickers["symbol"].to_list()
    random.shuffle(tickers)
    return tickers

def get_wait_time():
        minute = datetime.now().minute
        wait_time = (10 - (minute % 10)) * 60
        return wait_time

def get_wait_time_1():
        seconds = datetime.now().second
        wait_time = (60 - (seconds % 60))
        return wait_time


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
        if (current_mean / last_mean) >= 1:
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
        if ratio > -1:
            lowest_difference_to_maximum = ticker
    return lowest_difference_to_maximum


def is_buy_decision(exchange, ticker):
    data = get_data(exchange, ticker, "1m", limit=90)
    data = add_min_max(data)
    data = add_aroon(data)

    max_column = data['max'].dropna().sort_values()
        
    current_close = data.iloc[-1, 4]
    last_max = (max_column.values)[-1]
    previous_max = (max_column.values)[-2]
    
    if current_close < last_max:
        return [False, None]
    elif current_close == last_max and current_close > previous_max:
        return [True, current_close]
    else:
        return [False, None]

  

def buy(ticker, price):
    print("***** Buy: ", price)


def set_sell_trigger(exchange, ticker, initial_set, buy_price, max_loss, min_profit):
    data = get_data(exchange, ticker, "1m", limit=90)
    data = add_min_max(data)
    data = add_ema(data)

    current_price = data.iloc[-1, 4]
    print("*** buy price: ", buy_price)
    print("*** current price: ", current_price)

    current_pnl = (current_price - buy_price) / buy_price
    max_loss_price = buy_price * (1 - max_loss)
    min_profit_price = buy_price * (1 + min_profit)
    print ("*** current pnl: ", current_pnl)
    print ("*** max loss: ", max_loss_price)
    print ("*** min profit: ", min_profit_price)

    sell_value = None

    if initial_set or (current_pnl >= max_loss_price and current_pnl < min_profit_price):
        print("new or not within range")
        min_column = data['min'].dropna().sort_values()
        max_loss_price = buy_price * (1 - max_loss)
        min_value = [None, 0]
        for el in min_column:
            diff = abs(max_loss_price - el)
            if (min_value[0] == None or diff < min_value[0]):
                min_value[0] = diff
                min_value[1] = el
        print("set sell at: ", min_value[1])
        sell_value = min_value[1]
    if current_pnl >= min_profit_price:
        print("profit range")
        sell_value = min_column.tail(1).item()
        print("set sell at: ", sell_value)

    # data['ema_20_gr_ema_9'] = data["ema_20"] > data["ema_9"]
    # vs = data.tail(5)['ema_20_gr_ema_9'].to_list() 
    # print(vs)
    # if (vs).count(True) == 5:
    #     now = datetime.now()
    #     current_time = now.strftime("%H:%M:%S")
    #     print("Current Time =", current_time)
    #     print("*** *** SELL now: ", current_price)
    #     sell_value = current_price
    #     raise Exception("SELL position EMA crossing")

    if sell_value == current_price:
        print("*** *** SELL at triggered price: ", sell_value)
        raise Exception("SELL at triggered price")

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
    tickers = get_tickers(exchange)
    major_move = get_ticker_with_bigger_moves(exchange, tickers)
    print("major move: ", major_move)
    increased_volume = get_ticker_with_increased_volume(exchange, major_move)
    print("increased volume: ", increased_volume)
    buy_signals = get_ticker_with_aroon_buy_signals(exchange, increased_volume)
    print("buy signals", buy_signals)
    selected_Ticker = get_lowest_difference_to_maximum(exchange, buy_signals)
    return selected_Ticker

def still_has_postion(ticker):
    return True

def run_trader():

    exchange = Exchange("cryptocom")

    running = True

    while running:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print("Current Time =", current_time)
        selected_Ticker = get_candidate(exchange)
        
        if selected_Ticker:
            print("selected: ", selected_Ticker)
            buy_attempts = 1

            #observe selected Ticker
            price = None
            buy_decision = False
            while not buy_decision and buy_attempts <= 10:
                print("attempt: ", buy_attempts)
                is_buy_info = is_buy_decision(exchange, selected_Ticker)
                if not is_buy_info[0]:
                    buy_attempts += 1
                    wait_time = get_wait_time_1()
                    
                    print("wait: ", wait_time)
                    time.sleep(wait_time)
                else:
                    price = is_buy_info[1]
                    buy_decision = True
            print("buy decision: ", buy_decision)    

            #buy sleected Ticker
            if buy_decision:
                buy(selected_Ticker, price)

                #adjust sell order
                adjust_sell_trigger = True
                initial_set = True
                while adjust_sell_trigger:
                    if still_has_postion(selected_Ticker):
                        print("set sell trigger")
                        set_sell_trigger(exchange, selected_Ticker, initial_set, price, max_loss = 0.01, min_profit=0.015)
                        initial_set = False
                        wait_time = get_wait_time_1()
                        print("wait: ", wait_time)
                        time.sleep(wait_time)
                    else:
                        adjust_sell_trigger = False
        else:  
            wait_time = get_wait_time() 
            print("Wait for next check: ", wait_time)  
            time.sleep(wait_time)



if __name__ == "__main__":
    
    run_trader()
    


