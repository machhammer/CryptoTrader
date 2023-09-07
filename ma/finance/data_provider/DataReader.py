import requests
import pandas_datareader as web
import pandas as pd
import config as cfg
from abc import ABC, abstractmethod
import yahoo_fin.stock_info as yahoo_fin


class DataReader(ABC):
    @abstractmethod
    def historic_price_data(self, symbol, start, end):
        pass

    @abstractmethod
    def price(self, symbol):
        pass

    @abstractmethod
    def currency_catalog(self):
        pass


def instatiate(reader) -> DataReader:
    try:
        return globals()[cfg.data_provider[reader]]()
    except:
        raise Exception("DataReader ID not found: " + reader)


# ****************************************************************************************************


class YahooDataReader(DataReader):
    def historic_price_data(self, symbol, start, end):
        return yahoo_fin.get_data(
            symbol, start_date=start, end_date=end, index_as_date=True, interval="1d"
        )

    def price(self, symbol):
        return yahoo_fin.get_live_price(symbol)

    def currency_catalog(self):
        raise Exception("Not implemented!")


# ****************************************************************************************************


class CoinbaseDataReader(DataReader):
    def historic_price_data(self, symbol, start, end):
        raise Exception("Not implemented!")

    def price(self, symbol):
        raise Exception("Not implemented!")

    def currency_catalog(self):
        api_url = f"https://api.exchange.coinbase.com/currencies"
        raw = requests.get(api_url).json()
        df = pd.json_normalize(raw)

        return df


# ****************************************************************************************************


class MessariDataReader(DataReader):
    def historic_price_data(self, symbol, start, end):
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

    def price(self, symbol):
        raise Exception("Not implemented!")

    def currency_catalog(self):
        raise Exception("Not implemented!")


# ****************************************************************************************************


class StooqDataReader(DataReader):
    def historic_price_data(self, symbol, start_date, end_date):
        try:
            return web.DataReader(symbol, "stooq", start_date, end_date)
        except:
            raise Exception("Error connecting to Pandas 'stooq'")

    def price(self, symbol):
        raise Exception("Not implemented!")

    def currency_catalog(self):
        raise Exception("Not implemented!")
