import datetime as dt
import data_provider.DataReader as data_provider
import exchange.ExchangeHandler as exchange_provider


start_date = dt.datetime(2023, 1, 1)
end_date = dt.datetime(2023, 9, 15)


data = data_provider.instatiate("messari").price_data("perp", start_date, end_date)

# exchange = exchange_provider.instatiate("coinbase").description()

# data = data_provider.instatiate("coinbase").currency_catalog()


print(data)
