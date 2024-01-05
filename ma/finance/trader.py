import pandas as pd
import numpy as np
import time
import logging
import argparse
import schedule
import exchanges
from models import V1
from datetime import datetime

previous_dataset = None
has_position = False
position = {"price": 0, "size": 0, "total": 0}
pnl = 0
commission = 0.075 / 100

exchange = exchanges.cryptocom()

# Helper Functions


def log(txt):
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = "%s - %s" % (dt, txt)
    logging.info(txt)


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


def fetch_data(frequency):
    bars = exchange.fetch_ohlcv(coin + "/USDT", timeframe=frequency, limit=300)
    df = pd.DataFrame(
        bars[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


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
    log(
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
    log(
        "Offline Trading:\t{}\tSell Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}\tPnL:\t{:.5f}".format(
            ts, price, position["size"], sell_total, sell_com, pnl
        )
    )
    position["price"] = 0
    position["size"] = 0
    position["total"] = 0


# Live Trading


def live_buy():
    log("Trading: BUY")


def live_sell():
    log("Trading: SELL")


# Data Processing


def data_processing(frequency, trading_mode):
    global previous_dataset
    data = fetch_data(frequency)

    log("Mode {}. Loading new data.".format(trading_mode))

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

    log("Mode {}. Loaded: {}".format(trading_mode, len(data)))

    previous_dataset = data.copy(deep=True)

    if trading_mode == "live":
        if new_data_available:
            buy_sell_decision = V1.live_trading_model(data)
            log("Mode {}. Decision: {}".format(trading_mode, buy_sell_decision))
            if buy_sell_decision == 1:
                live_buy()
            if buy_sell_decision == -1:
                live_buy()
        else:
            log("Mode {}. No new data.")
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
        format="%(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler(
                filename="trading-" + coin + "-v2.log", mode="w", encoding="utf-8"
            ),
            logging.StreamHandler(),
        ],
    )

    log(
        "Starting Trader for Coin: {}, Live mode: {}, Frequency: {}".format(
            coin, Live, frequency
        )
    )

    if Live:
        data_processing(frequency=frequency, trading_mode="live")
        schedule.every(1).minutes.do(
            data_processing, frequency=frequency, trading_mode="live"
        )
        log("Wainting 30 minutes.")

        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        data_processing(frequency=frequency, trading_mode="back")
        print(pnl)
