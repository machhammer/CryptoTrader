import backtrader as bt


class MACD1226(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = (
        # Standard MACD Parameters
        ("macd1", 12),
        ("macd2", 26),
        ("macdsig", 9),
        ("atrperiod", 14),  # ATR Period (standard)
        ("atrdist", 3.0),  # ATR distance for stop price
        ("smaperiod", 30),  # SMA Period (pretty standard)
        ("dirperiod", 10),  # Lookback period to consider SMA trend direction
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data,
            period_me1=self.p.macd1,
            period_me2=self.p.macd2,
            period_signal=self.p.macdsig,
        )

        # Cross of macd.macd and macd.signal
        self.mcross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # To set the stop price
        self.atr = bt.indicators.ATR(self.data, period=self.p.atrperiod)

        # Control market trend
        self.sma = bt.indicators.SMA(self.data, period=self.p.smaperiod)
        self.smadir = self.sma - self.sma(-self.p.dirperiod)

    def next(self):
        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast MA crosses above slow MA
                self.buy()  # enter long position
        else:
            if self.crossover < 0:  # if fast MA crosses below slow MA
                self.close()  # close the position
