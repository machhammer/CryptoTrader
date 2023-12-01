from datetime import datetime, timedelta
import credentials
from dateutil.relativedelta import relativedelta
import data_provider.DataReader as data_provider
import backtrader as bt
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
    params = (
        ("smaperiod", 10),
        ("rsiperiod", 14),
        ("macdperiod1", 12),
        ("macdperiod2", 26),
        ("macdsignal", 9),
        ("macdepsilon", 8),
        ("rsi_sell_threshold", 73),
        ("rsi_buy_threshold", 33),
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
        self.adx = bt.indicators.AverageDirectionalMovementIndex(self.data)
        self.aroonUpDown = bt.indicators.AroonUpDown(self.data)
        self.bollinger = bt.indicators.BollingerBands(self.data)

        self.macd_diff = abs(abs(self.macd.signal) - abs(self.macd.macd))
        self.p.macdepsilon = self.p.macdepsilon / 1000
        self.macd_threshold = self.macd_diff > self.p.macdepsilon

        self.reset_flags()

    def reset_flags(self):
        self.sma_buy_alert = False
        self.sma_sell_alert = False

        self.rsi_buy_alert = False
        self.rsi_sell_alert = False

        self.macd_buy_alert = False
        self.macd_sell_alert = False

        self.adx_buy_alert = False
        self.adx_sell_alert = False

        self.aroon_buy_alert = False
        self.aroon_sell_alert = False

        self.bb_buy_alert = False
        self.bb_sell_alert = False

        self.buy_confirmation_1 = False
        self.buy_confirmation_2 = False

        self.sell_confirmation_1 = False
        self.sell_confirmation_2 = False
        self.sell_confirmation_3 = False

        self.executed_buy_price = -99

    def next(self):
        if hasattr(self, "live_data") and self.live_data:
            cash, value = self.broker.get_wallet_balance("XRP")
            usdc_cash, usdc_value = self.broker.get_wallet_balance("USDC")
            self.log(self.position)
            self.log(cash)
            self.log("USDC {}".format(usdc_value))

        else:
            cash = "NA"

        # SMA Flag
        if self.sma < self.data.close:
            self.sma_buy_alert = True
            self.sma_sell_alert = False
        else:
            self.sma_sell_alert = True
            self.sma_buy_alert = False

        # RSI Flag
        if self.rsi < self.p.rsi_buy_threshold:
            self.rsi_buy_alert = True
            self.rsi_sell_alert = False

        if self.rsi > self.p.rsi_sell_threshold:
            self.rsi_sell_alert = True
            self.rsi_buy_alert = False

        # MACD Flag
        if self.macd.macd > self.macd.signal:
            self.macd_buy_alert = True
            self.macd_sell_alert = False
        else:
            self.macd_buy_alert = False
            self.macd_sell_alert = True

        # ADX Flag
        if self.adx.DIplus > self.adx.DIminus:
            self.adx_buy_alert = True
            self.adx_sell_alert = False
        else:
            self.adx_buy_alert = False
            self.adx_sell_alert = True

        # Aroon Flag
        if self.aroonUpDown.up > self.aroonUpDown.down:
            self.aroon_buy_alert = True
            self.aroon_sell_alert = False
        else:
            self.aroon_buy_alert = False
            self.aroon_sell_alert = True

        # BB Flag
        top_bot_diff = self.bollinger.lines.top - self.bollinger.lines.bot
        price_bot_diff = self.data.close - self.bollinger.lines.bot

        ratio = price_bot_diff / top_bot_diff

        if ratio > 0.9:
            self.bb_sell_alert = True
            self.bb_buy_alert = False
        if ratio < 0.1:
            self.bb_sell_alert = False
            self.bb_buy_alert = True
        if ratio >= 0.1 and ratio <= 0.9:
            self.bb_sell_alert = True
            self.bb_buy_alert = True

        # print Log information

        for data in self.datas:
            self.log(
                "{} - {} | Cash {} | C: {:.4f} | SMA: {:.5f} | RSI: {:.0f} | MACD: {:.5f} | MACD S: {:.5f} | MACD D: {:.7f} | DI: {:.0f} | ADX: {:.0f} | Ad: {:.0f} | Au: {:.0f} | Bt: {:.4f} | Bb: {:.4f}".format(
                    data.datetime.datetime().strftime("%H:%M"),
                    data._name,
                    cash,
                    data.close[0],
                    self.sma[0],
                    self.rsi[0],
                    self.macd.macd[0],
                    self.macd.signal[0],
                    self.macd_diff[0],
                    self.adx.DIplus[0] - self.adx.DIminus[0],
                    self.adx[0],
                    self.aroonUpDown.down[0],
                    self.aroonUpDown.up[0],
                    self.bollinger.lines.top[0],
                    self.bollinger.lines.bot[0],
                )
            )
            self.log(
                "SMA B: {} | SMA S: {} | RSI B: {} | RSI S: {} | MACD B: {} | MACD S: {} | ADX B: {} | ADX S: {} | AROON B: {} | AROON S: {} | BB B: {} | BB S: {}".format(
                    self.sma_buy_alert,
                    self.sma_sell_alert,
                    self.rsi_buy_alert,
                    self.rsi_sell_alert,
                    self.macd_buy_alert,
                    self.macd_sell_alert,
                    self.adx_buy_alert,
                    self.adx_sell_alert,
                    self.aroon_buy_alert,
                    self.aroon_sell_alert,
                    self.bb_buy_alert,
                    self.bb_sell_alert,
                )
            )

        # Check for BUY condition

        if (
            not self.position
            and [
                self.sma_buy_alert,
                self.rsi_buy_alert,
                self.macd_buy_alert,
                self.adx_buy_alert,
                self.aroon_buy_alert,
                self.bb_buy_alert,
            ].count(True)
            > 4
        ):
            if self.buy_confirmation_2:
                # self.buy()
                self.reset_flags()
            else:
                if self.buy_confirmation_1:
                    self.buy_confirmation_2 = True
                else:
                    self.buy_confirmation_1 = True

        # Check for SELL condition

        if (
            data.close[0] <= self.executed_buy_price * 0.9
            or data.close[0] > self.executed_buy_price
        ):
            if (
                self.position
                and [
                    self.sma_sell_alert,
                    self.rsi_sell_alert,
                    self.macd_sell_alert,
                    self.adx_sell_alert,
                    self.aroon_sell_alert,
                    self.bb_sell_alert,
                ].count(True)
                > 4
            ):
                if self.sell_confirmation_3:
                    # self.sell()
                    self.reset_flags()
                else:
                    if self.sell_confirmation_2:
                        self.sell_confirmation_3 = True
                    else:
                        if self.sell_confirmation_1:
                            self.sell_confirmation_2 = True
                        else:
                            self.sell_confirmation_1 = True

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

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))


if __name__ == "__main__":
    Opt = False
    Live = True

    coin = "XRP/USDC"

    historical_data = 74

    if Live:
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
        historical=not Live,
    )

    cerebro = bt.Cerebro(maxcpus=None, optreturn=False, quicknotify=True, exactbars=-1)
    if Live:
        cerebro.setbroker(broker)
    else:
        cerebro.broker.setcash(50.0)
        cerebro.broker.setcommission(commission=0.005)

    cerebro.adddata(data)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)

    if Opt:
        cerebro.optstrategy(
            SimpleTesting,
            smaperiod=[10],
            rsiperiod=[14],
            macdperiod1=[12],
            macdperiod2=[26],
            macdsignal=[9],
            macdepsilon=range(5, 10),
            rsi_sell_threshold=range(65, 80),
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


    else:
        cerebro.addstrategy(SimpleTesting)
        cerebro.run()
        # cerebro.plot()
