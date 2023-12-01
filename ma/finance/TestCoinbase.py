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
    exchange="coinbase", currency="XRP", config=config, retries=5, debug=False
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

    def next(self):
        self.log("SMA {} - Data {}".format(self.sma[0], self.data.close[0]))
        if self.live_data:
            print("********** Price: ", self.data.close[0])
            # self.order = self.sell(exectype=Order.Limit, price=0.8)
            self.log("BUY: {}".format(self.order))

    def notify_order(self, order):
        if order.status == order.Completed:  # Check if the order is executed
            if order.isbuy():  # Check if it was a buy order
                self.log(
                    "Executed BUY (Price: %.2f, Value: %.2f, Commission %.2f)"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                self.executed_buy_price = order.executed.price
                self.log(
                    "Sell if price lower than {:.2f}".format(
                        self.executed_buy_price * 0.9
                    )
                )
            else:  # Check if it was a sell order
                self.log(
                    "Executed SELL (Price: %.2f, Value: %.2f, Commission %.2f)"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
            self.bar_executed = len(
                self
            )  # This locks bar_executed to last trade number.

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
    coin = "XRP/USDC"

    historical_data = 200

    hist_to_date = datetime.utcnow()
    hist_start_date = hist_to_date - timedelta(minutes=historical_data)

    data = store.getdata(
        dataname=coin,
        name=coin,
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=1,
        ohlcv_limit=1000,
        drop_newest=True,
        historical=False,
    )

    cerebro = bt.Cerebro(maxcpus=None, optreturn=False, quicknotify=True, exactbars=-1)
    cerebro.setbroker(broker)
    print("Balance: {}".format(cerebro.broker.get_balance()))
    print("Value: {}".format(cerebro.broker.getvalue()))
    print("FundValue: {}".format(cerebro.broker.fundvalue))
    print("FundShares: {}".format(cerebro.broker.fundshares))
    print("Starting Vaoue: {}".format(cerebro.broker.startingvalue))
    print("Position: {}".format(len(cerebro.broker.positions)))
    print("Cash: {}".format(cerebro.broker.cash))

    print("Shares: ", dir(cerebro.broker))

    cerebro.adddata(data)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
    cerebro.addstrategy(SimpleTesting)
    cerebro.run()
