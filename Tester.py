from pybitget import Client
import credentials

api_key = credentials.provider_3.get("key")
api_secret = credentials.provider_3.get("secret")
password = credentials.provider_3.get("password")
passphrase = credentials.provider_3.get("passphrase")
client = Client(api_key, api_secret, passphrase=passphrase)

data = client.spot_get_order_details(symbol="RDNTUSDT", orderId="1216905450744254467", clientOrderId=None)

print(data)