import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
from scipy.signal import argrelextrema

from ta.trend import EMAIndicator
from ta.volume import VolumeWeightedAveragePrice

from exchanges import Exchange



exchange = Exchange("cryptocom")

# Laden der historischen Daten für eine Aktie
def load_data(ticker):
    bars = exchange.fetch_ohlcv(
        ticker, "1m", limit=90
    )
    data = pd.DataFrame(
        bars[:], columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"]
    )
    data["Timestamp"] = pd.to_datetime(data["Timestamp"], unit="ms")
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

# Zeichnen der Unterstützung- und Widerstandslinien
def plot_support_resistance(data):
    plt.figure(figsize=(14, 7))
    plt.plot(data['Close'], label='Close Price', color='black')

    
    # Plotting local minima and maxima
    plt.scatter(data.index, data['min'], label='Local Minima', color='green', marker='^', alpha=1)
    plt.scatter(data.index, data['max'], label='Local Maxima', color='red', marker='v', alpha=1)
  
    plt.plot(data.index, data['ema_9'], label='EMA 9', color='red', alpha=1)
    plt.plot(data.index, data['ema_20'], label='EMA 20', color='blue', alpha=1)

    # Plotting support and resistance lines based on local extrema
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
    ticker = 'WLD/USD'
    
    # Daten laden
    data = load_data(ticker)

    # Lokale Hoch- und Tiefpunkte berechnen
    data = find_local_extrema(data)

    data = apply_indicators(data)

    data = find_big_candles(data)

    print(data)

    buy_sell(data)

    # Unterstützung- und Widerstandslinien plotten
    plot_support_resistance(data)


if __name__ == "__main__":
    main()
