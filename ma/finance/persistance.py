# Module Imports
import mariadb
import sys
import credentials
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
                "fear_and_greed INT, "\
                "coins VARCHAR(50) "\
            ")"
    connection.cursor().execute(create_table)

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
                "sell_throeshold INT, "\
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
                "price FLOAT, "\
                "fee FLOAT "\
            ")"
    connection.cursor().execute(create_table)

def insert_manager(timestamp, starting_balance, current_balance, winner, looser, pos_neg, pos_neg_median, fear_and_greed):
    connection = connect()
    insert_record = "INSERT INTO manager " \
        "(timestamp, starting_balance, current_balance, winner, looser, pos_neg, pos_neg_median, fear_and_greed) "\
        "VALUES ('{}', {}, {}, {}, {}, {}, {}, {})".format(timestamp, starting_balance, current_balance, winner, looser, pos_neg, pos_neg_median, fear_and_greed)
    print(insert_record)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()

def last_balance():
    connection = connect()
    cursor = connection.cursor()
    select_record = "SELECT current_balance FROM manager ORDER by timestamp DESC LIMIT 1"
    cursor.execute(select_record)
    current_balance = 0
    for element in cursor:
        current_balance = element[0]
    connection.close()
    return current_balance

def insert_trader(timestamp, chart_time, coin, sma, aroon, profit_threshold, sell_threshold, pnl, c_price):
    connection = connect()
    insert_record = "INSERT INTO trader " \
        "(timestamp, starting_balance, current_balance, winner, looser, pos_neg, pos_neg_median, fear_and_greed) "\
        "VALUES ('{}', '{}', '{}', {}, {}, {}, {}, {}, {}, {}, {})".format(timestamp, chart_time, coin, sma, aroon, profit_threshold, sell_threshold, pnl, c_price)
    print(insert_record)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()

def insert_transaction(timestamp, coin, type, amount, price, fee):
    connection = connect()
    insert_record = "INSERT INTO transaction " \
        "(timestamp, coin, type, amount, price, fee) "\
        "VALUES ('{}', '{}', '{}', {}, {}, {})".format(timestamp, coin, type, amount, price, fee)
    print(insert_record)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()



if __name__ == "__main__":
    initialize_manager_table()
    initialize_trader_table()
    initialize_transaction_table()


