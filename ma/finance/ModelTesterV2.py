import logging
import pandas as pd
from pandas_datareader import data as pdr
import yfinance as yf
from models import V4, V3
import pprint

yf.pdr_override() # <== that's all it takes :-)

pp = pprint.PrettyPrinter(indent=4)

highest_price = 0
has_position = False
position = {}


def setLogger(coin):
    logger = logging.getLogger("test-" + coin)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler = logging.FileHandler(
        filename="test-trading-" + coin + ".log",
        mode="w",
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def fetch_data(coin):    
    data = pdr.get_data_yahoo(coin, start="2024-04-01", end="2024-04-19", interval="5m")
    data.reset_index(inplace=True)
    data.rename(columns={'Datetime': 'timestamp','Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'}, inplace=True)
    data = pd.DataFrame(
        data[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    
    return data

def set_position(price, size, total, timestamp):
    global has_position
    position["price"] = price
    position["size"] = size
    position["total"] = total
    position["timestamp"] = timestamp
    if size > 0:
        has_position = True
    else:
        has_position = False

def offline_buy(price, ts, commission, logger):
    costs = price * 10 - price * 10 * commission
    set_position(price, 10, costs, ts)
    logger.info(
        "Offline Trading:\t{}\tBuy Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}".format(
            ts,
            price,
            10,
            price * 10,
            price * 10 * commission,
        )
    )
    return costs

def offline_sell(price, ts, commission, logger):
    sell_com = price * position["size"] * commission
    sell_total = price * position["size"] - sell_com
    logger.info(
        "Offline Trading:\t{}\tSell Price:\t{:.5f}\tSize:\t{:.5f}\tTotal:\t{:.5f}\t\tCommission:\t{:.5f}".format(
            ts, price, position["size"], sell_total, sell_com
        )
    )
    set_position(0, 0, 0, None)
    return sell_total


def backtrading(coin, strategy, data, logger):
    global highest_price
    global has_position
    commission = 0
    pnl = 0
    set_position(0, 0, 0, None)
    for i in range(len(data)):
        if data.iloc[i, 2] > highest_price:
            highest_price = data.iloc[i, 2]
        if i > 1:
            buy_sell_decision = strategy.live_trading_model(
                data,
                None,
                highest_price,
                1.5,
                strategy.params["mood_treshold"],
                0,
                0,
                strategy.params["pos_neg_threshold"],
                i,
                has_position,
                position,
            )
            if buy_sell_decision == -1:
                pnl = pnl + offline_sell(data.iloc[i, 4], data.iloc[i, 0], commission, logger)
                logger.info("PnL:\t{:.5f}".format(pnl))
                data.iloc[i, -1] = -1
                highest_price = 0
            if buy_sell_decision == 1:
                pnl = pnl - offline_buy(data.iloc[i, 4], data.iloc[i, 0], commission, logger)
                logger.info("PnL:\t{:.5f}".format(pnl))
                data.iloc[i, -1] = 1
                highest_price = data.iloc[i, 4]
    return [pnl, data]


def data_processing(coin, strategy, params):
    logger = setLogger(coin)
    original = fetch_data(coin)
    data = original.copy()
    results = {}
    print(params["sma"])
    for sma in params["sma"]:
        for aroon in params["aroon"]:
            for profit_threshold in params["profit_threshold"]:
                for sell_threshold in params["sell_threshold"]:
                    strategy.params["sma"] = sma
                    strategy.params["aroon"] = aroon
                    strategy.params["profit_threshold"] = profit_threshold
                    strategy.params["sell_threshold"] = sell_threshold
                    data = strategy.apply_indicators(data)
                    #data.to_csv("data.csv")
                    [pnl, data] = backtrading(coin, strategy, data, logger)
                    results[sma, aroon, profit_threshold, sell_threshold] = pnl

    
    pprint.pprint(results)
    strategy.show_plot(data)




if __name__ == "__main__":

    params = {
        "sma": [3, 7, 14, 21, 28, 32],
        "aroon": [3, 7, 14, 21, 28, 32],
        "profit_threshold": [0, 2, 3, 4, 10],
        "sell_threshold": [0, 2, 3, 4, 10]
    }

    #(3, 28, 3, 0)

    params = {
        "sma": [3],
        "aroon": [28],
        "profit_threshold": [3],
        "sell_threshold": [0]
    }


    data_processing("SOL-USD", V3, params)