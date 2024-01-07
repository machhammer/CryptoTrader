import credentials
import json
import ccxt


coin = "XLM"

coins = {
    "XRP": {"product": "XRP/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "SOL": {"product": "SOL/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "XLM": {"product": "XLM/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "CRO": {"product": "CRO/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
    "NEAR": {"product": "NEAR/USDT", "last_executed_buy_price": 0, "dist_ratio": 0.2},
}

api_key = credentials.provider_2.get("key")
api_secret = credentials.provider_2.get("secret")

config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

exchange = ccxt.cryptocom(
    {
        "apiKey": api_key,
        "secret": api_secret,
        #'verbose': True
    }
)
tickers = exchange.fetch_tickers()

dict = {}

for ticker in tickers:
    if 'USDT' in ticker:
        dict['symbol']=ticker
        dict['percentage']=tickers[ticker]['percentage']
        
print(dict)