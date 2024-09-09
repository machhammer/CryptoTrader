from flask import Flask
from flask_cors import CORS, cross_origin
from datetime import datetime
import pandas as pd
from datetime import datetime

import Database as database

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route("/")
def trading_info():
    result = database.execute_select("select * from trading_info where DATE(timestamp) = CURDATE() order by timestamp desc")
    result.rename(columns={ result.columns[0]: "Timestamp" }, inplace = True)
    result.rename(columns={ result.columns[1]: "Symbol" }, inplace = True)
    result.rename(columns={ result.columns[2]: "Transaction" }, inplace = True)
    result.rename(columns={ result.columns[3]: "Price" }, inplace = True)
    result.rename(columns={ result.columns[4]: "Market" }, inplace = True)
    result['Timestamp']=result['Timestamp'].astype(str)
    result = (result.to_json(orient='records'))
    return result

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050)