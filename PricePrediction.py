import pandas as pd
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta

import ta.trend
import ta.volume
from Exchange import Offline_Exchange
from DataToolbox import get_data
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import ta  # Technical Analysis library

# Load your data (ensure 'timestamp' and 'close' columns are present)
def load_data(filepath):
    df = pd.read_csv(filepath, parse_dates=['timestamp'])
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def save_data(data, filepath):
    data.to_csv(filepath)


# Basic statistical features
def add_features(df):
    df['return_1min'] = df['close'].pct_change()
    df['rolling_mean_5'] = df['close'].rolling(window=5).mean()
    df['rolling_std_5'] = df['close'].rolling(window=5).std()
    df['rolling_mean_15'] = df['close'].rolling(window=15).mean()
    df['rolling_std_15'] = df['close'].rolling(window=15).std()
    return df

# Add technical indicators: RSI, MACD, Bollinger Bands
def add_technical_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df["macd_diff"] = macd.macd_diff()
    df['macd_signal'] = macd.macd_signal()
    
    bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    
    ema9 = ta.trend.EMAIndicator(close=df["close"], window=9)
    df["ema_9"] = ema9.ema_indicator()
    ema20 = ta.trend.EMAIndicator(close=df["close"], window=20)
    df["ema_20"] = ema20.ema_indicator()

    aroon = ta.trend.AroonIndicator(high=df["high"], low=df["low"], window=14)
    df["aroon_up"] = aroon.aroon_up()
    df["aroon_down"] = aroon.aroon_down()

    vwap = ta.volume.VolumeWeightedAveragePrice(
        high=df["high"], low=df["low"], close=df["close"], volume=df["volume"]
    )
    df["vwap"] = vwap.volume_weighted_average_price()

    return df

# Create the target label: price increases by X% in next 120 minutes
def create_target(df, minutes=120, target_percent=0.02):  # 2% increase
    df['future_max'] = df['close'].shift(-minutes).rolling(window=minutes).max()
    df['target'] = (df['future_max'] >= df['close'] * (1 + target_percent)).astype(int)
    return df

# Train model
def train_model(df):
    features = [
        'return_1min', 'rolling_mean_5', 'rolling_std_5',
        'rolling_mean_15', 'rolling_std_15',
        'rsi', 'macd', 'macd_diff', 'macd_signal',
        'bb_upper', 'bb_lower', 'bb_width',
        'ema_9', 'ema_20', 'vwap'
    ]
    
    df = df.dropna(subset=features + ['target'])  # Drop rows with NaNs in features or target
    X = df[features]
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    print("Evaluation:")
    print(classification_report(y_test, model.predict(X_test)))
    
    return model, features

# Predict probability of hitting target increase in next 2 hours
def predict_probability(model, features, df):
    latest_data = df.dropna(subset=features).tail(1)
    if latest_data.empty:
        return None
    X_latest = latest_data[features]
    proba = model.predict_proba(X_latest)[0][1]
    return proba

# === Example usage ===
if __name__ == "__main__":
        
    coin = "ETH/USDT"
    

    mode = 2

    if mode == 1:
        exchange = Offline_Exchange("bitget", 1000)
        batch_size = 200
        nr_batches = 80

        #current = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #timestamp = datetime.strptime("2025-02-01 01:00", "%Y-%m-%d %H:%M")   

        current = datetime.now()
        print("Now: ", current)
        timestamp = current - timedelta(minutes=batch_size * (nr_batches-1))
        print("Start: ", timestamp)
        exchange.observation_start = timestamp
        data = get_data(exchange, coin, "1m", limit=batch_size)
        
        for i in range(1, nr_batches):
            timestamp = timestamp + timedelta(minutes=batch_size)
            exchange.observation_start = timestamp
            data_new = get_data(exchange, coin, "1m", limit=batch_size)
            
            data = pd.concat([data, data_new], ignore_index=True)
        
        save_data(data, "coin_data.csv")


    df = load_data("coin_data.csv")  # Replace with your actual CSV

    if mode == 2:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # Plot the candlestick chart
        mpf.plot(
            df,
            type='candle',
            volume=True,
            title='Candlestick Chart',
            style='yahoo',  # other styles: 'classic', 'charles', 'mike', 'nightclouds', etc.
            mav=(10, 20),   # optional: moving averages
            ylabel='Price',
            ylabel_lower='Volume'
        )

    target_percentage = 0.02
    period = 1

    df = add_features(df)
    df = add_technical_indicators(df)
    df = create_target(df, minutes = period * 60, target_percent=target_percentage)  # Predict 2% increase in 2 hours
    
    df.to_csv("encriched_coin_data.csv")

    model, features = train_model(df)
    probability = predict_probability(model, features, df)
    
    

    if probability is not None:
        print(f"Probability of price increasing by {target_percentage*100}% in next {period} hours: {probability:.2%}")
    else:
        print("Not enough data to make prediction.")
