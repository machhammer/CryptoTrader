# Module Imports
import mariadb
import credentials
import pandas as pd


def connect():
    # Connect to MariaDB Platform
    #try:
    conn = mariadb.connect(
        user=credentials.mariadb.get("user"),
        password=credentials.mariadb.get("password"),
        host=credentials.mariadb.get("host"),
        port=credentials.mariadb.get("port"),
        database=credentials.mariadb.get("database")
)
    #except mariadb.Error as e:
        
    #    print(f"Error connecting to MariaDB Platform: {e}")
    #    sys.exit(1)

    # Get Cursor
    
    return conn


def test_connection():
    connection = connect()
    connection.close()


def initialize_balance_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE balance " \
            "( "\
                "timestamp TIMESTAMP, "\
                "base_currency VARCHAR(5), "\
                "balance FLOAT "\
            ")"
    connection.cursor().execute(create_table)

def insert_balance(timestamp, base_currency, balance):
    connection = connect()
    insert_record = "INSERT INTO balance " \
        "(timestamp, base_currency, balance) "\
        "VALUES ('{}', '{}', {})".format(timestamp, base_currency, balance)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()


def initialize_trading_info_table():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE trading_info " \
            "( "\
                "timestamp TIMESTAMP, "\
                "asset VARCHAR(15), "\
                "side VARCHAR(4), "\
                "price FLOAT, "\
                "market_movement FLOAT "\
            ")"
    connection.cursor().execute(create_table)


def insert_trading_info_table(timestamp, asset, side, price, market_movement):
    connection = connect()
    insert_record = "INSERT INTO trading_info " \
        "(timestamp, asset, side, price, market_movement) "\
        "VALUES ('{}', '{}', '{}', {}, {})".format(timestamp, asset, side, price, market_movement)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()


def initialize_coin_select():
    connection = connect()
    create_table ="CREATE or REPLACE TABLE coin_select " \
            "( "\
                "timestamp TIMESTAMP, "\
                "asset VARCHAR(25), "\
                "level VARCHAR(5) "\
            ")"
    connection.cursor().execute(create_table)


def insert_coin_select_table(timestamp, asset, level):
    connection = connect()
    insert_record = "INSERT INTO coin_select " \
        "(timestamp, asset, level) "\
        "VALUES ('{}', '{}', '{}')".format(timestamp, asset, level)
    connection.cursor().execute(insert_record)
    connection.commit()
    connection.close()


def execute_select(select):
    connection = connect()
    cursor = connection.cursor()
    cursor.execute(select)
    rows = cursor.fetchall()
    connection.close()
    return pd.DataFrame(rows)



if __name__ == "__main__":
    initialize_coin_select()

