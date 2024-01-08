import pandas as pd
import numpy as np
import json
import time
import logging
import argparse
import schedule
from random import randint
from models import V1
from datetime import datetime
import threading
import exchanges


class TraderClass:
    commission = 0.075 / 100
    base_currency = "USDT"

    def __init__(self, trading_mode, coin, coin_distribution, frequency, exchange):
        self.trading_mode = trading_mode
        self.coin = coin
        self.coin_distribution = coin_distribution
        self.frequency = frequency
        self.exchange = exchange
        self.previous_dataset = None
        self.has_position = False
        self.position = {}
        self.pnl = 0
        self.stop_running = False
        self.set_position(0, 0, 0)

        self.logger = logging.getLogger(self.coin)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler = logging.FileHandler(
            filename="trading-" + coin + "-v3.log", mode="w", encoding="utf-8"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def set_stop_running(self):
        self.logger.info("Stop processing.")
        self.stop_running = True

    def set_position(self, price, size, total):
        self.position["price"] = price
        self.position["size"] = size
        self.position["total"] = total
        if size > 0:
            self.has_position = True
        else:
            self.has_position = False

    def set_stop_running(self):
        self.logger.info("Stop processing.")
        self.stop_running = True

    def fetch_data(self):
        bars = self.exchange.fetch_ohlcv(
            self.coin + "/" + self.base_currency, timeframe=self.frequency, limit=300
        )
        data = pd.DataFrame(
            bars[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        return data

    def get_initial_position(self):
        current_balance = self.exchange.fetch_balance()[self.coin]["free"]

        trades = self.exchange.fetch_my_trades(self.coin + "/" + self.base_currency)
        current_price = 0
        if len(trades) > 0:
            if trades[-1]["side"] == "buy":
                current_price = trades[-1]["price"]
        else:
            current_price = self.exchange.fetch_ticker(
                self.coin + "/" + self.base_currency
            )["last"]

        if current_balance * current_price > 1:
            self.set_position(
                current_price, current_balance, current_balance * current_price
            )
        else:
            self.set_position(0, 0, 0)

    def get_funding(self):
        total = 0
        coin_keys = self.coin_distribution.keys()
        time.sleep(randint(1, 5))
        for key in coin_keys:
            try:
                current_balance = self.exchange.fetch_balance()[key]["free"]
            except:
                current_balance = 0
            current_price = self.exchange.fetch_ticker(key + "/" + self.base_currency)[
                "last"
            ]
            if current_balance * current_price < 1:
                total = total + float(self.coin_distribution[key]) * 10
        ratio = (self.coin_distribution[self.coin] * 10) / total
        return (self.exchange.fetch_balance()[self.base_currency]["free"] * ratio) - 3

    def get_trade_price(self, order_id):
        trades = self.exchange.fetch_my_trades(
            symbol=self.coin + "/" + self.base_currency,
            since=None,
            limit=None,
            params={},
        )
        total_sum = 0
        amount_sum = 0
        found = False
        while not found:
            time.sleep(5)
            for trade in trades:
                if trade["order"] == order_id:
                    found = True
                    total_sum = total_sum + (trade["price"] * trade["amount"])
                    amount_sum = amount_sum + trade["amount"]
        final_price = total_sum / amount_sum
        return final_price

    # Trading Functions

    # Backtrading

    def backtrading(self, data):
        for i in range(len(data)):
            if i > 1:
                if data.iloc[i, -1] == -1:
                    self.offline_sell(data.iloc[i, 4], data.iloc[i, 0])
                if data.iloc[i, -1] == 1:
                    self.offline_buy(data.iloc[i, 4], data.iloc[i, 0])

    def offline_buy(self, price, ts):
        self.set_position(price, 10, price * 10 - price * 10 * self.commission)
        self.logger.info(
            "Offline Trading:\t{}\tBuy Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}".format(
                ts,
                price,
                10,
                price * 10,
                price * 10 * self.commission,
            )
        )

    def offline_sell(self, price, ts):
        sell_com = price * self.position["size"] * self.commission
        sell_total = price * self.position["size"] - sell_com
        self.pnl = self.pnl + (sell_total - self.position["total"])
        self.logger.info(
            "Offline Trading:\t{}\tSell Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}\tPnL:\t{:.5f}".format(
                ts, price, self.position["size"], sell_total, sell_com, self.pnl
            )
        )
        self.set_position(0, 0, 0)

    # Live Trading

    def live_buy(self, price, ts):
        time.sleep(randint(1, 3))
        funding = self.get_funding()

        size = funding / price
        self.logger.info(
            "Prepare BUY: Funding {}, Price: {}, Size: {}, Coin: {}".format(
                funding, price, size, self.coin
            )
        )
        order = self.exchange.create_order(
            self.coin + "/" + self.base_currency,
            "market",
            "buy",
            size,
            price,
        )
        price = self.get_trade_price(order["id"])
        self.set_position(price, size, price * size)
        self.logger.info(
            "Trading BUY: {}, order id: {}, price: {}".format(ts, order["id"], price)
        )

    def live_sell(self, ts):
        time.sleep(randint(1, 3))
        size = self.exchange.fetch_balance()[self.coin]["free"]
        self.logger.info(
            "Prepare SELL: Size: {}, Coin: {}, Size: {}".format(
                self.position["size"], self.coin, size
            )
        )
        order = self.exchange.create_order(
            self.coin + "/" + self.base_currency,
            "market",
            "sell",
            size,
        )
        self.set_position(0, 0, 0)

        price = self.get_trade_price(self.coin, order["id"])
        pnl = pnl + price - self.position["price"]

        has_position = False

        self.logger.info(
            "Trading SELL: {}, order id: {}, price: {}, PnL: {}".format(
                ts, order["id"], price, pnl
            )
        )

    # Data Processing

    def data_processing(self):
        time.sleep(randint(1, 5))
        data = self.fetch_data()

        new_data_available = True
        if not self.previous_dataset is None:
            data = pd.concat([previous_dataset, data])
            data = data.drop_duplicates()
            new_data = data.merge(
                previous_dataset, on=["timestamp"], how="left", indicator=True
            )
            new_data = new_data[new_data["_merge"] == "left_only"]
            new_data.drop(
                new_data.columns[len(new_data.columns) - 1], axis=1, inplace=True
            )
            new_data = new_data.dropna(axis=1, how="all")
            if new_data.empty:
                new_data_available = False

        self.logger.info(
            "Mode: {}, Loaded: {}, new: {}".format(
                self.trading_mode, len(data), new_data_available
            )
        )

        previous_dataset = data.copy(deep=True)

        if self.trading_mode == "live":
            if new_data_available:
                buy_sell_decision = V1.live_trading_model(
                    data,
                    self.logger,
                    self.has_position,
                    self.position,
                    self.highest_price,
                )
                if buy_sell_decision == 1:
                    self.live_buy(data.iloc[-1, 4], data.iloc[-1, 0])
                if buy_sell_decision == -1:
                    self.live_sell(data.iloc[-1, 4])

        if self.trading_mode == "back":
            dataset = V1.backtrading_model(data)
            V1.show_plot(dataset)
            self.backtrading(dataset)

    def run_threaded(job_func):
        job_thread = threading.Thread(target=job_func)
        job_thread.start()

    def run(self):
        self.logger.info(
            "Starting Trader for Coin: {}, Live mode: {}, Frequency: {}".format(
                self.coin, self.trading_mode, self.frequency
            )
        )

        self.get_initial_position()
        self.logger.info(
            "Has Position: {}, Initial Position: Size: {}, Price: {}, Total: {}".format(
                self.has_position,
                self.position["size"],
                self.position["price"],
                self.position["total"],
            )
        )

        if self.trading_mode:
            self.data_processing()
            schedule.every(1).minutes.do(self.data_processing)
            self.logger.info("Waiting 15 minutes.")

            while not self.stop_running:
                schedule.run_pending()
                time.sleep(1)
        else:
            self.data_processing()
            print(self.pnl)

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


if __name__ == "__main__":
    exchange = exchanges.cryptocom()
    trader = TraderClass(
        trading_mode="live",
        coin="GMT",
        coin_distribution={"XRP": 0.25, "XLM": 0.25, "GMT": 0.25, "SOL": 0.25},
        frequency="15m",
        exchange=exchange,
    )

    trader.run()
