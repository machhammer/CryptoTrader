import ccxt
import credentials
from datetime import datetime
import time
import traceback
import asyncio

class Exchange():

    exchange = None
    name = None


    def __init__(self, name):
        self.name = name
        self.connect()

    def log_error(self, proc):
        d = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        print("Reconnecting from {} at {}".format(proc, d))

    def connect(self):
        print("Connecting to {}.".format(self.name))
        if self.name == "cryptocom":
            self.exchange = self.cryptocom()
        elif self.name == "coinbase":
            self.exchange = self.coinbase()
        else: raise Exception("Exchange {} not implemented!".format(self.name))

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
    
    def fetch_ohlcv(self, asset, timeframe, limit):
        result = None
        try:
            if self.exchange is not None:
                result = self.exchange.fetch_ohlcv(asset, timeframe, limit=limit)
            else:
                raise Exception("Exchange is None.")
        except Exception as e:
            self.log_error(e)
            time.sleep(10)
            self.connect()
            if self.exchange is not None:
                result = self.exchange.fetch_ohlcv(asset, timeframe, limit=limit)
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


    def cancel_orders(self, asset):
        if self.exchange is not None:
            self.exchange.cancel_all_orders(symbol=asset)
        else:
            raise Exception("Exchange is None.")
        

    def create_stop_loss_order(self, asset, size, stopLossPrice):
        if self.exchange is not None:
            self.exchange.create_order(asset, 'market', 'sell', size, None, {'stopLossPrice': stopLossPrice})
        else:
            raise Exception("Exchange is None.")


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

    def fetch_orders(self, asset):
        if self.exchange is not None:
            return self.exchange.fetch_orders(asset)
        else:
            raise Exception("Exchange is None.")
