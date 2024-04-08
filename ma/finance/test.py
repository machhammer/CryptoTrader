import yfinance as yf
import pandas as pd

yf.pdr_override()


data = pd.DataFrame(yf.download("SOL-USD", period="5d", interval="1h", progress=False))


print(data)


print("Dies ist ein Test")