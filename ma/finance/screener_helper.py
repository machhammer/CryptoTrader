from calendar import weekday
import time
import logging
import pandas as pd
from datetime import datetime
import persistance as database
import matplotlib.pyplot as plt

logger = logging.getLogger("screener")

class Helper():
     
    def __init__(
        self,
        logger,
        wait_time_next_asset_selection_minutes,
        wait_time_next_buy_selection_seconds
    ):
         self.logger = logger
         self.wait_time_next_asset_selection_minutes = wait_time_next_asset_selection_minutes
         self.wait_time_next_buy_selection_seconds = wait_time_next_buy_selection_seconds

    #************************************ Helper - Wait functions
    def wait(self, period):
        if period == "short":
            wait_time = self.get_wait_time_1()
        if period == "long":
            wait_time = self.get_wait_time()
        logger.debug("wait: {}".format(wait_time))
        time.sleep(wait_time)


    def get_wait_time(self):
            minute = datetime.now().minute
            wait_time = (self.wait_time_next_asset_selection_minutes - (minute % self.wait_time_next_asset_selection_minutes)) * 60
            return wait_time


    def get_wait_time_1(self):
        seconds = datetime.now().second
        wait_time = (self.wait_time_next_buy_selection_seconds - (seconds % self.wait_time_next_buy_selection_seconds))
        return wait_time

    def wait_1_hour(self):
        time.sleep (60 * 60)

    def wait_5_minutes(self):
        time.sleep (5 * 60)


    def in_business_hours(self, from_time, to_time):    
        now = datetime.now()
        if to_time < from_time:
            raise Exception("case end < start not implemeted!")
        run = now.hour >= from_time.hour and now.hour < to_time.hour and now.weekday() < 6
        return run
                
    def in_buying_period(self, by_time):
        now = datetime.now()
        run = now.hour < by_time.hour
        return run

    def get_time(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    def print_time(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        logger.info("Current Time: {}".format(current_time))


    #************************************ Helper - Save data to File
    def save_to_file(self, data, filename):
        data.to_csv(filename, header=True, index=None, sep=';', mode='w')


    #************************************ Helper - Read data from File
    def read_from_file(self, filename):
        return pd.read_csv(filename, sep=';')


    def plot(self, data):
        plt.figure(figsize=(14, 7))
        plt.plot(data['close'], label='close Price', color='black')
        plt.scatter(data.index, data['min'], label='Local Minima', color='green', marker='^', alpha=1)
        plt.scatter(data.index, data['max'], label='Local Maxima', color='red', marker='v', alpha=1)
        plt.plot(data.index, data['ema_9'], label='EMA 9', color='red', alpha=1)
        plt.plot(data.index, data['ema_20'], label='EMA 20', color='blue', alpha=1)
        minima = data.dropna(subset=['min'])
        maxima = data.dropna(subset=['max'])
        for i in range(len(minima) - 1):
            plt.plot([minima.index[i], minima.index[i + 1]], [minima['min'].iloc[i], minima['min'].iloc[i + 1]], label='Support Line', color='green', linestyle='--')
        
        for i in range(len(maxima) - 1):
            plt.plot([maxima.index[i], maxima.index[i + 1]], [maxima['max'].iloc[i], maxima['max'].iloc[i + 1]], label='Resistance Line', color='red', linestyle='--')

        plt.title('Stock Support and Resistance Levels')
        plt.show()


    def write_to_db(self, market=None, market_factor=None, base_currency=None, selected_ticker=None, funding=None, major_move=None, increase_volume=None, buy_signal=None, close_to_maximum=None, is_buy=None, current_close=None, last_max=None, previous_max=None, vwap=None,macd=None, macd_signal=None, macd_diff=None, buy_order_id=None, sell_order_id=None):
        if (major_move and len(major_move) > 0): 
            major_move=';'.join(map(str, major_move))
        else:
            major_move=None
        if (increase_volume and len(increase_volume) > 0 ): 
            increase_volume=';'.join(map(str, increase_volume))
        else:
            increase_volume=None
        if (buy_signal and len(buy_signal) > 0): 
            buy_signal=';'.join(map(str, buy_signal))
        else:
            buy_signal=None
        database.insert_screener(self.get_time(), market, market_factor, base_currency, selected_ticker, funding, major_move, increase_volume, buy_signal, close_to_maximum, is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff, buy_order_id, sell_order_id)    


    def write_trading_info_to_db(self, asset, side, price, market_movement):
        database.insert_trading_info_table(self.get_time(), asset, side, price, market_movement)


