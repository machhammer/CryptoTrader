#!/bin/sh

source /home/pi/Projects/CryptoTrader/.venv/bin/activate

python ma/finance/TestStrategies.py --coin=SOL --live=true &
python ma/finance/TestStrategies.py --coin=XRP --live=true &
python ma/finance/TestStrategies.py --coin=XLM --live=true &
python ma/finance/TestStrategies.py --coin=VET --live=true &
python ma/finance/TestStrategies.py --coin=VARA --live=true &
python ma/finance/TestStrategies.py --coin=GRT --live=true &
python ma/finance/TestStrategies.py --coin=NEAR --live=true &


