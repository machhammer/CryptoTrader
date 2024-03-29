import exchanges
import threading
import pandas as pd
import logging
import requests
import queue
import time
from datetime import datetime
from TraderClass import TraderClass
import yfinance as yf
from models import V2

import warnings

yf.pdr_override()
warnings.filterwarnings("ignore")

STOP_TRADING_EMERGENCY_THRESHOLD = -5

commission = 0.075 / 100
frequency = 1800
mood_treshold = 0.0
pos_neg_threshold = -4
timeframe = "30m"
base_currency = "USDT"
number_of_attempts_for_random_coins_wo_position = 24

coins_amount = 4
fix_coins = ["SOL"]

ignore_coins = ["USDT", "USD", "CRO", "PAXG"]
coins = {}

exchange = exchanges.cryptocom()

logger = logging.getLogger("manager")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler = logging.FileHandler(
    filename="trading-manager-v4.log",
    mode="a",
    encoding="utf-8",
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_my_coins(all_coins):
    counter = 0
    current_coins = exchange.fetch_balance()["free"]
    my_coins = []
    for check_coin in current_coins:
        if check_coin not in ignore_coins:
            current_balance = exchange.fetch_balance()[check_coin]["free"]
            current_price = exchange.fetch_ticker(check_coin + "/USDT")["last"]
            if current_balance * current_price > 5:
                my_coins.append(check_coin)

    temp_coins = {}
    for fix in fix_coins:
        if counter < coins_amount:
            temp_coins[fix] = 1 / coins_amount
            counter = counter + 1
    for flex in my_coins:
        if not flex in temp_coins:
            if counter < coins_amount:
                temp_coins[flex] = 1 / coins_amount
                counter = counter + 1

    for i in range(0, coins_amount - len(temp_coins)):
        if counter < coins_amount:
            new_coin = identify_candidate(all_coins, temp_coins)
            temp_coins[new_coin] = 1 / coins_amount
            logger.info("NEW temp coins: {}".format(temp_coins))
            counter = counter + 1

    return temp_coins


def fetch_coins():

    tickers = exchange.fetch_tickers()
    df = pd.DataFrame(tickers)
    df = df.T
    df = df[df["symbol"].str.contains("/USDT")]

    return df

def fetch_fear_and_greed():
    url = "https://api.alternative.me/fng/"
    response = requests.get(url)
    data = response.json()
    fear_greed_index = data['data'][0]['value']
    return fear_greed_index

def fetch_data(df):
    global coins
    amount_looser = 50
    amount_winner = 50
    pos_neg = 0
    market_mood = 1

    try:
        df = fetch_coins()
        fear_and_greed = fetch_fear_and_greed()

        looser = df[df["percentage"] <= 0]
        amount_looser = len(looser)
        winner = df[df["percentage"] > 0]
        amount_winner = len(winner)

        pos_neg = df["percentage"].sum()
        pos_neg_median = df["percentage"].median()
        market_mood = amount_winner / amount_looser

    except Exception as e:
        logger.error(e)
        logger.error("Setting Default Values.")

    return {
        "looser": amount_looser,
        "winner": amount_winner,
        "pos_neg": round(pos_neg, 2),
        "pos_neg_median": round(pos_neg_median * 100, 2),
        "fear_and_greed": fear_and_greed,
        "mood": round(market_mood, 2),
        "coins": coins,
    }

def get_current_balance():
    current_assets = exchange.fetch_balance()["free"]

    balance = 0
    for asset in current_assets:
        if not asset =="USD":
            price = exchange.fetch_ticker(asset + "/USD")["last"] * current_assets[asset]
        else:
            price = current_assets['USD']        
        balance = balance + price
    return balance


def identify_candidate(all_coins, selected_coins):
    all_coins = all_coins.sample(frac=1)
    found_coin = None
    random = True
    logger.info("selected coins: {}".format(selected_coins.keys()))
    for i in range(len(all_coins)):
        try:
            found_coin = all_coins.iloc[i, 0].replace("/USDT", "-USD")
            data = pd.DataFrame(yf.download(found_coin, period="5d", interval="1h", progress=False))
            data = data.rename(columns={"Close": "close", "High": "high", "Low": "low"})
            data = V2.apply_indicators(data)
            if len(data) > 0:
                buy_sell_decision = V2.live_trading_model(dataset=data, logger=None, highest_price=0, mood=0.2, mood_threshold=mood_treshold, pos_neg=0, pos_neg_median=0, pos_neg_threshold=-1)
                if buy_sell_decision == 1:
                    found_coin = found_coin.replace("-USD", "")
                    logger.info(
                        "found_coin {} in selected_coins {}: {}".format(
                            found_coin, selected_coins.keys(), found_coin in selected_coins
                        )
                    )
                    if not (found_coin in selected_coins) and not (
                        found_coin in ignore_coins
                    ):
                        random = False
                        break
        except Exception as e:
            print(e)
    if found_coin:
        found_coin = found_coin.replace("-USD", "")
    logger.info("Candidate found: {} - random: {}".format(found_coin, random))

    return found_coin


def check_candidate():

    data = pd.DataFrame(yf.download("NEO-USD", period="5d", interval="60m"))
    data = data.rename(columns={"Close": "close", "High": "high", "Low": "low"})
    data = V2.apply_indicators(data)

    print(data)

    buy_sell_decision = V2.live_trading_model(datetime=data, logger=None, highest_price=0, mood=0.2, mood_threshold=mood_treshold, pos_neg=0, pos_neg_median=0, pos_neg_threshold=-1)

    print(buy_sell_decision)


def add_trader(coin):
    event_t = threading.Event()
    output_t = queue.Queue()
    input_t = queue.Queue()

    trader = TraderClass(
        event=event_t,
        input=output_t,
        output=input_t,
        coin=coin,
        frequency=frequency,
        timeframe=timeframe,
        exchange=exchange,
        mood_threshold=mood_treshold,
        pos_neg_threshold=pos_neg_threshold
    )

    trader.start()

    return [trader, event_t, output_t, input_t]


def run():
    global coins
    DAILY_STARTING_BALANCE = 0
    CURRENT_BALANCE = 0
    STOP_TRADING_FOR_TODAY = False

    traders = {}
    logger.info("")
    logger.info("Start Crypto Trader!")
    all_coins = fetch_coins()
    coins = get_my_coins(all_coins)
    logger.info("Trade with coins: {}".format(coins))
    for coin in coins:
        logger.info(" *** {}".format(coin))
        traders[coin] = add_trader(coin)
    print("Crypto Trader Running!")
    logger.info("Crypto Trader Running!")


    first_run = True
    has_random_coins_wo_position = False
    number_of_current_attempts_for_random_coins = 1
    while True:
        if not first_run:
            all_coins = fetch_coins()
        else:
            first_run = False
    
        if (datetime.now().minute >= 0 and datetime.now().minute < 30 and datetime.now().hour == 1):
            logger.info("Reset Daily Balance.")
            STOP_TRADING_FOR_TODAY = False  
            DAILY_STARTING_BALANCE = 0

        CURRENT_BALANCE = get_current_balance()
        if DAILY_STARTING_BALANCE == 0:
            DAILY_STARTING_BALANCE = CURRENT_BALANCE
        daily_return = (CURRENT_BALANCE - DAILY_STARTING_BALANCE) * 100 / DAILY_STARTING_BALANCE

        if not STOP_TRADING_FOR_TODAY:
            if daily_return < STOP_TRADING_EMERGENCY_THRESHOLD:
                STOP_TRADING_FOR_TODAY = True
            else:
                STOP_TRADING_FOR_TODAY = False
        
        logger.info("Starting Balance: {:.2f}, Current Balance: {:.2f}".format(DAILY_STARTING_BALANCE, CURRENT_BALANCE))
        logger.info("Daily Result: {:.2f}, Stop Trading: {:.2f}".format(daily_return, STOP_TRADING_FOR_TODAY))   
                
        params = fetch_data(all_coins)
        logger.info("Parameters: {}".format(params))

        params['STOP_TRADING_FOR_TODAY'] = STOP_TRADING_FOR_TODAY

        traders_copy = traders.copy()
        for trader in traders:
            is_alive = traders[trader][0].is_alive()
            logger.info("Working with Trader: {}".format(trader))
            if is_alive:
                logger.info("--- Trader: {} is alive".format(trader))
                traders[trader][2].put(params)
                values = traders[trader][3].get()
                now = datetime.now()
                logger.info(
                    "--- {}, Coin: {}, Success: {}, has Position: {}".format(
                        now.strftime("%Y-%m-%d %H:%M:%S"), trader, values[0], values[1]
                    )
                )
                if values[0] == False:
                    traders[trader][1].set()
                    logger.info(
                        "{} - Error in Trader: {} - Deactivating!".format(
                            now.strftime("%Y-%m-%d %H:%M:%S"), trader
                        )
                    )
                if (
                    values[1] == False
                    and params["mood"] > mood_treshold
                    and trader not in fix_coins
                ):
                    if number_of_current_attempts_for_random_coins >= number_of_attempts_for_random_coins_wo_position:
                        new_trader = identify_candidate(all_coins, coins)
                        if new_trader:
                            traders[trader][1].set()
                            logger.info(
                                "{} - No Position for {} - Deactivating and try a different Coin! ".format(
                                    now.strftime("%Y-%m-%d %H:%M:%S"), trader
                                )
                            )
                            time.sleep(5)
                            traders[trader][0] = None
                            traders[trader][1] = None
                            traders[trader][2] = None

                            del coins[trader]
                            del traders_copy[trader]
                            traders_copy[new_trader] = add_trader(new_trader)
                            coins[new_trader] = 1 / coins_amount
                            params["coins"] = coins
                            time.sleep(5)
                            is_alive = traders_copy[new_trader][0].is_alive()
                            if is_alive:
                                traders_copy[new_trader][2].put(params)
                                time.sleep(5)
                                logger.info(
                                    "{} --- New coin {} started successfull: {}".format(
                                        now.strftime("%Y-%m-%d %H:%M:%S"),
                                        new_trader,
                                        is_alive,
                                    )
                                )
                                values = traders_copy[new_trader][3].get()
                                logger.info(
                                    "{} --- Status: {}, Has Position: {}".format(
                                        now.strftime("%Y-%m-%d %H:%M:%S"),
                                        values[0],
                                        values[1],
                                    )
                                )
                                if values[1] == False:
                                    has_random_coins_wo_position = True
                    else:
                        has_random_coins_wo_position = True

            else:
                logger.error("--- Error. Trader not alive!")

        if number_of_current_attempts_for_random_coins >= number_of_attempts_for_random_coins_wo_position:
            logger.info("Reset number_of_current_attempts_for_random_coins = 1")
            number_of_current_attempts_for_random_coins = 1

        if has_random_coins_wo_position:
            number_of_current_attempts_for_random_coins = number_of_current_attempts_for_random_coins + 1
            logger.info("Increase number_of_current_attempts_for_random_coins: {}".format(number_of_current_attempts_for_random_coins))
            has_random_coins_wo_position = False

        traders = traders_copy.copy()

        m1 = 30
        m2 = 60
        wait_time = datetime.now().minute
        if wait_time < m1:
            wait_time = (m1 - wait_time + 0.2) * 60
        else:
            if wait_time < m2:
                wait_time = (m2 - wait_time + 0.2) * 60




        logger.info("Waiting Time in Seconds: {}".format(wait_time))
        time.sleep(wait_time)


if __name__ == "__main__":
    run()
