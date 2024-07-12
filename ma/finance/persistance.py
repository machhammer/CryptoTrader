# Module Imports
import mariadb
import sys
import credentials
import pandas as pd
from datetime import datetime


def connect():
    # Connect to MariaDB Platform
    try:
        conn = mariadb.connect(
            user=credentials.mariadb.get("user"),
            password=credentials.mariadb.get("password"),
            host=credentials.mariadb.get("host"),
            port=credentials.mariadb.get("port"),
            database=credentials.mariadb.get("database")
    )
    except mariadb.Error as e:
        
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)

    # Get Cursor
    
    return conn


def test_connection():
    connection = connect()
    connection.close()


def initialize_manager_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE manager " \
            "( "\
                "timestamp TIMESTAMP, "\
                "starting_balance FLOAT, "\
                "current_balance FLOAT, "\
                "winner INT, "\
                "looser INT, "\
                "pos_neg FLOAT, "\
                "pos_neg_median FLOAT, "\
                "fear_and_greed INT "\
            ")"
    connection.cursor().execute(create_table)


def initialize_screener_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE screener " \
            "( "\
                "timestamp TIMESTAMP, "\
                "market FLOAT, "\
                "market_factor FLOAT, "\
                "base_currency VARCHAR(3), "\
                "selected_ticker VARCHAR(10), "\
                "major_move TEXT, "\
                "increase_volume TEXT, "\
                "buy_signal TEXT, "\
                "close_to_maximum TEXT, "\
                "is_buy BOOL, "\
                "current_close FLOAT, "\
                "last_max FLOAT, "\
                "previous_max FLOAT, "\
                "vwap FLOAT, "\
                "macd FLOAT, "\
                "macd_signal FLOAT, "\
                "macd_diff FLOAT, "\
                "buy_order_id TINYTEXT, "\
                "sell_order_id TINYTEXT "\
            ")"
    connection.cursor().execute(create_table)

def insert_screener(timestamp, market, market_factor, base_currency, selected_ticker, major_move, increase_volume, buy_signal, close_to_maximum, is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff, buy_order_id, sell_order_id):
    connection = connect()
    query = "INSERT INTO trader " \
        "(timestamp, market, market_factor, base_currency, selected_ticker, major_move, increase_volume, buy_signal, close_to_maximum, is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff, buy_order_id, sell_order_id) " \
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(timestamp, market, market_factor, base_currency, selected_ticker, major_move, increase_volume, buy_signal, close_to_maximum, is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff, buy_order_id, sell_order_id)
    values = (timestamp, market, market_factor, base_currency, selected_ticker, major_move, increase_volume, buy_signal, close_to_maximum, is_buy, current_close, last_max, previous_max, vwap, macd, macd_signal, macd_diff, buy_order_id, sell_order_id)
    connection.cursor().execute(query, values)
    connection.commit()
    connection.close()



def initialize_trader_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE trader " \
            "( "\
                "timestamp TIMESTAMP, "\
                "chart_time TIMESTAMP, "\
                "coin VARCHAR(10), "\
                "sma INT, "\
                "aroon INT, "\
                "profit_threshold INT, "\
                "sell_threshold INT, "\
                "pnl FLOAT, "\
                "c_price FLOAT "\
            ")"
    connection.cursor().execute(create_table)


def initialize_transaction_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE transactions " \
            "( "\
                "timestamp TIMESTAMP, "\
                "coin VARCHAR(10), "\
                "type VARCHAR(5), "\
                "amount FLOAT, "\
                "price FLOAT "\
            ")"
    connection.cursor().execute(create_table)


def initialize_optimizer_results_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE optimizer_results " \
            "( "\
                "coin VARCHAR(10), "\
                "sma INT, "\
                "aroon INT, "\
                "profit_threshold FLOAT, "\
                "sell_threshold FLOAT, "\
                "pos_neg_threshold FLOAT, "\
                "pnl FLOAT"\
            ")"
    connection.cursor().execute(create_table)

def initialize_optimizer_results_transactions_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE optimizer_results_transactions " \
            "( "\
                "timestamp TIMESTAMP, "\
                "coin VARCHAR(10), "\
                "sma INT,"\
                "aroon INT, "\
                "profit_threshold FLOAT, "\
                "sell_threshold FLOAT, "\
                "pos_neg_threshold FLOAT, "\
                "type VARCHAR(10), "\
                "price FLOAT, "\
                "budget FLOAT, "\
                "pnl FLOAT"\
            ")"
    connection.cursor().execute(create_table)


def insert_manager(timestamp, starting_balance, current_balance, winner, looser, pos_neg, pos_neg_median, fear_and_greed):
    connection = connect()
    insert_record = "INSERT INTO manager " \
        "(timestamp, starting_balance, current_balance, winner, looser, pos_neg, pos_neg_median, fear_and_greed) "\
        "VALUES ('{}', {}, {}, {}, {}, {}, {}, {})".format(timestamp, starting_balance, current_balance, winner, looser, pos_neg, pos_neg_median, fear_and_greed)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()


def starting_balance():
    connection = connect()
    cursor = connection.cursor()
    select_record = "SELECT starting_balance FROM manager ORDER by timestamp DESC LIMIT 1"
    cursor.execute(select_record)
    current_balance = 0
    for element in cursor:
        current_balance = element[0]
    connection.close()
    return current_balance

def execute_select(select):
    connection = connect()
    cursor = connection.cursor()
    cursor.execute(select)
    rows = cursor.fetchall()
    connection.close()
    return pd.DataFrame(rows)

def insert_trader(timestamp, chart_time, coin, sma, aroon, profit_threshold, sell_threshold, pos_neg_threshold, pnl, c_price):
    connection = connect()
    insert_record = "INSERT INTO trader " \
        "(timestamp, chart_time, coin, sma, aroon, profit_threshold, sell_threshold, pnl, c_price, pos_neg_threshold) "\
        "VALUES ('{}', '{}', '{}', {}, {}, {}, {}, {}, {}, {})".format(timestamp, chart_time, coin, sma, aroon, profit_threshold, sell_threshold, pnl, c_price, pos_neg_threshold)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()


def insert_transaction(timestamp, coin, type, amount, price):
    connection = connect()
    insert_record = "INSERT INTO transactions " \
        "(timestamp, coin, type, amount, price) "\
        "VALUES ('{}', '{}', '{}', {}, {})".format(timestamp, coin, type, amount, price)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()

def generate_optimizer_results(coin, data):
    initialize_optimizer_results_table()
    connection = connect()
    for i in range(len(data)):
        insert_record = "INSERT INTO optimizer_results " \
            "(coin, sma, aroon, profit_threshold, sell_threshold, pos_neg_threshold, pnl) "\
            "VALUES ('{}', {}, {}, {}, {}, {}, {})".format(coin, data.iloc[i, 0], data.iloc[i, 1], data.iloc[i, 2], data.iloc[i, 3], data.iloc[i, 4], data.iloc[i, 5])
        connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()

def insert_optimizer_results_transactions(connection, timestamp, coin, sma, aroon,  profit_threshold, sell_threshold, pos_neg_threshold, type, price, budget, pnl):
    insert_record = "INSERT INTO optimizer_results_transactions " \
        "(timestamp, coin, sma, aroon,  profit_threshold, sell_threshold, pos_neg_threshold, type, price, budget, pnl) "\
        "VALUES ('{}', '{}', {}, {}, {}, {}, {}, '{}', {}, {}, {})".format(timestamp, coin, sma, aroon,  profit_threshold, sell_threshold, pos_neg_threshold, type, price, budget, pnl)
    connection.cursor().execute(insert_record)



if __name__ == "__main__":
    initialize_screener_table()


