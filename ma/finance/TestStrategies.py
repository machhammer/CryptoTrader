import datetime as dt
import time
from dateutil.relativedelta import relativedelta
import data_provider.DataReader as data_provider
from trading.MACDStrategy import MACD1226
import config as cfg
import yahoo_fin.stock_info as yf
import pandas as pd
import backtrader as bt
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

end_date = dt.datetime.now()
start_date = end_date - relativedelta(days=60)
data = data_provider.yFinanceReader().historic_price_data(
    "xrp-usd", start_date, end_date
)


class SimpleTesting(bt.Strategy):
    params = (
        ("rsiperiod", 14),
        ("smaperiod", 21),
        ("macdperiod1", 12),
        ("macdperiod2", 26),
        ("macdsignal", 9),
        ("macdepsilon", 9),
    )

    def __init__(self):
        self.sma = bt.indicators.SMA(self.data, period=self.p.smaperiod)
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.p.rsiperiod)
        self.macd = bt.indicators.MACD(
            self.data,
            period_me1=self.p.macdperiod1,
            period_me2=self.p.macdperiod2,
            period_signal=self.p.macdsignal,
        )

        self.rsi_buy_alert = False
        self.rsi_sell_alert = False

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

        """ for data in self.datas:
            print(
                "{} - {} | Cash {} | C: {} Diff:{}".format(
                    data.datetime.datetime(),
                    data._name,
                    cash,
                    data.close[0],
                    round(abs(self.macd.signal) - abs(self.macd.macd), 5),
                )
            ) """

        if self.rsi < 30:
            self.rsi_buy_alert = True

        if self.rsi > 80:
            self.rsi_sell_alert = True

        if (
            not self.position
            and (self.rsi_buy_alert)
            and (self.data.close[0] > self.sma)
            and (self.macd.signal < self.macd.macd)
            and (
                round(abs(self.macd.signal) - abs(self.macd.macd), 5)
                > (self.p.macdepsilon / 100000)
            )
        ):
            self.buy()
            self.rsi_buy_alert = False

        if (
            self.position
            and (self.rsi_sell_alert)
            and (self.data.close[0] < self.sma)
            and (self.macd.signal < self.macd.macd)
            and (
                round(abs(self.macd.signal) - abs(self.macd.macd), 5)
                > (self.p.macdepsilon / 100000)
            )
        ):
            self.sell()
            self.rsi_sell_alert = False

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


if __name__ == "__main__":
    cerebro = bt.Cerebro(maxcpus=None)

    cerebro.optstrategy(
        SimpleTesting,
        smaperiod=range(14, 15),
        rsiperiod=range(21, 22),
        macdperiod1=range(12, 13),
        macdperiod2=range(26, 27),
        macdsignal=range(9, 10),
        macdepsilon=range(9, 10),
    )

    cerebro.broker.setcash(100000.0)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    cerebro.addsizer(bt.sizers.FixedSize, stake=20)
    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())

    optimized_runs = cerebro.run()

    final_results_list = []

    for run in optimized_runs:

        for strategy in run:
            PnL = round(strategy.broker.get_value() - 10000,2)
            print(strategy)
            sharpe = strategy.analyzers.sharpe_ratio.get_analysis()
            final_results_list.append([strategy.params.smaperiod, strategy.params.rsiperiod, strategy.params.macdperiod1, strategy.params.macdperiod2, strategy.params.macdsignal, strategy.params.macdepsilon, sharpe])
    
        sort_by_sharpe = sorted(final_results_list, key=lambda x: x[3], reverse=True)


    for line in sort_by_sharpe[:5]:
        print(line)
