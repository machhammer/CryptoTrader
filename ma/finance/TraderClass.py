import pandas as pd
import time
import logging
import argparse
import random
from random import randint
import datetime
from models import V2
from threading import Thread
import datetime


class TraderClass(Thread):
    commission = 0.075 / 100
    base_currency = "USDT"

    def __init__(
        self,
        event,
        input,
        output,
        coin,
        frequency,
        timeframe,
        exchange,
        mood_threshold
    ):
        Thread.__init__(self)
        self.event = event
        self.input = input
        self.output = output
        self.coin = coin
        self.frequency = frequency
        self.timeframe = timeframe
        self.exchange = exchange
        self.mood_threshold = mood_threshold
        self.coin_distribution = {}
        self.previous_dataset = None
        self.has_position = False
        self.position = {}
        self.pnl = 0
        self.stop_running = False
        self.set_position(0, 0, 0, None)
        self.mood = 0
        self.pos_neg = 0
        self.highest_price = 0
        self.STOP_TRADING_FOR_TODAY = False

        self.logger = logging.getLogger(self.coin)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler = logging.FileHandler(
            filename="trading-" + coin + "-v4.log",
            mode="a",
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

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
            self.coin + "/" + self.base_currency, timeframe=self.timeframe, limit=35
        )
        data = pd.DataFrame(
            bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        
        return data

    def get_highest_price(self, data):

        timestamp = 0

        if self.has_position:
            timestamp = self.position["timestamp"]

        if len(data) > 0:
            data = pd.DataFrame(
                data[:],
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )

        if timestamp == 0:
            return data.iloc[-1, 4]
        else:
            timestamp = datetime.datetime.utcfromtimestamp(timestamp / 1e3)
            data = data[(data['timestamp'] >= timestamp)]
            return data["high"].max()

    def get_initial_position(self):
        time.sleep(random.randint(1, 3))
        try:
            current_balance = self.exchange.fetch_balance()[self.coin]["free"]
        except:
            current_balance = 0

        trades = self.exchange.fetch_my_trades(self.coin + "/" + self.base_currency)
        current_price = 0
        ts_position = None

        if len(trades) > 0:
            if trades[-1]["side"] == "buy":
                current_price = trades[-1]["price"]
                ts_position = trades[-1]["timestamp"]
        else:
            current_price = self.exchange.fetch_ticker(
                self.coin + "/" + self.base_currency
            )["last"]

        if current_balance * current_price > 5:
            self.set_position(
                current_price,
                current_balance,
                current_balance * current_price,
                ts_position,
            )
        else:
            self.set_position(0, 0, 0, None)

    def get_funding(self):
        time.sleep(random.randint(1, 3))
        total = 0
        coin_keys = self.coin_distribution.keys()
        for key in coin_keys:
            try:
                current_balance = self.exchange.fetch_balance()[key]["free"]
                self.logger.info("Coin: {}, Current Balance: {}".format(key, current_balance))
            except:
                current_balance = 0
            current_price = self.exchange.fetch_ticker(key + "/" + self.base_currency)[
                "last"
            ]
            self.logger.info("Coin: {}, Current Price: {}".format(key, current_price))
            if current_balance * current_price < 5:
                total = total + float(self.coin_distribution[key]) * 10
                self.logger.info("Total: {}".format(total))
            
        ratio = (self.coin_distribution[self.coin] * 10) / total
        self.logger.info("Ratio: {}".format(ratio))

        balance_base_currency = self.exchange.fetch_balance()[self.base_currency]["free"]
        self.logger.info("Balance USDT: {}".format(balance_base_currency))

        funding = (balance_base_currency * ratio) - 3
        self.logger.info("Funding: {}".format(funding))
        
        return funding

    def get_trade_price(self, order_id):
        time.sleep(random.randint(2, 4))
        trades = self.exchange.fetch_my_trades(
            symbol=self.coin + "/" + self.base_currency,
            since=None,
            limit=None,
            params={},
        )
        total_sum = 0
        amount_sum = 0
        ts = None
        found = False
        while not found:
            for trade in trades:
                if trade["order"] == order_id:
                    found = True
                    total_sum = total_sum + (trade["price"] * trade["amount"])
                    amount_sum = amount_sum + trade["amount"]
                    ts = trade["timestamp"]
        final_price = total_sum / amount_sum
        return [final_price, ts]

    # Live Trading

    def live_buy(self, price, ts):
        funding = self.get_funding()

        size = funding / price
        self.logger.info(
            "Prepare BUY: Funding {}, Price: {}, Size: {}, Coin: {}".format(
                funding, price, size, self.coin
            )
        )
        try:
            order = self.exchange.create_order(
                self.coin + "/" + self.base_currency,
                "market",
                "buy",
                size,
                price,
            )
            price = self.get_trade_price(order["id"])[0]
            self.set_position(price, size, price * size, int(ts.timestamp() * 1e3))
            self.logger.info(
                "Trading BUY: {}, order id: {}, price: {}".format(
                    ts, order["id"], price
                )
            )
            self.highest_price = self.position["price"]
        except Exception as e:
            self.logger.error(e)

    def live_sell(self, ts):
        size = self.exchange.fetch_balance()[self.coin]["free"]
        self.logger.info(
            "Prepare SELL: Size: {}, Coin: {}, Size: {}".format(
                self.position["size"], self.coin, size
            )
        )
        try:
            order = self.exchange.create_order(
                self.coin + "/" + self.base_currency,
                "market",
                "sell",
                size,
            )
            self.set_position(0, 0, 0, None)

            price = self.get_trade_price(order["id"])[0]
            self.pnl = self.pnl + price - self.position["price"]

            self.logger.info(
                "Trading SELL: {}, order id: {}, price: {}, PnL: {}".format(
                    ts, order["id"], price, self.pnl
                )
            )
            self.highest_price = 0
        except Exception as e:
            self.logger.error(e)

    # Data Processing

    def data_processing(self):
        self.logger.info("Data Processing start.")

        success = True

        try:
            self.logger.info("Waiting for Parameters.")
            value = self.input.get()
            self.logger.info("Parameters: {}".format(value))
            self.coin_distribution = value["coins"]
            self.mood = value["mood"]
            self.pos_neg = value["pos_neg"]
            self.STOP_TRADING_FOR_TODAY = value["STOP_TRADING_FOR_TODAY"]

            if not (self.STOP_TRADING_FOR_TODAY):

                data = self.fetch_data()
                self.highest_price = self.get_highest_price(data)

                new_data_available = True
                
                self.previous_dataset = data.copy(deep=True)

                if new_data_available:
                    data = V2.apply_indicators(data)
                    buy_sell_decision = V2.live_trading_model(
                        data,
                        self.logger,
                        self.highest_price,
                        self.mood,
                        self.mood_threshold,
                        self.pos_neg,
                        -1,
                        self.has_position,
                        self.position,
                    )
                    if buy_sell_decision == 1:
                        if not self.has_position:
                            self.live_buy(data.iloc[-1, 4], data.iloc[-1, 0])
                    if buy_sell_decision == -1:
                        if self.has_position:
                            self.live_sell(data.iloc[-1, 4])

            else:
                if self.has_position:
                    self.live_sell("automated")

            success = True

        except Exception as e:
            success = False
            self.logger.exception(e)

        self.logger.info("Putting Feedback: {}".format([success, self.has_position]))
        self.output.put([success, self.has_position])

        self.logger.info("Data Processing finished.")


    def run(self):
        self.logger.info(
            "Starting Trader for Coin: {}, Frequency: {}".format(
                self.coin, self.frequency
            )
        )

        self.get_initial_position()
        self.logger.info(
            "Has Position: {}, Initial Position: Size: {}, Price: {}, Total: {}, TS: {}".format(
                self.has_position,
                self.position["size"],
                self.position["price"],
                self.position["total"],
                self.position["timestamp"],
            )
        )

        while not self.event.is_set():
            self.data_processing()
            
            m1 = 30
            m2 = 60
            wait_time = datetime.datetime.now().minute
            if wait_time < m1:
                wait_time = (m1 - wait_time + 0.2) * 60
            else:
                if wait_time < m2:
                    wait_time = (m2 - wait_time + 0.2) * 60
                
            self.logger.info("Waiting Time in Seconds: {}".format(wait_time))

            time.sleep(wait_time)

        self.logger.info(
            "Stopping Trader for Coin: {}, Frequency: {}".format(
                self.coin, self.frequency
            )
        )

        self.logger = None

    # Helper Functions


if __name__ == "__main__":
    pass
