import pandas as pd
import time
import logging
import argparse
import threading
import queue
import random
from random import randint
from models import V2
from threading import Thread
import exchanges


class ModelTester:
    commission = 0.075 / 100
    base_currency = "USDT"

    def __init__(
        self,
        coin,
        frequency,
        timeframe,
        exchange,
    ):
        self.coin = coin
        self.frequency = frequency
        self.timeframe = timeframe
        self.exchange = exchange
        self.position = {}
        self.set_position(0, 0, 0, None)
        self.pnl = 0
        self.logger = logging.getLogger(self.coin)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.ERROR)

    def set_position(self, price, size, total, timestamp):
        self.position["price"] = price
        self.position["size"] = size
        self.position["total"] = total
        self.position["timestamp"] = timestamp
        if size > 0:
            self.has_position = True
        else:
            self.has_position = False

    def fetch_data(self):
        time.sleep(random.randint(1, 3))
        bars = self.exchange.fetch_ohlcv(
            self.coin + "/" + self.base_currency, timeframe=self.timeframe, limit=50
        )
        data = pd.DataFrame(
            bars[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        return data

    # Trading Functions

    # Backtrading

    def backtrading(self, data):
        data = V2.apply_indicators(data)

        highest_price = 0

        for i in range(len(data)):
            if data.iloc[i, 4] > highest_price:
                highest_price = data.iloc[i, 4]
            if i > 1:
                buy_sell_decision = V2.live_trading_model(
                    data,
                    None,
                    highest_price,
                    1.5,
                    0,
                    i,
                    self.has_position,
                    self.position,
                )
                if buy_sell_decision == -1:
                    self.offline_sell(data.iloc[i, 4], data.iloc[i, 0])
                    data.iloc[i, -1] = -1
                    highest_price = 0
                if buy_sell_decision == 1:
                    self.offline_buy(data.iloc[i, 4], data.iloc[i, 0])
                    data.iloc[i, -1] = 1
                    highest_price = data.iloc[i, 4]
        # if self.has_position:
        #    self.offline_sell(data.iloc[i, 4], data.iloc[i, 0])
        #    data.iloc[i, -1] = -1
        data.to_csv("test.csv")
        return data

    def offline_buy(self, price, ts):
        costs = price * 10 - price * 10 * self.commission
        self.set_position(price, 10, costs, ts)

        self.logger.info(
            "Offline Trading:\t{}\tBuy Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}".format(
                ts,
                price,
                10,
                price * 10,
                price * 10 * self.commission,
            )
        )
        self.pnl = self.pnl - costs

    def offline_sell(self, price, ts):
        sell_com = price * self.position["size"] * self.commission
        sell_total = price * self.position["size"] - sell_com
        self.pnl = self.pnl + sell_total
        self.logger.info(
            "Offline Trading:\t{}\tSell Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}\tPnL:\t{:.5f}".format(
                ts, price, self.position["size"], sell_total, sell_com, self.pnl
            )
        )
        self.set_position(0, 0, 0, None)

    # Data Processing

    def data_processing(self):
        data = self.fetch_data()
        data = self.backtrading(data)
        print("PnL: ", self.pnl)
        V2.show_plot(data)
        print(data["close"].pct_change().mean() * 100)

    def run(self):
        self.data_processing()


if __name__ == "__main__":
    exchange = exchanges.cryptocom()
    exchange.set_sandbox_mode(False)
    m = ModelTester(coin="SOL", frequency=1800, timeframe="1h", exchange=exchange)
    m.data_processing()
