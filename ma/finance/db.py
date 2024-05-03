# Module Imports
import mariadb
import sys

# Connect to MariaDB Platform
#try:
conn = mariadb.connect(
    user="crypto",
    password="crypto",
    host="192.168.1.123",
    port=3306,
    database="cryptotrader"

)
#except mariadb.Error as e:
#    
#    print(f"Error connecting to MariaDB Platform: {e}")
#    sys.exit(1)

# Get Cursor
cur = conn.cursor()