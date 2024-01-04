import pandas as pd
import numpy as np

data1 = {'Name': ['Tom', 'nick', 'krish', 'jack'],
        'Age': [20, 21, 19, 18]}

df1 = pd.DataFrame(data1)



print(df1)

print("********")

for i in range(len(df1)):
    print(df1.iloc[i, 1])


print(df1.iloc[-1, 0])