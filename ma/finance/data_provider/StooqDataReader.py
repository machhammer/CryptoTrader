#!pip install pandas_datareader
import pandas_datareader as web


class Reader:
    def price_data(self, symbol, start_date, end_date):
        return web.DataReader(symbol, "stooq", start_date, end_date)
