SELECT * FROM trader order BY timestamp descINSERT INTO trader (
    timestamp,
    chart_time,
    coin,
    sma,
    aroon,
    profit_threshold,
    sell_threshold,
    pnl,
    c_price
  )
VALUES (
    'timestamp:timestamp',
    'chart_time:timestamp',
    'coin:varchar',
    sma:int,
    aroon:int,
    profit_threshold:int,
    sell_threshold:int,
    'pnl:float',
    'c_price:float'
  );