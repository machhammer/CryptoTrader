import requests
import pandas as pd


class Reader:
    def price_data(self, symbol, start, end):
        api_url = f"https://data.messari.io/api/v1/markets/binance-{symbol}-usdt/metrics/price/time-series?start={start}&end={end}&interval=1d"
        raw = requests.get(api_url).json()
        df = pd.DataFrame(raw["data"]["values"])
        df = df.rename(
            columns={0: "date", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume"}
        )
        df["date"] = pd.to_datetime(df["date"], unit="ms")
        df = df.set_index("date")
        return df
