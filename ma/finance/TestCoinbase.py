import pandas as pd
import pandas_ta as ta
import exchanges
import matplotlib.pyplot as plt 

exchange = exchanges.cryptocom()

def fetch_data(coin):
    bars = exchange.fetch_ohlcv(
        coin + "/USDT", timeframe="30m", limit=50
    )
    data = pd.DataFrame(
        bars[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data

def plot_data(data):
    stock_prices = pd.DataFrame({'open': [36, 56, 45, 29, 65, 66, 67], 
                             'close': [29, 72, 11, 4, 23, 68, 45], 
                             'high': [42, 73, 61, 62, 73, 56, 55], 
                             'low': [22, 11, 10, 2, 13, 24, 25]}, 
                            index=pd.date_range( 
                              "2021-11-10", periods=7, freq="d")) 
  
    stock_prices  = data

    plt.figure() 
  
    up = stock_prices[stock_prices.close >= stock_prices.open] 
  
    down = stock_prices[stock_prices.close < stock_prices.open] 

    col1 = 'blue'
    col2 = 'green'

    width = .3
    width2 = .03
  
    # Plotting up prices of the stock 
    plt.bar(up.index, up.close-up.open, width, bottom=up.open, color=col1) 
    plt.bar(up.index, up.high-up.close, width2, bottom=up.close, color=col1) 
    plt.bar(up.index, up.low-up.open, width2, bottom=up.open, color=col1) 
  
    # Plotting down prices of the stock 
    plt.bar(down.index, down.close-down.open, width, bottom=down.open, color=col2) 
    plt.bar(down.index, down.high-down.open, width2, bottom=down.open, color=col2) 
    plt.bar(down.index, down.low-down.close, width2, bottom=down.close, color=col2) 
  
    plt.xticks(rotation=30, ha='right') 
  
    plt.plot(data['sma'])

    plt.show() 

data = fetch_data("SOL")
sma = ta.sma(data["close"], length=10)
data.ta.aroon(high=data['high'], low=data['low'], length=3, append=True)

data['sma'] = sma
#print(data)

print(data[['timestamp', 'open', 'close', 'AROONU_3', 'AROOND_3', 'sma']])