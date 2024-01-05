#!/bin/sh

source /home/pi/Projects/CryptoTrader/.venv/bin/activate

python ma/finance/trader.py --coin=SOL --frequency=30m --live=true &
python ma/finance/trader.py --coin=XRP --frequency=30m --live=true &