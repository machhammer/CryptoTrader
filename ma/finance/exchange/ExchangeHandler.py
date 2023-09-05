from abc import ABC, abstractmethod
import credentials
import config as cfg
from coinbase.wallet.client import Client


class ExchangeHandler(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def description(self):
        pass

    @abstractmethod
    def user(self):
        pass


def instatiate(reader) -> ExchangeHandler:
    return globals()[cfg.exchange_provider[reader]]()


class CoinbaseHandler(ExchangeHandler):
    def connect(self):
        self.client = Client(
            credentials.provider_1["key"], credentials.provider_1["secret"]
        )

    def description(self):
        return "Coinbase"

    def user(self):
        return self.client.get_current_user()
