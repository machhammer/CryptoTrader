import credentials
import backtrader as bt
import backtrader.feeds as btfeeds
from ccxtbt import CCXTStore
import ccxt
import time
import pandas as pd
from datetime import datetime, timedelta

from ccxtbt import CCXTFeed

api_key = credentials.provider_1.get("key")
api_secret = credentials.provider_1.get("secret")


class TestStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SMA(self.data, period=21)

    def next(self):
        # Get cash and balance
        # New broker method that will let you get the cash and balance for
        # any wallet. It also means we can disable the getcash() and getvalue()
        # rest calls before and after next which slows things down.

        # NOTE: If you try to get the wallet balance from a wallet you have
        # never funded, a KeyError will be raised! Change LTC below as approriate
        if hasattr(self, "live_Data") and self.live_data:
            cash, value = self.broker.get_wallet_balance("XRP")
        else:
            # Avoid checking the balance during a backfill. Otherwise, it will
            # Slow things down.
            cash = "NA"

        for data in self.datas:
            print(
                "{} - {} | Cash {} | O: {} H: {} L: {} C: {} V:{} SMA:{}".format(
                    data.datetime.datetime(),
                    data._name,
                    cash,
                    data.open[0],
                    data.high[0],
                    data.low[0],
                    data.close[0],
                    data.volume[0],
                    self.sma[0],
                )
            )

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        print(status)
        msg = "Data Status: {}".format(data._getstatusname(status))
        print(dt, dn, msg)
        if data._getstatusname(status) == "LIVE":
            self.live_data = True
        else:
            self.live_data = False


cerebro = bt.Cerebro(quicknotify=True)


# Add the strategy
cerebro.addstrategy(TestStrategy)

# Create our store
config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.coinbase(
    {
        "apiKey": api_key,
        "secret": api_secret,
        # 'verbose': True,  # for debug output
    }
)

ohlcv = exchange.fetch_ohlcv("BTC/USDT", "6h")
df = pd.DataFrame(ohlcv, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
df["Time"] = [datetime.fromtimestamp(float(time) / 1000) for time in df["Time"]]
df.set_index("Time", inplace=True)

# IMPORTANT NOTE - Kraken (and some other exchanges) will not return any values
# for get cash or value if You have never held any LTC coins in your account.
# So switch LTC to a coin you have funded previously if you get errors
store = CCXTStore(
    exchange="coinbase", currency="XRP", config=config, retries=5, debug=False
)


# Get the broker and pass any kwargs if needed.
# ----------------------------------------------
# Broker mappings have been added since some exchanges expect different values
# to the defaults. Case in point, Kraken vs Bitmex. NOTE: Broker mappings are not
# required if the broker uses the same values as the defaults in CCXTBroker.
broker_mapping = {
    "order_types": {
        bt.Order.Market: "market",
        bt.Order.Limit: "limit",
        bt.Order.Stop: "stop-loss",  # stop-loss for kraken, stop for bitmex
        bt.Order.StopLimit: "stop limit",
    },
    "mappings": {
        "closed_order": {"key": "status", "value": "closed"},
        "canceled_order": {"key": "result", "value": 1},
    },
}

broker = store.getbroker(broker_mapping=broker_mapping)
cerebro.setbroker(broker)

# Get our data
# Drop newest will prevent us from loading partial data from incomplete candles
hist_start_date = datetime.utcnow() - timedelta(days=90)
data = store.getdata(
    dataname="XRP/USD",
    name="XRPUSD",
    timeframe=bt.TimeFrame.Days,
    fromdate=hist_start_date,
    compression=1,
    ohlcv_limit=90,
    drop_newest=True,
    historical=True,
)


# Add the feed
cerebro.adddata(data)

# Run the strategy
cerebro.run()
cerebro.plot()
