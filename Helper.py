from calendar import weekday
import time
import credentials
import logging
import argparse
import pandas as pd
from datetime import datetime, time as ti
import Database as database
import matplotlib.pyplot as plt
import logging
from Exchange import Exchange, Offline_Exchange

logger = logging.getLogger("screener")




def __init__(
    self,
    wait_time_next_asset_selection_minutes,
    wait_time_next_buy_selection_seconds,
):
    
    self.wait_time_next_asset_selection_minutes = (
        wait_time_next_asset_selection_minutes
    )
    self.wait_time_next_buy_selection_seconds = wait_time_next_buy_selection_seconds

# ************************************ Helper - Wait functions
def wait(period, params):
    wait_time = 0
    if params["mode"] == credentials.MODE_PROD:
        if period == "short":
            wait_time = get_wait_time_1(params)
        if period == "long":
            wait_time = get_wait_time(params)
        logger.debug("wait: {} PROD".format(wait_time))
        time.sleep(wait_time)
    else:
        if period == "short":
            wait_time = params["wait_time_next_buy_selection_seconds"]
        if period == "long":
            wait_time = params["wait_time_next_asset_selection_minutes"] * 60
        time.sleep(1)
        logger.debug("wait: {} TEST".format(wait_time))
    return wait_time

def get_wait_time(params):
    minute = datetime.now().minute
    wait_time = (
        params["wait_time_next_asset_selection_minutes"]
        - (minute % params["wait_time_next_asset_selection_minutes"])
    ) * 60
    return wait_time

def get_wait_time_1(params):
    seconds = datetime.now().second
    wait_time = params["wait_time_next_buy_selection_seconds"] - (
        seconds % params["wait_time_next_buy_selection_seconds"]
    )
    return wait_time

def wait_hours(hours, params):
    wait_time = hours * 60 * 60
    if params["mode"] == credentials.MODE_PROD:
        time.sleep(wait_time)
    return wait_time

def wait_minutes(minutes, params):
    wait_time = minutes * 60
    if params["mode"] == credentials.MODE_PROD:
        time.sleep(wait_time)
    return minutes * 60

def wait_seconds(seconds, params):
    if params["mode"] == credentials.MODE_PROD:
        time.sleep(seconds)
    return seconds



def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_time():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    logger.info("Current Time: {}".format(current_time))

# ************************************ Helper - Save data to File
def save_to_file(data, filename):
    data.to_csv(filename, header=True, index=None, sep=";", mode="w")

# ************************************ Helper - Read data from File
def read_from_file(filename):
    return pd.read_csv(filename, sep=";")

def plot(data):
    plt.figure(figsize=(14, 7))
    plt.plot(data["close"], label="close Price", color="black")
    plt.scatter(
        data.index,
        data["min"],
        label="Local Minima",
        color="green",
        marker="^",
        alpha=1,
    )
    plt.scatter(
        data.index,
        data["max"],
        label="Local Maxima",
        color="red",
        marker="v",
        alpha=1,
    )
    plt.plot(data.index, data["ema_9"], label="EMA 9", color="red", alpha=1)
    plt.plot(data.index, data["ema_20"], label="EMA 20", color="blue", alpha=1)
    minima = data.dropna(subset=["min"])
    maxima = data.dropna(subset=["max"])
    for i in range(len(minima) - 1):
        plt.plot(
            [minima.index[i], minima.index[i + 1]],
            [minima["min"].iloc[i], minima["min"].iloc[i + 1]],
            label="Support Line",
            color="green",
            linestyle="--",
        )

    for i in range(len(maxima) - 1):
        plt.plot(
            [maxima.index[i], maxima.index[i + 1]],
            [maxima["max"].iloc[i], maxima["max"].iloc[i + 1]],
            label="Resistance Line",
            color="red",
            linestyle="--",
        )

    plt.title("Stock Support and Resistance Levels")
    plt.show()

def write_to_db(
    market=None,
    market_factor=None,
    base_currency=None,
    selected_ticker=None,
    funding=None,
    major_move=None,
    increase_volume=None,
    buy_signal=None,
    close_to_maximum=None,
    is_buy=None,
    current_close=None,
    last_max=None,
    previous_max=None,
    vwap=None,
    macd=None,
    macd_signal=None,
    macd_diff=None,
    buy_order_id=None,
    sell_order_id=None,
):
    if major_move and len(major_move) > 0:
        major_move = ";".join(map(str, major_move))
    else:
        major_move = None
    if increase_volume and len(increase_volume) > 0:
        increase_volume = ";".join(map(str, increase_volume))
    else:
        increase_volume = None
    if buy_signal and len(buy_signal) > 0:
        buy_signal = ";".join(map(str, buy_signal))
    else:
        buy_signal = None
    database.insert_screener(
        get_time(),
        market,
        market_factor,
        base_currency,
        selected_ticker,
        funding,
        major_move,
        increase_volume,
        buy_signal,
        close_to_maximum,
        is_buy,
        current_close,
        last_max,
        previous_max,
        vwap,
        macd,
        macd_signal,
        macd_diff,
        buy_order_id,
        sell_order_id,
    )

def write_trading_info_to_db(asset, side, price, market_movement):
    database.insert_trading_info_table(
        get_time(), asset, side, price, market_movement
    )

def write_balance_to_db(write_to_db, base_currency, balance):
    if write_to_db: database.insert_balance(get_time(), base_currency, balance)

def write_to_db_activity_tracker(write_to_db, run_id, mode, timestamp, activity, asset, size, price):
    if write_to_db: database.insert_activity_tracker_table(run_id, mode, timestamp, activity, asset, size, price)

def get_next_sequence(write_to_db):
    return database.get_next_sequence() if write_to_db else None

def read_last_balance_from_db():
    return database.execute_select(
        "SELECT balance FROM balance WHERE timestamp >= CURDATE() - INTERVAL 100 DAY AND timestamp < CURDATE() order by timestamp desc limit 1"
    )


def set_logger(type):
    # ************************************ Logging
    logger = logging.getLogger("screener")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(filename)25s %(funcName)25s - %(message)s")
    handler = logging.FileHandler(
        filename="screener.log",
        mode="w",
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    if type == "INFO":
        logger.setLevel(logging.INFO)
    elif type == "DEBUG":
        logger.setLevel(logging.DEBUG)

    return logger


def get_exchange(params):

    exchange_class = globals()[params["exchange"]]
    exchange = exchange_class(params["exchange_name"], params["starting_balance"])
    if params["observation_start"] and params["observation_stop"]:
        exchange.set_observation_start(datetime.strptime(params["observation_start"], "%Y-%m-%d %H:%M"))
        exchange.set_observation_stop(datetime.strptime(params["observation_stop"], "%Y-%m-%d %H:%M"))
    return exchange

def read_arguments():
    parser = argparse.ArgumentParser(description="Crypto Trader application")
    parser.add_argument("exchange", type=str, help="Exchange")
    parser.add_argument("exchange_name", type=str, help="Exchange Name")
    parser.add_argument(
        "--ignore_profit_loss",
        type=bool,
        default=False,
        required=True,
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--use_db", type=bool, default=False, action=argparse.BooleanOptionalAction
    )
    parser.add_argument("--sell_end_of_day", type=bool, required=True, default=True, action=argparse.BooleanOptionalAction)
    parser.add_argument("--write_to_db", type=bool, required=True, default=True, action=argparse.BooleanOptionalAction)
    parser.add_argument("--mode", type=int, default=1)
    parser.add_argument("--selected", type=str, default=None)
    parser.add_argument("--observation_start", default=None)  # 2024-11-10 12:00
    parser.add_argument("--observation_stop", default=None)  # 2024-11-10 12:00
    parser.add_argument("--logging", default="INFO")
    parser.add_argument("--amount_coins", type=int, required=True, default=1000)
    parser.add_argument("--take_profit_in_percent", required=True, type=float, default=3)
    parser.add_argument("--max_loss_in_percent", required=True, type=float, default=3.5)
    parser.add_argument("--starting_balance", type=float, default=None)
    parser.add_argument("--base_currency", default= "USDT")
    parser.add_argument("--ignored_coins", default = ["USDT", "USD", "CRO", "PAXG", "BGB"])
    parser.add_argument("--wait_time_next_asset_selection_minutes", type=int, default = 15)
    parser.add_argument("--wait_time_next_buy_selection_seconds", type=int, default = 60)
    parser.add_argument("--funding_ratio_in_percent", type=float, default=90)
    parser.add_argument("--buy_attempts_nr", type=int, default = 30)
    parser.add_argument("--move_increase_threshold", type=float, default = 0.003)
    parser.add_argument("--move_increase_period_threshold", type=float, default = 1)
    parser.add_argument("--volume_increase_threshold", type=float, default = 0.5)
    parser.add_argument("--difference_to_maximum_max", type=float, default = -2)
    parser.add_argument("--valid_position_amount", type=int, default = 2)
    parser.add_argument(
        "--acknowledge_profit_loss", type=bool, default=True, action=argparse.BooleanOptionalAction
    )
    parser.add_argument("--daily_pnl_target_in_percent", type=float, default = None)
    parser.add_argument("--daily_pnl_max_loss_in_percent", type=float, default = None)
    parser.add_argument("--minimum_funding", type=float, default = 10)
    parser.add_argument("--winning_buy_nr", type=int, default = 2)
    parser.add_argument(
        "--acknowledge_business_hours", type=bool, default=True, action=argparse.BooleanOptionalAction
    )
    parser.add_argument("--start_trading_at", type=int, default = 1)
    parser.add_argument("--stop_trading_at", type=int, default = 23)
    parser.add_argument("--stop_buying_at", type=int, default = 21)
    
    args = parser.parse_args()

    parameters = vars(args)
    parameters['start_trading_at'] = ti(hour=parameters['start_trading_at'])
    parameters['stop_trading_at'] = ti(hour=parameters['stop_trading_at'])
    parameters['stop_buying_at'] = ti(hour=parameters['stop_buying_at'])

    logger.info("Parameters: {}".format(parameters))

    return parameters

