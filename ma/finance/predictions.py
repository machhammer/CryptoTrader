import numpy as np
import pandas as pd


data = pd.read_csv("predictions.txt", delimiter=";")

max_date = data["Date"].max()

data = data[data["Date"] == max_date]

data['change'] = (data["Day3"] - data["Day1"]) / data["Day1"]
data.replace([np.inf, -np.inf], np.nan, inplace=True)

data = data.sort_values(by='change', ascending=False)


print(data.head(50))