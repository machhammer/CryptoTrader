import logging
import numpy as np

from ta.trend import SMAIndicator
from ta.trend import AroonIndicator

import matplotlib.pyplot as plt

from datetime import datetime

class V3:

    name = "Version 3.0"

    def __init__(
        self,
        scenario,
        params = {
            "sma": 0,
            "aroon": 0,
            "profit_threshold": 0,
            "sell _threshold": 0,
            "urgency_sell": 0,
            "pos_neg_threshold": 0,
        }
    ):
        self.params = params
        self.scenario = scenario

    def apply_indicators(self, df):
       
        indicator_SMA = SMAIndicator(close=df["close"], window=self.params["sma"])
        df["sma"] = indicator_SMA.sma_indicator()

        indicator_AROON = AroonIndicator(
            high=df["high"], low=df["low"], window=self.params["aroon"]
        )
        df["aroon_up"] = indicator_AROON.aroon_up()
        df["aroon_down"] = indicator_AROON.aroon_down()

        df["aroon_buy_alert"] = np.where((df["aroon_up"] > df["aroon_down"]), True, False)
        df["aroon_sell_alert"] = np.where((df["aroon_up"] > df["aroon_down"]), False, True)

        df["ACTION"] = 0
        
        return df


    def live_trading_model(self,
        dataset,
        logger,
        highest_price,
        mood,
        pos_neg,
        pos_neg_median,
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
            if pos_neg_median > self.params["pos_neg_threshold"]:
                if logger:
                    logger.info("{}, Up: {:.4f}, Down: {:.4f}, SMA: {:.4f}, Price Open: {:.4f}, Price close: {:.4f}".format(dataset.iloc[i-5, 0],
                        dataset.iloc[i-5, 7],
                        dataset.iloc[i-5, 8], dataset.iloc[i-5, 6], dataset.iloc[i-5, 1], dataset.iloc[i-5, 4]))
                    logger.info("{}, Up: {:.4f}, Down: {:.4f}, SMA: {:.4f}, Price Open: {:.4f}, Price close: {:.4f}".format(dataset.iloc[i-4, 0],
                        dataset.iloc[i-4, 7],
                        dataset.iloc[i-4, 8], dataset.iloc[i-4, 6], dataset.iloc[i-4, 1], dataset.iloc[i-4, 4]))
                    logger.info("{}, Up: {:.4f}, Down: {:.4f}, SMA: {:.4f}, Price Open: {:.4f}, Price close: {:.4f}".format(dataset.iloc[i-3, 0],
                        dataset.iloc[i-3, 7],
                        dataset.iloc[i-3, 8], dataset.iloc[i-3, 6], dataset.iloc[i-3, 1], dataset.iloc[i-3, 4]))
                    logger.info("{}, Up: {:.4f}, Down: {:.4f}, SMA: {:.4f}, Price Open: {:.4f}, Price Close: {:.4f}".format(dataset.iloc[i-2, 0],
                        dataset.iloc[i-2, 7],
                        dataset.iloc[i-2, 8], dataset.iloc[i-2, 6], dataset.iloc[i-2, 1], dataset.iloc[i-2, 4]))
                    logger.info("{}, Up: {:.4f}, Down: {:.4f}, SMA: {:.4f}, Price Open: {:.4f}, Price Close: {:.4f}".format(dataset.iloc[i-1, 0],
                        dataset.iloc[i-1, 7],
                        dataset.iloc[i-1, 8], dataset.iloc[i-1, 6], dataset.iloc[i-1, 1], dataset.iloc[i-1, 4]))
                    logger.info("{}, Up: {:.4f}, Down: {:.4f}, SMA: {:.4f}, Price Open: {:.4f}, Price Close: {:.4f}".format(dataset.iloc[i, 0],
                        dataset.iloc[i, 7],
                        dataset.iloc[i, 8], dataset.iloc[i, 6], dataset.iloc[i, 1], dataset.iloc[i, 4]))
                
                if (
                    (dataset.iloc[i - 5, 8] >= dataset.iloc[i - 5, 7])
                    and (dataset.iloc[i, 7] > dataset.iloc[i, 8])
                    and (dataset.iloc[i, 6] < dataset.iloc[i, 4]) and (dataset.iloc[i, 6] < dataset.iloc[i, 1])
                    and (dataset.iloc[i, 7] >= 95 or dataset.iloc[i - 1, 7] >= 95)
                ):
                    buy_sell_decision = 1
                else:
                    if logger:
                        logger.info("Buy condition not met")               

        if has_position:
            down_price = (1 - self.params["sell_threshold"] / 100) * highest_price
            up_price = (1 + self.params["profit_threshold"] / 100) * position["price"] 
            if logger:
                logger.info(
                    "{}, C: {:.4f}, High: {:.4f}, Sell Down <= {:.4f}%: {:.4f} , Sell Up >= {:.4f}%: {:.4f}".format(
                        dataset.iloc[i, 0],
                        dataset.iloc[i, 4],
                        highest_price,
                        self.params["sell_threshold"],
                        down_price,
                        self.params["profit_threshold"],
                        up_price,
                    )
                )
            if (
                dataset.iloc[i, 4] <= down_price
                and (dataset.iloc[i, 6] > dataset.iloc[i, 4]) and (dataset.iloc[i, 6] > dataset.iloc[i, 1])
            ):
                if logger:
                    logger.info("{}, Sell Decision: Price close: {:.4f} <= Down Price: {:.4f} and SMA: {:.4f}, Proce open: {:.4f}".format(dataset.iloc[i, 0],
                        dataset.iloc[i, 4], down_price, dataset.iloc[i, 6], dataset.iloc[i, 1]))
                    
                buy_sell_decision = -1
            
            if (
                dataset.iloc[i, 4]
                >= up_price
            ):
                if dataset.iloc[i, 6] > dataset.iloc[i, 4]:
                    if (dataset.iloc[i, 7] < dataset.iloc[i, 8]) and (dataset.iloc[i, 8] == 100 or dataset.iloc[i - 1, 8] == 100):
                        if logger:
                            logger.info("{}, Sell Decision: SMA: {:.4f} > Price close: {:.4f}".format(dataset.iloc[i, 0],
                                dataset.iloc[i, 6], dataset.iloc[i, 4]))
                    
                            logger.info("{}, Sell Decision: Up: {:.4f} < Down: {:.4f}, Price Close: {:.4f}".format(dataset.iloc[i, 0],
                                dataset.iloc[i, 7],
                                dataset.iloc[i, 8], dataset.iloc[i, 4]))
                    
                        buy_sell_decision = -1

        return buy_sell_decision


    def show_plot(self, df):
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
