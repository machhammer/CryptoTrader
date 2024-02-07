from datetime import datetime, timedelta
import credentials
import backtrader as bt
from ccxtbt import CCXTStore
import argparse
import logging
import json
import ccxt
import os


Live = False

frequenz = "1 h"

coin = "XLM"

coins = {
    "XRP": {"product": "XRP/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "SOL": {"product": "SOL/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "XLM": {"product": "XLM/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "CRO": {"product": "CRO/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "NEAR": {"product": "NEAR/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
}

position_file = "positions.json"

api_key = credentials.provider_2.get("key")
api_secret = credentials.provider_2.get("secret")

config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.cryptocom(
    {
        "apiKey": api_key,
        "secret": api_secret,
        #'verbose': True
    }
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


def synchronize_coins_dict():
    print(os.getcwd())
    try:
        coins_from_file = coins_dict_from_file()
        for f_coin in coins_from_file.keys():
            if f_coin in coins:
                coins[f_coin]["last_executed_buy_price"] = coins_from_file[f_coin][
                    "last_executed_buy_price"
                ]
    except Exception as e:
        print(e)
    coins_dict_to_file()
    return coins


def coins_dict_to_file():
    with open(position_file, "w") as pf:
        json.dump(coins, pf, indent = 2)


def coins_dict_from_file():
    with open(position_file, "r") as pf:
        return json.load(pf)


def get_funding():
    total = 0
    coin_keys = coins.keys()
    for key in coin_keys:
        try:
            current_balance = exchange.fetch_balance()[key]["free"]
        except:
            current_balance = 0
        current_price = exchange.fetch_ticker(coins[key]["product"])["last"]
        if current_balance * current_price < 1:
            total = total + float(coins[key]["dist_ratio"]) * 10

    ratio = (coins[coin]["dist_ratio"] * 10) / total
    return (exchange.fetch_balance()["USDT"]["free"] * ratio) - 1


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Sample for pivot point and cross plotting",
    )
    parser.add_argument("--coin", required=True, help="Coin to trade")
    parser.add_argument("--live", required=True, help="Live (True/False)")
    return parser.parse_args()


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
        ("coin", [coin, coins[coin]]),
        ("sell_down_threshold", 2),
        ("sell_up_threshold", 2),
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

        self.initial_position = 0
        try:
            [self.initial_position, _] = self.broker.get_balance()
        except Exception as e:
            self.log(e)

        coins = synchronize_coins_dict()
        print(coins)
        self.executed_buy_price = coins[coin]["last_executed_buy_price"]

        self.size_position = 10

        self.reset_flags()

    def reset_flags(self):
        self.log("*** Reset Flags.")

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

        self.highest_price = -99
        self.lowest_price = 99999999

    def next(self):
        if self.initial_position > 0:
            if self.initial_position * self.data.close[0] < 1:
                self.initial_position = 0
                self.log("Initial Position set to 0 due to low value")

        if self.data.close[0] > self.highest_price:
            self.highest_price = self.data.close[0]
        if self.executed_buy_price > self.highest_price:
            self.highest_price = self.executed_buy_price
        if self.data.close[0] < self.lowest_price:
            self.lowest_price = self.data.close[0]

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

        BUY_ALERT = [
            self.sma_buy_alert,
            self.rsi_buy_alert,
            self.macd_buy_alert,
            self.adx_buy_alert,
            self.aroon_buy_alert,
            self.bb_buy_alert,
        ].count(True) >= 4

        SELL_ALERT = [
            self.sma_sell_alert,
            self.rsi_sell_alert,
            self.macd_sell_alert,
            self.adx_sell_alert,
            self.aroon_sell_alert,
            self.bb_sell_alert,
        ].count(True) >= 4

        # print Log information

        for data in self.datas:
            self.log(
                "{} | Coin: {} | Initial Position: {} | Executed Buy Price: {} | Price: {} | Next Sell > {} | Next Sell < {:.7f}".format(
                    data.datetime.datetime().strftime("%H:%M"),
                    coin,
                    self.initial_position,
                    self.executed_buy_price,
                    self.data.close[0],
                    self.executed_buy_price
                    + (self.p.sell_up_threshold / 100) * self.executed_buy_price,
                    self.highest_price * (1 - self.p.sell_down_threshold / 100),
                )
            )

            self.log(
                "{} - {} | High {} | Low {} | C: {:.4f} | SMA: {:.5f} | RSI: {:.0f} | MACD: {:.5f} | MACD S: {:.5f} | MACD D: {:.7f} | DI: {:.0f} | ADX: {:.0f} | Ad: {:.0f} | Au: {:.0f} | Bt: {:.4f} | Bb: {:.4f}".format(
                    data.datetime.datetime().strftime("%H:%M"),
                    data._name,
                    self.highest_price,
                    self.lowest_price,
                    self.data.close[0],
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
                "{} - {} | SMA B: {} | SMA S: {} | RSI B: {} | RSI S: {} | MACD B: {} | MACD S: {} | ADX B: {} | ADX S: {} | AROON B: {} | AROON S: {} | BB B: {} | BB S: {} | BUY Alert: {} | SELL Alert: {}".format(
                    data.datetime.datetime().strftime("%H:%M"),
                    data._name,
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
                    BUY_ALERT,
                    SELL_ALERT,
                )
            )

        # BUY/SELL -> only in test mode, or with live data

        if not Live or (Live and self.live_data):
            # Check for BUY condition
            if BUY_ALERT:
                self.log("*** BUY ALERT set")
                if self.initial_position == 0 and self.position.size == 0.0:
                    self.log(
                        "*** Initial Position: {} has Position: {} ".format(
                            self.initial_position, self.position.size
                        )
                    )
                    if self.buy_confirmation_2:
                        #try:
                            if Live:
                                current_balance = get_funding()
                                self.size_position = current_balance / data.close[0]
                                self.log(
                                    "*** Size Position = {} / {} = {} ".format(
                                        current_balance,
                                        data.close[0],
                                        self.size_position,
                                    )
                                )
                                self.log(
                                    "*** Execute BUY - Size: {}, Price: {} ".format(
                                        self.size_position, data.close[0]
                                    )
                                )
                                order = exchange.create_order(
                                    coins[coin]["product"],
                                    "market",
                                    "buy",
                                    self.size_position,
                                    data.close[0],
                                )
                                self.log(order)
                                self.executed_buy_price = data.close[0]
                                self.highest_price = self.executed_buy_price
                                self.initial_position = self.size_position
                                self.log(
                                    "*** Initial Position has been set to: {}".format(
                                        self.initial_position
                                    )
                                )
                            else:
                                self.log("*** BUY OFFLINE")
                                self.order = self.buy(size=10)
                                self.initial_position = 0

                            coins[coin]["last_executed_buy_price"] = data.close[0]
                            coins_dict_to_file()
                            self.reset_flags()
                        #except Exception as e:
                        #    self.log(e)

                    else:
                        if self.buy_confirmation_1:
                            self.log("*** Set BUY confirmation 2")
                            self.buy_confirmation_2 = True
                        else:
                            self.log("*** Set BUY confirmation 1")
                            self.buy_confirmation_1 = True
                else:
                    self.log("*** BUY Aborted: Position exists already!")
                    self.log(
                        "*** Initial Position: {} has Position: {} ".format(
                            self.initial_position, self.position.size
                        )
                    )
            else:
                self.reset_buy_confirmations()

            # Check for SELL condition

            # Urgency SELL
            if self.position.size > 0.0 or self.initial_position > 0:
                if self.data.close[0] <= self.data.close[-1] * (
                    1 - self.p.sell_down_threshold / 100
                ):
                    self.log("*** URGENCY SELL")
                    self.log(
                        "*** Current Price ({}) is {}% lower than previous Price ({})".format(
                            self.data.close[0],
                            self.p.sell_down_threshold,
                            self.data.close[-1],
                        )
                    )
                    self.execute_sell_position()

            # Regular SELL

            if SELL_ALERT:
                self.log("*** SELL ALERT set")
                self.log("*** Excecuted Buy: {}".format(self.executed_buy_price))
                if self.position.size > 0.0 or self.initial_position > 0:
                    if self.data.close[0] > (
                        self.executed_buy_price
                        + (self.p.sell_up_threshold / 100) * self.executed_buy_price
                    ) or self.data.close[0] <= self.highest_price * (
                        1 - self.p.sell_down_threshold / 100
                    ):
                        self.log(
                            "*** SELL price IN right range. Price {}, Executed {}, highest_price {}, highest {}% {} ".format(
                                self.data.close[0],
                                self.executed_buy_price,
                                self.highest_price,
                                (1 - self.p.sell_down_threshold),
                                self.highest_price
                                * (1 - self.p.sell_down_threshold / 100),
                            )
                        )
                        if self.sell_confirmation_2:
                            self.execute_sell_position()
                        else:
                            if self.sell_confirmation_1:
                                self.log("*** Set SELL confirmation 2")
                                self.sell_confirmation_2 = True
                            else:
                                self.log("*** Set SELL confirmation 1")
                                self.sell_confirmation_1 = True
                    else:
                        self.log(
                            "*** SELL price not in right range. Price {}, Executed {}, highest_price {}, highest {}% {} ".format(
                                self.data.close[0],
                                self.executed_buy_price,
                                self.highest_price,
                                (1 - self.p.sell_down_threshold),
                                self.highest_price
                                * (1 - self.p.sell_down_threshold / 100),
                            )
                        )
                else:
                    self.log("*** SELL Aborted: No Position")
                    self.log(
                        "*** Initial Position: {} has Position: {} ".format(
                            self.initial_position, self.position.size
                        )
                    )
            else:
                self.reset_sell_confirmations()

    def reset_buy_confirmations(self):
        if self.buy_confirmation_1 or self.buy_confirmation_2:
            self.log("*** BUY aborted")
            self.log("*** Reset BUY confirmations")
            self.buy_confirmation_1 = False
            self.buy_confirmation_2 = False

    def reset_sell_confirmations(self):
        if self.sell_confirmation_1 or self.sell_confirmation_2:
            self.log("*** SELL aborted")
            self.log("*** Reset SELL confirmations")
            self.sell_confirmation_1 = False
            self.sell_confirmation_2 = False

    def execute_sell_position(self):
        try:
            self.size_position = self.broker.get_balance()[0]
        except Exception as e:
            self.log(e)
        self.log(
            "*** Execute SELL - Size: {}, Price: {} ".format(
                self.size_position, data.close[0]
            )
        )
        if Live:
            #try:
                order = exchange.create_order(
                    coins[coin]["product"],
                    "market",
                    "sell",
                    self.size_position,
                    data.close[0],
                )
                self.log(order)
            #except Exception as e:
            #    self.log(e)
        else:
            self.log("*** SELL OFFLINE")
            self.order = self.sell()

        coins[coin]["last_executed_buy_price"] = 0
        coins_dict_to_file()
        self.initial_position = 0
        self.reset_flags()

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = "Data Status: {}".format(data._getstatusname(status))
        self.log("{}, {}, {}".format(dt, dn, msg))
        if data._getstatusname(status) == "LIVE":
            self.live_data = True
        else:
            self.live_data = False

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.log(
                    "*** Executed BUY (Price: {}, Value: {}, Commission {})".format(
                        order.executed.price, order.executed.value, order.executed.comm
                    )
                )
                self.executed_buy_price = order.executed.price
            else:
                self.log(
                    "*** Executed SELL (Price: {}, Value: {}, Commission {})".format(
                        order.executed.price, order.executed.value, order.executed.comm
                    )
                )
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order was canceled/margin/rejected")
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(
            "OPERATION PROFIT, GROSS {0:8.2f}, NET {1:8.2f}".format(
                trade.pnl, trade.pnlcomm
            )
        )

    def log(self, txt):
        dt = None
        try:
            dt = self.datas[0].datetime.date(0)
            txt = "%s, %s" % (dt.isoformat(), txt)
        except:
            txt = "%s" % (txt)
        logging.info(txt)


if __name__ == "__main__":
    args = parse_args()

    Live = True if args.live.lower() == "true" else False
    coin = args.coin

    print("Crypto Trader started for coin {}. Live Mode: {} ".format(coin, Live))

    if coin not in coins.keys():
        raise Exception("Coin {} not in repository!".format(coin))

    logging.basicConfig(
        filename="trading-" + coin + ".log",
        filemode="w",
        encoding="utf-8",
        level=logging.INFO,
    )

    frequenz_list = {
        "daily": {"historical_data": 300, "compression": 1440},
        "1 min": {"historical_data": 0.2, "compression": 1},
        "15 min": {"historical_data": 3, "compression": 15},
        "30 min": {"historical_data": 6, "compression": 30},
        "1 h": {"historical_data": 12, "compression": 60},
        "6 h": {"historical_data": 70, "compression": 360},
    }

    hist_to_date = datetime.utcnow()
    hist_start_date = hist_to_date - timedelta(
        minutes=frequenz_list[frequenz]["historical_data"] * 1440
    )

    store = CCXTStore(
        exchange="cryptocom", currency=coin, config=config, retries=5, debug=False
    )

    data = store.getdata(
        dataname=coins[coin]["product"],
        name=coins[coin]["product"],
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=frequenz_list[frequenz]["compression"],
        ohlcv_limit=1000,
        drop_newest=True,
        historical=not Live,
    )

    cerebro = bt.Cerebro(maxcpus=None, optreturn=False, quicknotify=True, exactbars=-1)
    if Live:
        broker = store.getbroker(broker_mapping=broker_mapping)
        cerebro.setbroker(broker)
    else:
        cerebro.broker.setcash(10000)
        cerebro.broker.setcommission(commission=0.005)
        cerebro.addsizer(bt.sizers.SizerFix, stake=100)

    cerebro.adddata(data)
    cerebro.addobserver(bt.observers.BuySell, barplot=True, bardist=0.0025)
    cerebro.addstrategy(SimpleTesting)
    cerebro.run()
    cerebro.plot()
