from os import write
import numpy as np
import pandas as pd
import random
import math
import logging
import argparse
from Exchange import Exchange, Offline_Exchange
from datetime import time, datetime, timedelta
from tqdm import tqdm
from ta.trend import AroonIndicator, EMAIndicator, MACD
from ta.volume import VolumeWeightedAveragePrice
from scipy.signal import argrelextrema
from Helper import Helper


# ************************************ Logging
logger = logging.getLogger("screener")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler = logging.FileHandler(
    filename="screener.log",
    mode="w",
    encoding="utf-8",
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


# ************************************ Confiuguration

base_currency = "USDT"
ignored_coins = [base_currency, "USDT", "USD", "CRO", "PAXG", "BGB"]
wait_time_next_asset_selection_minutes = 15
wait_time_next_buy_selection_seconds = 60

funding_ratio_in_percent = 90

buy_attempts_nr = 30
move_increase_threshold = 0.003
move_increase_period_threshold = 1
volume_increase_threshold = 0.5
difference_to_maximum_max = -2
valid_position_amount = 2
daily_pnl_target_in_percent = 999999999999999999
daily_pnl_max_loss_in_percent = -999999999999999999

# difference_to_resistance_min = 0.01
minimum_funding = 10
winning_buy_nr = 2

start_trading_at = time(hour=1)
stop_trading_at = time(hour=23)
stop_buying_at = time(hour=21)


helper = Helper(
    logger, wait_time_next_asset_selection_minutes, wait_time_next_buy_selection_seconds
)


# ************************************ Get Ticker Data
def get_data(exchange, ticker, interval, limit):
    bars = exchange.fetch_ohlcv(ticker, interval, limit=limit)
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data


# ************************************ Balance of base currency
def get_base_currency_balance(exchange):
    usd = exchange.fetch_balance()[base_currency]["total"]
    logger.debug("Base currency balance: {}".format(usd))
    return usd


# ************************************ Assets with existing balance
def find_asset_with_balance(exchange):
    asset_with_balance = None
    price = None
    current_assets = exchange.fetch_balance()["total"]
    for asset in current_assets:
        if not asset in ignored_coins:
            found_price = exchange.fetch_ticker(asset + "/" + base_currency)["last"]
            balance = exchange.fetch_balance()[asset]["total"]
            if (balance * found_price) > valid_position_amount:
                logger.info("Found asset with balance: {}".format(asset))
                asset_with_balance = asset + "/" + base_currency
                price = found_price
    if asset_with_balance:
        logger.debug("Asset with balance: ".format(asset_with_balance))
    else:
        logger.debug("No asset with balance")
    return asset_with_balance, price


# ************************************ Balance for specific ticker
def get_Ticker_balance(exchange, ticker):
    ticker = ticker.replace("/" + base_currency, "")
    ticker_balance = 0
    try:
        ticker_balance = exchange.fetch_balance()[ticker]["total"]
    except:
        logger.debug("   Ticker not in Wallet")
    logger.debug("   Ticker Balance: {}".format(ticker_balance))
    return ticker_balance


# ************************************ check for valid position
def still_has_postion(size, price):
    value = (size * price) > valid_position_amount
    logger.debug("   still has position: {}".format(value))
    return value


# ************************************ get All Tickers
def get_tickers(exchange, amount_coins):
    tickers = exchange.fetch_tickers()
    tickers = pd.DataFrame(tickers)
    tickers = tickers.T
    tickers = tickers[tickers["symbol"].str.endswith("/" + base_currency)].head(
        amount_coins
    )
    return tickers


def get_tickers_as_list(tickers):
    tickers = tickers["symbol"].to_list()
    random.shuffle(tickers)
    return tickers


# ************************************ Funding based on market movment
def get_funding(usd):
    """ fund_ratio = funding_ratio_in_percent / 100
    funding = usd * fund_ratio
    if funding < minimum_funding:
        funding = minimum_funding
    logger.debug(
        "{} {} * Market Factor {} = Funding {}".format(
            base_currency, usd, fund_ratio, funding
        )
    ) """
    return usd - minimum_funding


# ************************************ get precision for specific ticker
def get_precision(exchange, ticker):
    markets = exchange.exchange.load_markets()
    amount = float((markets[ticker]["precision"]["amount"]))
    price = float((markets[ticker]["precision"]["price"]))
    logger.debug(
        "   get_precision - ticker: {}, amount: {}, price: {}".format(
            ticker, amount, price
        )
    )
    return amount, price


# ************************************ get convert price fitting to precision
def convert_to_precision(value, precision):
    rounded = round(math.floor(value / precision) * precision, 10)
    logger.debug(
        "   convert_to_precision - size: {}, precision: {}, value: {}".format(
            value, precision, rounded
        )
    )
    return rounded


# ************************************ add Indicators
def add_min_max(data):
    order = 3
    data["min"] = data.iloc[
        argrelextrema(data["close"].values, np.less_equal, order=order)[0]
    ]["close"]
    data["max"] = data.iloc[
        argrelextrema(data["close"].values, np.greater_equal, order=order)[0]
    ]["close"]
    return data


def add_aroon(data):
    indicator_AROON = AroonIndicator(high=data["high"], low=data["low"], window=14)
    data["aroon_up"] = indicator_AROON.aroon_up()
    data["aroon_down"] = indicator_AROON.aroon_down()
    return data


def add_vwap(data):
    indicator_vwap = VolumeWeightedAveragePrice(
        high=data["high"], low=data["low"], close=data["close"], volume=data["volume"]
    )
    data["vwap"] = indicator_vwap.volume_weighted_average_price()
    return data


def add_macd(data):
    indicator_macd = MACD(close=data["close"])
    data["macd"] = indicator_macd.macd()
    data["macd_diff"] = indicator_macd.macd_diff()
    data["macd_signal"] = indicator_macd.macd_signal()
    return data


def add_ema(data):
    indicator_EMA_9 = EMAIndicator(close=data["close"], window=9)
    data["ema_9"] = indicator_EMA_9.ema_indicator()
    indicator_EMA_20 = EMAIndicator(close=data["close"], window=20)
    data["ema_20"] = indicator_EMA_20.ema_indicator()
    return data


# ************************************ get Candidate Functions
def get_candidate(exchange, amount_coins):
    logger.debug("1. ******** Check for New Candidate ********")
    tickers = get_tickers(exchange, amount_coins)
    tickers = get_tickers_as_list(tickers)
    major_move = get_ticker_with_bigger_moves(exchange, tickers)
    #expected_results = get_top_ticker_expected_results(exchange, major_move)
    #logger.debug("   expected_results: {}".format(expected_results))
    close_to_high = get_close_to_high(exchange, major_move)
    logger.debug("   close_to_high: {}".format(close_to_high))
    relevant_tickers = close_to_high
    logger.debug("   relevant_tickers: {}".format(relevant_tickers))
    #increased_volume = get_ticker_with_increased_volume(exchange, relevant_tickers)
    buy_signals = get_ticker_with_aroon_buy_signals(exchange, relevant_tickers)
    selected_Ticker = get_lowest_difference_to_maximum(exchange, buy_signals)
    selected_Ticker = get_with_sufficient_variance(exchange, selected_Ticker)
    if selected_Ticker:
        logger.info("   Selected: {}".format(selected_Ticker))
    return selected_Ticker


def get_ticker_with_bigger_moves(exchange, tickers):
    limit = 4
    bigger_moves = []
    iterations = len(tickers)
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit)
        # data["change"] = ((data["close"] - data["open"]) / data["open"]) * 100
        if not data.empty:
            data["change"] = data["close"].pct_change()
            data["is_change_relevant"] = data["change"] >= move_increase_threshold
            ticker_check = {}
            ticker_check["ticker"] = ticker
            ticker_check["change"] = data["change"].to_list()
            ticker_check["relevant"] = data["is_change_relevant"].to_list()
            ticker_check["data"] = data
            if ticker_check["relevant"].count(True) >= move_increase_period_threshold:
                bigger_moves.append(ticker)
        try:
            next(progress_bar)
        except Exception as e:
            print(e)
    logger.debug("   ticker with bigger moves: {}".format(len(bigger_moves)))
    return bigger_moves


def get_ticker_with_aroon_buy_signals(exchange, tickers):
    buy_signals = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit=20)
        data = add_aroon(data)
        if 100 in data.tail(3)["aroon_up"].to_list():
            buy_signals.append(ticker)
    logger.debug("   ticker_with_aroon_buy_signals: {}".format(len(buy_signals)))
    return buy_signals


def get_ticker_with_increased_volume(exchange, tickers):
    increased_volumes = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "15m", limit=28)
        last_mean = data.head(24)["volume"].mean()
        current_mean = data.tail(4)["volume"].mean()
        if (current_mean / last_mean) >= volume_increase_threshold:
            increased_volumes.append(ticker)
    logger.debug("   ticker_with_increased_volume: {}".format(len(increased_volumes)))
    return increased_volumes


def get_top_ticker_expected_results(exchange, tickers):
    accepted_expected_results = {}
    for ticker in tickers:
        data = get_data(exchange, ticker, "5m", limit=120)
        data["pct_change"] = data["close"].pct_change(periods=3)
        min = data["pct_change"].min()
        if min > -0.005:
            accepted_expected_results[ticker] = min
    df = pd.DataFrame(accepted_expected_results.items(), columns=["ticker", "min"])
    df = df.sort_values(by="min")
    df = df.tail(5)["ticker"].to_list()
    logger.debug("   ticker_with_expected_results: {}".format(len(df)))
    return df


def get_close_to_high(exchange, tickers):
    close_to_high = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1h", limit=48)
        max = data["close"].max()
        if data.iloc[-1, 4] >= max:
            close_to_high.append(ticker)
    logger.debug("   ticker_close_to_high: {}".format(len(close_to_high)))
    return close_to_high


def get_lowest_difference_to_maximum(exchange, tickers):
    lowest_difference_to_maximum = None
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit=90)
        data = add_min_max(data)
        local_max = data["max"].max()
        current_close = data.iloc[-1, 4]
        ratio = ((current_close - local_max) * 100) / local_max
        if ratio > difference_to_maximum_max:
            lowest_difference_to_maximum = ticker
    logger.debug(
        "   lowest_difference_to_maximum: {}".format(lowest_difference_to_maximum)
    )
    return lowest_difference_to_maximum


def get_with_sufficient_variance(exchange, ticker):
    duplicate_data = 99
    if ticker:
        data = get_data(exchange, ticker, "1m", limit=5)
        data = data.duplicated(subset=["close"])
        data = data.loc[lambda x: x == True]
        duplicate_data = len(data)
        logger.debug("   variance: {}".format(duplicate_data))
    if duplicate_data > 0:
        return None
    else:
        return ticker


# ************************************ BUY Functions
def is_buy_decision(exchange, ticker, attempt):
    logger.debug(
        "2. ******** Check for Buy Decision, Ticker: {}, #{}".format(ticker, attempt)
    )
    data = get_data(exchange, ticker, "1m", limit=180)
    data = add_min_max(data)
    data = add_aroon(data)
    data = add_vwap(data)
    data = add_macd(data)
    max_column = data["max"].dropna().drop_duplicates().sort_values()
    current_close = data.iloc[-1, 4]
    last_max = (max_column.values)[-1]
    previous_max = (max_column.values)[-2]

    is_buy = False

    if current_close < last_max:
        is_buy = False
    elif current_close >= last_max and current_close > previous_max:
        is_buy = True
    else:
        is_buy = False
    logger.debug("   Resistance check - buy: {}".format(is_buy))

    aroon_up = data.iloc[-1, 8]
    if is_buy:
        if isinstance(aroon_up, float):
            if aroon_up > 90:
                is_buy = True
            else:
                is_buy = False
        logger.debug("   Aroon check - buy: {}".format(is_buy))

    vwap = data.iloc[-1, 10]
    if is_buy:
        if isinstance(current_close, float) and isinstance(vwap, float):
            if vwap < current_close:
                is_buy = True
            else:
                is_buy = False
        logger.debug("   vwap check - buy: {}".format(is_buy))

    macd = data.iloc[-1, 11]
    macd_diff = data.iloc[-1, 12]
    macd_signal = data.iloc[-1, 13]
    if is_buy:
        if (
            isinstance(macd, float)
            and isinstance(macd_signal, float)
            and isinstance(macd_diff, float)
        ):
            if macd > macd_signal and macd_diff > 0:
                is_buy = True
            else:
                is_buy = False
        logger.debug("   macd check - buy: {}".format(is_buy))

    return is_buy, current_close


def buy_order(exchange, ticker, price, funding):
    logger.debug(
        "3. ******** Buy Decision, Ticker: {}, Price: {}, Funding: {}".format(
            ticker, price, funding
        )
    )
    amount_precision, price_precision = get_precision(exchange, ticker)
    price = convert_to_precision(price, price_precision)
    size = convert_to_precision(funding / price, amount_precision)
    order = exchange.create_buy_order(ticker, size, price)
    logger.info("   buy: {}, Time: {}, size: {}, price: {}".format(ticker, exchange.get_observation_start(), size, price))
    return order, price, size


# ************************************ SELL Functions
def set_sell_trigger(
    exchange, isInitial, ticker, size, highest_value, max_loss, previous_resistance
):
    logger.debug(
        "4. ********  Check Sell - ticker: {}, isInitial: {}, size: {}, highest_value: {}, max_loss: {}".format(
            ticker, isInitial, size, highest_value, max_loss
        )
    )
    logger.debug("set sell previous resistance: {}".format(previous_resistance))
    data = get_data(exchange, ticker, "1m", limit=720)
    data = add_min_max(data)
    min_column = data["min"].dropna().drop_duplicates().sort_values()
    current_value = data.iloc[-1, 4]
    order = None
    resistance = None
    logger.debug(
        "   highest value: {}, current value: {}".format(highest_value, current_value)
    )
    if isInitial or (highest_value < current_value):
        highest_value = current_value
        logger.debug("   new high: {}".format(highest_value))
        resistance_found = False
        row = -1
        while not resistance_found:
            if row >= (-1) * len(min_column):
                resistance = min_column.iloc[row]
                diff = (current_value - resistance) / current_value
                if diff >= max_loss:
                    logger.debug(
                        "previous resistance: {}, resistance: {}".format(
                            previous_resistance, resistance
                        )
                    )
                    if resistance > previous_resistance:
                        logger.debug("   set new sell triger: {}".format(resistance))
                        order = sell_order(exchange, ticker, current_value, size, resistance)
                    resistance_found = True
                else:
                    row -= 1
            else:
                resistance = min_column.iloc[(-1) * len(min_column)]
                logger.debug(
                    "previous resistance: {}, resistance: {}".format(
                        previous_resistance, resistance
                    )
                )
                if resistance > previous_resistance:
                    logger.debug("   set new sell triger: {}".format(resistance))
                    order = sell_order(exchange, ticker, current_value, size, resistance)
                resistance_found = True
    else:
        logger.debug("   No new sell trigger")
    return highest_value, current_value, order, resistance


def sell_order_take_profit(exchange, ticker, price, size, takeProfitPrice):
    amount_precision, price_precision = get_precision(exchange, ticker)
    takeProfitPrice = convert_to_precision(takeProfitPrice, price_precision)
    size = convert_to_precision(size, amount_precision)
    logger.info(
        "   put sell order take profit- Ticker: {}, Time: {}, Size: {}, Price: {}, takeProfitPrice: {}".format(
            ticker, exchange.get_observation_start(), size, price, takeProfitPrice
        )
    )
    order = exchange.create_take_profit_order(ticker, size, takeProfitPrice)
    logger.debug("   sell TP order id : {}".format(order))


def sell_order(exchange, ticker, price, size, stopLossPrice):
    # exchange.cancel_orders(ticker)
    amount_precision, price_precision = get_precision(exchange, ticker)
    stopLossPrice = convert_to_precision(stopLossPrice, price_precision)
    size = convert_to_precision(size, amount_precision)
    logger.info(
        "   put sell order - Ticker: {}, Time: {}, Size: {}, Price: {}, stopLossPrice: {}".format(
            ticker, exchange.get_observation_start(), size, price, stopLossPrice
        )
    )
    order = exchange.create_stop_loss_order(ticker, size, stopLossPrice)
    logger.debug("   sell order id : {}".format(order))
    return order


def sell_now(exchange, ticker, size):
    # exchange.cancel_orders(ticker)
    amount_precision, _ = get_precision(exchange, ticker)
    size = convert_to_precision(size, amount_precision)
    order = exchange.create_sell_order(ticker, size)
    logger.info("   sell inmediately - Ticker: {}".format(ticker))
    return order


def cancel_order(exchange, ticker, orderId):
    order = exchange.cancel_order(ticker, orderId)
    logger.info("   cancel Order: {}".format(order))
    logger.info("   cancel Order - Ticker: {}, Order Id: {}".format(ticker, orderId))


def daily_pnl_target_achieved(current_balance, last_balance):
    current_pnl = ((current_balance - last_balance) * 100) / last_balance
    logger.info(
        "   last_balance: {}, current_balance: {}, current pnl: {}".format(
            last_balance, current_balance, current_pnl
        )
    )
    if current_pnl >= daily_pnl_target_in_percent:
        return True
    else:
        return False


def daily_max_loss_reached(current_balance, last_balance):
    current_pnl = ((current_balance - last_balance) * 100) / last_balance
    if current_pnl <= daily_pnl_max_loss_in_percent:
        return True
    else:
        return False


def observation_date_offset(exchange, offset_in_seconds):
    observation_start = exchange.get_observation_start()
    if observation_start:
        observation_start = observation_start + timedelta(
            minutes=offset_in_seconds / 60
        )
        exchange.set_observation_start(observation_start)
        logger.debug("Observation Time: {}".format(exchange.get_observation_start()))
    
def observation_stop_check(exchange):
    return True if exchange.get_observation_stop and exchange.get_observation_stop() >= exchange.get_observation_start() else False


def run_trader(
    exchange,
    mode,
    amount_coins,
    take_profit_in_percent,
    max_loss_in_percent,
    ignore_profit_loss=False,
    selected=None,
    write_to_db=True,
    starting_balance=None,
    sell_end_of_day=True
):

    
    running = True
    in_business = False

    current_price = None
    size = None
    if not selected is None:
        selected = selected + "/" + base_currency
    selected_new_asset = selected
    existing_asset = None
    previous_asset = None
    start_price = None
    end_price = None
    winning_buy_count = 0
    base_currency_balance = 0
    pnl_achieved = False
    max_loss_reached = False
    existing_asset, current_price = find_asset_with_balance(exchange)

    run_id = helper.get_next_sequence(write_to_db)

    while running:
        if helper.in_business_hours(
            start_trading_at, stop_trading_at, exchange.get_observation_start(), exchange.get_observation_stop()
        ) and helper.in_buying_period(stop_buying_at, exchange.get_observation_start()):
            in_business = True
            if not existing_asset:
                base_currency_balance = get_base_currency_balance(exchange)
                last_balance = starting_balance if not starting_balance is None else helper.read_last_balacne_from_db().iloc[0, 0]
                pnl_achieved = daily_pnl_target_achieved(base_currency_balance, last_balance)
                max_loss_reached = daily_max_loss_reached(base_currency_balance, last_balance)

            if (not pnl_achieved and not max_loss_reached) or not ignore_profit_loss:
                if not start_price is None and not end_price is None:
                    if (
                        isinstance(start_price, float)
                        and isinstance(end_price, float)
                        and start_price < end_price
                    ):
                        winning_buy_count += 1
                        if winning_buy_count <= winning_buy_nr:
                            selected_new_asset = previous_asset
                            logger.info("Sold with proft #{}".format(winning_buy_count))
                        else:
                            winning_buy_count = 0
                            selected_new_asset = None
                        wait_time = helper.wait_minutes(5)
                        observation_date_offset(exchange, wait_time)
                    if (
                        isinstance(start_price, float)
                        and isinstance(end_price, float)
                        and start_price >= end_price
                    ):
                        selected_new_asset = None
                        existing_asset = None
                        winning_buy_count = 0
                        logger.info("Sold with loss. Waiting 1 hour!")
                        wait_time = helper.wait_hours(1)
                        observation_date_offset(exchange, wait_time)
                    previous_asset = None
                    start_price = None
                    end_price = None
                else:
                    if not existing_asset and not selected_new_asset:
                        selected_new_asset = get_candidate(exchange, amount_coins)
                        if selected_new_asset: helper.write_to_db_activity_tracker(write_to_db, run_id, exchange.get_mode(), exchange.get_timestamp(), "selected", selected_new_asset, 0, 0)
                        buy_decision = True

                if selected_new_asset or existing_asset:
                    buy_attempts = 1
                    # observe selected Ticker
                    buy_decision = False
                    while (
                        not buy_decision
                        and buy_attempts <= buy_attempts_nr
                        and not existing_asset
                    ):
                        is_buy, current_price = is_buy_decision(
                            exchange, selected_new_asset, buy_attempts
                        )
                        if not is_buy:
                            buy_attempts += 1
                            wait_time = helper.wait("short", mode)
                            observation_date_offset(exchange, wait_time)
                        else:
                            buy_decision = True
                        if not get_lowest_difference_to_maximum(
                            exchange, [selected_new_asset]
                        ):
                            buy_attempts = buy_attempts_nr + 1
    

                    if buy_decision or existing_asset:

                        adjust_sell_trigger = True

                        # buy sleected Ticker
                        if not existing_asset:
                            funding = get_funding(base_currency_balance)
                            try:
                                # BUY Order
                                buy_order(
                                    exchange, selected_new_asset, current_price, funding
                                )
                                helper.wait_seconds(5)
                                start_price = current_price
                                size = get_Ticker_balance(exchange, selected_new_asset)
                                helper.write_to_db_activity_tracker(write_to_db, run_id, exchange.get_mode(), exchange.get_timestamp(), "buy", selected_new_asset, size, current_price)
                                # Take Profit Order
                                if isinstance(current_price, float):
                                    take_profit_price = current_price * (
                                        1 + (take_profit_in_percent / 100)
                                    )
                                    sell_order_take_profit(
                                        exchange,
                                        selected_new_asset,
                                        current_price,
                                        size,
                                        take_profit_price,
                                    )
                                    helper.write_to_db_activity_tracker(write_to_db, run_id, exchange.get_mode(), exchange.get_timestamp(), "take profit order", selected_new_asset, size, take_profit_price)

                                existing_asset = selected_new_asset
                            except Exception as e:
                                adjust_sell_trigger = False
                                logger.info("Error buying: {}".format(e))

                        if selected_new_asset:
                            isInitial = True
                        else:
                            isInitial = False

                        highest_value = current_price
                        previous_resistance = 0
                        while adjust_sell_trigger:
                            if helper.in_business_hours(
                                start_trading_at, stop_trading_at, exchange.get_observation_start(), exchange.get_observation_stop()
                            ):
                                max_loss = max_loss_in_percent / 100
                                if winning_buy_count >= 1:
                                    max_loss = take_profit_in_percent / 100 / 3
                                size = get_Ticker_balance(exchange, existing_asset)
                                if still_has_postion(size, highest_value):
                                    (
                                        highest_value,
                                        current_price,
                                        order,
                                        new_resistance,
                                    ) = set_sell_trigger(
                                        exchange,
                                        isInitial,
                                        existing_asset,
                                        size,
                                        highest_value,
                                        max_loss,
                                        previous_resistance,
                                    )
                                    logger.debug(
                                        "trader previous resistance: {}, new_resistance: {}".format(
                                            previous_resistance, new_resistance
                                        )
                                    )
                                    if new_resistance:
                                        previous_resistance = new_resistance
                                        helper.write_to_db_activity_tracker(write_to_db, run_id, exchange.get_mode(), exchange.get_timestamp(), "sell loss order", existing_asset, size, new_resistance)

                                    isInitial = False
                                    wait_time = helper.wait("short", mode)
                                    observation_date_offset(exchange, wait_time)
                                else:
                                    logger.info("Asset has been sold!, Time: {}".format(exchange.get_observation_start()))
                                    adjust_sell_trigger = False
                                    buy_decision = False
                                    end_price = current_price
                                    helper.write_to_db_activity_tracker(write_to_db, run_id, exchange.get_mode(), exchange.get_timestamp(), "sell", existing_asset, size, current_price)
                                    previous_asset = existing_asset
                                    balance = get_base_currency_balance(exchange)
                                    helper.write_balance_to_db(write_to_db, base_currency, balance)
                                    existing_asset = None
                            else:
                                if sell_end_of_day:
                                    existing_asset, current_price = find_asset_with_balance(
                                        exchange
                                    )
                                    if existing_asset:
                                        size = get_Ticker_balance(exchange, existing_asset)
                                        sell_now(exchange, existing_asset, size)
                                        helper.write_to_db_activity_tracker(write_to_db, run_id, exchange.get_mode(), exchange.get_timestamp(), "sell", existing_asset, size, current_price)
                                        
                                    adjust_sell_trigger = False
                                    existing_asset = None
                else:
                    logger.debug("No Asset selected!")
                    winning_buy_count = 0
                    wait_time = helper.wait("long", mode)
                    observation_date_offset(exchange, wait_time)
            else:
                if pnl_achieved:
                    logger.info("PnL achieved. No activities for today!")
                    helper.wait("long", mode)
                if max_loss_reached:
                    logger.info("Too much loss. No activities for today!")
                    helper.wait("long", mode)
        else:
            if in_business:
                if sell_end_of_day:
                    in_business = False
                    existing_asset, current_price = find_asset_with_balance(exchange)
                    if existing_asset:
                        size = get_Ticker_balance(exchange, existing_asset)
                        sell_now(exchange, existing_asset, size)
                        helper.write_to_db_activity_tracker(write_to_db, run_id, exchange.get_mode(), exchange.get_timestamp(), "sell", existing_asset, size, current_price)
                        existing_asset = None
                    start_price = None
                    end_price = None
                    balance = get_base_currency_balance(exchange)
                    if write_to_db:
                        helper.write_balance_to_db(write_to_db, base_currency, balance)

            wait_time = helper.wait("long", mode)
            observation_date_offset(exchange, wait_time)
            
        selected_new_asset = None
        running = observation_stop_check(exchange)
        
if __name__ == "__main__":

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

    parser.add_argument("--selected", default=None)
    parser.add_argument("--observation_start", default=None)  # 2024-11-10 12:00
    parser.add_argument("--observation_stop", default=None)  # 2024-11-10 12:00
    parser.add_argument("--logging", default="INFO")
    parser.add_argument("--amount_coins", type=int, required=True, default=1000)
    parser.add_argument("--take_profit_in_percentage", required=True, type=float, default=3)
    parser.add_argument("--max_loss_in_percentage", required=True, type=float, default=3.5)
    parser.add_argument("--starting_balance", type=float, default=None)
    
    

    args = parser.parse_args()
    if args.logging == "INFO":
        logger.setLevel(logging.INFO)
    elif args.logging == "DEBUG":
        logger.setLevel(logging.DEBUG)
    observation_start = None
    if args.observation_start:
        observation_start = datetime.strptime(args.observation_start, "%Y-%m-%d %H:%M")
    if args.observation_stop:
        observation_stop = datetime.strptime(args.observation_stop, "%Y-%m-%d %H:%M")

    exchange_class = globals()[args.exchange]
    exchange = exchange_class(args.exchange_name, args.starting_balance)
    if observation_start:
        exchange.set_observation_start(observation_start)
    if observation_stop:
        exchange.set_observation_stop(observation_stop)
        
    logger.info("Trader started!")
    logger.info("Exchange: {}".format(exchange.__class__))
    logger.info("Exchange Name: {}".format(exchange.get_name()))
    logger.info("Mode: {}".format(exchange.get_mode()))
    logger.info("Log Level: {}".format(logger.level))
    logger.info("Observation Start: {}".format(exchange.get_observation_start()))
    logger.info("Observation Start: {}".format(exchange.get_observation_stop()))
    logger.info("Amount Coins: {}".format(args.amount_coins))
    logger.info("Take Profit Percentage: {}".format(args.take_profit_in_percentage))
    logger.info("Max Loss Percentage: {}".format(args.max_loss_in_percentage))
    logger.info("Ignore Profit/Loss: {}".format(args.ignore_profit_loss))
    logger.info("Selected: {}".format(args.selected))
    logger.info("Use DB: {}".format(args.use_db))
    logger.info("Starting Balance: {}".format(args.starting_balance))
    logger.info("Sell end of day: {}".format(args.sell_end_of_day))
    
    

    run_trader(
        exchange,
        exchange.get_mode(),
        args.amount_coins,
        args.take_profit_in_percentage,
        args.max_loss_in_percentage,
        args.ignore_profit_loss,
        args.selected,
        args.use_db,
        args.starting_balance,
        args.sell_end_of_day
    )
