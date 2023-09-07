import requests
import pandas_datareader as web
import pandas as pd
import config as cfg
from abc import ABC, abstractmethod


class DataReader(ABC):
    @abstractmethod
    def price_data(self, symbol, start, end):
        pass

    @abstractmethod
    def currency_catalog(self, symbol, start, end):
        pass


def instatiate(reader) -> DataReader:
    try:
        return globals()[cfg.data_provider[reader]]()
    except:
        raise Exception("DataReader ID not found: " + reader)


class CoinbaseDataReader(DataReader):
    def price_data(self, symbol, start, end):
        raise Exception("Not implemented!")

    def currency_catalog(self):
        api_url = f"https://api.exchange.coinbase.com/currencies"
        raw = requests.get(api_url).json()
        # df = pd.DataFrame(raw)
        df = pd.json_normalize(raw)

        return df


class MessariDataReader(DataReader):
    def price_data(self, symbol, start, end):
        try:
            api_url = f"https://data.messari.io/api/v1/markets/binance-{symbol}-usdt/metrics/price/time-series?start={start}&end={end}&interval=1d"
            raw = requests.get(api_url).json()
            df = pd.DataFrame(raw["data"]["values"])
            df = df.rename(
                columns={
                    0: "date",
                    1: "open",
                    2: "high",
                    3: "low",
                    4: "close",
                    5: "volume",
                }
            )
            df["date"] = pd.to_datetime(df["date"], unit="ms")
            df = df.set_index("date")
            return df
        except KeyError:
            raise Exception("No data found for symbol: " + symbol)
        except:
            raise Exception("Error connecting to Messari")

    def currency_catalog(self):
        raise Exception("Not implemented!")


class StooqDataReader(DataReader):
    def price_data(self, symbol, start_date, end_date):
        try:
            return web.DataReader(symbol, "stooq", start_date, end_date)
        except:
            raise Exception("Error connecting to Pandas 'stooq'")

    def currency_catalog(self):
        raise Exception("Not implemented!")
