#!/bin/sh

source /home/pi/Projects/CryptoTrader/.venv/bin/activate

python ma/finance/trader.py --coin=MASK --frequency=30m --live=true &
python ma/finance/trader.py --coin=XRP --frequency=30m --live=true &
python ma/finance/trader.py --coin=VELO --frequency=30m --live=true &
python ma/finance/trader.py --coin=POWR --frequency=30m --live=true &
