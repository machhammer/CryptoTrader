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
    "sma": 14,
    "rsi": 14,
    "macd_slow": 26,
    "macd_fast": 12,
    "macd_sign": 9,
    "adx": 6,
    "aroon": 26,
    "bb": 20,
    "bb_dev": 2.5,
    "rsi_buy_threshold": 33,
    "rsi_sell_threshold": 73,
    "profit_threshold": 1,
    "sell_threshold": 1.5,
    "urgency_sell": 3,
}


def apply_indicators(df):
    indicator_SMA = SMAIndicator(close=df["close"], window=params["sma"])
    df["sma"] = indicator_SMA.sma_indicator()

    indicator_AROON = AroonIndicator(
        high=df["high"], low=df["low"], window=params["aroon"]
    )
    df["aroon_up"] = indicator_AROON.aroon_up()
    df["aroon_down"] = indicator_AROON.aroon_down()

    df["aroon_buy_alert"] = np.where((df["aroon_up"] > df["aroon_down"]), True, False)
    df["aroon_sell_alert"] = np.where((df["aroon_up"] > df["aroon_down"]), False, True)

    df["ACTION"] = 0

    return df


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

    if logger:
        logger.info(
            "{}, Has Pos: {}, O-Price: {:.4f}, C-Price: {:.4f}, H-Price: {:.4f}, A-Up: {:.0f}, A-Down: {:.0f}, SMA: {:.4f}, Mood: {:.2f}, Buy/Sell {}".format(
                dataset.iloc[i, 0],
                has_position,
                position["price"],
                dataset.iloc[i, 4],
                highest_price,
                dataset.iloc[i, 7],
                dataset.iloc[i, 8],
                dataset.iloc[i, 6],
                mood,
                buy_sell_decision,
            )
        )

    if not has_position:
        if mood > 0.2:
            if logger:
                logger.info("{}, Up: {:.4f}, Down: {:.4f}, Price: {:.4f}".format(dataset.iloc[i-3, 0],
                    dataset.iloc[i-3, 7],
                    dataset.iloc[i-3, 8], dataset.iloc[i-3, 4]))
                logger.info("{}, Up: {:.4f}, Down: {:.4f}, Price: {:.4f}".format(dataset.iloc[i-2, 0],
                    dataset.iloc[i-2, 7],
                    dataset.iloc[i-2, 8], dataset.iloc[i-2, 4]))
                logger.info("{}, Up: {:.4f}, Down: {:.4f}, Price: {:.4f}".format(dataset.iloc[i-1, 0],
                    dataset.iloc[i-1, 7],
                    dataset.iloc[i-1, 8], dataset.iloc[i-1, 4]))
                logger.info("{}, Up: {:.4f}, Down: {:.4f}, Price: {:.4f}".format(dataset.iloc[i, 0],
                    dataset.iloc[i, 7],
                    dataset.iloc[i, 8], dataset.iloc[i, 4]))
            
            if (
                (dataset.iloc[i - 2, 8] > dataset.iloc[i - 2, 7])
                and (dataset.iloc[i, 7] > dataset.iloc[i, 8])
                and dataset.iloc[i, 7] == 100
            ):
                buy_sell_decision = 1

    if has_position:
        down_price = (1 - params["sell_threshold"] / 100) * highest_price
        up_price = (1 + params["profit_threshold"] / 100) * position["price"] 
        if logger:
            logger.info(
                "{}, C: {}, High: {}, Sell Down < {}%: {} , Sell Up > {}%: {}".format(
                    dataset.iloc[i, 0],
                    dataset.iloc[i, 4],
                    highest_price,
                    params["sell_threshold"],
                    down_price,
                    params["profit_threshold"],
                    up_price,
                )
            )
        if (
            dataset.iloc[i, 4] <= down_price
        ) :
            buy_sell_decision = -1
        
        if (
            dataset.iloc[i, 4]
            >= up_price
        ):
            if dataset.iloc[i, 6] > dataset.iloc[i, 4]:
                buy_sell_decision = -1

            if dataset.iloc[i, 7] <= dataset.iloc[i, 8]:
                buy_sell_decision = -1

    return buy_sell_decision


def show_plot(df):
    figure, axis = plt.subplots(
        2, sharex=True, figsize=(16, 9), gridspec_kw={"height_ratios": [4, 2]}
    )

    axis[0].plot(df["timestamp"], df["close"], linewidth=2)
    axis[0].plot(df["timestamp"], df["sma"])

    action_copy = df.copy(deep=True)
    action_copy = action_copy[action_copy["ACTION"] == 1]
    axis[0].scatter(action_copy["timestamp"], action_copy["close"], c="blue")
    action_copy = None

    action_copy = df.copy(deep=True)
    action_copy = action_copy[action_copy["ACTION"] == -1]
    axis[0].scatter(action_copy["timestamp"], action_copy["close"], c="red")
    action_copy = None

    axis[1].set_title("Aroon", fontsize="small", loc="left")
    axis[1].plot(df["timestamp"], df["aroon_up"])
    axis[1].plot(df["timestamp"], df["aroon_down"])

    plt.show()
