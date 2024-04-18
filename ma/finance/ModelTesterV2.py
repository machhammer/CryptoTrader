import pandas as pd
from pandas_datareader import data as pdr
import yfinance as yf
from models import V4

yf.pdr_override() # <== that's all it takes :-)



def fetch_data(coin):    
    data = pdr.get_data_yahoo(coin, start="2024-04-01", end="2024-04-19", interval="5m")
    data.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'}, inplace=True)
    return data

def data_processing(coin, strategy):
    data = fetch_data(coin)
    data = strategy.apply_indicators(data)

    print(data)


if __name__ == "__main__":
    data_processing("PENDLE-USD", V4)