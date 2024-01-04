import os
import json
import trader
import exchanges

exchange = exchanges.cryptocom()

position_file = "positions.json"

coins = {
    "XRP": {"product": "XRP/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "SOL": {"product": "SOL/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "XLM": {"product": "XLM/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "CRO": {"product": "CRO/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "NEAR": {"product": "NEAR/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
}


def synchronize_coins_dict():
    print(os.getcwd())
    try:
        coins_from_file = coins_dict_from_file()
        for f_coin in coins_from_file.keys():
            if f_coin in coins:
                coins[f_coin]["last_executed_buy_price"] = coins_from_file[f_coin][
                    "last_executed_buy_price"
                ]
    except Exception as e:
        print(e)
    coins_dict_to_file()
    return coins


def coins_dict_to_file():
    with open(position_file, "w") as pf:
        json.dump(coins, pf, indent = 2)


def coins_dict_from_file():
    with open(position_file, "r") as pf:
        return json.load(pf)


def get_funding():
    total = 0
    coin_keys = coins.keys()
    for key in coin_keys:
        try:
            current_balance = exchange.fetch_balance()[key]["free"]
        except:
            current_balance = 0
        current_price = exchange.fetch_ticker(coins[key]["product"])["last"]
        if current_balance * current_price < 1:
            total = total + float(coins[key]["dist_ratio"]) * 10

    ratio = (coins[coin]["dist_ratio"] * 10) / total
    return (exchange.fetch_balance()["USDT"]["free"] * ratio) - 1


        