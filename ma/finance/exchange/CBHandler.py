from coinbase.wallet.client import Client
import credentials


class Handler:
    def __init__(self):
        self.client = Client(
            credentials.provider_1["key"], credentials.provider_1["secret"]
        )

    def current_user(self):
        return self.client.get_current_user()
