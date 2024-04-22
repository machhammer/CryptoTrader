import ccxt
import credentials
from datetime import datetime
import traceback

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
        api_key = credentials.provider_2.get("key")
        api_secret = credentials.provider_2.get("secret")

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
            result = self.exchange.fetch_balance()
        except Exception as e:
            self.log_error(e)
            self.connect()
            result = self.exchange.fetch_balance()
            self.log_error("fetch_balance")
        return result

    def fetch_tickers(self):
        result = None
        try:
            result = self.exchange.fetch_tickers()
        except Exception as e:
            print(traceback.format_exc())
            self.log_error(e)
            self.connect()
            result = self.exchange.fetch_tickers()
            self.log_error("fetch_tickers")
        return result
    

    def fetch_ticker(self, asset):
        result = None
        try:
            result = self.exchange.fetch_ticker(asset)
        except Exception as e:
            self.log_error(e)
            self.connect()
            result = self.exchange.fetch_ticker(asset)
            self.log_error("fetch_ticker")
        return result
    
    def fetch_ohlcv(self, asset, timeframe, limit):
        result = None
        try:
            result = self.exchange.fetch_ohlcv(asset, timeframe, limit=limit)
        except Exception as e:
            self.log_error(e)
            self.connect()
            result = self.exchange.fetch_ohlcv(asset, timeframe, limit=limit)
            self.log_error("fetch_ohlcv")
        return result

    def fetch_my_trades(self, asset):
        result = None
        try:
            result = self.exchange.fetch_my_trades(asset)
        except Exception as e:
            self.log_error(e)
            self.connect()
            result = self.exchange.fetch_my_trades(asset)
            self.log_error("fetch_my_trades")
        return result

    def create_buy_order(self, asset, market, type, size, price):
        return self.exchange.create_order(
            asset,
            "market",
            "buy",
            size,
            price,
        )
    
    def create_sell_order(self, asset, size):
        return self.exchange.create_order(
            asset,
            "market",
            "sell",
            size,
        )

    