API_KEY = ''
API_SECRET = ''

trading_strategy = 'tripleEMAStochasticRSIATR'
leverage = 10
order_size = 2 ## % of account
interval = '1m'
TP_SL_choice = 'USDT'
SL_mult = .05 ## SL_mult x TP_SL_choice = SL value
TP_mult = .05 ## TP_mult x TP_SL_choice = TP value
trade_all_symbols = True
symbols_to_trade = ['BTCUSDT']
use_trailing_stop = False
trailing_stop_callback = .1
trading_threshold = .1 ## used to cancel trades that have moved this distance in % away from our attempted entry price
use_market_orders = False
max_number_of_positions = 3

buffer = '3 hours ago' ## TODO auto-calculate this

## Logging configuration
LOG_LEVEL = 20 ## CRITICAL = 50, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0
log_to_file = False ## Set this to True to log trading session to a file also

'''
Use multiprocessing for trades by setting to True
This will speed up order execution, but will also use more CPU
For lower end PCs/ servers it may be better to have this as False
'''
use_multiprocessing_for_trade_execution = False ##TODO Setup multiprocessing, This is Not Functioning yet DO NOT USE

## List of tp_sl functions that require information about a placed trade before running
custom_tp_sl_functions = ['USDT']

## Additional configuration options for make_decision
make_decision_options = {}