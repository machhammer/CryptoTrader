from exchanges import Exchange

coin = 'SOL'


exchange = Exchange("cryptocom")



current_assets = exchange.fetch_balance()["free"]
balance = 0
for asset in current_assets:
    if not asset in ["USD"]:
        price = exchange.fetch_ticker(asset + "/USD")["last"] * current_assets[asset]
    else:
        price = current_assets[asset]
    balance = balance + price


print(balance)