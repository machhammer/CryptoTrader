import logging
import numpy as np

from ta.trend import SMAIndicator
from ta.trend import ADXIndicator
from ta.trend import AroonIndicator
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

import matplotlib.pyplot as plt


params = {
    "sma": 10,
    "rsi": 14,
    "macd_slow": 26,
    "macd_fast": 12,
    "macd_sign": 9,
    "adx": 6,
    "aroon": 9,
    "bb": 20,
    "bb_dev": 2,
    "rsi_buy_threshold": 33,
    "rsi_sell_threshold": 73,
    "profit_threshold": 5,
    "urgency_sell": 3,
}

def apply_bb_buy_sell(df):
    buy = False
    sell = False
    for i in range(len(df)):
        if df.iloc[i, 30] < 0.15:
            buy = True
            sell = False
        if df.iloc[i, 30] >= 0.15 and df.iloc[i, 30] <= 0.85:
            buy = False
            sell = False
        if df.iloc[i, 30] > 0.85:
            sell = True 
            buy = False
        df.iloc[i, 31] = buy
        df.iloc[i, 32] = sell
    return df

def apply_rsi_buy_sell(df):
    buy = False
    sell = False
    for i in range(len(df)):
        if df.iloc[i, 9] < params["rsi_buy_threshold"]:
            buy = True
            sell = False
        if df.iloc[i, 9] > params["rsi_sell_threshold"]:
            sell = True 
            buy = False
        df.iloc[i, 10] = buy
        df.iloc[i, 11] = sell
    return df

def apply_indicators(df):
    indicator_SMA = SMAIndicator(close=df["close"], window=params["sma"])
    df["sma"] = indicator_SMA.sma_indicator()

    df["sma_buy_alert"] = np.where((df["sma"] < df["close"]), True, False)
    df["sma_sell_alert"] = np.where((df["sma"] < df["close"]), False, True)

    indicator_RIS = RSIIndicator(close=df["close"], window=params["rsi"])
    df["rsi"] = indicator_RIS.rsi()

    df["rsi_buy_alert"] = False
    df["rsi_sell_alert"] = False

    indicator_MACD = MACD(
        close=df["close"],
        window_fast=params["macd_fast"],
        window_slow=params["macd_slow"],
        window_sign=params["macd_sign"],
    )
    df["macd"] = indicator_MACD.macd()
    df["macd_signal"] = indicator_MACD.macd_signal()

    df["macd_buy_alert"] = np.where((df["macd"] > df["macd_signal"]), True, False)
    df["macd_sell_alert"] = np.where((df["macd"] > df["macd_signal"]), False, True)

    indicator_ADX = ADXIndicator(
        high=df["high"], low=df["low"], close=df["close"], window=params["adx"]
    )
    df["adx_plus"] = indicator_ADX.adx_pos()
    df["adx_neg"] = indicator_ADX.adx_neg()
    df["adx"] = indicator_ADX.adx()

    df["adx_buy_alert"] = np.where(((df["adx_plus"] > df["adx_neg"]) & df["adx_neg"] > 30), True, False)
    df["adx_sell_alert"] = np.where((df["adx_plus"] > df["adx_neg"]), False, True)

    indicator_AROON = AroonIndicator(
        high=df["high"], low=df["low"], window=params["aroon"]
    )
    df["aroon_up"] = indicator_AROON.aroon_up()
    df["aroon_down"] = indicator_AROON.aroon_down()

    df["aroon_buy_alert"] = np.where((df["aroon_up"] > df["aroon_down"]), True, False)
    df["aroon_sell_alert"] = np.where((df["aroon_up"] > df["aroon_down"]), False, True)

    indicator_BB = BollingerBands(
        close=df["close"], window=params["bb"], window_dev=params["bb_dev"]
    )
    df["bb_top"] = indicator_BB.bollinger_hband()
    df["bb_bot"] = indicator_BB.bollinger_lband()
    df["bb_avg"] = indicator_BB.bollinger_mavg()
    df["top_bot_diff"] = indicator_BB.bollinger_hband() - indicator_BB.bollinger_lband()
    df["price_bot_diff"] = df["close"] - indicator_BB.bollinger_lband()

    df["ratio"] = df["price_bot_diff"] / df["top_bot_diff"]
    df["bb_buy_alert"] = False
    df["bb_sell_alert"] = False

    df["BUY_ALERT"] = False
    df["SELL_ALERT"] = False

    df["ACTION"] = 0

    apply_rsi_buy_sell(df)

    apply_bb_buy_sell(df)

    df["BUY_ALERT"] = df.apply(set_buy_alert, axis=1)
    df["SELL_ALERT"] = df.apply(set_sell_alert, axis=1)

    return df


def set_buy_alert(df):
    return [
        df["sma_buy_alert"],
        df["rsi_buy_alert"],
        df["macd_buy_alert"],
        df["adx_buy_alert"],
        df["aroon_buy_alert"],
        df["bb_buy_alert"],
    ].count(True) >= 4


def set_sell_alert(df):
    return [
        df["sma_sell_alert"],
        df["rsi_sell_alert"],
        df["macd_sell_alert"],
        df["adx_sell_alert"],
        df["aroon_sell_alert"],
        df["bb_sell_alert"],
    ].count(True) >= 4


def live_trading_model(
    dataset,
    logger,
    highest_price,
    mood,
    pos_neg,
    index=-1,
    has_position=False,
    position=None,
):
    buy_sell_decision = 0

    i = index

    if buy_sell_decision == 0:
        if has_position:
            if dataset.iloc[i, 4] <= (
                highest_price * (1 - params["urgency_sell"] / 100)
            ):
                logger.info(
                    "URGENCY SELL - Current Price: {}, Highest Price minus urgency sell rate: {}".format(
                        dataset.iloc[i, 4],
                        (highest_price * (1 - params["urgency_sell"] / 100)),
                    )
                )
                buy_sell_decision = -1

    """ if buy_sell_decision == 0:
        if has_position:
            if dataset.iloc[i, 4] >= (
                position["price"] * (1 + params["profit_threshold"] / 100)
            ):
                logger.info(
                    "PROFIT SELL - Current Price: {}, Want to take some profit: {}".format(
                        dataset.iloc[i, 4],
                        (position["price"] * (1 + params["profit_threshold"] / 100)),
                    )
                )
                buy_sell_decision = -1 """

    current_buy_alert = dataset.iloc[i, -3]
    previous_buy_alert = dataset.iloc[i - 1, -3]

    if current_buy_alert == True and previous_buy_alert == True:
        if mood > 1.2:
            if not has_position:
                buy_sell_decision = 1
                logger.info("Buy Decision")
        else:
            logger.info("Don't buy, mood is too bad!")

    current_sell_alert = dataset.iloc[i, -2]
    previous_sell_alert = dataset.iloc[i - 1, -2]
    if current_sell_alert == True and previous_sell_alert == True:
        logger.info("Sell Alert!")
        if has_position:
            logger.info(
                "Condition 1: Sell if Current Price: {} >= Price: {}".format(
                    dataset.iloc[i, 4],
                    (1 + params["profit_threshold"] / 100) * position["price"],
                )
            )
            if (
                dataset.iloc[i, 4]
                >= (1 + params["profit_threshold"] / 100) * position["price"]
            ):
                logger.info("Sell condition 1 met!")
                buy_sell_decision = -1
                logger.info("Sell")
            else:
                logger.info("Sell Condition 1 not met!")
                logger.info(
                    "Condition 2: Sell if Current Price: {} <= Highest Price: {} minus threshold sell: {}".format(
                        dataset.iloc[i, 4], highest_price,
                        (1 - params["profit_threshold"] / 100) * highest_price,
                    )
                )
                if (
                    dataset.iloc[i, 4]
                    <= (1 - params["profit_threshold"] / 100) * highest_price
                ):
                    logger.info("Sell condition 2 met!")
                    buy_sell_decision = -1
                    logger.info("Sell")
                else:
                    logger.info("Sell Condition 2 not met!")
        else:
            logger.info("No position to sell!")

    logger.info(
        "{}, Has Pos: {}, O Price: {}, C Price: {}, H Price: {}, P Buy: {}, C Buy: {}, P Sell: {}, C Sell: {} -> {}".format(
            dataset.iloc[i, 0],
            has_position,
            position["price"],
            dataset.iloc[i, 4],
            highest_price,
            previous_buy_alert,
            current_buy_alert,
            previous_sell_alert,
            current_sell_alert,
            buy_sell_decision,
        )
    )

    return buy_sell_decision


def show_plot(df):
    figure, axis = plt.subplots(
        5, sharex=True, figsize=(16, 9), gridspec_kw={"height_ratios": [4, 1, 1, 1, 1]}
    )

    axis[0].plot(df["timestamp"], df["close"], linewidth=2)
    axis[0].plot(df["timestamp"], df["bb_top"])
    axis[0].plot(df["timestamp"], df["bb_bot"])
    axis[0].plot(df["timestamp"], df["bb_avg"])

    action_copy = df.copy(deep=True)
    action_copy = action_copy[action_copy["ACTION"] == 1]
    axis[0].scatter(action_copy["timestamp"], action_copy["close"], c="blue")
    action_copy = None

    action_copy = df.copy(deep=True)
    action_copy = action_copy[action_copy["ACTION"] == -1]
    axis[0].scatter(action_copy["timestamp"], action_copy["close"], c="red")
    action_copy = None

    axis[1].set_title("RSI", fontsize="small", loc="left")
    axis[1].plot(df["timestamp"], df["rsi"])
    axis[1].axhline(y=30, color="g", linestyle="dotted")
    axis[1].axhline(y=70, color="g", linestyle="dotted")

    axis[2].set_title("MACD", fontsize="small", loc="left")
    axis[2].plot(df["timestamp"], df["macd"])
    axis[2].plot(df["timestamp"], df["macd_signal"])

    axis[3].set_title("ADX", fontsize="small", loc="left")
    axis[3].plot(df["timestamp"], df["adx_plus"])
    axis[3].plot(df["timestamp"], df["adx_neg"])
    axis[3].plot(df["timestamp"], df["adx"])

    axis[4].set_title("Aroon", fontsize="small", loc="left")
    axis[4].plot(df["timestamp"], df["aroon_up"])
    axis[4].plot(df["timestamp"], df["aroon_down"])

    plt.show()
