import pandas as pd
import numpy as np
import ccxt
import time
import logging
import argparse
import schedule
import credentials
import matplotlib.pyplot as plt
from datetime import datetime
from ta.trend import SMAIndicator
from ta.trend import ADXIndicator
from ta.trend import AroonIndicator
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

dataset = None
has_position = False

params = {
     "sma": 10,
     "rsi": 14,
     "macd_slow": 26,
     "macd_fast": 12,
     "macd_sign": 9,
     "adx": 14,
     "aroon": 25,
     "bb": 20,
     "bb_dev": 2,
     "rsi_buy_threshold": 33,
     "rsi_sell_threshold": 73,
}


api_key = credentials.provider_2.get("key")
api_secret = credentials.provider_2.get("secret")

config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.cryptocom(
    {
        "apiKey": api_key,
        "secret": api_secret,
        #'verbose': True
    }
)

def log(txt):
    dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    txt = "%s - %s" % (dt, txt)
    logging.info(txt)


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Sample for pivot point and cross plotting",
    )
    parser.add_argument("--coin", required=True, help="Coin to trade")
    parser.add_argument("--frequency", required=True, help="Refresh frequency in seconds.")
    parser.add_argument("--live", required=True, help="Live (True/False)")
    return parser.parse_args()



def fetch_data(frequency):

    bars = exchange.fetch_ohlcv(coin + '/USDT', timeframe=frequency, limit=300)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    return df



def set_buy_alert(df):
     return [
            df['sma_buy_alert'],
            df['rsi_buy_alert'],
            df['macd_buy_alert'],
            df['adx_buy_alert'],
            df['aroon_buy_alert'],
            df['bb_buy_alert']
        ].count(True) >= 4

def set_sell_alert(df):
     return [
            df['sma_sell_alert'],
            df['rsi_sell_alert'],
            df['macd_sell_alert'],
            df['adx_sell_alert'],
            df['aroon_sell_alert'],
            df['bb_sell_alert']
        ].count(True) >= 4


def check_buy_sell_signals(df):
    indicator_SMA = SMAIndicator(close=df['close'], window=params["sma"])
    df['sma'] = indicator_SMA.sma_indicator()
    
    df['sma_buy_alert'] = np.where((df['sma'] < df['close']), True, False)
    df['sma_sell_alert'] = np.where((df['sma'] < df['close']), False, True)

    indicator_RIS = RSIIndicator(close=df['close'], window=params["rsi"])
    df['rsi'] = indicator_RIS.rsi()

    df['rsi_buy_alert'] = np.where((df['rsi'] < params['rsi_buy_threshold']), True, False)
    df['rsi_sell_alert'] = np.where((df['rsi'] < params['rsi_buy_threshold']), False, True)
    
    indicator_MACD = MACD(close=df['close'], window_fast=params["macd_fast"], window_slow=params["macd_slow"], window_sign=params["macd_sign"])
    df['macd'] = indicator_MACD.macd()
    df['macd_signal'] = indicator_MACD.macd_signal()

    df['macd_buy_alert'] = np.where((df['macd'] > df['macd_signal']), True, False)
    df['macd_sell_alert'] = np.where((df['macd'] > df['macd_signal']), False, True)
  
    indicator_ADX = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=params["adx"])
    df['adx_plus'] = indicator_ADX.adx_pos()
    df['adx_neg'] = indicator_ADX.adx_neg()

    df['adx_buy_alert'] = np.where((df['adx_plus'] > df['adx_neg']), True, False)
    df['adx_sell_alert'] = np.where((df['adx_plus'] > df['adx_neg']), False, True)

    indicator_AROON = AroonIndicator(high=df['high'], low=df['low'], window=params["aroon"])
    df['aroon_up']  = indicator_AROON.aroon_up()
    df['aroon_down']  = indicator_AROON.aroon_down()

    df['aroon_buy_alert'] = np.where((df['aroon_up'] > df['aroon_down']), True, False)
    df['aroon_sell_alert'] = np.where((df['aroon_up'] > df['aroon_down']), False, True)

    indicator_BB = BollingerBands(close=df['close'],  window=params["bb"],  window_dev=params["bb_dev"])
    df['bb_top'] = indicator_BB.bollinger_hband()
    df['bb_bot'] = indicator_BB.bollinger_lband()
    df['bb_avg'] = indicator_BB.bollinger_mavg()
    df['top_bot_diff'] = indicator_BB.bollinger_hband() - indicator_BB.bollinger_lband()
    df['price_bot_diff'] = df['close'] - indicator_BB.bollinger_lband()

    df['ratio'] = df['price_bot_diff'] / df['top_bot_diff']
    
    df['bb_sell_alert'] = np.where((df['price_bot_diff'] / df['top_bot_diff'] > 0.9), True, False)
    df['bb_buy_alert'] = np.where((df['price_bot_diff'] / df['top_bot_diff'] > 0.9), False, True)
    
    df['bb_sell_alert'] = np.where((df['price_bot_diff'] / df['top_bot_diff'] < 0.1), False, True)
    df['bb_buy_alert'] = np.where((df['price_bot_diff'] / df['top_bot_diff'] < 0.1), True, False)

    df['bb_sell_alert'] = np.where(((df['price_bot_diff'] / df['top_bot_diff'] >= 0.1) & (df['price_bot_diff'] / df['top_bot_diff'] <= 0.9)), True, False)
    df['bb_buy_alert'] = np.where(((df['price_bot_diff'] / df['top_bot_diff'] >= 0.1) & (df['price_bot_diff'] / df['top_bot_diff'] <= 0.9)), True, False)

    df['BUY_ALERT'] = df.apply(set_buy_alert, axis=1)
    df['SELL_ALERT'] = df.apply(set_sell_alert, axis=1)


    df['ACTION'] = 0

    

def backtrading_engine(dataset, has_position=False):
    for i in range(len(dataset)):
        if i > 1:
            if has_position:
                dataset.iloc[i, -1] = np.where((dataset.iloc[i, -2]==True) & (dataset.iloc[i, -2] == dataset.iloc[i-1, -2]),-1, 0)
                has_position = np.where((dataset.iloc[i, -1]==-1), False, True)
            else:
                dataset.iloc[i, -1] = np.where((dataset.iloc[i, -3]==True) & (dataset.iloc[i, -3] == dataset.iloc[i-1, -3]), 1, 0)
                has_position = np.where((dataset.iloc[i, -1]==1), True, False)


def live_trading_engine(dataset):
    global has_position
    i = -1
    
    current_buy_ts = dataset.iloc[i, 0]
    current_buy_alert = dataset.iloc[i, -3]
    previous_buy_ts = dataset.iloc[i-1, 0]
    previous_buy_alert = dataset.iloc[i-1, -3]
    log("Current: {}, Buy: {}".format(current_buy_ts, previous_buy_alert))
    log("Previous: {}, Buy: {}".format(previous_buy_ts, previous_buy_alert))
    if (current_buy_alert == True and previous_buy_alert == True):
        if not has_position:    
            log("Trading: Ready to BUY")
            dataset.iloc[i-1, -1] = 1
            live_buy()
            has_position = True
        else:
            log("Trading: Would BUY but already has position.")
    else:
        log("Buy not equal TRUE")

    current_sell_ts = dataset.iloc[i, 0]
    current_sell_alert = dataset.iloc[i, -2]
    previous_sell_ts = dataset.iloc[i-1, 0]
    previous_sell_alert = dataset.iloc[i-1, -2]
    log("Current: {}, Sell: {}".format(current_sell_ts, previous_sell_alert))
    log("Previous: {}, Sell: {}".format(previous_sell_ts, previous_sell_alert))
    if (current_sell_alert == True and previous_sell_alert == True):
        if has_position:
            log("Trading: Ready to SELL")
            dataset.iloc[i-1, -1] = -1
            live_sell()
            has_position = False
        else:
            log("Trading: Would SELL but no position.")
    else:
        log("Sell not equal TRUE")

def live_buy():
    log("Trading: BUY")

def live_sell():
    log("Trading: SELL")


def data_processing(frequency, trading_mode):
    global dataset
    
    data = fetch_data(frequency)
    
    check_buy_sell_signals(data)

    new_data_available = False    
    if (not dataset is None):
        data = pd.concat([dataset, data])
        c_names = list(data.columns.values)
        data = data.drop_duplicates()
        new_data = data.merge(dataset, on=['timestamp'], how='left', indicator=True)
        new_data = new_data[new_data['_merge'] == 'left_only']
        new_data.drop(new_data.columns[len(new_data.columns)-1], axis=1, inplace=True)
        new_data = new_data.dropna(axis=1, how='all')
        if (not new_data.empty):
            new_data_available = True
            #log_data = log_data.set_axis(c_names, axis=1)
            #log(log_data.to_string(index=False))

    if trading_mode == 'live':
        if new_data_available:
            live_trading_engine(data)
    if trading_mode == 'back':
        backtrading_engine(data)

    if new_data_available or (dataset is None):
        log("TS: {}, Last Price: {}, Buy: {}, Sell: {}".format(data.iloc[-1, 0], data.iloc[-1, 4], data.iloc[-1, -3], data.iloc[-1, -2]))

    dataset = data.copy(deep=True)


def show_plot(df):

    figure, axis = plt.subplots(6, figsize=(16,9), gridspec_kw={'height_ratios': [4, 1, 1, 1, 1, 1]})

    axis[0].plot(df['close'])    
    axis[0].plot(df['bb_top'])
    axis[0].plot(df['bb_bot'])
    axis[0].plot(df['bb_avg'])
        
    axis[1].plot(df['ACTION'], 'ro')
    
    axis[2].plot(df['rsi'])
    
    axis[3].plot(df['macd'])
    axis[3].plot(df['macd_signal'])

    axis[4].plot(df['adx_plus'])
    axis[4].plot(df['adx_neg'])

    axis[5].plot(df['aroon_up'])
    axis[5].plot(df['aroon_down'])

    plt.show()



if __name__ == "__main__":
    args = parse_args()
    Live = True if args.live.lower() == "true" else False
    coin = args.coin
    frequency = args.frequency

   
    logging.basicConfig(
        format='%(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(filename="trading-" + coin + ".log", mode="w", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    log("Starting Trader for Coin: {}, Live mode: {}, Frequency: {}".format(coin, Live, frequency))
    
    if Live:
        data_processing(frequency=frequency, trading_mode='none')
        schedule.every(1).minutes.do(data_processing, frequency=frequency, trading_mode='live')
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        data_processing(frequency=frequency, trading_mode='back')
        show_plot(dataset)
    
