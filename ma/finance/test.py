import pandas as pd
import persistance as database
import matplotlib.pyplot as plt
from pandas_datareader import data as pdr
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
import pytz
from datetime import datetime, timedelta

coin = 'SOL'

pos_neg = database.execute_select("select timestamp, pos_neg_median from v_manager")
indicator_SMA = SMAIndicator(close=pos_neg.iloc[:,1], window=200)
pos_neg["sma"] = indicator_SMA.sma_indicator()



sol = database.execute_select("select timestamp, c_price from v_trader where coin = 'SOL'")
indicator_SMA = SMAIndicator(close=sol.iloc[:,1], window=200)
sol["sma"] = indicator_SMA.sma_indicator()



figure, axis = plt.subplots(
            2, sharex=True, figsize=(16, 9), gridspec_kw={"height_ratios": [2, 2]}
        )
axis[0].plot(pos_neg.iloc[:,0], pos_neg.iloc[:,1], linewidth=2)
axis[0].plot(pos_neg.iloc[:,0], pos_neg.iloc[:,2])

axis[1].plot(sol.iloc[:,0], sol.iloc[:,1], linewidth=2)
axis[1].plot(sol.iloc[:,0], sol.iloc[:,2])


plt.show()
