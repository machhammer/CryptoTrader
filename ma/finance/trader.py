import pandas as pd
import numpy as np
import json
import time
import logging
import argparse
import schedule
import exchanges
from random import randint
from models import V1
from datetime import datetime

previous_dataset = None
has_position = False
position = {'price': 0, 'size': 0, 'total': 0}
pnl = 0
commission = 0.075 / 100
base_currency = 'USDT'
coin = None

exchange = exchanges.cryptocom()

coins = {
    "XRP": 0.25,
    "FITFI": 0.25,
    "GMT": 0.25,
    "SOL": 0.25

}

# Helper Functions

def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Sample for pivot point and cross plotting",
    )
    parser.add_argument("--coin", required=True, help="Coin to trade")
    parser.add_argument(
        "--frequency", required=True, help="Refresh frequency in seconds."
    )
    parser.add_argument("--live", required=True, help="Live (True/False)")
    return parser.parse_args()


def fetch_data(frequency, coin):
    bars = exchange.fetch_ohlcv(coin + "/" + base_currency, timeframe=frequency, limit=300)
    df = pd.DataFrame(
        bars[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def get_initial_position(coin):
    global position
    global has_position
    try:
        current_balance = exchange.fetch_balance()[coin]["free"]
        current_price = exchange.fetch_ticker(coin + "/" + base_currency)["last"]
        if current_balance * current_price > 1:
            position['price'] = current_price
            position['size'] = current_balance
            position['total'] = current_balance * current_price
            has_position = True
        else:
            has_position = False
    except:
        has_position = False

def get_funding(coin):
    total = 0
    coin_keys = coins.keys()
    time.sleep(randint(1,5))
    for key in coin_keys:
        try:
            current_balance = exchange.fetch_balance()[key]["free"]
        except:
            current_balance = 0
        current_price = exchange.fetch_ticker(key + "/" + base_currency)["last"]
        if current_balance * current_price < 1:
            total = total + float(coins[key]) * 10
    ratio = (coins[coin] * 10) / total
    return (exchange.fetch_balance()[base_currency]["free"] * ratio) - 3


def get_trade_price(coin, order_id):
    trades = exchange.fetch_my_trades(symbol=coin + "/" + base_currency, since=None, limit=None, params={})
    total_sum = 0
    amount_sum = 0
    found = False
    while not found:
        time.sleep(5)
        for trade in trades:
            if (trade['order'] == order_id):
                found = True
                total_sum = total_sum + (trade['price'] * trade['amount'])
                amount_sum = amount_sum + trade['amount']
    final_price = total_sum / amount_sum
    return final_price


# Trading Functions

# Backtrading


def backtrading(data):
    for i in range(len(data)):
        if i > 1:
            if data.iloc[i, -1] == -1:
                offline_sell(data.iloc[i, 4], data.iloc[i, 0])
            if data.iloc[i, -1] == 1:
                offline_buy(data.iloc[i, 4], data.iloc[i, 0])


def offline_buy(price, ts):
    global position
    global pnl
    position["price"] = price
    position["size"] = 10
    position["total"] = position["price"] * position["size"]
    position["total"] = position["total"] - position["total"] * commission
    logging.info(
        "Offline Trading:\t{}\tBuy Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}".format(
            ts,
            price,
            position["size"],
            position["total"],
            position["total"] * commission,
        )
    )


def offline_sell(price, ts):
    global position
    global pnl
    sell_com = price * position["size"] * commission
    sell_total = price * position["size"] - sell_com
    pnl = pnl + (sell_total - position["total"])
    logging.info(
        "Offline Trading:\t{}\tSell Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}\tPnL:\t{:.5f}".format(
            ts, price, position["size"], sell_total, sell_com, pnl
        )
    )
    position["price"] = 0
    position["size"] = 0
    position["total"] = 0


# Live Trading


def live_buy(price, ts):
    global position
    global has_position
    
    time.sleep(randint(1,3))
    funding = get_funding(coin)
    
    size = funding / price
    logging.info("Prepare BUY: Funding {}, Price: {}, Size: {}, Coin: {}".format(funding, price, size, coin))
    order = exchange.create_order(
        coin + "/" + base_currency,
        "market",
        "buy",
        size,
        price,
    )
    price = get_trade_price(coin, order['id'])
    position["price"] = price
    position["size"] = size
    position["total"] = price * size
    has_position = True
    logging.info("Trading BUY: {}, order id: {}, price: {}".format(ts, order['id'], price))


def live_sell(ts):
    global position
    global pnl
    global has_position

    time.sleep(randint(1,3))

    size = exchange.fetch_balance()[coin]["free"]
    
    logging.info("Prepare SELL: Size: {}, Coin: {}, Size: {}".format(position['size'], coin, size))

    order = exchange.create_order(
        coin + "/" + base_currency,
        "market",
        "sell",
        size,
    )
    position["price"] = 0
    position["size"] = 0
    position["total"] = 0
        
    price = get_trade_price(coin, order['id'])
    pnl = pnl + price - position['price']
    
    has_position = False

    logging.info("Trading SELL: {}, order id: {}, price: {}, PnL: {}".format(ts, order['id'], price, pnl))
    


# Data Processing


def data_processing(frequency, trading_mode):
    global previous_dataset
    global position
    global has_position

    time.sleep(randint(1,5))
    data = fetch_data(frequency, coin)

    new_data_available = True
    if not previous_dataset is None:
        data = pd.concat([previous_dataset, data])
        data = data.drop_duplicates()
        new_data = data.merge(
            previous_dataset, on=["timestamp"], how="left", indicator=True
        )
        new_data = new_data[new_data["_merge"] == "left_only"]
        new_data.drop(new_data.columns[len(new_data.columns) - 1], axis=1, inplace=True)
        new_data = new_data.dropna(axis=1, how="all")
        if new_data.empty:
            new_data_available = False

    logging.info("Mode: {}, Loaded: {}, new: {}".format(trading_mode, len(data), new_data_available))

    previous_dataset = data.copy(deep=True)

    if trading_mode == "live":
        if new_data_available:
            buy_sell_decision = V1.live_trading_model(data, has_position, position)
            if buy_sell_decision == 1:
                live_buy(data.iloc[-1, 4], data.iloc[-1, 0])
                has_position = True
            if buy_sell_decision == -1:
                live_sell(data.iloc[-1, 4])
                has_position = False

    if trading_mode == "back":
        dataset = V1.backtrading_model(data)
        V1.show_plot(dataset)
        backtrading(dataset)


if __name__ == "__main__":

    args = parse_args()
    Live = True if args.live.lower() == "true" else False
    coin = args.coin
    frequency = args.frequency

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler(
                filename="trading-" + coin + "-v2.log", mode="w", encoding="utf-8"
            ),
        ],
    )

    logging.info(
        "Starting Trader for Coin: {}, Live mode: {}, Frequency: {}".format(
            coin, Live, frequency
        )
    )

    get_initial_position(coin)
    logging.info("Has Position: {}, Initial Position: Size: {}, Price: {}, Total: {}".format(has_position, position['size'], position['price'], position['total']))

    
    if Live:
        data_processing(frequency=frequency, trading_mode="live")
        schedule.every(15).minutes.do(
            data_processing, frequency=frequency, trading_mode="live"
        )
        logging.info("Waiting 15 minutes.")

        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        data_processing(frequency=frequency, trading_mode="back")
        print(pnl)
