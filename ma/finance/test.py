import pandas as pd
import numpy as np

import math
import pause

import matplotlib.pyplot as plt

from scipy.signal import argrelextrema
from datetime import datetime

from ta.trend import EMAIndicator
from ta.trend import MACD
from ta.volume import VolumeWeightedAveragePrice

from exchanges import Exchange

import pprint

pd.set_option('display.max_rows', None)

exchange = Exchange("cryptocom")

# Laden der historischen Daten für eine Aktie
def load_data(ticker):
    bars = exchange.fetch_ohlcv(
        ticker, "5m", limit=120
    )
    data = pd.DataFrame(
        bars[:], columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"]
    )
    data["Timestamp"] = pd.to_datetime(data["Timestamp"], unit="ms")
    data.to_csv("data.csv", sep=";")
    return data

# Berechnung der lokalen Hoch- und Tiefpunkte
def find_local_extrema(data, order=3):
    data['min'] = data.iloc[argrelextrema(data['Close'].values, np.less_equal, order=order)[0]]['Close']
    data['max'] = data.iloc[argrelextrema(data['Close'].values, np.greater_equal, order=order)[0]]['Close']
    return data

def find_big_candles(data):
    data["change"] = (((data["Close"] - data["Open"]) / data["Open"]) * 100) >= 0.2
    return data

def apply_indicators(data):
    indicator_EMA_9 = EMAIndicator(close=data["Close"], window=9)
    data["ema_9"] = indicator_EMA_9.ema_indicator()
    indicator_EMA_20 = EMAIndicator(close=data["Close"], window=20)
    data["ema_20"] = indicator_EMA_20.ema_indicator()
    return data

def apply_vwap(data):
    indicator_vwap = VolumeWeightedAveragePrice(high=data["High"], low=data["Low"], close=data["Close"], volume=data["Volume"])
    data["vwap"] = indicator_vwap.volume_weighted_average_price()
    return data

def apply_macd(data):
    indicator_macd = MACD(close=data["Close"])
    data["macd"] = indicator_macd.macd()
    data["macd_diff"] = indicator_macd.macd_diff()
    data["macd_signal"] = indicator_macd.macd_signal()
    return data

def plot_support_resistance(data):
    plt.figure(figsize=(14, 7))
    plt.plot(data['Close'], label='Close Price', color='black')

    plt.scatter(data.index, data['min'], label='Local Minima', color='green', marker='^', alpha=1)
    plt.scatter(data.index, data['max'], label='Local Maxima', color='red', marker='v', alpha=1)
  
    plt.plot(data.index, data['ema_9'], label='EMA 9', color='red', alpha=1)
    plt.plot(data.index, data['ema_20'], label='EMA 20', color='blue', alpha=1)

    minima = data.dropna(subset=['min'])
    maxima = data.dropna(subset=['max'])
    
    # Plotting support lines
    for i in range(len(minima) - 1):
        plt.plot([minima.index[i], minima.index[i + 1]], [minima['min'].iloc[i], minima['min'].iloc[i + 1]], label='Support Line', color='green', linestyle='--')
    
    # Plotting resistance lines
    for i in range(len(maxima) - 1):
        plt.plot([maxima.index[i], maxima.index[i + 1]], [maxima['max'].iloc[i], maxima['max'].iloc[i + 1]], label='Resistance Line', color='red', linestyle='--')

    plt.title('Stock Support and Resistance Levels')
    #plt.legend()
    plt.show()

def candlesticks(stock_prices):
    
    plt.figure() 

    # "up" dataframe will store the stock_prices 
    # when the closing stock price is greater 
    # than or equal to the opening stock prices 
    up = stock_prices[stock_prices.Close >= stock_prices.Open] 

    # "down" dataframe will store the stock_prices 
    # when the closing stock price is 
    # lesser than the opening stock prices 
    down = stock_prices[stock_prices.Close < stock_prices.Open] 

    big = stock_prices[(((stock_prices.Close - stock_prices.Open) * 100) / stock_prices.Open) > 1]

    # When the stock prices have decreased, then it 
    # will be represented by blue color candlestick 
    col1 = 'blue'

    # When the stock prices have increased, then it 
    # will be represented by green color candlestick 
    col2 = 'green'

    # Setting width of candlestick elements 
    width = .3
    width2 = .03

    # Plotting up prices of the stock 
    plt.bar(up.index, up.Close-up.Open, width, bottom=up.Open, color=col1) 
    plt.bar(up.index, up.High-up.Close, width2, bottom=up.Close, color=col1) 
    plt.bar(up.index, up.Low-up.Open, width2, bottom=up.Open, color=col1) 

    # Plotting down prices of the stock 
    plt.bar(down.index, down.Close-down.Open, width, bottom=down.Open, color=col2) 
    plt.bar(down.index, down.High-down.Open, width2, bottom=down.Open, color=col2) 
    plt.bar(down.index, down.Low-down.Close, width2, bottom=down.Close, color=col2) 

    plt.bar(big.index, big.Close-big.Open, width, bottom=big.Open, color='red') 

    # rotating the x-axis tick labels at 30degree 
    # towards right 
    plt.xticks(rotation=30, ha='right') 

    # displaying candlestick chart of stock data 
    # of a week 
    plt.show() 


def buy_sell(data):
    max_column = data['max'].dropna().sort_values()
    min_column = data['min'].dropna().sort_values()
    
    print (min_column)
    print (max_column)
    current_close = data.iloc[-1, 4]
    print (current_close)
    last_max = (max_column.values)[-1]
    previous_max = (max_column.values)[-2]
    
    if current_close < last_max:
        print('dont buy')
    if current_close == last_max and current_close > previous_max:
        print('buy')    


# Hauptfunktion
def main():
    ticker = 'MYRO/USD'
    
    # Daten laden
    data = load_data(ticker)

    # Lokale Hoch- und Tiefpunkte berechnen
    data = find_local_extrema(data)

    data = apply_indicators(data)
    data = apply_vwap(data)

    #data = find_big_candles(data)

    print(data)

    buy_sell(data)

    # Unterstützung- und Widerstandslinien plotten
    plot_support_resistance(data)


def get_precision(ticker):
    markets = exchange.exchange.load_markets()
    return float((markets[ticker]['precision']['amount']))

def convert_to_precision(size, precision):
    return math.floor(size/precision) * precision

def get_orders():
    pprint.pprint(exchange.exchange.fetch_order(id='4611686087313874522'))
    

def get_ticker(ticker):
    pprint.pprint(exchange.fetch_ticker(ticker))

def get_variance(ticker):
    d = {'ICX/USD': -0.011768219832735904, 'DRIFT/USD': -0.03062400922323094, 'W/USD': -0.01640441914964852, 'VANRY/USD': -0.01392312463224199, 'CRPT/USD': -0.02989790957705396, 'AIOZ/USD': -0.029128551693238358, 'JUP/USD': -0.018636770535828462, 'LIT/USD': -0.011240772250432074, 'ELON/USD': -0.01273116391373541, 'CSPR/USD': -0.04425955100433243, 'SC/USD': -0.02395766809597666, 'MINA/USD': -0.04080914361928756, 'LPT/USD': -0.014185320145757463, 'NYAN/USD': -0.032552783109404904, 'TAIKO/USD': -0.01678692386982783, 'CKB/USD': -0.026930409914204034, 'TIA/USD': -0.0198119543317663, 'ZBCN/USD': -0.03165621654687267, 'SPEC/USD': -0.024134548334101558, 'STX/USD': -0.02695763799743256, 'AUDIO/USD': -0.015077787677335364, 'ILV/USD': -0.045726915520628686, 'NUM/USD': -0.004856115107913617, 'VRA/USD': -0.016511029909324626, 'WEMIX/USD': -0.005704169944925286, 'FARM/USD': -0.0114593029268798, 'MOBILE/USD': -0.014625228519195566, 'TRU/USD': -0.02132101686005039, 'OXT/USD': -0.019718648551160123, 'GHST/USD': -0.01228568809021735, 'DEGEN/USD': -0.025213867627194908, 'DOGE/USD': -0.018214844341288727, 'TURBO/USD': -0.030205918450838642, 'ORCA/USD': -0.03450508756960191, 'MANEKI/USD': -0.04643693018792183, 'MYRO/USD': -0.02722430459656744, 'ONDO/USD': -0.014750132751194633, 'GLMR/USD': -0.011903047756179563, 'SQT/USD': -0.015074823943661997, 'PEPE/USD': -0.013940386189627785, 'PYTH/USD': -0.015380341448631096, 'POLYX/USD': -0.01072278133577309, 'SUI/USD': -0.011742543171114561, 'STORJ/USD': -0.05530498752025226, 'SYN/USD': -0.01304435079269517, 'ZK/USD': -0.015600146824911287, 'SPS/USD': -0.019294638620907745, 'JOE/USD': -0.01338393421884887, 'MNDE/USD': -0.011252926516124084, 'BAND/USD': -0.013439999999999896, 'INJ/USD': -0.020127034537514965, 'MXC/USD': -0.08908313185791339, 'GLM/USD': -0.00971577726218098, 'ENA/USD': -0.013497012777462847, 'SPELL/USD': -0.014440970671430686, 'SNT/USD': -0.03664454019642094, 'STPT/USD': -0.009825441622243192, 'RVN/USD': -0.01135196219437018, 'FLUX/USD': -0.009535531881782022, 'IDEX/USD': -0.01210228381807521, 'AXL/USD': -0.015222534052338532, 'KDA/USD': -0.01291029172612923, 'CROB/USD': -0.009556053077048987, 'YFI/USD': -0.006388066947351834, 'LQTY/USD': -0.013356206347261423, 'RAY/USD': -0.022114484987666994, 'DYM/USD': -0.024308809746954152, '1INCH/USD': -0.011659789697857081, 'DATA/USD': -0.008406949745122683, 'ERN/USD': -0.017937030471849358}
    df = pd.DataFrame(d.items(), columns=['ticker', 'min'])
    df = df.sort_values(by='min')
    print(df)

if __name__ == "__main__":
    
    get_variance('SHDW/USD')
