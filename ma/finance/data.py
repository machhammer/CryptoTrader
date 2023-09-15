import datetime as dt
from datetime import datetime
import data_provider.DataReader as data_provider
import config as cfg
import pandas as pd
import backtrader as bt

from trading.SMAStrategy import SmaCross

start_date = dt.datetime(2023, 1, 1)
end_date = dt.datetime(2023, 9, 15)


cerebro = bt.Cerebro()  # create a "Cerebro" engine instance


data = data_provider.instatiate("yahoo").historic_price_data(
    "btc-usd", start_date, end_date
)

cerebro.adddata(data)  # Add the data feed

cerebro.addstrategy(SmaCross)  # Add the trading strategy
cerebro.run()  # run it all
cerebro.plot()  # and plot it with a single command
