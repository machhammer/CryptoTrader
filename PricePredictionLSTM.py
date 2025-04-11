import os
import ta
import ta.momentum
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Bidirectional, LSTM, Dense, Dropout, GRU
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.models import load_model

from datetime import datetime, timedelta

import matplotlib.pyplot as plt

from Exchange import Offline_Exchange
from DataToolbox import get_data

import pandas as pd
import numpy as np
import joblib

from sklearn.preprocessing import MinMaxScaler


def add_technical_indicators(df):
    df = df.copy()

    # Ensure timestamps are sorted
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Relative Strength Index (RSI)
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()

    # MACD
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df["macd_diff"] = macd.macd_diff()
    df['macd_signal'] = macd.macd_signal()

    # Exponential Moving Averages
    df['ema_9'] = ta.trend.EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['ema_20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['ema_diff'] = df['ema_9'] - df['ema_20']

    bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = df['bb_upper'] - df['bb_lower']

    # VWAP (uses high, low, close, volume)
    df['vwap'] = ta.volume.VolumeWeightedAveragePrice(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        volume=df['volume']
    ).volume_weighted_average_price()

    # AROON
    aroon = ta.trend.AroonIndicator(high=df["high"], low=df["low"], window=14)
    df['aroon_up'] = aroon.aroon_up()
    df['aroon_down'] = aroon.aroon_down()

    #momentum = ta.momentum.MomentumIndicator(close=df['close'], window=10)
    #df['momentum'] = momentum.momentum()

    obv = ta.volume.OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
    df['obv'] = obv.on_balance_volume()

    adx = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['adx'] = adx.adx()
    df['adx_pos'] = adx.adx_pos()  # +DI
    df['adx_neg'] = adx.adx_neg()  # -DI

    # Drop rows with NaNs due to indicator calculations
    df.dropna(inplace=True)

    return df


def preprocess_for_lstm(df, scaler, target_percentage, seq_len, lookahead):
    """
    Prepares LSTM-ready sequences from a coin price DataFrame.

    Parameters:
        df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        seq_len: length of input sequences (e.g. 60 for 1-hour if data is in 1-min intervals)
        lookahead: how many steps ahead to check for the 2% increase (e.g. 120 for 2 hours)

    Returns:
        X: numpy array of shape (samples, seq_len, features)
        y: binary target array of shape (samples,)
    """
    df = df.copy()
    
    # Sort by time (just in case)
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Create target column
    df['future_close'] = df['close'].shift(-lookahead).rolling(window=lookahead).max()
    df['target'] = (df['future_close'] >= df['close'] * (1 + target_percentage)).astype(int)
    
    # Drop rows with NaNs (due to shift)
    df.dropna(inplace=True)

    df.to_csv("enriched_data.csv")

    # Select features
    data = df[feature_cols]

    # Normalize
    
    data_scaled = scaler.fit_transform(data)

    # Convert to sequences
    X = []
    y = []

    for i in range(len(data_scaled) - seq_len):
        X_seq = data_scaled[i:i+seq_len]
        y_label = df['target'].iloc[i + seq_len]
        X.append(X_seq)
        y.append(y_label)

    return np.array(X), np.array(y)

def build_lstm_model(input_shape):
    model = Sequential()
    
    # First LSTM layer
    model.add(LSTM(units=64, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))

    # Second LSTM layer
    model.add(LSTM(units=32))
    model.add(Dropout(0.2))

    # Output layer for binary classification
    model.add(Dense(1, activation='sigmoid'))

    # Compile the model
    model.compile(optimizer=Adam(learning_rate=0.001), 
                  loss='binary_crossentropy', 
                  metrics=['accuracy'])

    return model


def build_gru_model(input_shape):
    model = Sequential()

    # First GRU layer
    model.add(GRU(units=64, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))

    # Second GRU layer
    model.add(GRU(units=32))
    model.add(Dropout(0.2))

    # Optional Dense layer before output
    model.add(Dense(16, activation='relu'))
    model.add(Dropout(0.2))

    # Output layer for binary classification
    model.add(Dense(1, activation='sigmoid'))

    # Compile the model
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return model

def plot_training_history(history):
    # Accuracy
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='Train Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.title('Model Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()

    # Loss
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title('Model Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    plt.tight_layout()
    plt.show()


def predict_latest(df, model, scaler, feature_cols, seq_len=60):
    latest_data = df[feature_cols].copy()
    latest_scaled = scaler.transform(latest_data)
    last_seq = latest_scaled[-seq_len:]
    X_last = np.expand_dims(last_seq, axis=0)
    prob = model.predict(X_last)[0][0]
    return prob, int(prob > 0.5)


def load_data(filepath):
    df = pd.read_csv(filepath, parse_dates=['timestamp'])
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def train_data(df_with_indicators, target_percentage, lookahead, seq_len):

    scaler = MinMaxScaler()

    # Step 2: Preprocess for LSTM
    X, y = preprocess_for_lstm(df_with_indicators, scaler, target_percentage, seq_len, lookahead)

    print("Input shape:", X.shape)  # (samples, 60, 5)
    print("Target shape:", y.shape)  # (samples,)

    # Train/test split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # Assuming you already have X_train, y_train, X_test, y_test
    input_shape = (X_train.shape[1], X_train.shape[2])  # (seq_len, num_features)
    model = build_lstm_model(input_shape)
    #model = build_gru_model(input_shape)

    # Optional: Early stopping to prevent overfitting
    early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

    # Fit the model
    history = model.fit(
        X_train, y_train,
        epochs=60,
        batch_size=64,
        validation_split=0.2,
        callbacks=[early_stop]
    )

    loss, accuracy = model.evaluate(X_test, y_test)
    print(f"Test Accuracy: {accuracy:.4f}")

    model.save("lstm_model_folder")  # Creates a folder with all model files
    joblib.dump(scaler, "scaler.save")


def load_trained_model():
    model = load_model("lstm_model_folder")
    scaler = joblib.load("scaler.save")
    return model, scaler

def source_data(exchange, coin, current_datetime):
    
    batch_size = 200
    nr_batches = 960

    current = current_datetime

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
    
    data.to_csv("D:\\tech_projects\\CryptoTrader\\data\\" + coin.replace("/USDT", "") + ".csv")

def source_data_for_all_coins(exchange, current_datetime):
    coins = exchange.fetch_tickers()
    coins = pd.DataFrame(coins)
    coins = coins.T
    coins = coins[coins["symbol"].str.endswith("/USDT")]
    coins = coins["symbol"].to_list()
    coins = sorted(coins)
    #coins = [coin for coin in coins if coin.startswith('C')]

    directory_path = 'D:\\tech_projects\\CryptoTrader\\data\\'
    files = os.listdir(directory_path)

    ignore_coins = [file.replace(".csv", "") for file in files]

    for coin in coins:
        if coin.replace("/USDT", "") not in ignore_coins:
            print("Download coin: " + coin)
            source_data(exchange, coin, current_datetime)


if __name__ == "__main__":

    target_percentage = 1.5
    lookahead = 1
    seq_len = 30

    feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi', 'macd', 'macd_signal',
            'ema_9', 'ema_20', 'ema_diff', 'vwap',
            'aroon_up', 'aroon_down',
            'obv', 'adx', 'adx_pos', 'adx_neg'
    ]

    current = datetime.strptime("2025-04-01 20:15", "%Y-%m-%d %H:%M")   
    #current = datetime.now()

    exchange = Offline_Exchange("bitget", 1000)
    source_data_for_all_coins(exchange, current)

    
    

    #source_data(exchange, "SOL/USDT", current)

    
    

    """ data = load_data("coin_data.csv")
    df_with_indicators = add_technical_indicators(data)

    train_data(df_with_indicators, target_percentage=target_percentage/100, lookahead=lookahead * 60, seq_len=seq_len)
    

    model, scaler = load_trained_model()

    probability, prediction = predict_latest(df=df_with_indicators, model=model, scaler=scaler, feature_cols=feature_cols, seq_len=seq_len)

    print(f"Predicted Probability of ≥{target_percentage}% increase in next {lookahead}h: {probability:.4f}")
    print("Prediction:", "YES 🚀" if prediction else "NO ❌") """


#plot_training_history(history)