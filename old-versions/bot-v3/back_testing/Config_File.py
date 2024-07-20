##fill in your API keys here to be accessed by other scripts
API_KEY = ''
API_SECRET = ''

################## settings, these are very strategy dependant ensure you have enough data for your chosen strategy ##################################
order_Size = 2.5  ## As % of account, i.e 2.5 = 2.5%
leverage = 10
buffer = '2 day ago'  ## Buffer of candle sticks be careful if you don't provide enough the bot will throw an error
Interval = '1m'  ##candle sticks you want to trade
Max_Number_Of_Trades = 8  ## How many positions we can have open at once
use_trailing_stop = 0  ##If on we will use our TP value as the Activation price for a trailing stop loss
trailing_stop_callback = 0.1  ##trailing stop percent, this is .1% range is [.1% - 5%] .ie [0.1 - 5] (increments of .1 only)**
use_market_orders = False
trading_threshold = 0.1  ## %, i.e 0.1 = 0.1%

## New vars needed for the gui, running script from terminal will also need these now
strategy = 'StochRSIMACD'
TP_SL_choice = '%'
SL_mult = .5
TP_mult = 1

##Trade All Coins if True, can also specify a list of coins to trade instead. Example: symbol = ['ETHUSDT','BTCUSDT'] & set Trade_All_Coins = False
Trade_All_Coins = False
symbol = ['AAVEUSDT', 'APEUSDT', 'API3USDT', 'AUDIOUSDT', 'AVAXUSDT', 'AXSUSDT', 'BAKEUSDT', 'DYDXUSDT', 'ENSUSDT', 'LITUSDT', 'NEARUSDT', 'RAYUSDT', 'PEOPLEUSDT', 'RUNEUSDT']  ## If Trade_All_Coins is False then we list the coins we want to trade here, otherwise the bot will automatically get all coins and trade them

