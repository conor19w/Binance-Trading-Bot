from pprint import PrettyPrinter
from helper import *
from trade_manager import *
import multiprocessing
from queue import Queue
from trading_config import symbols_to_trade, buffer

if __name__ == '__main__':
    # log.info(f'Configuration:\ntrading strategy: {trading_strategy}\nleverage: {leverage}\norder size: {order_size}\n'
    #          f'interval: {interval}\nTP/SL choice: {TP_SL_choice}\nSL mult: {SL_mult}\nTP mult: {TP_mult}\n'
    #          f'trade all symbols: {trade_all_symbols}\nsymbols to trade: {symbols_to_trade}\nuse trailing stop: {use_trailing_stop}\n'
    #          f'trailing stop callback: {trailing_stop_callback}\ntrading threshold: {trading_threshold}\nuse market orders: {use_market_orders}\n'
    #          f'max number of positions: {max_number_of_positions}\nuse multiprocessing for trade execution: {use_multiprocessing_for_trade_execution}\n'
    #          f'custom TP/SL Functions: {custom_tp_sl_functions}\nmake decision options: {make_decision_options}\n')

    pp = PrettyPrinter()  ##for printing json text cleanly (inspect binance API call returns)
    Bots: [Bot] = []
    signal_queue = None
    print_trades_q = None
    user_socket_q = None
    if use_multiprocessing_for_trade_execution:
        signal_queue = multiprocessing.Queue()
        print_trades_q = multiprocessing.Queue()
        user_socket_q = multiprocessing.Queue()
    else:
        signal_queue = Queue()
        print_trades_q = Queue()
        user_socket_q = Queue()

    python_binance_client = Client(api_key=API_KEY, api_secret=API_SECRET)
    client = CustomClient(python_binance_client, user_socket_q)
    if trade_all_symbols:
        symbols_to_trade = get_all_symbols(python_binance_client, coin_exclusion_list)

    client.set_leverage(symbols_to_trade)

    # Initialize a bot for each coin we're trading
    client.setup_bots(Bots, symbols_to_trade, signal_queue, print_trades_q)

    client.start_websockets(Bots)

    # Initialize Trade manager for order related tasks
    new_trade_loop = None
    event_loop = get_loop()
    TM = None
    if use_multiprocessing_for_trade_execution:
        new_trade_loop = multiprocessing.Process(target=start_new_trades_loop_multiprocess, args=(python_binance_client, signal_queue, print_trades_q, user_socket_q))
        new_trade_loop.start()
    else:
        TM = TradeManager(python_binance_client, signal_queue, print_trades_q, user_socket_q)
        event_loop.create_task(TM.new_trades_loop())

    # Loop to ping the server & reconnect websockets
    event_loop.create_task(client.ping_server_reconnect_sockets(Bots))

    if auto_calculate_buffer:
        # auto-calculate the required buffer size
        buffer_int = get_required_buffer()
        buffer = convert_buffer_to_string(buffer_int)
    # Combine data collected from websockets with historical data, so we have a buffer of data to calculate signals
    event_loop.create_task(client.combine_data(Bots, symbols_to_trade, buffer))
    if new_trade_loop is not None:
        new_trade_loop.join()
