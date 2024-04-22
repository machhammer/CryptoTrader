from scenarios import S1
from models import V3

class A:
    params = {
        "exchange": "cryptocom",
        "commission": 0.075 / 100,
        "base_currency": "USDT",
        "number_of_attempts_for_random_coins_wo_position": 24,
        "ignore_coins": ["USDT", "USD", "CRO", "PAXG"],
        "coins_amount": 1,
        "fix_coins": ["SOL"],
    }


if __name__ == "__main__":
    scenario = V3(params = {
        "exchange": "cryptocom",
        "commission": 0.075 / 100,
        "base_currency": "USDT",
        "number_of_attempts_for_random_coins_wo_position": 24,
        "ignore_coins": ["USDT", "USD", "CRO", "PAXG"],
        "coins_amount": 1,
        "fix_coins": ["SOL"],
    }, none)


    scenario.params["exchange"] = "hallo"
