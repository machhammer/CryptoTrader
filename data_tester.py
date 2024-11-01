import os
import pandas as pd
from os import listdir
from fabric import Connection, Config
import plotly.graph_objects as go



def delete_files(in_path):
    for file_name in listdir(in_path):
        os.remove(in_path + '/' + file_name)


def get_remote_file(ssh_connection, file_name, my_path):
    print(file_name)
    print(my_path)
    cur_path = os.getcwd()
    os.chdir(my_path)
    file = ssh_connection.get('/home/pi/Projects/CryptoTrader/' + file_name)
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
    
    
    c = Connection(
        host="192.168.1.136",
        user="pi",
    )
    

    df = get_ohlc(c, "ZBU", '1min')
   
    
    print(df)

    fig = go.Figure(data=go.Ohlc(x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close']))
    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.show()
    
   