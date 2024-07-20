API_KEY = ''
API_SECRET = ''

trading_strategy = 'tripleEMAStochasticRSIATR'
'''
valid options for trading_strategy are: 'StochRSIMACD', 'tripleEMAStochasticRSIATR', 'tripleEMA', 'breakout', 'stochBB',
'goldenCross', 'candle_wick', 'fibMACD', 'EMA_cross', 'heikin_ashi_ema2', 'heikin_ashi_ema', 'ema_crossover'
'''
TP_SL_choice = '%'
'''valid options for TP_SL_choice are: 'USDT', '%', 'x (ATR)', 'x (Swing High/Low) level 1',
'x (Swing High/Low) level 2', 'x (Swing High/Low) level 3', 'x (Swing Close) level 1',
'x (Swing Close) level 2', 'x (Swing Close) level 3
'''
leverage = 10
order_size = 3 ## % of account
interval = '1m'
SL_mult = 1.5 ## SL_mult x TP_SL_choice = SL value
TP_mult = 1 ## TP_mult x TP_SL_choice = TP value
trade_all_symbols = True
symbols_to_trade = ['BTCUSDT']
coin_exclusion_list = ['USDCUSDT', 'BTCDOMUSDT'] ## Put coins you want to exclude in here, so they won't be traded
use_trailing_stop = False
trailing_stop_callback = .1
trading_threshold = .3 ## used to cancel trades that have moved this distance in % away from our attempted entry price
use_market_orders = False
max_number_of_positions = 10
wait_for_candle_close = True ## Not recommended setting to False, but was requested. If set to False the bot will take trades before candles close
auto_calculate_buffer = True ## Set this to false if you want to manually allocate a buffer
buffer = '3 hours ago'

## Logging configuration
LOG_LEVEL = 20 ## CRITICAL = 50, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0
log_to_file = False ## Set this to True to log trading session to a file also

'''
For lower end PCs/ servers it may be better to have this as False, but if you see errors about reconnecting issues
then lower the number of symbols you're monitoring or else set this to True
'''
use_multiprocessing_for_trade_execution = True

## List of tp_sl functions that require information about a placed trade before running
custom_tp_sl_functions = ['USDT']

## Additional configuration options for make_decision
make_decision_options = {}