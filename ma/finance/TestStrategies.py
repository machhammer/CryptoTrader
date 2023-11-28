import datetime as dt
from dateutil.relativedelta import relativedelta
import data_provider.DataReader as data_provider
import backtrader as bt
import warnings

warnings.filterwarnings("ignore")

end_date = dt.datetime.now()
start_date = end_date - relativedelta(days=60)
data = data_provider.yFinanceReader().historic_price_data(
    "xrp-usd", start_date, end_date
)


class SimpleTesting(bt.Strategy):
    params = (
        ("smaperiod", 10),
        ("rsiperiod", 14),
        ("macdperiod1", 12),
        ("macdperiod2", 26),
        ("macdsignal", 9),
        ("macdepsilon", 8),
        ("rsi_sell_threshold", 73),
        ("rsi_buy_threshold", 30),
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

        if self.rsi < self.p.rsi_buy_threshold:
            self.rsi_buy_alert = True
            self.rsi_sell_alert = False

        if self.rsi > self.p.rsi_sell_threshold:
            self.rsi_sell_alert = True
            self.rsi_buy_alert = False

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
<<<<<<< HEAD
    test = False

    cerebro = bt.Cerebro(maxcpus=None, optreturn=False)
=======
    cerebro = bt.Cerebro(maxcpus=8, optreturn=False, exactbars=2)

    cerebro.optstrategy(
        SimpleTesting,
        smaperiod=range(10, 20),
        rsiperiod=range(10, 30),
        macdperiod1=range(5, 21),
        macdperiod2=range(15, 30),
        macdsignal=range(5, 15),
        macdepsilon=range(5, 9),
    )

>>>>>>> b54995c044c59ef75b7a6ea42aa65527cdd7df40
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.005)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe_ratio")
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    cerebro.addsizer(bt.sizers.PercentSizer, percents=80)

    if test:
        cerebro.optstrategy(
            SimpleTesting,
            smaperiod=[10],
            rsiperiod=[14],
            macdperiod1=[12],
            macdperiod2=[26],
            macdsignal=[9],
            macdepsilon=range(7, 10),
            rsi_sell_threshold=range(73, 80),
            rsi_buy_threshold=range(28, 35),
        )

        optimized_runs = cerebro.run()

        final_results_list = []

        for run in optimized_runs:
            for strategy in run:
                PnL = round(strategy.broker.get_value(), 2)
                sharpe = strategy.analyzers.sharpe_ratio.get_analysis()
                final_results_list.append(
                    [
                        strategy.params.smaperiod,
                        strategy.params.rsiperiod,
                        strategy.params.macdperiod1,
                        strategy.params.macdperiod2,
                        strategy.params.macdsignal,
                        strategy.params.macdepsilon,
                        strategy.params.rsi_buy_threshold,
                        strategy.params.rsi_sell_threshold,
                        sharpe,
                        PnL,
                    ]
                )

            sort_by_sharpe = sorted(
                final_results_list, key=lambda x: x[3], reverse=True
            )

        for line in sort_by_sharpe[:5]:
            print(line)

<<<<<<< HEAD
    else:
        cerebro.addstrategy(SimpleTesting)
        cerebro.run()
        cerebro.plot()
=======
    for line in sort_by_sharpe[:10]:
        print(line)
>>>>>>> b54995c044c59ef75b7a6ea42aa65527cdd7df40
