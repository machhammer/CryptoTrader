import logging
import pandas as pd
from tqdm import tqdm
from pandas_datareader import data as pdr
import yfinance as yf
from models import V4, V3
import pprint
import time
from datetime import datetime, timedelta

yf.pdr_override() # <== that's all it takes :-)

pp = pprint.PrettyPrinter(indent=4)

highest_price = 0
has_position = False
position = {}

test_params = {
        "sma": [3, 5, 7, 9, 12, 14, 21, 28, 32],
        "aroon": [3, 5, 7, 9, 12, 14, 21, 28, 32],
        "profit_threshold": [0, 1, 2, 3, 4, 5, 8, 10],
        "sell_threshold": [0, 1, 2, 3, 4, 5, 8, 10]
    }



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
    end_date = datetime.now() + timedelta(days=1)
    start_date = end_date - timedelta(days=20)
    print(start_date, end_date)
    data = pdr.get_data_yahoo(coin, start=start_date, end=end_date, interval="5m")
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

def offline_buy(price, ts, commission, size, logger):
    costs = price * size + price * size * commission
    set_position(price, size, costs, ts)
    logger.info(
        "BUY:\t{}\tBuy Price:\t{:.5f}\tSize:\t{:.5f}\tValue:\t{:.5f}\tCommission:\t{:.5f}\t\tTotal:\t{:.5f}".format(
            ts,
            price,
            size,
            price * size,
            price * size * commission,
            costs
        )
    )
    return costs

def offline_sell(price, ts, commission, logger):
    revenue = price * position["size"]
    costs = price * position["size"] * commission
    sell_total = revenue - costs
    logger.info(
        "SELL: \t{}\tSell Price:\t{:.5f}\tSize:\t{:.5f}\Value:\t{:.5f}\tCommission:\t{:.5f}\t\tTotal:\t{:.5f}".format(
            ts, price, position["size"], revenue, costs, sell_total
        )
    )
    set_position(0, 0, 0, None)
    return sell_total


def backtrading(coin, strategy, data, logger):
    global highest_price
    global has_position
    commission = 0.075 / 100
    original_budget = 100
    budget = original_budget
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
                budget = budget + offline_sell(data.iloc[i, 4], data.iloc[i, 0], commission, logger)
                pnl = budget - original_budget
                logger.info("Budget:\t{:.5f}\tPnL:\t{:.5f}".format(budget, pnl))
                data.iloc[i, -1] = -1
                highest_price = 0
            if buy_sell_decision == 1:
                budget = budget - offline_buy(data.iloc[i, 4], data.iloc[i, 0], commission, (budget-1)/data.iloc[i, 4], logger)
                logger.info("\tBudget:\t{:.5f}".format(budget))
                data.iloc[i, -1] = 1
                highest_price = data.iloc[i, 4]
    return [pnl, data]


def optimal_parameters(coin, strategy):
    logger = setLogger(coin)
    original = fetch_data(coin)
    data = original.copy()
    results = {}
    iterations = len(test_params["sma"]) * len(test_params["aroon"]) * len(test_params["profit_threshold"]) * len(test_params["sell_threshold"])
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for sma in test_params["sma"]:
        for aroon in test_params["aroon"]:
            for profit_threshold in test_params["profit_threshold"]:
                for sell_threshold in test_params["sell_threshold"]:
                    strategy.params["sma"] = sma
                    strategy.params["aroon"] = aroon
                    strategy.params["profit_threshold"] = profit_threshold
                    strategy.params["sell_threshold"] = sell_threshold
                    data = strategy.apply_indicators(data)
                    [pnl, data] = backtrading(coin, strategy, data, logger)
                    results[sma, aroon, profit_threshold, sell_threshold] = pnl
                    try:
                        next(progress_bar)
                    except:
                        pass
    
    max_key = (max(results, key=results.get))
    return max_key, results[max_key]




if __name__ == "__main__":

    par = optimal_parameters("SOL-USD", V3)
    print("SOL")
    print(par)
    