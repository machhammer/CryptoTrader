from datetime import datetime

class S1:

    params = {
        "exchange": "cryptocom",
        "commission": 0.2 / 100,
        "base_currency": "USDT",
        "number_of_attempts_for_random_coins_wo_position": 24,
        "ignore_coins": ["USDT", "USD", "CRO", "PAXG"],
        "coins_amount": 1,
        "fix_coins": ["SOL"],
        "STOP_TRADING_EMERGENCY_THRESHOLD": -100,
        "frequency": 300,
        "timeframe": "5m",
        "mood_threshold": 0.0,
        "days_for_optimizing": 2.5,
    }

    name = "Scenario v1.0"


    def get_wait_time(self):
        minute = datetime.now().minute
        wait_time = (5 - (minute % 5)) * 60
        return wait_time