from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# Access the variables
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

trading_strategy = 'triple_ema_stochastic_rsi_atr'
'''
valid options for trading_strategy are: 'stoch_rsi_macd', 'triple_ema_stochastic_rsi_atr', 'triple_ema', 'breakout', 'stoch_bb',
'golden_cross', 'candle_wick', 'fib_macd', 'ema_cross', 'heikin_ashi_ema2', 'heikin_ashi_ema', 'ema_crossover'
'''
tp_sl_choice = '%'
'''valid options for TP_SL_choice are: 'USDT', '%', 'x (ATR)', 'x (Swing High/Low) level 1',
'x (Swing High/Low) level 2', 'x (Swing High/Low) level 3', 'x (Swing Close) level 1',
'x (Swing Close) level 2', 'x (Swing Close) level 3
'''
leverage = 10
order_size = 3  # % of account
interval = '1m'
sl_mult = 1.5  # SL_mult x TP_SL_choice = SL value
tp_mult = 1  # TP_mult x TP_SL_choice = TP value
trade_all_symbols = False
symbols_to_trade = ['BTCUSDT', 'ETHUSDT', 'BCHUSDT', 'XRPUSDT', 'EOSUSDT', 'LTCUSDT', 'TRXUSDT', 'ETCUSDT', 'LINKUSDT', 'XLMUSDT', 'ADAUSDT', 'XMRUSDT', 'DASHUSDT', 'ZECUSDT', 'XTZUSDT', 'BNBUSDT', 'ATOMUSDT', 'ONTUSDT', 'IOTAUSDT', 'BATUSDT', 'VETUSDT', 'NEOUSDT', 'QTUMUSDT', 'IOSTUSDT', 'THETAUSDT', 'ALGOUSDT', 'ZILUSDT', 'KNCUSDT', 'ZRXUSDT', 'COMPUSDT', 'OMGUSDT', 'DOGEUSDT', 'SXPUSDT', 'KAVAUSDT', 'BANDUSDT', 'RLCUSDT', 'MKRUSDT', 'SNXUSDT', 'DOTUSDT', 'DEFIUSDT', 'YFIUSDT', 'BALUSDT', 'CRVUSDT', 'TRBUSDT', 'RUNEUSDT', 'SUSHIUSDT', 'EGLDUSDT', 'SOLUSDT', 'ICXUSDT', 'STORJUSDT', 'BLZUSDT', 'UNIUSDT', 'AVAXUSDT', 'FTMUSDT', 'ENJUSDT', 'FLMUSDT', 'RENUSDT', 'KSMUSDT', 'NEARUSDT', 'AAVEUSDT', 'FILUSDT', 'RSRUSDT', 'LRCUSDT', 'MATICUSDT', 'BELUSDT', 'AXSUSDT', 'ALPHAUSDT', 'ZENUSDT', 'SKLUSDT', 'GRTUSDT', '1INCHUSDT']#, 'CHZUSDT', 'SANDUSDT', 'ANKRUSDT', 'LITUSDT', 'UNFIUSDT', 'REEFUSDT', 'RVNUSDT', 'SFPUSDT', 'XEMUSDT', 'COTIUSDT', 'CHRUSDT', 'MANAUSDT', 'ALICEUSDT', 'HBARUSDT', 'ONEUSDT', 'LINAUSDT', 'STMXUSDT', 'DENTUSDT', 'CELRUSDT', 'HOTUSDT', 'MTLUSDT', 'OGNUSDT', 'NKNUSDT', '1000SHIBUSDT', 'BAKEUSDT', 'GTCUSDT', 'IOTXUSDT', 'C98USDT', 'MASKUSDT', 'ATAUSDT', 'DYDXUSDT', '1000XECUSDT', 'GALAUSDT', 'CELOUSDT', 'ARUSDT', 'KLAYUSDT', 'ARPAUSDT', 'CTSIUSDT', 'LPTUSDT', 'ENSUSDT', 'PEOPLEUSDT', 'ROSEUSDT', 'DUSKUSDT', 'FLOWUSDT', 'IMXUSDT', 'API3USDT', 'GMTUSDT', 'APEUSDT', 'WOOUSDT', 'JASMYUSDT', 'DARUSDT', 'OPUSDT', 'INJUSDT', 'STGUSDT', 'SPELLUSDT', '1000LUNCUSDT', 'LUNA2USDT', 'LDOUSDT', 'ICPUSDT', 'APTUSDT', 'QNTUSDT', 'FETUSDT', 'FXSUSDT', 'HOOKUSDT', 'MAGICUSDT', 'TUSDT', 'HIGHUSDT', 'MINAUSDT', 'ASTRUSDT', 'PHBUSDT', 'GMXUSDT', 'CFXUSDT', 'STXUSDT', 'BNXUSDT', 'ACHUSDT', 'SSVUSDT', 'CKBUSDT', 'PERPUSDT', 'TRUUSDT', 'LQTYUSDT', 'IDUSDT', 'ARBUSDT', 'JOEUSDT', 'TLMUSDT', 'AMBUSDT', 'LEVERUSDT', 'RDNTUSDT', 'HFTUSDT', 'XVSUSDT', 'BLURUSDT', 'EDUUSDT', 'SUIUSDT', '1000PEPEUSDT', '1000FLOKIUSDT', 'UMAUSDT', 'KEYUSDT', 'COMBOUSDT', 'NMRUSDT', 'MAVUSDT', 'XVGUSDT', 'WLDUSDT', 'PENDLEUSDT', 'ARKMUSDT', 'AGLDUSDT', 'YGGUSDT', 'DODOXUSDT', 'BNTUSDT', 'OXTUSDT']#, 'SEIUSDT', 'CYBERUSDT', 'HIFIUSDT', 'ARKUSDT', 'FRONTUSDT', 'BICOUSDT', 'LOOMUSDT', 'BIGTIMEUSDT', 'BONDUSDT', 'ORBSUSDT', 'WAXPUSDT', 'BSVUSDT', 'RIFUSDT', 'POLYXUSDT', 'GASUSDT', 'POWRUSDT', 'TIAUSDT', 'CAKEUSDT', 'MEMEUSDT', 'TWTUSDT', 'TOKENUSDT', 'ORDIUSDT', 'STEEMUSDT', 'BADGERUSDT', 'ILVUSDT', 'NTRNUSDT', 'KASUSDT', 'BEAMXUSDT', '1000BONKUSDT', 'PYTHUSDT', 'SUPERUSDT', 'USTCUSDT', 'ONGUSDT', 'ETHWUSDT', 'JTOUSDT', '1000SATSUSDT', 'AUCTIONUSDT', '1000RATSUSDT', 'ACEUSDT', 'MOVRUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'WIFUSDT', 'MANTAUSDT', 'ONDOUSDT', 'LSKUSDT', 'ALTUSDT', 'JUPUSDT', 'ZETAUSDT', 'RONINUSDT', 'DYMUSDT', 'OMUSDT', 'PIXELUSDT', 'STRKUSDT', 'MAVIAUSDT', 'GLMUSDT', 'PORTALUSDT', 'TONUSDT', 'AXLUSDT', 'MYROUSDT', 'METISUSDT', 'AEVOUSDT', 'VANRYUSDT', 'BOMEUSDT', 'ETHFIUSDT', 'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT', 'OMNIUSDT', 'REZUSDT', 'BBUSDT', 'NOTUSDT', 'TURBOUSDT', 'IOUSDT', 'ZKUSDT', 'MEWUSDT', 'LISTAUSDT', 'ZROUSDT']
coin_exclusion_list = ['USDCUSDT', 'BTCDOMUSDT']  # Put coins you want to exclude in here, so they won't be traded
use_trailing_stop = False
trailing_stop_callback = .1
trading_threshold = .3  # used to cancel trades that have moved this distance in % away from our attempted entry price
use_market_orders = False
max_number_of_positions = 10
wait_for_candle_close = True  # Not recommended setting to False, but was requested. If set to False the bot will take trades before candles close
auto_calculate_buffer = True  # Set this to false if you want to manually allocate a buffer
buffer = '3 hours ago'

# Logging configuration
LOG_LEVEL = 20  # CRITICAL = 50, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0
log_to_file = False  # Set this to True to log trading session to a file also

'''
For lower end PCs/ servers it may be better to have this as False, but if you see errors about reconnecting issues
then lower the number of symbols you're monitoring or else set this to True
'''
use_multiprocessing_for_trade_execution = True

# List of tp_sl functions that require information about a placed trade before running
custom_tp_sl_functions = ['USDT']

# Additional configuration options for make_decision
make_decision_options = {}
