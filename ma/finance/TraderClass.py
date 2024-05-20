import pandas as pd
import time
import logging
import argparse
import random
from random import randint
import persistance as database
import datetime
from datetime import datetime, timedelta
from threading import Thread
import ParameterOptimizer as optimizer

class TraderClass(Thread):
    commission = 0.075 / 100
    base_currency = "USDT"

    def __init__(
        self,
        event,
        input,
        output,
        coin,
        exchange,
        model,
        scenario
    ):
        Thread.__init__(self)
        self.event = event
        self.input = input
        self.output = output
        self.coin = coin
        self.frequency = scenario.params["frequency"]
        self.timeframe = scenario.params["timeframe"]
        self.exchange = exchange
        self.model = model
        self.scenario = scenario
        self.coin_distribution = {}
        self.has_position = False
        self.position = {}
        self.pnl = 0
        self.stop_running = False
        self.set_position(0, 0, 0, None)
        self.mood = 0
        self.pos_neg = 0
        self.pos_neg_median = 0
        self.highest_price = 0
        self.STOP_TRADING_FOR_TODAY = False
        self.tradeable_today = True
        self.not_tradeable_until_hour = 99

        self.logger = logging.getLogger(self.coin)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler = logging.FileHandler(
            filename="trading-" + coin + ".log",
            mode="a",
            encoding="utf-8",
        )
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
            self.coin + "/" + self.base_currency, timeframe=self.timeframe, limit=38
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
            if timestamp is None:
                return data["high"].max()
            else:
                timestamp = datetime.utcfromtimestamp(timestamp / 1e3)
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
            except:
                current_balance = 0
            current_price = self.exchange.fetch_ticker(key + "/" + self.base_currency)[
                "last"
            ]
            self.logger.info("Coin: {}, Current Price: {:.4f}".format(key, current_price))
            if current_balance * current_price < 5:
                total = total + float(self.coin_distribution[key]) * 10
                self.logger.info("Total: {}".format(total))
        ratio = (self.coin_distribution[self.coin] * 10) / total
        balance_base_currency = self.exchange.fetch_balance()[self.base_currency]["free"]
        funding = (balance_base_currency * ratio) - 1
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
            if not found:
                total_sum = 1
                amount_sum=1
                found = True
        final_price = total_sum / amount_sum
        return [final_price, ts]

    # Live Trading

    def live_buy(self, price, ts):
        funding = self.get_funding()
        size = funding / price
        self.logger.info(
            "Prepare BUY: Funding {:.4f}, Price: {:.4f}, Size: {:.4f}, Coin: {}".format(
                funding, price, size, self.coin
            )
        )
        try:
            self.exchange.create_buy_order(
                self.coin + "/" + self.base_currency,
                size,
                price,
            )
            self.set_position(price, size, price * size, int(ts.timestamp() * 1e3))
            database.insert_transaction(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.coin, "buy", size, price)
            self.highest_price = self.position["price"]
        except Exception as e:
            self.logger.error(e)

    def live_sell(self, price):
        size = self.exchange.fetch_balance()[self.coin]["free"]
        self.logger.info(
            "Prepare SELL: Size: {:.4f}, Coin: {}, Size: {:.4f}".format(
                self.position["size"], self.coin, size
            )
        )
        try:
            self.exchange.create_sell_order(
                self.coin + "/" + self.base_currency,
                size
            )
            self.set_position(0, 0, 0, None)
            database.insert_transaction(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.coin, "sell", self.position["size"], price)
            self.highest_price = 0
        except Exception as e:
            self.logger.error(e)

    # Data Processing

    def data_processing(self):
        self.logger.info("Data Processing start.")

        success = True

        try:
            value = self.input.get()
            self.coin_distribution = value["coins"]
            self.mood = value["mood"]
            self.pos_neg = value["pos_neg"]
            self.pos_neg_median = value["pos_neg_median"]
            self.STOP_TRADING_FOR_TODAY = value["STOP_TRADING_FOR_TODAY"]

            self.logger.info("STOP_TRADING_FOR_TODAY: {} --- tradeable_today: {}".format(self.STOP_TRADING_FOR_TODAY, self.tradeable_today))

            if (datetime.now().minute >= 0 and datetime.now().minute < 30 and datetime.now().hour == 1):
                self.logger.info("New day. Set tradeable_today Flag.")
                self.tradeable_today = True

            if not self.tradeable_today:
                if self.not_tradeable_until_hour == datetime.now().hour:
                    self.logger.info("6 hours passed. Set tradeable_today Flag.")
                    self.tradeable_today = True

            if (not (self.STOP_TRADING_FOR_TODAY)) and self.tradeable_today:

                if self.model.params["pnl"] < 99:

                    data = self.fetch_data()
                    self.highest_price = self.get_highest_price(data)

                    data = self.model.apply_indicators(data)
                    #data.to_csv("data_" + self.coin + ".csv")
                    buy_sell_decision = self.model.live_trading_model(
                        data,
                        self.logger,
                        self.highest_price,
                        self.mood,
                        self.pos_neg,
                        self.pos_neg_median,
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

                    database.insert_trader(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), data.iloc[-1, 0], self.coin, self.model.params["sma"], self.model.params["aroon"], self.model.params["profit_threshold"], self.model.params["sell_threshold"], self.model.params["pos_neg_threshold"], self.model.params["pnl"], data.iloc[-1, 4])

                else:
                     self.logger.info("Expected PnL below threshold!")
            else:
                if self.has_position:
                    self.live_sell("automated")

            success = True

        except Exception as e:
            success = False
            self.logger.exception(e)

        return [success, self.has_position]



    def run(self):
        self.logger.info(
            "Starting Trader for Coin: {}, Frequency: {}".format(
                self.coin, self.frequency
            )
        )
        
        self.get_initial_position()
        self.logger.info(
            "Has Position: {}, Initial Position: Size: {:.4f}, Price: {:.4f}, Total: {:.4f}, TS: {}".format(
                self.has_position,
                self.position["size"],
                self.position["price"],
                self.position["total"],
                self.position["timestamp"],
            )
        )

        firstRun = True

        while not self.event.is_set():

            #if firstRun or (datetime.now().hour == 15 and datetime.now().minute < 5) or (datetime.now().hour == 1 and datetime.now().minute < 5):
            if firstRun:
                firstRun = False
                """ opt = optimizer.optimize_parameters(self.coin + "-USD", self.model, days=6)

                params = {
                    "sma": opt[0],
                    "aroon": opt[1],
                    "profit_threshold": opt[2],
                    "sell_threshold": opt[3],
                    "urgency_sell": 0,
                    "pos_neg_threshold": opt[4],
                    "pnl": opt[5]
                }

                self.model.params = params """

            self.data_processing()
            
            wait_time = self.scenario.get_wait_time()
                
            self.logger.info("Waiting Time in Seconds: {}".format(wait_time))
            self.logger.info("")

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
