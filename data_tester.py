import os
from xml.etree.ElementInclude import LimitedRecursiveIncludeError
from numpy import int64
import pandas as pd
from os import listdir
from fabric import Connection, Config
import plotly.graph_objects as go
from Exchange import Exchange


def delete_files(in_path):
    for file_name in listdir(in_path):
        os.remove(in_path + '/' + file_name)


def get_remote_file(ssh_connection, file_name, my_path):
    print(file_name)
    print(my_path)
    cur_path = os.getcwd()
    os.chdir(my_path)
    file = ssh_connection.get('/home/pi/Projects/CryptoTrader/data/' + file_name)
    os.chdir(cur_path)


def get_ohlc(ssh_connection, coin, interval, limit=None):
    file_name = coin + '.csv'
    path = 'D:\\tech_projects\\CryptoTrader\\data\\'
    delete_files(path)
    get_remote_file(ssh_connection, file_name, path)
    df = pd.read_csv(path + file_name)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    while True:
        m = df.index[0].minute
        if m % 5 > 0:
            df.drop(index=df.index[0], inplace=True)
        else:
            break
    ohlc_dict = {'open':'first', 'high':'max', 'low':'min', 'close': 'last', 'volume': 'sum'}
    df = df.resample(interval, origin='start').agg(ohlc_dict)
    return df





if __name__ == "__main__":
    
    exchange_1 = Exchange('test')
    exchange_2 = Exchange('bitget')

    bars = exchange_2.fetch_ohlcv('SOL/USDT', "1m", limit=200)
    print(bars)
    print("---------------------------------")

    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")

    data["timestamp"] = data["timestamp"].astype(int64) // 10**6

    data.to_csv('SOL.csv', index=False)

    input = pd.read_csv('SOL.csv')

    print(input.values.tolist())




    
