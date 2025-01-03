import ccxt
from matplotlib.offsetbox import OffsetBox
import credentials
from datetime import datetime, timedelta
import time
import logging
import traceback
import asyncio
from pybitget import Client
import pprint
import pandas as pd

logger = logging.getLogger("screener")

class Exchange:

    exchange = None
    name = None

    def __init__(self, name, *args):
        self.name = name
        self.connect()
        self.observation_start = None
        self.observation_stop = None

    def log_error(self, proc):
        d = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        print("Reconnecting from {} at {}".format(proc, d))
        logger.error("Reconnecting from {} at {}".format(proc, d))

    def get_mode(self):
        return credentials.MODE_PROD

    def get_name(self):
        return self.name

    def set_observation_start(self, observation_start):
        logger.debug("Observation Start: {}".format(observation_start))
        self.observation_start = observation_start

    def set_observation_stop(self, observation_stop):
        logger.debug("Observation Stop: {}".format(observation_stop))
        self.observation_stop = observation_stop
   

    def get_observation_start(self):
        return self.observation_start

    def get_observation_stop(self):
        return self.observation_stop

    def observation_run_check(self):
        if not self.observation_start is None and not self.observation_stop is None:
            return self.exchange.get_observation_stop() >= self.exchange.get_observation_start()
        else:
            return True


    def get_timestamp(self):
        return datetime.now() if self.observation_start is None else self.observation_start

    def connect(self):
        logger.info("Connecting to {}.".format(self.name))

        if self.name == "cryptocom":
            self.exchange = self.cryptocom()
        elif self.name == "coinbase":
            self.exchange = self.coinbase()
        elif self.name == "bitget":
            self.exchange = self.bitget()
        else:
            raise Exception("Exchange {} not implemented!".format(self.name))

    def cryptocom(self):
        api_key = credentials.provider_2.get("key")
        api_secret = credentials.provider_2.get("secret")

        return ccxt.cryptocom(
            {
                "apiKey": api_key,
                "secret": api_secret,
                #'verbose': True
            }
        )

    def bitget(self):
        api_key = credentials.provider_3.get("key")
        api_secret = credentials.provider_3.get("secret")
        password = credentials.provider_3.get("password")
        passphrase = credentials.provider_3.get("passphrase")

        return ccxt.bitget(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "password": passphrase,
                #'verbose': True
            }
        )

    def bitget_native(self):
        api_key = credentials.provider_3.get("key")
        api_secret = credentials.provider_3.get("secret")
        password = credentials.provider_3.get("password")
        passphrase = credentials.provider_3.get("passphrase")
        client = Client(api_key, api_secret, passphrase=passphrase)
        return client

    def coinbase(self):
        api_key = credentials.provider_1.get("key")
        api_secret = credentials.provider_1.get("secret")

        return ccxt.coinbase(
            {
                "apiKey": api_key,
                "secret": api_secret,
                #'verbose': True
            }
        )

    def fetch_balance(self):
        result = None
        try:
            if self.exchange is not None:
                result = self.exchange.fetch_balance()
            else:
                raise Exception("Exchange is None.")
        except Exception as e:
            self.log_error(e)
            time.sleep(10)
            self.connect()
            if self.exchange is not None:
                result = self.exchange.fetch_balance()
            else:
                raise Exception("Exchange is None.")
            self.log_error("fetch_balance")
        return result

    def fetch_tickers(self):
        result = None
        try:
            if self.exchange is not None:
                result = self.exchange.fetch_tickers()
            else:
                raise Exception("Exchange is None.")
        except Exception as e:
            print(traceback.format_exc())
            self.log_error(e)
            time.sleep(10)
            self.connect()
            if self.exchange is not None:
                result = self.exchange.fetch_tickers()
            else:
                raise Exception("Exchange is None.")
            self.log_error("fetch_tickers")
        return result

    def fetch_ticker(self, asset):
        result = None
        try:
            if self.exchange is not None:
                result = self.exchange.fetch_ticker(asset)
            else:
                raise Exception("Exchange is None.")
        except Exception as e:
            self.log_error(e)
            time.sleep(10)
            self.connect()
            if self.exchange is not None:
                result = self.exchange.fetch_ticker(asset)
            else:
                raise Exception("Exchange is None.")
            self.log_error("fetch_ticker")
        return result

    def fetch_ohlcv(self, asset, timeframe, limit, since=None):
        result = None
        try:
            if self.exchange is not None:
                result = self.exchange.fetch_ohlcv(
                    asset, timeframe, since=since, limit=limit
                )
            else:
                raise Exception("Exchange is None.")
        except Exception as e:
            self.log_error(e)
            time.sleep(10)
            self.connect()
            if self.exchange is not None:
                result = self.exchange.fetch_ohlcv(
                    asset, timeframe, since=since, limit=limit
                )
            else:
                raise Exception("Exchange is None.")
            self.log_error("fetch_ohlcv")
        return result

    def fetch_my_trades(self, asset):
        result = None
        try:
            if self.exchange is not None:
                result = self.exchange.fetch_my_trades(symbol=asset)
            else:
                raise Exception("Exchange is None.")
        except Exception as e:
            self.log_error(e)
            time.sleep(10)
            self.connect()
            if self.exchange is not None:
                result = self.exchange.fetch_my_trades(symbol=asset)
            else:
                raise Exception("Exchange is None.")
            self.log_error("fetch_my_trades")
        return result

    def cancel_order(self, asset, orderId):
        if self.name == "bitget":
            client = self.bitget_native()
            asset = asset.split("/")
            asset = asset[0] + asset[1] + "_SPBL"

            client.spot_cance_order(asset, orderId)
        else:
            if self.exchange is not None:
                self.exchange.cancel_order(orderId)
            else:
                raise Exception("Exchange is None.")

    def cancel_orders(self, asset):
        if self.exchange is not None:
            self.exchange.cancel_all_orders(symbol=asset)
        else:
            raise Exception("Exchange is None.")

    def bitget_native_create_plan_order(self, asset, quantity, triggerPrice):
        client = self.bitget_native()
        asset = asset.split("/")
        asset = asset[0] + asset[1] + "_SPBL"
        order = client.spot_place_plan_order(
            asset,
            side="sell",
            triggerPrice=triggerPrice,
            size=quantity,
            triggerType="market_price",
            orderType="market",
            timeInForceValue="normal",
        )
        return order

    def create_stop_loss_order(self, asset, size, stopLossPrice):
        if self.name == "bitget":
            order = self.bitget_native_create_plan_order(asset, size, stopLossPrice)
        else:
            if self.exchange is not None:
                order = self.exchange.create_order(
                    asset,
                    "market",
                    "sell",
                    size,
                    None,
                    {"stopLossPrice": stopLossPrice},
                )
            else:
                raise Exception("Exchange is None.")
        return order

    def create_take_profit_order(self, asset, size, takeProfitPrice):
        if self.name == "bitget":
            order = self.bitget_native_create_plan_order(asset, size, takeProfitPrice)
        else:
            if self.exchange is not None:
                order = self.exchange.create_order(
                    asset, "limit", "sell", size, takeProfitPrice
                )
            else:
                raise Exception("Exchange is None.")
        return order

    def create_buy_order(self, asset, size, price):
        if self.exchange is not None:
            order = self.exchange.create_order(
                asset,
                "market",
                "buy",
                size,
                price,
            )
            return order
        else:
            raise Exception("Exchange is None.")

    def create_sell_order(self, asset, size):
        if self.exchange is not None:
            order = self.exchange.create_order(
                asset,
                "market",
                "sell",
                size,
            )
            return order
        else:
            raise Exception("Exchange is None.")

    def fetch_order(self, id, asset):
        if self.exchange is not None:
            return self.exchange.fetch_order(id, asset)
        else:
            raise Exception("Exchange is None.")

    def fetch_ohlcv_history(self, asset, timeframe, since, limit):
        if self.exchange is not None:
            result = self.exchange.fetch_ohlcv(
                asset, timeframe, since=since, limit=limit
            )
        else:
            raise Exception("Exchange is None.")
        return result


class Offline_Exchange(Exchange):

    order = {
        "type": None,
        "asset": None,
        "size": None,
        "price": None,
        "timestamp": None,
    }

    sell_orders = {"profit_sell": None, "loss_sell": []}


    def get_mode(self):
        return credentials.MODE_TEST

    def set_balance(self, starting_balance):
        self.balance = {
            "total": {"USDT": starting_balance},
            "USDT": {"total": starting_balance},
        }
        logger.debug("Balance: {}".format(self.balance))

    def __init__(self, exchange_name, starting_balance):
        super().__init__(exchange_name)
        self.starting_balance = starting_balance
        self.set_balance(self.starting_balance)

    def fetch_balance(self):
        return self.balance

    def create_buy_order(self, asset, size, price):
        base_currency = asset.split("/")[1]
        symbol = asset.split("/")[0]

        print("** Buy Asset: {},  Size: {}, Price: {})".format(symbol, size, price))

        if symbol in self.balance["total"]:
            self.balance["total"][symbol] = self.balance["total"][symbol] + size
            self.balance[symbol]["total"] = self.balance[symbol]["total"] + size
        else:
            self.balance["total"][symbol] = size
            self.balance[symbol] = {"total": size}

        self.balance["total"][base_currency] = self.balance["total"][base_currency] - (
            size * price
        )
        self.balance[base_currency]["total"] = self.balance[base_currency]["total"] - (
            size * price
        )

    def create_take_profit_order(self, asset, size, takeProfitPrice):
        self.sell_orders["profit_sell"] = {
            "asset": asset,
            "size": size,
            "price": takeProfitPrice,
            "timestamp": None,
        }

    def create_stop_loss_order(self, asset, size, stopLossPrice):
        self.sell_orders["loss_sell"].append(
            {"asset": asset, "size": size, "price": stopLossPrice, "timestamp": None}
        )

    def check_for_sell(self, asset, data):
        base_currency = asset.split("/")[1]
        symbol = asset.split("/")[0]
        if symbol in self.balance['total'].keys() and self.balance['total'][symbol]>0:
            if not data is None and len(data) > 0:
                ts = data[-1][0]
                date = datetime.fromtimestamp(ts/1000)
                if not self.sell_orders['profit_sell'] is None:
                    if data[-1][2] >= self.sell_orders["profit_sell"]["price"]:
                        print("** Profit sell - Date: {}, Asset: {}, Price: {}, Order: {}".format(date, asset, data[-1][2], self.sell_orders["profit_sell"]["price"]))
                        self.sell(date, symbol, base_currency, self.sell_orders["profit_sell"]["price"])

                for order in self.sell_orders["loss_sell"]:
                    if data[-1][2] < order["price"]:
                        print("** Loss sell - Date: {}, Asset: {}, Price: {}, Order: {}".format(date, asset, data[-1][2], self.sell_orders["loss_sell"]))
                        self.sell(date, symbol, base_currency, data[-1][2])
                        break

    def create_sell_order(self, asset, size):
        base_currency = asset.split("/")[1]
        symbol = asset.split("/")[0]
        data = self.fetch_ohlcv(asset, "1m", 1)
        price = data[-1][2]
        self.sell(self.observation_start, symbol, base_currency, price)

    def sell(self, date, symbol, base_currency, price):
        
        logger.info ("{} Sell Asset: {}".format(self.observation_start, symbol))
        logger.debug ("{} Current Balance: {} + (amount: {} * price: {})".format(self.observation_start, round(self.balance["total"][base_currency], 2), self.balance["total"][symbol], price))
        
        self.balance["total"][base_currency] = self.balance["total"][base_currency] + self.balance["total"][symbol] * price
        self.balance[base_currency]["total"] = self.balance[base_currency]["total"] + self.balance["total"][symbol] * price
        
        logger.info("{} New Balance: {}".format(self.observation_start, round(self.balance["total"][base_currency], 2)))
        
        self.balance["total"][symbol] = 0
        self.balance[symbol]["total"] = 0
        self.sell_orders = {"profit_sell": None, "loss_sell": []}

        df = pd.json_normalize(self.balance)
        df.to_csv('balance' + '-' + self.observation_start.strftime("%Y-%m-%d") + '.csv', index=False)


    def fetch_ohlcv(self, ticker, interval, limit):
        if self.observation_start is None:
            data = super().fetch_ohlcv(ticker, interval, limit)
        else:
            value = int(interval[0 : len(interval) - 1])
            if interval.endswith("m"):
                value = value * limit * 1
            if interval.endswith("h"):
                value = value * limit * 60
            if interval.endswith("d"):
                value = value * limit * 60 * 24
            since = self.observation_start - timedelta(minutes=value)
            since = int(time.mktime(since.timetuple())) * 1000
            data = super().fetch_ohlcv(ticker, interval, limit, since=since)
            self.check_for_sell(ticker, data)
        return data

    def convert(self, bars):
        data = pd.DataFrame(
            bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        return data


if __name__ == "__main__":

    observation_start = datetime.strptime("2024-11-10 12:00", "%Y-%m-%d %H:%M")

    dynamic_class = globals()["Offline_Exchange"]
    exchange = dynamic_class("bitget")
    exchange.set_observation_start(observation_start)

    result = exchange.fetch_ohlcv("NEAR/USDT", "15m", limit=5)
    print(exchange.convert(result))

    exchange.create_stop_loss_order("NEAR/USDT")

    observation_start = observation_start + timedelta(minutes=15)
    exchange.set_observation_start(observation_start)

    result = exchange.fetch_ohlcv("NEAR/USDT", "15m", limit=5)
    print(exchange.convert(result))
