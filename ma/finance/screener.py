from exchanges import Exchange
import numpy as np
import pandas as pd
import random
import math
import logging
from tqdm import tqdm
from ta.trend import AroonIndicator, EMAIndicator, MACD
from ta.volume import VolumeWeightedAveragePrice
from scipy.signal import argrelextrema
from screener_helper import Helper


#************************************ Logging
logger = logging.getLogger("screener")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler = logging.FileHandler(
    filename="screener.log",
    mode="w",
    encoding="utf-8",
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


#************************************ Confiuguration
exchange_name = "bitget"
base_currency = "USDT"
ignored_coins = [base_currency, "USDT", "USD", "CRO", "PAXG", "BGB"]
amount_coins = 1000
wait_time_next_asset_selection_minutes = 15
wait_time_next_buy_selection_seconds = 60
take_profit_in_percent = 2
buy_attempts_nr = 120
move_increase_threshold = 0.003
move_increase_period_threshold = 1
volume_increase_threshold = 1
difference_to_maximum_max = -2
valid_position_amount = 2
#difference_to_resistance_min = 0.01
minimum_funding = 10


helper = Helper(logger, wait_time_next_asset_selection_minutes, wait_time_next_buy_selection_seconds)


#************************************ Get Ticker Data
def get_data(exchange, ticker, interval, limit):
    bars = exchange.fetch_ohlcv(
            ticker, interval, limit=limit
    )
    data = pd.DataFrame(
        bars[:], columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    return data


#************************************ Balance of base currency
def get_base_currency_balance(exchange):
    usd = exchange.fetch_balance()[base_currency]["total"]
    return usd


#************************************ Assets with existing balance
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
    return asset_with_balance, price


#************************************ Balance for specific ticker
def get_Ticker_balance(exchange, ticker):
    ticker = ticker.replace("/" + base_currency, "")
    ticker_balance = 0
    try:
        ticker_balance = exchange.fetch_balance()[ticker]["total"]
    except:
        logger.info("   Ticker not in Wallet")
    logger.info("   Ticker Balance: {}".format(ticker_balance))
    return ticker_balance


#************************************ check for valid position
def still_has_postion(size, price):
    value = (size * price) > valid_position_amount
    logger.info("   still has position: {}".format(value))
    return value


#************************************ get All Tickers
def get_tickers(exchange):
    tickers = exchange.fetch_tickers()
    tickers = pd.DataFrame(tickers)
    tickers = tickers.T
    tickers = tickers[tickers["symbol"].str.endswith("/" + base_currency)].head(amount_coins)
    return tickers


def get_tickers_as_list(tickers):
    tickers = tickers["symbol"].to_list()
    random.shuffle(tickers)
    return tickers


#************************************ get market movement
def get_market_movement(tickers):
    market_movement = tickers["percentage"].median()
    if not exchange_name == "bitget":
        market_movement *= 100
    return market_movement




#************************************ Funding based on market movment
def get_funding(usd, market_movement):
    fund_ratio, _ = get_market_factor(market_movement)
    funding = usd * fund_ratio
    if funding < minimum_funding:
        funding = minimum_funding
    logger.info("{} {} * Market Factor {} = Funding {}".format(base_currency, usd, fund_ratio, funding))
    return funding


#************************************ get Factors based on market movement
def get_market_factor(pos_neg_mean):
    fund_ratio = 0
    max_loss = 0
    if pos_neg_mean > 4:
        fund_ratio = 0.9
        max_loss = 0.05
    elif pos_neg_mean > 3:
        fund_ratio = 0.9
        max_loss = 0.04
    elif pos_neg_mean >1 and pos_neg_mean <=3:
        fund_ratio = 0.75
        max_loss = 0.03
    elif pos_neg_mean >0 and pos_neg_mean <=1:
        fund_ratio = 0.5
        max_loss = 0.025
    elif pos_neg_mean >-2 and pos_neg_mean <=0:
        fund_ratio = 0.25
        max_loss = 0.02
    else:
        fund_ratio = 0.1
        max_loss = 0.02
    logger.info("   get market factor for market_movement: {}, fund_ratio: {}, max_loss: {}".format(pos_neg_mean, fund_ratio, max_loss))    
    return fund_ratio, max_loss


#************************************ get precision for specific ticker
def get_precision(exchange, ticker):
    markets = exchange.exchange.load_markets()
    amount = float((markets[ticker]['precision']['amount'])) 
    price = float((markets[ticker]['precision']['price'])) 
    logger.info("   get_precision - ticker: {}, amount: {}, price: {}".format(ticker, amount, price))
    return amount, price


#************************************ get convert price fitting to precision
def convert_to_precision(value, precision):
    rounded = math.floor(value/precision) * precision
    numbers = len(str(precision))-2
    rounded = round(rounded, numbers)
    logger.info("   convert_to_precision - size: {}, precision: {}, value: {}".format(value, precision, rounded)) 
    return rounded



#************************************ add Indicators
def add_min_max(data):
    order = 3
    data['min'] = data.iloc[argrelextrema(data['close'].values, np.less_equal, order=order)[0]]['close']
    data['max'] = data.iloc[argrelextrema(data['close'].values, np.greater_equal, order=order)[0]]['close']
    return data


def add_aroon(data):
    indicator_AROON = AroonIndicator(
        high=data["high"], low=data["low"], window=14
    )
    data["aroon_up"] = indicator_AROON.aroon_up()
    data["aroon_down"] = indicator_AROON.aroon_down()
    return data


def add_vwap(data):
    indicator_vwap = VolumeWeightedAveragePrice(high=data["high"], low=data["low"], close=data["close"], volume=data["volume"])
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


#************************************ get Candidate Functions
def get_candidate(exchange):
    logger.info("1. ******** Check for New Candidate ********")
    tickers = get_tickers(exchange)
    market_movement = get_market_movement(tickers)
    tickers = get_tickers_as_list(tickers)
    major_move = get_ticker_with_bigger_moves(exchange, tickers)
    expected_results = get_top_ticker_expected_results(exchange, major_move)
    close_to_high = get_close_to_high(exchange, major_move)
    relevant_tickers = expected_results + close_to_high
    logger.info("   {}".format(relevant_tickers))
    increased_volume = get_ticker_with_increased_volume(exchange, relevant_tickers)
    buy_signals = get_ticker_with_aroon_buy_signals(exchange, relevant_tickers)
    selected_Ticker = get_lowest_difference_to_maximum(exchange, buy_signals)
    logger.info("   market movment: {}".format(market_movement))
    logger.info("   Selected: {}".format(selected_Ticker))
    return selected_Ticker, market_movement, major_move, increased_volume, buy_signals, selected_Ticker

def get_ticker_with_bigger_moves(exchange, tickers):
    limit = 4
    bigger_moves = []
    iterations = len(tickers)
    progress_bar = iter(tqdm(range(iterations)))
    next(progress_bar)
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit)
        #data["change"] = ((data["close"] - data["open"]) / data["open"]) * 100
        if not data.empty:
            data["change"] = data["close"].pct_change()
            data["is_change_relevant"] = data["change"] >= move_increase_threshold
            ticker_check = {}
            ticker_check['ticker'] = ticker
            ticker_check['change'] = data["change"].to_list()
            ticker_check['relevant'] = data["is_change_relevant"].to_list()
            ticker_check['data'] = data
            if ticker_check['relevant'].count(True) >= move_increase_period_threshold:
                bigger_moves.append(ticker)
        try:
            next(progress_bar)
        except:
            pass
    logger.info("   ticker with bigger moves: {}".format(len(bigger_moves)))
    return bigger_moves


def get_ticker_with_aroon_buy_signals(exchange, tickers):
    buy_signals = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit=20)
        data = add_aroon(data)
        logger.debug(ticker)
        logger.debug(data.tail(3)["aroon_up"])
        if (100 in data.tail(3)["aroon_up"].to_list()):
            buy_signals.append(ticker)
    logger.info("   ticker_with_aroon_buy_signals: {}".format(len(buy_signals)))
    return buy_signals


def get_ticker_with_increased_volume(exchange, tickers):
    increased_volumes = []
    print("increased volume")
    for ticker in tickers:
        data = get_data(exchange, ticker, "1d", limit=10)
        last_mean = data.head(9)["volume"].mean()
        current_mean = data.tail(1)["volume"].mean()
        print(ticker)
        print(current_mean / last_mean)
        if (current_mean / last_mean) >= volume_increase_threshold:
            increased_volumes.append(ticker)
    logger.info("   ticker_with_increased_volume: {}".format(len(increased_volumes)))
    return increased_volumes


def get_top_ticker_expected_results(exchange, tickers):
    accepted_expected_results = {}
    for ticker in tickers:
        data = get_data(exchange, ticker, "5m", limit=120)
        data['pct_change'] = data['close'].pct_change(periods=3)
        min = data['pct_change'].min()
        if min > -0.005:
            accepted_expected_results[ticker] = min
    df = pd.DataFrame(accepted_expected_results.items(), columns=['ticker', 'min'])
    df = df.sort_values(by='min')   
    df = df.tail(5)['ticker'].to_list()
    logger.info("   ticker_with_expected_results: {}".format(len(df)))
    return df


def get_close_to_high(exchange, tickers):
    close_to_high = []
    for ticker in tickers:
        data = get_data(exchange, ticker, "1h", limit=48)
        max = data['close'].max()
        if data.iloc[-1, 4] >= max:
            close_to_high.append(ticker)
    logger.info("   ticker_close_to_high: {}".format(len(close_to_high)))
    return close_to_high


def get_lowest_difference_to_maximum(exchange, tickers):
    lowest_difference_to_maximum = None
    for ticker in tickers:
        data = get_data(exchange, ticker, "1m", limit=90)
        data = add_min_max(data)
        local_max = data['max'].max()
        current_close = data.iloc[-1, 4]
        ratio = ((current_close - local_max) * 100) / local_max
        if ratio > difference_to_maximum_max:
            lowest_difference_to_maximum = ticker
    logger.info("   lowest_difference_to_maximum: {}".format(lowest_difference_to_maximum))
    return lowest_difference_to_maximum


#************************************ BUY Functions
def is_buy_decision(exchange, ticker, attempt):
    logger.info("2. ******** Check for Buy Decision, Ticker: {}, #{}".format(ticker, attempt))
    data = get_data(exchange, ticker, "1m", limit=120)
    data = add_min_max(data)
    data = add_aroon(data)
    data = add_vwap(data)
    data = add_macd(data)
    
    max_column = data['max'].dropna().drop_duplicates().sort_values()
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
    logger.info("   Resistance check - buy: {}".format(is_buy))

    vwap = data.iloc[-1, 10]
    if is_buy:
        if isinstance(current_close, float) and isinstance(vwap, float):
            if vwap < current_close:
                is_buy = True
            else:
                is_buy = False

    logger.info("   vwap check - buy: {}".format(is_buy))

    macd = data.iloc[-1, 11]
    macd_diff = data.iloc[-1, 12]
    macd_signal = data.iloc[-1, 13]
    if is_buy:
        if isinstance(macd, float) and isinstance(macd_signal, float) and isinstance(macd_diff, float):
            if macd > macd_signal and macd_diff > 0:
                is_buy = True
            else:
                is_buy = False

    logger.info("   macd check - buy: {}".format(is_buy))

    return is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff


def buy_order(exchange, ticker, price, funding):
    logger.info("3. ******** Buy Decision, Ticker: {}, Price: {}, Funding: {}".format(ticker, price, funding))
    amount_precision, price_precision = get_precision(exchange, ticker)
    price = convert_to_precision(price, price_precision)
    size = convert_to_precision(funding / price, amount_precision)
    order = exchange.create_buy_order(ticker, size, price)
    logger.info("   buy order id : {}".format(ticker, order["id"]))
    return order


#************************************ SELL Functions
def set_sell_trigger(exchange, isInitial, ticker, size, highest_value, max_loss):
    logger.info("4. ********  Check Sell - ticker: {}, isInitial: {}, size: {}, highest_value: {}, max_loss: {}".format(ticker, isInitial, size, highest_value, max_loss))
    data = get_data(exchange, ticker, "1m", limit=720)
    data = add_min_max(data)
    min_column = data['min'].dropna().drop_duplicates().sort_values()
    current_value = data.iloc[-1, 4]
    order = None
    logger.info("   highest value: {}, current value: {}".format(highest_value, current_value))
    if isInitial or (highest_value < current_value):
        highest_value = current_value
        logger.info("   new high: {}".format(highest_value))
        resistance_found = False
        row = -1
        while not resistance_found:
            if row >= (-1) * len(min_column):
                resistance = min_column.iloc[row]
                diff = (current_value - resistance) / current_value
                if (diff >= max_loss):
                    logger.info("   set new sell triger: {}".format(resistance))
                    order = sell_order(exchange, ticker, size, resistance)
                    resistance_found = True
                else:
                    row -= 1
            else:
                resistance = min_column.iloc[(-1) * len(min_column)]
                logger.info("   set new sell triger: {}".format(resistance))
                order = sell_order(exchange, ticker, size, resistance)
                resistance_found = True
    else:
        logger.info("   No new sell trigger")
    return highest_value, order


def sell_order_take_profit(exchange, ticker, size, takeProfitPrice):
    logger.info("   put sell order take profit- Ticker: {}, Size: {}, takeProfitPrice: {}".format(ticker, size, takeProfitPrice))
    order = exchange.create_take_profit_order(ticker, size, takeProfitPrice)
    logger.info("   sell TP order id : {}".format(order))


def sell_order(exchange, ticker, size, stopLossPrice):
    exchange.cancel_orders(ticker)
    logger.info("   put sell order - Ticker: {}, Size: {}, stopLossPrice: {}".format(ticker, size, stopLossPrice))
    order = exchange.create_stop_loss_order(ticker, size, stopLossPrice)
    logger.info("   sell order id : {}".format(order))
    return order



def run_trader():

    exchange = Exchange("bitget")
    running = True
    asset_with_balance, price = find_asset_with_balance(exchange)

    while running:
        usd_balance = get_base_currency_balance(exchange)
        if not asset_with_balance:
            selected_Ticker, market_movement, major_move, increased_volume, buy_signals, lowest_distance_to_max = get_candidate(exchange)
            #helper.write_to_db(market=market_movement, base_currency=base_currency, selected_ticker=selected_Ticker, major_move=major_move, increase_volume=increased_volume, buy_signal=buy_signals, close_to_maximum=lowest_distance_to_max)
            buy_decision = True
        else:
            selected_Ticker = asset_with_balance
            try:
                size = get_Ticker_balance(exchange, selected_Ticker)
                if isinstance(price, float):
                    take_profit_price = price * (1 + (take_profit_in_percent/100))
                    sell_order = sell_order_take_profit(exchange, selected_Ticker, size, take_profit_price)
                    logger.info(sell_order)
            except Exception as e:
                print(e)
                logger.info("Take Profit Sell Order exists.")
            #helper.write_to_db(base_currency=base_currency, selected_ticker=selected_Ticker)

        if selected_Ticker:
            buy_attempts = 1
            #observe selected Ticker
            buy_decision = False
           
            while (not buy_decision and buy_attempts <= buy_attempts_nr and not asset_with_balance):
                is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff = is_buy_decision(exchange, selected_Ticker , buy_attempts)
                #helper.write_to_db(selected_ticker=selected_Ticker, is_buy=is_buy, current_close=current_close, last_max=last_max, previous_max=previous_max, vwap=vwap, macd=macd, macd_signal=macd_signal, macd_diff=macd_diff)
                if not is_buy:
                    buy_attempts += 1
                    helper.wait("short")
                else:
                    price = current_close
                    buy_decision = True
                if not get_lowest_difference_to_maximum(exchange, [selected_Ticker]):
                    buy_attempts = buy_attempts_nr
            
            if buy_decision or asset_with_balance:

                #buy sleected Ticker
                if not asset_with_balance:
                    market_movement = get_market_movement(get_tickers(exchange))
                    funding = get_funding(usd_balance, market_movement)
                    buy_order_info = buy_order(exchange, selected_Ticker, price, funding)
                    logger.info(buy_order_info)
                    size = get_Ticker_balance(exchange, selected_Ticker)
                    if isinstance(price, float):
                        take_profit_price = price * (1 + (take_profit_in_percent/100))
                        sell_order = sell_order_take_profit(exchange, selected_Ticker, size, take_profit_price)
                        logger.info(sell_order)
                    #helper.write_to_db(selected_ticker=selected_Ticker, funding=funding, buy_order_id=buy_order['id'])

                #adjust sell order
                adjust_sell_trigger = True
                if asset_with_balance:
                    isInitial = False
                else:
                    isInitial = True

                highest_value = price
                current_order_id = None
                while adjust_sell_trigger:
                    tickers = get_tickers(exchange)
                    market_movement = get_market_movement(tickers)
                    _, max_loss = get_market_factor(market_movement)
                    size = get_Ticker_balance(exchange, selected_Ticker)
                    if still_has_postion(size, highest_value):
                        highest_value, order = set_sell_trigger(exchange, isInitial, selected_Ticker, size, highest_value, max_loss)
                        print(order)
                        if order:
                            if current_order_id: exchange.cancel_order(current_order_id)
                            #current_order_id = order['orderId']
                        #if order:
                        #    helper.write_to_db(selected_ticker=selected_Ticker, sell_order_id=0)
                        isInitial = False
                        helper.wait("short")
                    else:
                        logger.info("Asset has been sold!")
                        adjust_sell_trigger = False
                        asset_with_balance = None
                        buy_decision = False
        else:  
            logger.info("No Asset selected!")
            helper.wait("long")


if __name__ == "__main__":
    run_trader()
    


