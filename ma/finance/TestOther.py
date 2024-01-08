import exchanges
import pandas as pd

exchange = exchanges.cryptocom()

coin = "XLM/USDT"

trades = exchange.fetch_my_trades(coin)
if len(trades) > 0:
    if trades[-1]["side"] == "buy":
        print(trades[-1]["traded_price"])


exit()

print(trades)
print(trades["side"])
print(trades["timestamp"])
# print(pd.to_datetime(trades["timestamp"], unit="ms"))

bars = exchange.fetch_ohlcv(coin, timeframe="15m", limit=300, since=trades["timestamp"])
data = pd.DataFrame(
    bars[:-1], columns=["timestamp", "open", "high", "low", "close", "volume"]
)
data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
print(data)
