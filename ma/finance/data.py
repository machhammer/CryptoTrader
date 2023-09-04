import importlib
import config as cfg
import datetime as dt

import exchange.CBHandler as ch

start_date = dt.datetime(2020, 1, 1)
end_date = dt.datetime(2023, 1, 1)


MyClass = getattr(importlib.import_module(cfg.data_provider["stocks"]), "Reader")
instance = MyClass()

print(instance.price_data("aapl", start_date, end_date))


coinbase = ch.Handler()
print(coinbase.current_user()["name"])
