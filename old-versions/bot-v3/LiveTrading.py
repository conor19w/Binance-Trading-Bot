import asyncio
from pprint import PrettyPrinter
from LiveTradingConfig import *
from LiveTradingConfig import symbols_to_trade  # explicitly importing to remove a warning
from LiveTradingConfig import buffer  # explicitly importing to remove a warning

import SharedHelper
from Helper import *
from TradeManager import *
from threading import Thread
import multiprocessing
from queue import Queue
import os

os.environ['TYPE_CHECKING'] = 'False'

if __name__ == '__main__':
    log.info(f'Configuration:\ntrading strategy: {trading_strategy}\nleverage: {leverage}\norder size: {order_size}\n'
             f'interval: {interval}\nTP/SL choice: {TP_SL_choice}\nSL mult: {SL_mult}\nTP mult: {TP_mult}\n'
             f'trade all symbols: {trade_all_symbols}\nsymbols to trade: {symbols_to_trade}\nuse trailing stop: {use_trailing_stop}\n'
             f'trailing stop callback: {trailing_stop_callback}\ntrading threshold: {trading_threshold}\nuse market orders: {use_market_orders}\n'
             f'max number of positions: {max_number_of_positions}\nuse multiprocessing for trade execution: {use_multiprocessing_for_trade_execution}\n'
             f'custom TP/SL Functions: {custom_tp_sl_functions}\nmake decision options: {make_decision_options}\n')
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    pp = PrettyPrinter()  ##for printing json text cleanly (inspect binance API call returns)
    Bots: [BotClass.Bot] = []
    signal_queue = None
    print_trades_q = None
    if use_multiprocessing_for_trade_execution:
        signal_queue = multiprocessing.Queue()
        print_trades_q = multiprocessing.Queue()
    else:
        signal_queue = Queue()
        print_trades_q = Queue()

    python_binance_client = Client(api_key=API_KEY, api_secret=API_SECRET)
    client = CustomClient(python_binance_client)
    if trade_all_symbols:
        symbols_to_trade = SharedHelper.get_all_symbols(python_binance_client, coin_exclusion_list)

    client.set_leverage(symbols_to_trade)

    ## Initialize a bot for each coin we're trading
    client.setup_bots(Bots, symbols_to_trade, signal_queue, print_trades_q)

    client.start_websockets(Bots)

    ## Initialize Trade manager for order related tasks
    new_trade_loop = None
    TM = None
    if use_multiprocessing_for_trade_execution:
        new_trade_loop = multiprocessing.Process(target=start_new_trades_loop_multiprocess, args=(python_binance_client, signal_queue, print_trades_q))
        new_trade_loop.start()
    else:
        TM = TradeManager(python_binance_client, signal_queue, print_trades_q)
        new_trade_loop = Thread(target=TM.new_trades_loop)
        new_trade_loop.daemon = True
        new_trade_loop.start()

    ## Thread to ping the server & reconnect websockets
    ping_server_reconnect_sockets_thread = Thread(target=client.ping_server_reconnect_sockets, args=(Bots,))
    ping_server_reconnect_sockets_thread.daemon = True
    ping_server_reconnect_sockets_thread.start()

    if auto_calculate_buffer:
        ## auto-calculate the required buffer size
        buffer_int = SharedHelper.get_required_buffer(trading_strategy)
        buffer = convert_buffer_to_string(buffer_int)
    ## Combine data collected from websockets with historical data, so we have a buffer of data to calculate signals
    combine_data_thread = Thread(target=client.combine_data, args=(Bots, symbols_to_trade, buffer))
    combine_data_thread.daemon = True
    combine_data_thread.start()
    new_trade_loop.join()