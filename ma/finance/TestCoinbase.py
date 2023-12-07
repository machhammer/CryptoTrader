from datetime import datetime, timedelta
import credentials
from dateutil.relativedelta import relativedelta
import data_provider.DataReader as data_provider
import backtrader as bt
from backtrader import Order
from backtrader import Position

from ccxtbt import CCXTStore
import ccxt
import warnings

# warnings.filterwarnings("ignore")

coin = "XLM"

coins = {
    "XRP": "XRP/USDC",
    "SOL": "SOL/USDC",
    "ETH": "ETC/USDC",
    "BTC": "BTC/USDC",
    "XLM": "XLM/USDC",
    "VARA": "VARA/USDC",
    "SHIB": "SHIB/USDC",
}

api_key = credentials.provider_1.get("key")
api_secret = credentials.provider_1.get("secret")

config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.coinbase(
    {
        "apiKey": api_key,
        "secret": api_secret,
        # 'verbose': True,  # for debug output
    }
)

store = CCXTStore(
    exchange="coinbase", currency=coin, config=config, retries=1, debug=False
)

broker_mapping = {
    "order_types": {
        bt.Order.Market: "market",
        bt.Order.Limit: "limit",
        bt.Order.Stop: "stop-loss",
        bt.Order.StopLimit: "stop limit",
    },
    "mappings": {
        "closed_order": {"key": "status", "value": "closed"},
        "canceled_order": {"key": "result", "value": 1},
    },
}

broker = store.getbroker(broker_mapping=broker_mapping)


class SimpleTesting(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(period=15)
        self.mode = "Sell"

    def next(self):
        if self.live_data:
            print(self.mode)
            if self.mode == "Sell":
                try:
                    current_balance = self.broker.get_balance()[0]
                    print(current_balance)
                    size_position = current_balance

                    self.sell(
                        size=size_position,
                        exectype=Order.Market,
                        price=data.close[0],
                    )

                    self.log(
                        "*** Execute SELL - Size: {}, Price: {} ".format(
                            size_position, data.close[0]
                        )
                    )

                except Exception as e:
                    print(e)

            if self.mode == "Buy" and not self.position:
                try:
                    current_balance = exchange.fetch_balance()["USDC"]["free"] - 1
                    size_position = current_balance / data.close[0]
                    self.log(
                        "*** Size Position = {} / {} = {} ".format(
                            current_balance, data.close[0], size_position
                        )
                    )
                    self.log(
                        "*** Execute BUY - Size: {}, Price: {} ".format(
                            size_position, data.close[0]
                        )
                    )
                    self.buy(
                        size=size_position, exectype=Order.Market, price=data.close[0]
                    )

                except Exception as e:
                    print(e)

    def notify_order(self, order):
        if order.status == order.Completed:  # Check if the order is executed
            if order.isbuy():  # Check if it was a buy order
                self.log(
                    "Executed BUY (Price: %.2f, Value: %.2f, Commission %.2f)"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
            else:  # Check if it was a sell order
                self.log(
                    "Executed SELL (Price: %.2f, Value: %.2f, Commission %.2f)"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order was canceled/margin/rejected")
        self.order = None  # Once the order is executed, we don’t have any open order.

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(
            "OPERATION PROFIT, GROSS {0:8.2f}, NET {1:8.2f}".format(
                trade.pnl, trade.pnlcomm
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

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))


if __name__ == "__main__":
    historical_data = 0.2

    hist_to_date = datetime.utcnow()
    hist_start_date = hist_to_date - timedelta(minutes=historical_data * 1440)

    data = store.getdata(
        dataname=coins[coin],
        name=coins[coin],
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=1,
        ohlcv_limit=1000,
        drop_newest=True,
        historical=False,
    )

    cerebro = bt.Cerebro(maxcpus=None, optreturn=False, quicknotify=True, exactbars=-1)
    broker = store.getbroker(broker_mapping=broker_mapping)
    cerebro.setbroker(broker)

    cerebro.adddata(data)

    cerebro.addstrategy(SimpleTesting)
    cerebro.run()
    cerebro.plot()
