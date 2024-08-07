import logging
import pandas as pd
from tqdm import tqdm
from pandas_datareader import data as pdr
import yfinance as yf
from models import V4, V3
from scenarios import S1
import pprint
import time
import persistance as database
from datetime import datetime, timedelta

yf.pdr_override() # <== that's all it takes :-)

pp = pprint.PrettyPrinter(indent=4)

highest_price = 0
has_position = False
position = {}



test_params = {
    "sma": [3, 5, 7, 9, 14, 21, 28, 32, 41],
    "aroon": [3, 5, 7, 9, 14, 21, 28, 32, 41],
    "profit_threshold": [2, 1, 0],
    "sell_threshold": [2, 1, 0],
    "pos_neg_threshold": [-100]
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

def fetch_and_join_manager(ticker_data):
    manager_data = database.execute_select("SELECT * FROM manager")
    manager_data[0] = pd.to_datetime(manager_data[0]).dt.strftime('%Y-%m-%d %H:%M')
    ticker_data['timestamp'] = pd.to_datetime(ticker_data['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    manager_data = manager_data.rename(columns={manager_data.columns[0]: 'timestamp'})
    manager_data = manager_data.rename(columns={manager_data.columns[6]: 'pos_neg_median'})
    manager_data = manager_data[['timestamp', 'pos_neg_median']]
    data = manager_data.merge(ticker_data, how='right')
    data = data[['timestamp', 'pos_neg_median', 'close']]
    data = data.dropna(how='any')
    return data

def fetch_data(coin, days):    
    end_date = datetime.now() + timedelta(days=1)
    start_date = end_date - timedelta(days=days)
    data = pdr.get_data_yahoo(coin, start=start_date, end=end_date, interval="5m")
    data.reset_index(inplace=True)
    data.rename(columns={'Datetime': 'timestamp','Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'}, inplace=True)
    data = pd.DataFrame(
        data[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    #data.to_csv('data_' + coin + '.csv')
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


def backtrading(coin, model, data, logger, write_to_database=False):
    global highest_price
    global has_position
    commission = model.scenario.params["commission"]
    original_budget = 100
    budget = original_budget
    pnl = 0
    if write_to_database: connection = database.connect()
    data['mysql_timestamp'] = pd.to_datetime(data['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    set_position(0, 0, 0, None)
    logger.info("{}, {}, {}, {}".format(model.params['sma'], model.params['aroon'], model.params['profit_threshold'], model.params['sell_threshold'], model.params['pos_neg_threshold']))
    for i in range(len(data)):
        if data.iloc[i, 2] > highest_price:
            highest_price = data.iloc[i, 2]
        if i > 1:
            buy_sell_decision = model.live_trading_model(
                data,
                None,
                highest_price,
                1.5,
                0,
                0,
                i,
                has_position,
                position,
            )
            if buy_sell_decision == -1:
                budget = budget + offline_sell(data.iloc[i, 4], data.iloc[i, 0], commission, logger)
                pnl = budget - original_budget
                logger.info("Budget:\t{:.5f}\tPnL:\t{:.5f}".format(budget, pnl))
                if write_to_database: database.insert_optimizer_results_transactions(connection, data.iloc[i, -1], coin, model.params['sma'], model.params['aroon'], model.params['profit_threshold'], model.params['sell_threshold'], model.params['pos_neg_threshold'], "BUY", data.iloc[i, 4], budget, pnl)
                data.iloc[i, -2] = -1
                highest_price = 0
            if buy_sell_decision == 1:
                budget = budget - offline_buy(data.iloc[i, 4], data.iloc[i, 0], commission, (budget-1)/data.iloc[i, 4], logger)
                logger.info("\tBudget:\t{:.5f}".format(budget))
                if write_to_database: database.insert_optimizer_results_transactions(connection, data.iloc[i, -1], coin, model.params['sma'], model.params['aroon'], model.params['profit_threshold'], model.params['sell_threshold'], model.params['pos_neg_threshold'], "SELL", data.iloc[i, 4], budget, pnl)
                data.iloc[i, -2] = 1
                highest_price = data.iloc[i, 4]
    if has_position:
        budget = budget + offline_sell(data.iloc[i, 4], data.iloc[i, 0], commission, logger)
        pnl = budget - original_budget
        logger.info("Budget:\t{:.5f}\tPnL:\t{:.5f}".format(budget, pnl))
        if write_to_database: database.insert_optimizer_results_transactions(connection, data.iloc[i, -1], coin, model.params['sma'], model.params['aroon'], model.params['profit_threshold'], model.params['sell_threshold'], model.params['pos_neg_threshold'], "SELL", data.iloc[i, 4], budget, pnl)
        data.iloc[i, -2] = -1

    if write_to_database: 
        connection.commit()
        connection.close()

    return [pnl, data]


def analyze_paramters():
    data = pd.read_csv("parameters.csv").reset_index()
    max_row = data[data['pnl']==data['pnl'].max()]
    return (max_row.iloc[0,1]), (max_row.iloc[0,2]), (max_row.iloc[0,3]), (max_row.iloc[0,4])


def optimize_parameters(coin, model, days, write_to_database=False):
    logger = setLogger(coin)
    original = fetch_data(coin, days=days)
    data = original.copy()
    results = {}
    counter = 1
    iterations = len(test_params["sma"]) * len(test_params["aroon"]) * len(test_params["profit_threshold"]) * len(test_params["sell_threshold"]) * len(test_params["pos_neg_threshold"])
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for sma in test_params["sma"]:
        for aroon in test_params["aroon"]:
            for profit_threshold in test_params["profit_threshold"]:
                for sell_threshold in test_params["sell_threshold"]:
                    for pos_neg_threshold in test_params["pos_neg_threshold"]:
                        model.params["sma"] = sma
                        model.params["aroon"] = aroon
                        model.params["profit_threshold"] = profit_threshold
                        model.params["sell_threshold"] = sell_threshold
                        model.params["pos_neg_threshold"] = pos_neg_threshold
                        
                        data = model.apply_indicators(data)
                        [pnl, data] = backtrading(coin, model, data, logger, write_to_database)
                            
                        results[counter] = {}
                        results[counter]['sma'] = sma
                        results[counter]['aroon'] = aroon
                        results[counter]['profit_threshold'] = profit_threshold
                        results[counter]['sell_threshold'] = sell_threshold
                        results[counter]['pos_neg_threshold'] = pos_neg_threshold
                        results[counter]['pnl'] = pnl

                        counter += 1

                        try:
                            next(progress_bar)
                        except:
                            pass

    data = pd.DataFrame.from_dict(results, orient='index')
    if write_to_database: database.generate_optimizer_results(coin, data)
    max_row = data[data['pnl']==data['pnl'].max()]
    return (max_row.iloc[0,0]), (max_row.iloc[0,1]), (max_row.iloc[0,2]), (max_row.iloc[0,3]), (max_row.iloc[0,4]), (max_row.iloc[0,5])
    

def adjust_threshold(current_treshold, current_profit):
    return current_treshold / abs(current_profit)


def test_parameter(coin, model, params, days, write_to_database = False):
    logger = setLogger(coin)
    original = fetch_data(coin, days=days)
    data = original.copy()
    model.params["sma"] = params["sma"]
    model.params["aroon"] = params["aroon"]
    model.params["profit_threshold"] = params["profit_threshold"]
    model.params["sell_threshold"] = params["sell_threshold"]
    model.params["pos_neg_threshold"] = params["pos_neg_threshold"]
                    
    data = model.apply_indicators(data)
    [pnl, data] = backtrading(coin, model, data, logger, write_to_database)
    data.to_csv("test-trading-data.csv")
    model.show_plot(data)

    return pnl




if __name__ == "__main__":



    scenario = S1()


    params = {
        "sma": [5],
        "aroon": [32],
        "profit_threshold": [0],
        "sell_threshold": [0],
        "pos_neg_threshold": [-100]
    }


    model = V3(scenario=scenario)

    database.initialize_optimizer_results_transactions_table()

    days = 2.5

    par = optimize_parameters("SOL-USD", model, days=days, write_to_database=True)
    print(par)
    
    

    pnl = test_parameter("SOL-USD", model, params={'sma': par[0], 'aroon': par[1], 'profit_threshold': par[2], 'sell_threshold': par[3], 'pos_neg_threshold': par[4]}, days=days)
    print(pnl)
    
