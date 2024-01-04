import pandas as pd
import numpy as np
import time
import logging
import argparse
import schedule
import exchanges
from models import V1
from datetime import datetime

dataset = None
has_position = False
position = {'price': 0, 'size': 0, 'total': 0}
pnl = 0
commission = 0.075 / 100

exchange = exchanges.cryptocom()

# Helper Functions

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


# Trading Functions

# Backtrading

def backtrading_engine(dataset):
    global has_position
    for i in range(len(dataset)):
        if i > 1:
            if has_position:
                dataset.iloc[i, -1] = np.where((dataset.iloc[i, -2]==True) & (dataset.iloc[i, -2] == dataset.iloc[i-1, -2]),-1, 0)
                if (dataset.iloc[i, -1] == -1): offline_sell(dataset.iloc[i, 4], dataset.iloc[i, 0])
                has_position = np.where((dataset.iloc[i, -1]==-1), False, True)
            else:
                dataset.iloc[i, -1] = np.where((dataset.iloc[i, -3]==True) & (dataset.iloc[i, -3] == dataset.iloc[i-1, -3]), 1, 0)
                if (dataset.iloc[i, -1] == 1): offline_buy(dataset.iloc[i, 4], dataset.iloc[i, 0])
                has_position = np.where((dataset.iloc[i, -1]==1), True, False)

def offline_buy(price, ts):
    global position
    global pnl
    position['price'] = price
    position['size'] = 10
    position['total'] = position['price'] * position['size']
    position['total'] = position['total'] - position['total'] * commission
    log("Offline Trading:\t{}\tBuy Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}".format(ts, price, position['size'], position['total'], position['total'] * commission))

def offline_sell(price, ts):
    global position
    global pnl
    sell_com = price * position['size'] * commission
    sell_total = price * position['size'] - sell_com
    pnl = pnl + (sell_total - position['total'])
    log("Offline Trading:\t{}\tSell Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}\tPnL:\t{:.5f}".format(ts, price, position['size'], sell_total, sell_com, pnl))
    position['price'] = 0
    position['size'] = 0
    position['total'] = 0
    
    
# Live Trading

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


# Data Processing

def data_processing(frequency, trading_mode):
    global dataset
    data = fetch_data(frequency)
    
    V1.generate_buy_sell_signals(data)

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
        schedule.every(30).minutes.do(data_processing, frequency=frequency, trading_mode='live')
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        data_processing(frequency=frequency, trading_mode='back')
        print(pnl)
        V1.show_plot(dataset)
    
