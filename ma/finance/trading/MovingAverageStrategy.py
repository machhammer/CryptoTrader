from datetime import datetime
import backtrader as bt

# Create a subclass of Strategy to define the indicators and logic


class SimpleMovingAverage(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        period=10,  # period for the fast moving average
    )

    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.params.period)

    def next(self):
        if self.sma > self.data.close:
            # Do something
            pass

        elif self.sma < self.data.close:
            # Do something else
            pass
