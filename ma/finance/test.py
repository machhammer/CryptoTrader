import pandas as pd
import yfinance as yf
from pandas_datareader import data as pdr
import persistance as database
from datetime import datetime, timedelta, timezone
import pytz

yf.pdr_override()




data = database.execute_select("select * from transactions where coin = 'WIF' order by timestamp desc limit 1")

print(len(data))

if len(data)
    order_date = data.iloc[0,0]
    order = data.iloc[0,2]
    size = data.iloc[0,3]
    price = data.iloc[0,4]

    europe = pytz.timezone('Europe/Berlin')
    order_date = order_date.tz_localize(europe)
    start_date = order_date.tz_convert(pytz.utc)

    data = pdr.get_data_yahoo("SOL-USD", start=start_date, interval="5m")

print(data['High'].max())


