import ccxt
from matplotlib.offsetbox import OffsetBox
import credentials
from datetime import datetime
import time
import traceback
import asyncio
from pybitget import Client
import pprint
import pandas as pd

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
        elif self.name == "bitget":
            self.exchange = self.bitget()
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

    def bitget(self):
        api_key = credentials.provider_3.get("key")
        api_secret = credentials.provider_3.get("secret")
        password = credentials.provider_3.get("password")
        passphrase = credentials.provider_3.get("passphrase")

        return ccxt.bitget(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "password": passphrase

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
                result = self.exchange.fetch_ohlcv(asset, timeframe, since=since, limit=limit)
            else:
                raise Exception("Exchange is None.")
        except Exception as e:
            self.log_error(e)
            time.sleep(10)
            self.connect()
            if self.exchange is not None:
                result = self.exchange.fetch_ohlcv(asset, timeframe, since=since, limit=limit)
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
        if self.name == 'bitget':
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
        order = client.spot_place_plan_order(asset, side="sell", triggerPrice=triggerPrice, size=quantity, triggerType="market_price", orderType="market", timeInForceValue="normal")
        return order

    def create_stop_loss_order(self, asset, size, stopLossPrice):
        if self.name == 'bitget':
            order = self.bitget_native_create_plan_order(asset, size, stopLossPrice)
        else:
            if self.exchange is not None:
                order = self.exchange.create_order(asset, 'market', 'sell', size, None, {'stopLossPrice': stopLossPrice})
            else:
                raise Exception("Exchange is None.")
        return order


    def create_take_profit_order(self, asset, size, takeProfitPrice):
        if self.name == 'bitget':
            order = self.bitget_native_create_plan_order(asset, size, takeProfitPrice)
        else:
            if self.exchange is not None:
                order = self.exchange.create_order(asset, 'limit', 'sell', size, takeProfitPrice)
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
            result = self.exchange.fetch_ohlcv(asset, timeframe, since=since, limit=limit)
        else:
            raise Exception("Exchange is None.")
        return result


class Offline_Exchange(Exchange):

    order = {'type': None, 'asset': None, 'size': None, 'price':None, 'timestamp': None}
    
    buy_order = []
    sell_oders = []

    balance = {
        'total': { 
            'USDT': 100.0
        },
        'USDT': { 
            'total': 100.0
        },
    }

    def __init__(self, exchange_name):
        super().__init__(exchange_name)
        
        
    def fetch_balance(self):
        return self.balance
    

    def create_buy_order(self, asset, size, price):
        self.order = {'type': 'buy', 'asset': asset, 'size':size, 'price':price, 'timestamp': None}
        self.balance['total'][asset] = size * price


    def create_take_profit_order(self, asset, size, takeProfitPrice):
        self.sell_oders.append({'type': 'buy', 'asset': asset, 'size':size, 'price':takeProfitPrice, 'timestamp': None})

    def create_stop_loss_order(self, asset, size, stopLossPrice):
        self.sell_oders.append({'type': 'buy', 'asset': asset, 'size':size, 'price':stopLossPrice, 'timestamp': None})

    def convert(self, bars):
        data = pd.DataFrame(
            bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        return data

if __name__ == "__main__":
    dynamic_class = globals()['Offline_Exchange']
    exchange = dynamic_class("bitget")
    result = exchange.fetch_ohlcv("NEAR/USDT", "1m", since=1654356700000, limit=200)
    print(exchange.convert(result))
    print(len(result))