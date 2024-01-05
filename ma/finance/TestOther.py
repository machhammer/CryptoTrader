
import json

order = {'info': {'client_oid': '1704465267511', 'order_id': '4611686044110401397'}, 'id': '4611686044110401397', 'clientOrderId': '1704465267511', 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'status': None, 'symbol': 'XLM/USDT', 'type': None, 'timeInForce': None, 'postOnly': None, 'side': None, 'price': None, 'amount': None, 'filled': None, 'remaining': None, 'average': None, 'cost': None, 'fee': {'currency': None, 'cost': None}, 'trades': [], 'fees': [{'currency': None, 'cost': None}], 'lastUpdateTimestamp': None, 'reduceOnly': None, 'stopPrice': None, 'triggerPrice': None, 'takeProfitPrice': None, 'stopLossPrice': None}

print (json.dumps(order, indent=4))

print(order['id'])
print(order['fee'])