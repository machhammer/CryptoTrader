import numpy as np
import pandas as pd
import time as tm
import datetime as dt
import tensorflow as tf
import exchanges
import threading

# Data preparation
from yahoo_fin import stock_info as yf
from sklearn.preprocessing import MinMaxScaler
from collections import deque

# AI
from keras.models import Sequential
from keras.layers import Dense, LSTM, Dropout

# Graphics library
import matplotlib.pyplot as plt



def run(STOCK):

  print("STOCK: " + STOCK)

  STOCK = STOCK + "-USD"

  # SETTINGS

  # Window size or the sequence length, 7 (1 week)
  N_STEPS = 7

  # Lookup steps, 1 is the next day, 3 = after tomorrow
  LOOKUP_STEPS = [1, 2, 3]


  # Current date
  date_now = tm.strftime('%Y-%m-%d')
  date_3_years_back = (dt.date.today() - dt.timedelta(days=1104)).strftime('%Y-%m-%d')

  try:

    # LOAD DATA 
    # from yahoo_fin 
    # for 1104 bars with interval = 1d (one day)
    init_df = yf.get_data(
        STOCK, 
        start_date=date_3_years_back, 
        end_date=date_now, 
        interval='1d')


    # remove columns which our neural network will not use
    init_df = init_df.drop(['open', 'high', 'low', 'adjclose', 'ticker', 'volume'], axis=1)
    # create the column 'date' based on index column
    init_df['date'] = init_df.index

    # Scale data for ML engine
    scaler = MinMaxScaler()
    init_df['scaled_close'] = scaler.fit_transform(np.expand_dims(init_df['close'].values, axis=1))


    def PrepareData(days):
      df = init_df.copy()
      df['future'] = df['scaled_close'].shift(-days)
      last_sequence = np.array(df[['scaled_close']].tail(days))
      df.dropna(inplace=True)
      sequence_data = []
      sequences = deque(maxlen=N_STEPS)

      for entry, target in zip(df[['scaled_close'] + ['date']].values, df['future'].values):
          sequences.append(entry)
          if len(sequences) == N_STEPS:
              sequence_data.append([np.array(sequences), target])

      last_sequence = list([s[:len(['scaled_close'])] for s in sequences]) + list(last_sequence)
      last_sequence = np.array(last_sequence).astype(np.float32)

      # construct the X's and Y's
      X, Y = [], []
      for seq, target in sequence_data:
          X.append(seq)
          Y.append(target)

      # convert to numpy arrays
      X = np.array(X)
      Y = np.array(Y)

      return df, last_sequence, X, Y


    def GetTrainedModel(x_train, y_train):
      model = Sequential()
      model.add(LSTM(60, return_sequences=True, input_shape=(N_STEPS, len(['scaled_close']))))
      model.add(Dropout(0.3))
      model.add(LSTM(120, return_sequences=False))
      model.add(Dropout(0.3))
      model.add(Dense(20))
      model.add(Dense(1))

      BATCH_SIZE = 8
      EPOCHS = 80

      model.compile(loss='mean_squared_error', optimizer='adam', metrics=['accuracy'])

      model.fit(x_train, y_train,
                batch_size=BATCH_SIZE,
                epochs=EPOCHS, 
                verbose=0)

      #model.summary()
      
      #model.evaluate(x_train, y_train)

      return model


    # GET PREDICTIONS
    predictions = []

    for step in LOOKUP_STEPS:
      df, last_sequence, x_train, y_train = PrepareData(step)
      x_train = x_train[:, :, :len(['scaled_close'])].astype(np.float32)

      model = GetTrainedModel(x_train, y_train)

      last_sequence = last_sequence[-N_STEPS:]
      last_sequence = np.expand_dims(last_sequence, axis=0)
      prediction = model.predict(last_sequence)
      predicted_price = scaler.inverse_transform(prediction)[0][0]

      predictions.append(round(float(predicted_price), 2))

    if bool(predictions) == True and len(predictions) > 0:
      predictions_list = [str(d)+'$' for d in predictions]
      predictions_str = ', '.join(predictions_list)
      message = f'{STOCK} prediction for upcoming 3 days ({predictions_str})'

    print(message)

    predictions_file = open("predictions.txt", "a")
    predictions_file.write("{};{};{:.4f};{:.4f};{:.4f}\n".format(date_now, STOCK, predictions[0], predictions[1], predictions[2]))

  except:
     print("Error STOCK: ", STOCK)


if __name__ == "__main__":
  
  exchange = exchanges.cryptocom()
  tickers = exchange.fetch_tickers()
  df = pd.DataFrame(tickers)
  df = df.T
  df = df[['symbol']]
  df = df[df["symbol"].str.contains("/USDT")]
  df['symbol'] = df['symbol'].str.replace('/USDT','')
  df = df.sort_values(by='symbol', ascending=True)

  
  for i in range(0, len(df), 4):

    threads = [None, None, None, None]
    counter_threads = 0

    for t in range(len(threads)):
      if (i + t <= len(df)):
        threads[t] = threading.Thread(target=run, args=[df.iloc[i + t, 0]])
      counter_threads = counter_threads + 1

    for t in range(counter_threads):
      threads[t].start()

    for t in range(counter_threads):
      threads[t].join()
    
    
