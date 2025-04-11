import numpy as np
import pandas as pd
import random
import math
import logging
import argparse
from os import write
from Exchange import Exchange, Offline_Exchange
from datetime import time, datetime, timedelta
from tqdm import tqdm
from DataToolbox import get_data, add_aroon, add_macd, add_min_max, add_vwap
from scipy.signal import argrelextrema
from Helper import read_arguments, set_logger, get_exchange, get_next_sequence, write_to_db_activity_tracker, wait, wait_minutes, read_last_balance_from_db, wait_hours, wait_seconds, write_balance_to_db

logger = logging.getLogger("screener")

class Trader:

    def __init__(self, exchange, params):
        self.exchange = exchange
        self.params = params

    # ************************************ Balance of base currency
    def get_base_currency_balance(self):
        usd = self.exchange.fetch_balance()[params["base_currency"]]["total"]
        logger.debug("Base currency balance: {}".format(usd))
        return usd

    # ************************************ Assets with existing balance
    def find_asset_with_balance(self):
        exchange = self.exchange
        asset_with_balance = None
        price = None
        current_assets = self.exchange.fetch_balance()["total"]
        for asset in current_assets:
            if not asset in params["ignored_coins"]:
                found_price = exchange.fetch_ticker(
                    asset + "/" + self.params["base_currency"]
                )["last"]
                balance = exchange.fetch_balance()[asset]["total"]
                if (balance * found_price) > params["valid_position_amount"]:
                    logger.debug("Found asset with balance: {}".format(asset))
                    asset_with_balance = asset + "/" + self.params["base_currency"]
                    price = found_price
        if asset_with_balance:
            logger.debug("Asset with balance: ".format(asset_with_balance))
        else:
            logger.debug("No asset with balance")
        return asset_with_balance, price

    # ************************************ Balance for specific ticker
    def get_Ticker_balance(self, ticker):
        exchange = self.exchange

        ticker = ticker.replace("/" + self.params["base_currency"], "")
        ticker_balance = 0
        try:
            ticker_balance = exchange.fetch_balance()[ticker]["total"]
        except:
            logger.debug("Ticker not in Wallet")
        logger.debug("Ticker Balance: {}".format(ticker_balance))
        return ticker_balance

    # ************************************ check for valid position
    def still_has_postion(self, size, price):
        value = (size * price) > params["valid_position_amount"]
        logger.debug("   still has position: {}".format(value))
        return value

    # ************************************ get All Tickers
    def get_tickers(self):
        tickers = self.exchange.fetch_tickers()
        for ignore_coin in params["ignored_coins"]:
            tickers.pop(ignore_coin + '/' + params["base_currency"], None)
        tickers = pd.DataFrame(tickers)
        tickers = tickers.T
        tickers = tickers[
            tickers["symbol"].str.endswith("/" + self.params["base_currency"])
        ].head(self.params["amount_coins"])
        logger.debug("Amount Tickers: {}".format(len(tickers)))
        return tickers

    def get_tickers_as_list(self, tickers):
        tickers = tickers["symbol"].to_list()
        random.shuffle(tickers)
        return tickers

    # ************************************ Funding based on market movment
    def get_funding(self, balance):
        minimum_funding = params["minimum_funding"]
        fund_ratio = params["funding_ratio_in_percent"] / 100
        funding = balance * fund_ratio
        rest = balance - funding
        if funding < minimum_funding:
            funding = minimum_funding
        if rest < minimum_funding:
            funding = balance - minimum_funding
        logger.debug(
            "{} {} * Market Factor {} = Funding {}".format(
                params["base_currency"], balance, fund_ratio, funding
            )
        )
        return funding

    # ************************************ get precision for specific ticker
    def get_precision(self, ticker):
        markets = self.exchange.exchange.load_markets()
        amount = float((markets[ticker]["precision"]["amount"]))
        price = float((markets[ticker]["precision"]["price"]))
        logger.debug(
            "   get_precision - ticker: {}, amount: {}, price: {}".format(
                ticker, amount, price
            )
        )
        return amount, price

    # ************************************ get convert price fitting to precision
    def convert_to_precision(self, value, precision):
        rounded = round(math.floor(value / precision) * precision, 7)
        logger.debug(
            "   convert_to_precision - size: {}, precision: {}, value: {}".format(
                value, precision, rounded
            )
        )
        return rounded

    # ************************************ get Candidate Functions
    def get_candidate(self):

        logger.info("{} Check for New Candidate".format(self.exchange.get_observation_start()))
        tickers = self.get_tickers()
        tickers = self.get_tickers_as_list(tickers)
        major_move = self.get_ticker_with_bigger_moves(tickers)
        # expected_results = get_top_ticker_expected_results(exchange, major_move)
        # logger.debug("   expected_results: {}".format(expected_results))
        close_to_high = self.get_close_to_high(major_move)
        logger.debug("   close_to_high: {}".format(close_to_high))
        relevant_tickers = close_to_high
        logger.debug("   relevant_tickers: {}".format(relevant_tickers))
        # increased_volume = get_ticker_with_increased_volume(exchange, relevant_tickers)
        buy_signals = self.get_ticker_with_aroon_buy_signals(relevant_tickers)
        selected_Ticker = self.get_lowest_difference_to_maximum(buy_signals)
        selected_Ticker = self.get_with_sufficient_variance(selected_Ticker)
        logger.info("{} Selected: {}".format(self.exchange.get_observation_start(), selected_Ticker))
        return selected_Ticker

    def get_ticker_with_bigger_moves(self, tickers):
        limit = 4
        bigger_moves = []
        iterations = len(tickers)
        progress_bar = iter(tqdm(range(iterations)))
        next(progress_bar)
        for ticker in tickers:
            try:
                data = get_data(self.exchange, ticker, "1m", limit)
                # data["change"] = ((data["close"] - data["open"]) / data["open"]) * 100
                if not data.empty:
                    data["change"] = data["close"].pct_change()
                    data["is_change_relevant"] = data["change"] >= params["move_increase_threshold"]
                    ticker_check = {}
                    ticker_check["ticker"] = ticker
                    ticker_check["change"] = data["change"].to_list()
                    ticker_check["relevant"] = data["is_change_relevant"].to_list()
                    ticker_check["data"] = data
                    if (
                        ticker_check["relevant"].count(True)
                        >= params ["move_increase_period_threshold"]
                    ):
                        bigger_moves.append(ticker)
                try:
                    next(progress_bar)
                except Exception as e:
                    pass
            except Exception as e:
                logger.error("error loading data: {} {}".format(ticker, e))

        logger.debug("   ticker with bigger moves: {}".format(len(bigger_moves)))
        return bigger_moves

    def get_ticker_with_aroon_buy_signals(self, tickers):
        buy_signals = []
        for ticker in tickers:
            try:
                data = get_data(self.exchange, ticker, "1m", limit=20)
                data = add_aroon(data)
                if 100 in data.tail(3)["aroon_up"].to_list():
                    buy_signals.append(ticker)
            except Exception as e:
                logger.error("error loading data: {} {}".format(ticker, e))
        logger.debug("   ticker_with_aroon_buy_signals: {}".format(len(buy_signals)))
        return buy_signals

    def get_ticker_with_increased_volume(self, tickers):
        increased_volumes = []
        for ticker in tickers:
            try:
                data = get_data(ticker, "15m", limit=28)
                last_mean = data.head(24)["volume"].mean()
                current_mean = data.tail(4)["volume"].mean()
                if (current_mean / last_mean) >= params["volume_increase_threshold"]:
                    increased_volumes.append(ticker)
            except Exception as e:
                logger.error("error loading data: {} {}".format(ticker, e))
        logger.debug(
            "   ticker_with_increased_volume: {}".format(len(increased_volumes))
        )
        return increased_volumes

    def get_top_ticker_expected_results(self, tickers):
        accepted_expected_results = {}
        for ticker in tickers:
            try:
                data = get_data(self.exchange, ticker, "5m", limit=120)
                data["pct_change"] = data["close"].pct_change(periods=3)
                min = data["pct_change"].min()
                if min > -0.005:
                    accepted_expected_results[ticker] = min
            except Exception as e:
                logger.error("error loading data: {} {}".format(ticker, e))
        df = pd.DataFrame(accepted_expected_results.items(), columns=["ticker", "min"])
        df = df.sort_values(by="min")
        df = df.tail(5)["ticker"].to_list()
        logger.debug("   ticker_with_expected_results: {}".format(len(df)))
        return df

    def get_close_to_high(self, tickers):
        close_to_high = []
        for ticker in tickers:
            try:
                data = get_data(self.exchange, ticker, "1h", limit=48)
                max = data["close"].max()
                if data.iloc[-1, 4] >= max:
                    close_to_high.append(ticker)
            except Exception as e:
                logger.error("error loading data: {} {}".format(ticker, e))
        logger.debug("   ticker_close_to_high: {}".format(len(close_to_high)))
        return close_to_high

    def get_lowest_difference_to_maximum(self, tickers):
        lowest_difference_to_maximum = None
        for ticker in tickers:
            try:
                data = get_data(self.exchange, ticker, "1m", limit=90)
                data = add_min_max(data)
                local_max = data["max"].max()
                current_close = data.iloc[-1, 4]
                ratio = ((current_close - local_max) * 100) / local_max
                if ratio > params["difference_to_maximum_max"]:
                    lowest_difference_to_maximum = ticker
            except Exception as e:
                logger.error("error loading data: {} {}".format(ticker, e))
        logger.debug(
            "   lowest_difference_to_maximum: {}".format(lowest_difference_to_maximum)
        )
        return lowest_difference_to_maximum

    def get_with_sufficient_variance(self, ticker):
        duplicate_data = 99
        if ticker:
            try:
                data = get_data(self.exchange, ticker, "1m", limit=5)
                data = data.duplicated(subset=["close"])
                data = data.loc[lambda x: x == True]
                duplicate_data = len(data)
                logger.debug("   variance: {}".format(duplicate_data))
            except Exception as e:
                logger.error("error loading data: {} {}".format(ticker, e))
        if duplicate_data > 0:
            return None
        else:
            return ticker

    # ************************************ BUY Functions
    def is_buy_decision(self, ticker, attempt):

        logger.info(
            "{} Check for Buy Decision, Ticker: {}, #{}".format(
                self.exchange.get_observation_start(), ticker, attempt
            )
        )
        data = get_data(self.exchange, ticker, "1m", limit=180)
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
        logger.debug("Resistance check - buy: {}".format(is_buy))

        aroon_up = data.iloc[-1, 8]
        if is_buy:
            if isinstance(aroon_up, float):
                if aroon_up > 90:
                    is_buy = True
                else:
                    is_buy = False
            logger.debug("Aroon check - buy: {}".format(is_buy))

        vwap = data.iloc[-1, 10]
        if is_buy:
            if isinstance(current_close, float) and isinstance(vwap, float):
                if vwap < current_close:
                    is_buy = True
                else:
                    is_buy = False
            logger.debug("vwap check - buy: {}".format(is_buy))

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
            logger.debug("Macd check - buy: {}".format(is_buy))

        return is_buy, current_close


    def is_rebuy_decision(self, ticker, attempt):

        logger.info(
            "{} Check for Re-Buy Decision, Ticker: {}, #{}".format(
                self.exchange.get_observation_start(), ticker, attempt
            )
        )
        data = get_data(self.exchange, ticker, "1m", limit=180)
        data = add_min_max(data)
        data = add_aroon(data)
        data = add_vwap(data)
        data = add_macd(data)
        current_close = data.iloc[-1, 4]
        
        is_buy = False

        
        aroon_up = data.iloc[-1, 8]
        if is_buy:
            if isinstance(aroon_up, float):
                if aroon_up > 90:
                    is_buy = True
                else:
                    is_buy = False
            logger.debug("Aroon check - buy: {}".format(is_buy))

        
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
            logger.debug("Macd check - buy: {}".format(is_buy))

        return is_buy, current_close

    def buy_order(self, ticker, price, funding):
        amount_precision, price_precision = self.get_precision(ticker)
        price = self.convert_to_precision(price, price_precision)
        size = self.convert_to_precision(funding / price, amount_precision)
        order = self.exchange.create_buy_order(ticker, size, price)
        logger.info(
            "{} Buy Decision, Ticker: {}, Price: {}, Size: {}, Funding: {}".format(
                self.exchange.get_observation_start(), ticker, price, size, funding
            )
        )
        return order, price, size

    # ************************************ SELL Functions
    def set_sell_trigger(
        self, isInitial, ticker, size, highest_value, max_loss, previous_resistance
    ):

        logger.debug(
            "Check Sell - ticker: {}, isInitial: {}, size: {}, highest_value: {}, max_loss: {}".format(
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
            "Highest value: {}, current value: {}".format(
                highest_value, current_value
            )
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
                            "Previous resistance: {}, resistance: {}".format(
                                previous_resistance, resistance
                            )
                        )
                        if resistance > previous_resistance:
                            logger.info(
                                "{} Set new sell triger: {}".format(self.exchange.get_observation_start(), resistance)
                            )
                            order = self.sell_order(
                                ticker, current_value, size, resistance
                            )
                            
                        resistance_found = True
                    else:
                        row -= 1
                else:
                    resistance = min_column.iloc[(-1) * len(min_column)]
                    logger.debug(
                        "Previous resistance: {}, resistance: {}".format(
                            previous_resistance, resistance
                        )
                    )
                    if resistance > previous_resistance:
                        logger.debug("   set new sell triger: {}".format(resistance))
                        order = self.sell_order(
                           ticker, current_value, size, resistance
                        )
                    resistance_found = True
        else:
            logger.debug("No new sell trigger")
        return highest_value, current_value, order, resistance

    def sell_order_take_profit(self, ticker, price, size, takeProfitPrice):

        exchange = self.exchange
        amount_precision, price_precision = self.get_precision(ticker)
        takeProfitPrice = self.convert_to_precision(takeProfitPrice, price_precision)
        size = self.convert_to_precision(size, amount_precision)
        logger.info(
            "{} Put sell order take profit- Ticker: {}, Size: {}, Price: {}, takeProfitPrice: {}".format(
                self.exchange.get_observation_start(), ticker, size, price, takeProfitPrice
            )
        )
        order = self.exchange.create_take_profit_order(ticker, size, takeProfitPrice)
        logger.debug("Sell TP order id : {}".format(order))

    def sell_order(self, ticker, price, size, stopLossPrice):

        exchange = self.exchange
        # exchange.cancel_orders(ticker)
        amount_precision, price_precision = self.get_precision(ticker)
        stopLossPrice = self.convert_to_precision(stopLossPrice, price_precision)
        size = self.convert_to_precision(size, amount_precision)
        logger.info(
            "{} Put sell order - Ticker: {}, Size: {}, Price: {}, stopLossPrice: {}".format(
                self.exchange.get_observation_start(), ticker, size, price, stopLossPrice
            )
        )
        order = self.exchange.create_stop_loss_order(ticker, size, stopLossPrice)
        logger.debug("   sell order id : {}".format(order))
        return order

    def sell_now(self, ticker, size):
        # exchange.cancel_orders(ticker)
        amount_precision, _ = self.get_precision(ticker)
        size = self.convert_to_precision(size, amount_precision)
        order = self.exchange.create_sell_order(ticker, size)
        logger.info("{} Sell inmediately - Ticker: {}".format(self.exchange.get_observation_start(), ticker))
        return order

    def cancel_order(self, ticker, orderId):

        order = self.exchange.cancel_order(ticker, orderId)

    def daily_pnl_target_achieved(self, current_balance, last_balance):
        pnl = False
        if ["acknowledge_profit_loss"] is True:
            current_pnl = ((current_balance - last_balance) * 100) / last_balance
            logger.debug(
                "   last_balance: {}, current_balance: {}, current pnl: {}".format(
                    last_balance, current_balance, current_pnl
                )
            )
            if current_pnl >= params["daily_pnl_target_in_percent"]:
                pnl = True
            else:
                pnl = False
        else:
            pnl = False
        return pnl

    def daily_max_loss_reached(self, current_balance, last_balance):
        pnl = False
        if ["acknowledge_profit_loss"] is True: 
            current_pnl = ((current_balance - last_balance) * 100) / last_balance
            if current_pnl <= params["daily_pnl_max_loss_in_percent"]:
                pnl = True
            else:
                pnl = False
        else:
            pnl = False
        return pnl

    def observation_date_offset(self, offset_in_seconds):
        observation_start = self.exchange.get_observation_start()
        if observation_start:
            observation_start = observation_start + timedelta(
                minutes=offset_in_seconds / 60
            )
            self.exchange.set_observation_start(observation_start)
            logger.debug(
                "Observation Time: {}".format(self.exchange.get_observation_start())
            )

    def observation_stop_check(self):
        return (
            self.exchange.get_observation_stop() >= self.exchange.get_observation_start() if self.exchange.get_observation_stop and self.exchange.get_observation_start else True)

    def in_business_hours(self):
        run = False
        if params["acknowledge_business_hours"] is True:
            now = (
                params["observation_start"]
                if params["observation_start"]
                else datetime.now()
            )
            if params["observation_stop"] is None:
                if params["stop_trading_at"] < params["start_trading_at"]:
                    raise Exception("case end < start not implemeted!")
                run = (
                    now.hour >= params["start_trading_at"].hour
                    and now.hour < params["stop_trading_at"].hour
                )  # and now.weekday() < 6
            else:
                run = (
                    True
                    if self.exchange.get_observation_stop()
                    >= self.exchange.get_observation_start()
                    else False
                )
        else:
            run = True
        return run

    def in_buying_period(self):
        run = False
        if params["acknowledge_business_hours"] is True:
            now = (
                self.exchange.get_observation_start()
                if self.exchange.get_observation_start()
                else datetime.now()
            )
            run = now.hour < params["stop_buying_at"].hour
        else:
            run = True
        return run

    def run(self):

        running = True
        in_business = False

        current_price = None
        size = None
        selected = params["selected"]
        if not selected is None:
            selected = selected + "/" + params["base_currency"]
        selected_new_asset = selected
        existing_asset = None
        previous_asset = None
        start_price = None
        end_price = None
        winning_buy_count = 0
        base_currency_balance = 0
        pnl_achieved = False
        max_loss_reached = False
        existing_asset, current_price = self.find_asset_with_balance()
        write_to_db = params["write_to_db"]
        run_id = get_next_sequence(self.params["write_to_db"])

        while running:
            if self.in_business_hours() and self.in_buying_period():
                in_business = True
                if not existing_asset:
                    base_currency_balance = self.get_base_currency_balance()
                    last_balance = (
                        params["starting_balance"]
                        if not params["starting_balance"] is None
                        else read_last_balance_from_db().iloc[0, 0]
                    )
                    pnl_achieved = self.daily_pnl_target_achieved(
                        base_currency_balance, last_balance
                    )
                    max_loss_reached = self.daily_max_loss_reached(
                        base_currency_balance, last_balance
                    )

                if (
                    not pnl_achieved and not max_loss_reached
                ):
                    if not start_price is None and not end_price is None:
                        if (
                            isinstance(start_price, float)
                            and isinstance(end_price, float)
                            and start_price < end_price
                        ):
                            winning_buy_count += 1
                            if winning_buy_count <= params["winning_buy_nr"]:
                                selected_new_asset = previous_asset
                                logger.info(
                                    "{} Sold with proft #{}".format(self.exchange.get_observation_start(), winning_buy_count)
                                )
                            else:
                                winning_buy_count = 0
                                selected_new_asset = None
                            wait_time = wait_minutes(5, params)
                            self.observation_date_offset(wait_time)
                        if (
                            isinstance(start_price, float)
                            and isinstance(end_price, float)
                            and start_price >= end_price
                        ):
                            selected_new_asset = None
                            existing_asset = None
                            winning_buy_count = 0
                            logger.info("{} Sold with loss. Waiting 1 hour!".format(self.exchange.get_observation_start()))
                            wait_time = wait_hours(1, params)
                            self.observation_date_offset(wait_time)
                        previous_asset = None
                        start_price = None
                        end_price = None
                    else:
                        if not existing_asset and not selected_new_asset:
                            selected_new_asset = self.get_candidate()
                            if selected_new_asset:
                                write_to_db_activity_tracker(
                                    write_to_db,
                                    run_id,
                                    exchange.get_mode(),
                                    exchange.get_timestamp(),
                                    "selected",
                                    selected_new_asset,
                                    0,
                                    0,
                                )
                            buy_decision = True

                    if selected_new_asset or existing_asset:
                        buy_attempts = 1
                        # observe selected Ticker
                        confirm_buy = False
                        buy_decision = False
                        while (
                            not buy_decision
                            and buy_attempts <= params["buy_attempts_nr"]
                            and not existing_asset
                        ):
                            is_buy, current_price = self.is_buy_decision(
                                selected_new_asset, buy_attempts
                            )
                            if is_buy:
                                wait_time = wait_minutes(1, params)
                                self.observation_date_offset(wait_time)
                                confirm_buy, current_price = self.is_buy_decision(
                                    selected_new_asset, buy_attempts
                                )
                            if not is_buy:
                                buy_attempts += 1
                                wait_time = wait("short", params)
                                self.observation_date_offset(wait_time)
                            else:
                                if confirm_buy:
                                    buy_decision = True
                            if not self.get_lowest_difference_to_maximum(
                                [selected_new_asset]
                            ):
                                logger.info("{} Difference to maximum exceeds limit!".format(self.exchange.get_observation_start()))
                                buy_attempts = params["buy_attempts_nr"] + 1

                        if buy_decision or existing_asset:

                            adjust_sell_trigger = True

                            # buy sleected Ticker
                            if not existing_asset:
                                funding = self.get_funding(base_currency_balance)
                                try:
                                    # BUY Order
                                    self.buy_order(
                                        selected_new_asset,
                                        current_price,
                                        funding,
                                    )
                                    wait_seconds(5, params)
                                    start_price = current_price
                                    size = self.get_Ticker_balance(
                                        selected_new_asset
                                    )
                                    write_to_db_activity_tracker(
                                        write_to_db,
                                        run_id,
                                        exchange.get_mode(),
                                        exchange.get_timestamp(),
                                        "buy",
                                        selected_new_asset,
                                        size,
                                        current_price,
                                    )
                                    # Take Profit Order
                                    if isinstance(current_price, float):
                                        take_profit_price = current_price * (
                                            1 + (params["take_profit_in_percent"] / 100)
                                        )
                                        self.sell_order_take_profit(
                                            selected_new_asset,
                                            current_price,
                                            size,
                                            take_profit_price,
                                        )
                                        write_to_db_activity_tracker(
                                            write_to_db,
                                            run_id,
                                            exchange.get_mode(),
                                            exchange.get_timestamp(),
                                            "take profit order",
                                            selected_new_asset,
                                            size,
                                            take_profit_price,
                                        )

                                    existing_asset = selected_new_asset
                                except Exception as e:
                                    adjust_sell_trigger = False
                                    logger.info("{} Error buying: {}".format(self.exchange.get_observation_start(), e))

                            if selected_new_asset:
                                isInitial = True
                            else:
                                isInitial = False

                            highest_value = current_price
                            previous_resistance = 0
                            while adjust_sell_trigger:
                                if self.in_business_hours():
                                    max_loss = params["max_loss_in_percent"] / 100
                                    if winning_buy_count >= 1:
                                        max_loss = params["take_profit_in_percent"] / 100 / 3
                                    size = self.get_Ticker_balance(existing_asset)
                                    if self.still_has_postion(size, highest_value):
                                        (
                                            highest_value,
                                            current_price,
                                            order,
                                            new_resistance,
                                        ) = self.set_sell_trigger(
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
                                            write_to_db_activity_tracker(
                                                write_to_db,
                                                run_id,
                                                exchange.get_mode(),
                                                exchange.get_timestamp(),
                                                "sell loss order",
                                                existing_asset,
                                                size,
                                                new_resistance,
                                            )

                                        isInitial = False
                                        wait_time = wait("short", params)
                                        self.observation_date_offset(wait_time)
                                    else:
                                        logger.info(
                                            "{} Asset has been sold!".format(
                                                exchange.get_observation_start()
                                            )
                                        )
                                        adjust_sell_trigger = False
                                        buy_decision = False
                                        end_price = current_price
                                        write_to_db_activity_tracker(
                                            write_to_db,
                                            run_id,
                                            exchange.get_mode(),
                                            exchange.get_timestamp(),
                                            "sell",
                                            existing_asset,
                                            size,
                                            current_price,
                                        )
                                        previous_asset = existing_asset
                                        balance = self.get_base_currency_balance()
                                        write_balance_to_db(
                                            write_to_db, params["base_currency"], balance
                                        )
                                        existing_asset = None
                                else:
                                    if params["sell_end_of_day"]:
                                        existing_asset, current_price = (
                                            self.find_asset_with_balance()
                                        )
                                        if existing_asset:
                                            size = self.get_Ticker_balance(
                                                existing_asset
                                            )
                                            self.sell_now(existing_asset, size)
                                            write_to_db_activity_tracker(
                                                write_to_db,
                                                run_id,
                                                exchange.get_mode(),
                                                exchange.get_timestamp(),
                                                "sell",
                                                existing_asset,
                                                size,
                                                current_price,
                                            )

                                        adjust_sell_trigger = False
                                        existing_asset = None
                    else:
                        logger.debug("No Asset selected!")
                        winning_buy_count = 0
                        wait_time = wait("long", params)
                        self.observation_date_offset(wait_time)
                else:
                    if pnl_achieved:
                        logger.info("{} PnL achieved. No activities for today!".format(self.exchange.get_observation_start()))
                        wait("long", params)
                    if max_loss_reached:
                        logger.info("{} Too much loss. No activities for today!".format(self.exchange.get_observation_start()))
                        wait("long", params)
            else:
                if in_business:
                    if params["sell_end_of_day"]:
                        in_business = False
                        existing_asset, current_price = self.find_asset_with_balance()
                        if existing_asset:
                            size = self.get_Ticker_balance(existing_asset)
                            self.sell_now(existing_asset, size)
                            write_to_db_activity_tracker(
                                write_to_db,
                                run_id,
                                exchange.get_mode(),
                                exchange.get_timestamp(),
                                "sell",
                                existing_asset,
                                size,
                                current_price,
                            )
                            existing_asset = None
                        start_price = None
                        end_price = None
                        balance = self.get_base_currency_balance()
                        if write_to_db:
                            write_balance_to_db(
                                write_to_db, params["base_currency"], balance
                            )

                wait_time = wait("long", params)
                self.observation_date_offset(wait_time)

            selected_new_asset = None
            running = self.exchange.observation_run_check()


if __name__ == "__main__":

    params = read_arguments()

    set_logger(params["logging"])
    
    exchange = get_exchange(params)

    trader = Trader(exchange, params)
    trader.run()
