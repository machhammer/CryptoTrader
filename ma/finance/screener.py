import asyncio
from matplotlib import ticker
from exchanges import Exchange
import numpy as np
import pandas as pd
import random
import time
import pause
import math
import logging
from datetime import datetime
import persistance as database
from pandas_datareader import data as pdr
import time
import matplotlib.pyplot as plt
from tqdm import tqdm
from ta.trend import AroonIndicator, EMAIndicator, MACD
from ta.volume import VolumeWeightedAveragePrice
from scipy.signal import argrelextrema

logger = logging.getLogger("screener")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler = logging.FileHandler(
    filename="screener.log",
    mode="w",
    encoding="utf-8",
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

exchange_name = "bitget"

base_currency = "USDT"

ignored_coins = [base_currency, "USDT", "USD", "CRO", "PAXG"]

amount_coins = 1000

wait_time_next_asset_selection_minutes = 15
wait_time_next_buy_selection_seconds = 60
buy_attempts_nr = 120
move_increase_threshold = 0.003
move_increase_period_threshold = 1
volume_increase_threshold = 1
difference_to_maximum_max = -2
valid_position_amount = 2
#difference_to_resistance_min = 0.01
minimum_funding = 10

def get_tickers(exchange):
    tickers = exchange.fetch_tickers()
    tickers = pd.DataFrame(tickers)
    tickers = tickers.T
    tickers = tickers[tickers["symbol"].str.endswith("/" + base_currency)].head(amount_coins)
    market_movement = tickers["percentage"].median()
    if not exchange_name == "bitget":
        market_movement *= 100
    tickers = tickers["symbol"].to_list()
    random.shuffle(tickers)
    return tickers, market_movement


def get_market_factor(pos_neg_mean):
    fund_ratio = 0
    max_loss = 0
    if pos_neg_mean > 4:
        fund_ratio = 0.9
        max_loss = 0.03
    elif pos_neg_mean > 3:
        fund_ratio = 0.9
        max_loss = 0.03
    elif pos_neg_mean >1 and pos_neg_mean <=3:
        fund_ratio = 0.75
        max_loss = 0.03
    elif pos_neg_mean >0 and pos_neg_mean <=1:
        fund_ratio = 0.5
        max_loss = 0.025
    elif pos_neg_mean >-2 and pos_neg_mean <=0:
        fund_ratio = 0.25
        max_loss = 0.02
    else:
        fund_ratio = 0.1
        max_loss = 0.015
    logger.info("   get market factor for market_movement: {}, fund_ratio: {}, max_loss: {}".format(pos_neg_mean, fund_ratio, max_loss))    
    return fund_ratio, max_loss


def wait(period):
    if period == "short":
        wait_time = get_wait_time_1()
    if period == "long":
        wait_time = get_wait_time()
    logger.debug("wait: {}".format(wait_time))
    time.sleep(wait_time)


def get_wait_time():
        minute = datetime.now().minute
        wait_time = (wait_time_next_asset_selection_minutes - (minute % wait_time_next_asset_selection_minutes)) * 60
        return wait_time


def get_wait_time_1():
        seconds = datetime.now().second
        wait_time = (wait_time_next_buy_selection_seconds - (seconds % wait_time_next_buy_selection_seconds))
        return wait_time


def get_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def print_time():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    logger.info("Current Time: {}".format(current_time))


def get_base_currency_balance(exchange):
    usd = exchange.fetch_balance()[base_currency]["free"]
    return usd


def find_asset_with_balance(exchange):
    asset_with_balance = None
    price = None
    current_assets = exchange.fetch_balance()["free"]
    for asset in current_assets:
        if not asset in ignored_coins:
            found_price = exchange.fetch_ticker(asset + "/" + base_currency)["last"]
            balance = exchange.fetch_balance()[asset]["free"]
            if (balance * found_price) > valid_position_amount:
                logger.info("Found asset with balance: {}".format(asset))
                asset_with_balance = asset + "/" + base_currency
                price = found_price
    return asset_with_balance, price


def get_Ticker_balance(exchange, ticker):
    ticker = ticker.replace("/" + base_currency, "")
    ticker_balance = 0
    try:
        ticker_balance = exchange.fetch_balance()[ticker]["free"]
    except:
        logger.info("   Ticker not in Wallet")
    logger.info("   Ticker Balance: {}".format(ticker_balance))
    return ticker_balance


def get_funding(usd, market_movement):
    mf, _ = get_market_factor(market_movement)
    funding = usd * mf
    if funding < minimum_funding:
        funding = minimum_funding
    logger.info("{} {} * Market Factor {} = Funding {}".format(base_currency, usd, mf, funding))
    return funding


def convert_to_precision(size, precision):
    value = math.floor(size/precision) * precision
    logger.info("   convert_to_precision - size: {}, precision: {}, value: {}".format(size, precision, value)) 
    return math.floor(size/precision) * precision


def get_precision(exchange, ticker):
    markets = exchange.exchange.load_markets()
    value = float((markets[ticker]['precision']['amount'])) 
    logger.info("   get_precision - ticker: {}, value: {}".format(ticker, value))
    return value


def buy_order(exchange, usd, ticker, price, funding):
    logger.info("3. ******** Buy Decision, Ticker: {}, Price: {}, Funding: {}".format(ticker, price, funding))
    precision = get_precision(exchange, ticker)
    size = convert_to_precision(funding / price, precision)
    order = exchange.create_buy_order(ticker, size, price)
    logger.info("   buy order id : {}".format(ticker, order["id"]))
    return order


def sell_order(exchange, ticker, size, stopLossPrice):
    exchange.cancel_orders(ticker)
    logger.info("   put sell order - Ticker: {}, Size: {}, stopLossPrice: {}".format(ticker, size, stopLossPrice))
    order = exchange.create_stop_loss_order(ticker, size, stopLossPrice)
    logger.info("   sell order id : {}".format(order))
    return order


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
    logger.info("   ticker with bigger moves: {}".format(len(bigger_moves)))
    return bigger_moves


def get_ticker_with_aroon_buy_signals(exchange, tickers):
    buy_signals = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit=20)
        data = add_aroon(data)
        logger.debug(ticker)
        logger.debug(data.tail(3)["aroon_up"])
        if (100 in data.tail(3)["aroon_up"].to_list()):
            buy_signals.append(ticker)
    logger.info("   ticker_with_aroon_buy_signals: {}".format(len(buy_signals)))
    return buy_signals


def get_ticker_with_increased_volume(exchange, tickers):
    increased_volumes = []
    print("increased volume")
    for ticker in tickers:
        data = get_data(exchange, ticker, "1d", limit=10)
        last_mean = data.head(9)["volume"].mean()
        current_mean = data.tail(1)["volume"].mean()
        print(ticker)
        print(current_mean / last_mean)
        if (current_mean / last_mean) >= volume_increase_threshold:
            increased_volumes.append(ticker)
    logger.info("   ticker_with_increased_volume: {}".format(len(increased_volumes)))
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
    logger.info("   ticker_with_expected_results: {}".format(len(df)))
    return df


def get_close_to_high(exchange, tickers):
    close_to_high = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1h", limit=48)
        max = data['close'].max()
        if data.iloc[-1, 4] >= max:
            close_to_high.append(ticker)
    logger.info("   ticker_close_to_high: {}".format(len(close_to_high)))
    return close_to_high


def get_lowest_difference_to_maximum(excheange, tickers):
    lowest_difference_to_maximum = None
    for ticker in tickers:
        data = get_data(excheange, ticker, "1m", limit=90)
        data = add_min_max(data)
        local_max = data['max'].max()
        current_close = data.iloc[-1, 4]
        ratio = ((current_close - local_max) * 100) / local_max
        if ratio > difference_to_maximum_max:
            lowest_difference_to_maximum = ticker
    logger.info("   lowest_difference_to_maximum: {}".format(lowest_difference_to_maximum))
    return lowest_difference_to_maximum


def is_buy_decision(exchange, ticker, attempt):
    logger.info("2. ******** Check for Buy Decision, Ticker: {}, #{}".format(ticker, attempt))
    data = get_data(exchange, ticker, "1m", limit=120)
    data = add_min_max(data)
    data = add_aroon(data)
    data = add_vwap(data)
    data = add_macd(data)
    
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
    logger.info("   Resistance check - buy: {}".format(is_buy))

    vwap = data.iloc[-1, 10]
    if is_buy:
        if isinstance(current_close, float) and isinstance(vwap, float):
            if vwap < current_close:
                is_buy = True
            else:
                is_buy = False

    logger.info("   vwap check - buy: {}".format(is_buy))

    macd = data.iloc[-1, 11]
    macd_diff = data.iloc[-1, 12]
    macd_signal = data.iloc[-1, 13]
    if is_buy:
        if isinstance(macd, float) and isinstance(macd_signal, float) and isinstance(macd_diff, float):
            if macd > macd_signal and macd_diff > 0:
                is_buy = True
            else:
                is_buy = False

    logger.info("   macd check - buy: {}".format(is_buy))

    return is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff


def set_sell_trigger(exchange, isInitial, ticker, size, highest_value, max_loss):
    logger.info("4. ********  Check Sell - ticker: {}, isInitial: {}, size: {}, highest_value: {}, max_loss: {}".format(ticker, isInitial, size, highest_value, max_loss))
    data = get_data(exchange, ticker, "1m", limit=720)
    data = add_min_max(data)
    min_column = data['min'].dropna().drop_duplicates().sort_values()
    current_value = data.iloc[-1, 4]
    order = None
    logger.info("   highest value: {}, current value: {}".format(highest_value, current_value))
    if isInitial or (highest_value < current_value):
        highest_value = current_value
        logger.info("   new high: {}".format(highest_value))
        resistance_found = False
        row = -1
        while not resistance_found:
            if row >= (-1) * len(min_column):
                resistance = min_column.iloc[row]
                diff = (current_value - resistance) / current_value
                if (diff >= max_loss):
                    logger.info("   set new sell triger: {}".format(resistance))
                    order = sell_order(exchange, ticker, size, resistance)
                    resistance_found = True
                else:
                    row -= 1
            else:
                resistance = min_column.iloc[(-1) * len(min_column)]
                logger.info("   set new sell triger: {}".format(resistance))
                order = sell_order(exchange, ticker, size, resistance)
                resistance_found = True
    else:
        logger.info("   No new sell trigger")
    return highest_value, order

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
    logger.info("1. ******** Check for New Candidate ********")
    tickers, market_movement = get_tickers(exchange)
    major_move = get_ticker_with_bigger_moves(exchange, tickers)
    expected_results = get_top_ticker_expected_results(exchange, major_move)
    close_to_high = get_close_to_high(exchange, major_move)
    relevant_tickers = expected_results + close_to_high
    logger.info("   {}".format(relevant_tickers))
    increased_volume = get_ticker_with_increased_volume(exchange, relevant_tickers)
    buy_signals = get_ticker_with_aroon_buy_signals(exchange, relevant_tickers)
    selected_Ticker = get_lowest_difference_to_maximum(exchange, buy_signals)
    logger.info("   market movment: {}".format(market_movement))
    logger.info("   Selected: {}".format(selected_Ticker))
    return selected_Ticker, market_movement, major_move, increased_volume, buy_signals, selected_Ticker


def still_has_postion(size, price):
    value = (size * price) > valid_position_amount
    logger.info("   still has position: {}".format(value))
    return value


def write_to_db(market=None, market_factor=None, base_currency=None, selected_ticker=None, funding=None, major_move=None, increase_volume=None, buy_signal=None, close_to_maximum=None, is_buy=None, current_close=None, last_max=None, previous_max=None, vwap=None,macd=None, macd_signal=None, macd_diff=None, buy_order_id=None, sell_order_id=None):
    if (major_move and len(major_move) > 0): 
        major_move=';'.join(map(str, major_move))
    else:
        major_move=None
    if (increase_volume and len(increase_volume) > 0 ): 
        increase_volume=';'.join(map(str, increase_volume))
    else:
        increase_volume=None
    if (buy_signal and len(buy_signal) > 0): 
        buy_signal=';'.join(map(str, buy_signal))
    else:
        buy_signal=None
    database.insert_screener(get_time(), market, market_factor, base_currency, selected_ticker, funding, major_move, increase_volume, buy_signal, close_to_maximum, is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff, buy_order_id, sell_order_id)    


def run_trader():

    exchange = Exchange("bitget")

    running = True

    asset_with_balance, price = find_asset_with_balance(exchange)

    while running:

        usd_balance = get_base_currency_balance(exchange)

        if not asset_with_balance:
            selected_Ticker, market_movement, major_move, increased_volume, buy_signals, lowest_distance_to_max = get_candidate(exchange)
            write_to_db(market=market_movement, base_currency=base_currency, selected_ticker=selected_Ticker, major_move=major_move, increase_volume=increased_volume, buy_signal=buy_signals, close_to_maximum=lowest_distance_to_max)
            buy_decision = True
        else:
            selected_Ticker = asset_with_balance
            write_to_db(base_currency=base_currency, selected_ticker=selected_Ticker)
            

        if selected_Ticker:

            buy_attempts = 1

            #observe selected Ticker
            buy_decision = False
           
            while (not buy_decision and buy_attempts <= buy_attempts_nr and not asset_with_balance):
                is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff = is_buy_decision(exchange, selected_Ticker , buy_attempts)
                write_to_db(selected_ticker=selected_Ticker, is_buy=is_buy, current_close=current_close, last_max=last_max, previous_max=previous_max, vwap=vwap, macd=macd, macd_signal=macd_signal, macd_diff=macd_diff)
                if not is_buy:
                    buy_attempts += 1
                    wait("short")
                else:
                    price = current_close
                    buy_decision = True
            
            if buy_decision or asset_with_balance:

                #buy sleected Ticker
                if not asset_with_balance:
                    _, market_movement = get_tickers(exchange)
                    funding = get_funding(usd_balance, market_movement)
                    order = buy_order(exchange, usd_balance, selected_Ticker, price, funding)
                    write_to_db(selected_ticker=selected_Ticker, funding=funding, buy_order_id=order['id'])

                #adjust sell order
                adjust_sell_trigger = True
                if asset_with_balance:
                    isInitial = False
                else:
                    isInitial = True

                highest_value = price
                while adjust_sell_trigger:
                    _, market_movement = get_tickers(exchange)
                    _, max_loss = get_market_factor(market_movement)
                    size = get_Ticker_balance(exchange, selected_Ticker)
                    if still_has_postion(size, highest_value):
                        highest_value, order = set_sell_trigger(exchange, isInitial, selected_Ticker, size, highest_value, max_loss)
                        if order:
                            write_to_db(selected_ticker=selected_Ticker, sell_order_id=0)

                        isInitial = False
          
                        wait("short")
                    else:
                        logger.info("Asset has been sold!")
                        adjust_sell_trigger = False
                        asset_with_balance = None
                        buy_decision = False


        else:  
            logger.info("No Asset selected!")
            wait("long")



if __name__ == "__main__":
    run_trader()
    


