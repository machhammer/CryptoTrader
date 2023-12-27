import ccxt
import credentials
import pandas as pd

api_key = credentials.provider_1.get("key")
api_secret = credentials.provider_1.get("secret")

config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.coinbase(
    {
        "apiKey": api_key,
        "secret": api_secret,
        # 'verbose': True,  # for debug output
    }
)


def load_transactions_from_exchange():
    if exchange.has["fetchMyTrades"]:
        trades = exchange.fetch_my_trades(
            symbol=None, since=None, limit=None, params={}
        )

        df = pd.DataFrame(
            columns=[
                "Datetime",
                "Symbol",
                "Order",
                "Type",
                "Side",
                "TakerOrMaker",
                "Price",
                "Amount",
                "Cost",
                "Fee",
            ]
        )

        for trade in trades:
            trade_row = {
                "Datetime": trade["datetime"],
                "Symbol": trade["symbol"],
                "Order": trade["order"],
                "Type": trade["type"],
                "Side": trade["side"],
                "TakerOrMaker": trade["takerOrMaker"],
                "Price": trade["price"],
                "Amount": trade["amount"],
                "Cost": trade["cost"],
                "Fee": trade["fee"]["cost"],
            }
            df = pd.concat([df, pd.DataFrame([trade_row])], ignore_index=True)
        df = df.groupby(["Symbol", "Order", "Side"]).agg({"Cost": "sum", "Fee": "sum"})
        df.to_csv("transactions.csv")


def load_transactions_from_file():
    return pd.read_csv("transactions.csv")


if __name__ == "__main__":
    load_transactions_from_exchange()
    print(load_transactions_from_file())
