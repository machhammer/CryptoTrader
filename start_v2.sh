#!/bin/sh

source /home/pi/Projects/CryptoTrader/.venv/bin/activate

python ma/finance/trader.py --coin=CQT --frequency=15m --live=true &
python ma/finance/trader.py --coin=XRP --frequency=15m --live=true &
python ma/finance/trader.py --coin=GMT --frequency=15m --live=true &
python ma/finance/trader.py --coin=POWR --frequency=15m --live=true &
