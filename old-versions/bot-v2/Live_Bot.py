from pprint import PrettyPrinter
import sys, os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance import ThreadedWebsocketManager
from datetime import datetime, date, timedelta
from threading import Thread
from multiprocessing import Process, Pipe
import time

##Local Imports
import Bot_Class
from Helper import Trade_Manager, get_historical, Trade, Trade_Stats, Data_Handler

now = datetime.now()
current_time = now.strftime("%H:%M:%S")
csv_name = f"Logs_{current_time.replace(':','_')}.txt"
DH: [Data_Handler] = []
streams = []  ##store streams allowing the option to start and stop streams if needed
new_candle_flag = 0
Data = {}

time_delta = timedelta(hours=1)  ## Adjust time for printing based off GMT (This is GMT+1)


## If you are getting a rate limit error on startup this will add a delay for downloading candlesticks to start
RATE_LIMIT_WAIT = False  ## It will not slow down the bot, it will only slow down the startup by about (4 x (number of coins you're trading)) seconds


def listen_pipe(pipe: Pipe):
    global Data, new_candle_flag
    while True:
        Data = pipe.recv()
        new_candle_flag = 1
 

def web_soc_process(pipe: Pipe, twm: ThreadedWebsocketManager):
    global DH, Data, streams
    ##keep process running
    while True:
        time.sleep(3)
        ##Check if all coins we are trading have received a new data point
        count = 0
        for data in DH:
            if data.new_data:
                count += 1
            if data.socket_failed:
                try:
                    print(f"Attempting to reset socket for {data.symbol}")
                    twm.stop_socket(streams[data.index])
                    streams[data.index] = twm.start_kline_futures_socket(data.handle_socket_message, symbol=data.symbol)
                    data.socket_failed = False
                    print(f"Reset successful")
                except:
                    print(f"Error in resetting websocket for {data.symbol}")
        ##If they have, Send the updated Data_set to the process handling trading
        if count == len(DH):
            for data in DH:
                data.new_data = False
                Data[data.symbol] = data.next_candle
            pipe.send(Data)

def combine_data(Bots: [Bot_Class.Bot], symbol, streams, buffer, Interval, client):
    print("Combining Historical and web socket data...")
    i = 0
    while i < len(Bots):
        Date_temp, Open_temp, Close_temp, High_temp, Low_temp, Volume_temp = get_historical(symbol=symbol[i],
                                                                                            start_string=buffer,
                                                                                            Interval=Interval)
        ##Pop off last candle as it is a duplicate, luki009's suggestion
        Date_temp.pop(-1)
        Open_temp.pop(-1)
        Close_temp.pop(-1)
        High_temp.pop(-1)
        Low_temp.pop(-1)
        Volume_temp.pop(-1)
        client.futures_ping()  ## ping the server to stay connected
        if len(Date_temp) < 100:
            print(
                f"Not enough data for {symbol[i]}, Increase your buffer variable in Config_File.py so you have a buffer of candles")
            symbol.pop(i)
            Bots.pop(i)
            streams.pop(i)
        else:
            Bots[i].add_hist(Date_temp=Date_temp, Open_temp=Open_temp, Close_temp=Close_temp, High_temp=High_temp,
                             Low_temp=Low_temp, Volume_temp=Volume_temp)
            i += 1
        if RATE_LIMIT_WAIT:
            time.sleep(1)  ##wait a second to avoid API rate limit (if you are getting a rate limit error)
    print("Finished Combining data, Searching for trades now...")

def Check_for_signals(pipe: Pipe, leverage: int, order_Size: float, buffer: str, Interval: str,
                      Max_Number_Of_Trades: int, client: Client, Bots: [Bot_Class.Bot],
                      use_trailing_stop: bool, use_market_orders: bool, trading_threshold: float,
                      trailing_stop_callback: float, symbol: [str]):
    global new_candle_flag, Data
    pp = PrettyPrinter()  ## for printing json text cleanly (inspect binance API call returns)
    active_trades: [Trade] = []  ## List of active trades
    new_trades: [[int, [int, float, float]]] = []
    order_Size = round(order_Size/100, 3)
    trading_threshold = round(trading_threshold/100, 3)
    TM = Trade_Manager(client=client, use_trailing_stop=use_trailing_stop, trailing_stop_callback=trailing_stop_callback, use_market=use_market_orders)
    TS = Trade_Stats()

    thread_combine_data = Thread(target=combine_data, args=(Bots, symbol, streams, buffer, Interval, client))
    thread_combine_data.start()

    AccountBalance = 0
    y = client.futures_account_balance()
    for x in y:
        if x['asset'] == 'USDT':
            AccountBalance = float(x['balance'])
            break
    print("Start Balance:", AccountBalance)

    start = datetime.now().time()
    yesterdate = date.today()
    print_flag = 0
    account_balance = 0
    startup_account_balance = 0
    account_balance_info = client.futures_account_balance()
    for x in account_balance_info:
        if x['asset'] == 'USDT':
            account_balance = float(x['balance'])
            startup_account_balance = float(x['balance'])
            break
    data_thread = Thread(target=listen_pipe, args=(pipe,))  ## thread to listen for new candles
    data_thread.start()
    while True:
        try:
            if new_candle_flag:
                get_new_trades = True
                for Bot in Bots:
                    Bot.handle_socket_message(Data[Bot.symbol])
                    if not Bot.add_hist_complete:
                        get_new_trades = False
                print_flag = 1
                new_candle_flag = 0

                if get_new_trades:
                    ##Ensure Bot doesn't interfere with positions opened manually by the user & doesn't open a position when we're already in a trade on that symbol
                    position_info = client.futures_position_information()
                    open_trades = [position['symbol'] for position in position_info if float(position['notional']) != 0.0] ## All open Trades
                    bot_trades = [trade.symbol for trade in active_trades] ## Open/ attempting to open trades
                    temp_dec = [Bots[i].Make_decision() for i in range(len(Bots))] ## get all signals
                    new_trades = [[i, temp_dec[i]] for i in range(len(Bots)) if temp_dec[i][0]!=-99 and Bots[i].symbol
                                  not in open_trades+bot_trades] ## get new trades, exclude (trades that didn't give a long/short signal) AND (those tht already have an active position already)
            ##Sort out new trades to be opened
            while len(new_trades) > 0 and len(active_trades) < Max_Number_Of_Trades:
                '''
                If Trades are really time sensitive, you could speed this part up with a process pool.
                The Improvement would be very slight however
                '''
                account_balance = 0
                account_balance_info = client.futures_account_balance()
                for item in account_balance_info:
                    if item['asset'] == 'USDT':
                        account_balance = float(item['balance'])
                        break
                [index, [trade_direction, stop_loss, take_profit]] = new_trades.pop(0) ## decompose trade into variables for use

                order_notional = leverage * order_Size * account_balance

                order_id_temp, position_size_temp, entry_price_temp, _ = TM.open_trade_check_threshold(symbol=Bots[index].symbol, trade_direction=trade_direction, order_notional=order_notional,
                                                                  CP=Bots[index].CP, OP=Bots[index].OP, tick_size=Bots[index].tick_size,
                                                                  time=Bots[index].Date[-1], close=Bots[index].Close[-1], trading_threshold=trading_threshold)

                ##Add on the trade which we will later Check on
                if order_id_temp != '':
                    active_trades.append(Trade(index, position_size_temp, take_profit, stop_loss, trade_direction, order_id_temp, Bots[index].symbol))
                    active_trades[-1].entry_price = entry_price_temp

            ##Clear trades, so they don't carry to next candle
            new_trades = []

            rightnow = datetime.now().time()  ##time right now
            timer = timedelta(hours=0, minutes=0, seconds=15)  ##how often to run code below
            if (datetime.combine(date.today(), rightnow) - datetime.combine(yesterdate, start)) > timer:
                client.futures_ping()  ## ping the server every 15 seconds
                start = datetime.now().time()  ##reset start
                yesterdate = date.today()

                ##Set Tp's and SL's
                proceed_with_below = False ## Check If we need to set any TP's or SL's
                for trade in active_trades:
                    if trade.trade_status == 0:
                        proceed_with_below = True
                trade_index = 0
                while trade_index < len(active_trades):
                    if not proceed_with_below:
                        break ## Break out of this loop if all trades have TP's and SL's
                    pop_flag = False

                    if active_trades[trade_index].trade_status == 0 and float(client.futures_position_information(symbol=active_trades[trade_index].symbol)[0]['notional']) != 0:

                        active_trades[trade_index].entry_price = float(client.futures_position_information(symbol=active_trades[trade_index].symbol)[0]['entryPrice'])
                        take_profit_val = 0
                        stop_loss_val = 0
                        if active_trades[trade_index].trade_direction:
                            take_profit_val = active_trades[trade_index].TP_val + active_trades[trade_index].entry_price
                            stop_loss_val = active_trades[trade_index].entry_price - active_trades[trade_index].SL_val
                        else:
                            take_profit_val = active_trades[trade_index].entry_price - active_trades[trade_index].TP_val
                            stop_loss_val = active_trades[trade_index].entry_price + active_trades[trade_index].SL_val

                        ##This position has been opened
                        if active_trades[trade_index].TP_id == '':
                            active_trades[trade_index].TP_id = TM.place_TP(symbol=active_trades[trade_index].symbol, TP=[take_profit_val, active_trades[trade_index].position_size],
                                                                           trade_direction=active_trades[trade_index].trade_direction, CP=Bots[active_trades[trade_index].index].CP,
                                                                           tick_size=Bots[active_trades[trade_index].index].tick_size, time=Bots[trade_index].Date[-1])

                        active_trades[trade_index].SL_id = TM.place_SL(symbol=active_trades[trade_index].symbol, SL=stop_loss_val, trade_direction=active_trades[trade_index].trade_direction,
                                                                       CP=Bots[active_trades[trade_index].index].CP, tick_size=Bots[active_trades[trade_index].index].tick_size, time=Bots[trade_index].Date[-1])
                        active_trades[trade_index].trade_status = 1 ## In a Trade
                        ##Order would trigger immediately so close the position
                        if active_trades[trade_index].SL_id == -1 or active_trades[trade_index].TP_id == -1:
                            TM.close_position(symbol=active_trades[trade_index].symbol,
                                              trade_direction=active_trades[trade_index].trade_direction,
                                              total_position_size=active_trades[trade_index].position_size, time=Bots[trade_index].Date[-1])
                            print(f"Closed Trade on {active_trades[trade_index].symbol} as SL OR TP would have thrown a trigger immediately error")
                            pop_flag = True
                            break

                    if active_trades[trade_index].trade_status == 0:
                        ## trade hasn't opened yet so check it hasn't gone past threshold
                        order_notional = leverage * order_Size * account_balance
                        _, _, _, active_trades[trade_index].trade_status = TM.open_trade_check_threshold(symbol=active_trades[trade_index].symbol,
                                                                               trade_direction=active_trades[trade_index].trade_direction,
                                                                               order_notional=order_notional,
                                                                               CP=Bots[active_trades[trade_index].index].CP, OP=Bots[active_trades[trade_index].index].OP,
                                                                               tick_size=Bots[active_trades[trade_index].index].tick_size,
                                                                               time=Bots[active_trades[trade_index].index].Date[-1], close=Bots[active_trades[trade_index].index].Close[-1],
                                                                               trading_threshold=trading_threshold, orderID=active_trades[trade_index].order_id,
                                                                               old_entry_price=active_trades[trade_index].entry_price)
                        if active_trades[trade_index].trade_status == -99:
                            pop_flag = True  ## pop off trade as threshold was reached
                    if pop_flag:
                        try:
                            client.futures_cancel_all_open_orders(symbol=active_trades[trade_index].symbol)  ##Close open orders on that symbol
                        except Exception as e:
                            print(f"Failed to cancel Trade on {active_trades[trade_index].symbol}, Error: {e}")
                            pop_flag = False
                            trade_index += 1
                        if pop_flag:
                            active_trades.pop(trade_index)
                    else:
                        trade_index += 1

                ##Check If positions have been closed manually by the user or If trades have hit their TP values or SL value and move SL/ Cancel open orders cause the trade is finished
                i = 0
                while i < len(active_trades):
                    position_info = client.futures_position_information(symbol=active_trades[i].symbol)[0]
                    all_orders = client.futures_get_all_orders()
                    if float(position_info['positionAmt']) == 0 and (active_trades[i].trade_status == -99 or active_trades[i].trade_status == 1):
                        pop_flag = True
                        try:
                            client.futures_cancel_all_open_orders(symbol=active_trades[i].symbol)  ##Close open orders on that symbol

                        except Exception as e:
                            print(f"Failed to cancel orders on {active_trades[i].symbol}, Error: {e}")
                        for order in all_orders:
                            if order['symbol'] == active_trades[i].symbol and order['orderId'] == \
                                    active_trades[i].TP_id and order['status'] == 'FILLED':
                                ##Trading Statistics
                                TS.wins += 1
                                TS.total_number_of_trades += 1
                                account_balance = 0
                                account_balance_info = client.futures_account_balance()
                                for item in account_balance_info:
                                    if item['asset'] == 'USDT':
                                        account_balance = float(item['balance'])
                                        break
                            elif order['symbol'] == active_trades[i].symbol and order['orderId'] == \
                                    active_trades[i].SL_id and order['status'] == 'FILLED':
                                ##Trading Statistics
                                TS.losses += 1
                                TS.total_number_of_trades += 1
                                account_balance = 0
                                account_balance_info = client.futures_account_balance()
                                for item in account_balance_info:
                                    if item['asset'] == 'USDT':
                                        account_balance = float(item['balance'])
                                        break
                        if pop_flag:
                            active_trades.pop(i)
                        else:
                            i += 1
                    else:
                        i += 1

            if print_flag:
                account_balance = 0
                account_balance_info = client.futures_account_balance()
                for item in account_balance_info:
                    if item['asset'] == 'USDT':
                        account_balance = float(item['balance'])
                        break
                i = 0
                while i < len(active_trades):
                    ## Don't check close position if the strategy doesn't use it, may need to change this if running multiple strategies from the same bot
                    if not Bots[active_trades[i].index].use_close_pos:
                        break
                    if Bots[active_trades[i].index].use_close_pos and not active_trades[i].same_candle:
                        ## Check each interval if the close position was met
                        close_pos = Bots[active_trades[i].index].check_close_pos(active_trades[i].trade_direction)
                        if close_pos:
                            TM.close_position(active_trades[i].symbol,
                                              active_trades[i].trade_direction,
                                              active_trades[i].position_size, Bots[active_trades[i].index].Date[-1])
                            print(f"Closed Trade on {active_trades[i].symbol} as Close Position condition was met")
                            active_trades.pop(i)
                        else:
                            i += 1
                    else:
                        active_trades[i].same_candle = False
                        i += 1
                print_flag = 0
                temp_symbols = [active_trades[t].symbol for t in range(len(active_trades))]
                #Helper.log_info(active_trades, trade_prices, Dates, account_balance, csv_name, indicators)
                try:
                    print(f"Account Balance: {account_balance}, {str(datetime.utcfromtimestamp(round(Bots[0].Date[-1] / 1000)) + time_delta)}: Active Trades: {temp_symbols}")
                except:
                    pass
                try:
                    print(f"wins: {TS.wins}, losses: {TS.losses}, Total Profit: {account_balance - startup_account_balance},"
                          f" Average Trade Profit: ${(account_balance - startup_account_balance) / TS.total_number_of_trades}")
                except:
                    print(f"wins: {TS.wins}, losses: {TS.losses}, Total Profit: {account_balance - startup_account_balance}")

        except BinanceAPIException as e:
            pp.pprint(e)
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)


def run_bot(API_KEY, API_SECRET, leverage, order_Size, buffer, Interval, Max_Number_Of_Trades,
                 use_trailing_stop, trailing_stop_callback, symbol, strategy,
                 TP_SL_choice, SL_mult, TP_mult, Trade_All_Coins, use_market_orders, trading_threshold):
    client = Client(api_key=API_KEY, api_secret=API_SECRET)

    if Trade_All_Coins:
        x = client.futures_exchange_info()['symbols']
        symbol = [y['symbol'] for y in x if
                  (y['status'] == 'TRADING' and 'USDT' in y['symbol'] and not '_' in y['symbol'])]

    twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
    twm.start()  ##start manager

    print("Setting Leverage...")
    i = 0
    while i < len(symbol):
        try:
            client.futures_change_leverage(symbol=symbol[i], leverage=leverage)
            i += 1
        except BinanceAPIException as e:
            if e == 'APIError(code=-4141): Symbol is closed.':
                print(f"Symbol: {symbol[i]}, error: {e}")
                symbol.pop(i)
            else:
                print(f"Error: {e}, removing symbol")
                symbol.pop(i)

    i = 0
    while i < len(symbol):
        try:
            DH.append(Data_Handler(symbol[i], i))
            streams.append(twm.start_kline_futures_socket(callback=DH[i].handle_socket_message, symbol=symbol[i],
                                                          interval=Interval))
            i += 1
        except:
            symbol.pop(i)

    pipe1, pipe2 = Pipe()  ##pipe to communicate between processes
    _thread = Thread(target=web_soc_process, args=(pipe1, twm))
    _thread.start()
    Bots: [Bot_Class.Bot] = []

    y = client.futures_exchange_info()['symbols']
    coin_info = [[x['pair'], x['pricePrecision'], x['quantityPrecision'], x['filters'][0]['tickSize'],
                  x['filters'][0]['minPrice']] for x in y]

    i = 0
    while i < len(symbol):
        print(f"Starting {symbol[i]} web socket")
        Coin_precision_temp = -99
        Order_precision_temp = -99
        tick_temp = -99
        flag = 0
        for x in coin_info:
            if x[0] == symbol[i]:
                print(symbol[i], int(x[2]), int(x[1]))
                Coin_precision_temp = int(x[1])
                Order_precision_temp = int(x[2])
                tick_temp = float(x[3])
                flag = 1
                break
        if flag == 1:
            Bots.append(Bot_Class.Bot(symbol=symbol[i], Open=[], Close=[], High=[], Low=[], Volume=[], Date=[],
                                      OP=Order_precision_temp, CP=Coin_precision_temp,
                                      index=i, tick=tick_temp, strategy=strategy, TP_SL_choice=TP_SL_choice,
                                      SL_mult=SL_mult, TP_mult=TP_mult))
            i += 1
        else:
            print(f"{symbol.pop(i)} no info found")
            try:
                symbol.pop(i)
                Bots.pop(i)
                twm.stop_socket(streams[i])
                streams.pop(i)
            except:
                pass

    P1 = Process(target=Check_for_signals, args=(pipe2, leverage, order_Size, buffer, Interval, Max_Number_Of_Trades, client, Bots, use_trailing_stop, use_market_orders, trading_threshold,
                                                 trailing_stop_callback, symbol))
    P1.start()
    twm.join()  ##keep websockets running


if __name__ == '__main__':
    ## Still able to run from this script by configuring Config_File.py
    from Config_File import *
    from Config_File import symbol  # explicitly importing to remove a warning

    client = Client(api_key=API_KEY, api_secret=API_SECRET)

    if Trade_All_Coins:
        x = client.futures_exchange_info()['symbols']
        symbol = [y['symbol'] for y in x if (y['status'] == 'TRADING' and 'USDT' in y['symbol'] and not '_' in y['symbol'])]

    pp = PrettyPrinter()  ##for printing json text cleanly (inspect binance API call returns)
    twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
    twm.start()  ##start manager

    print("Setting Leverage...")
    i = 0
    while i < len(symbol):
        try:
            client.futures_change_leverage(symbol=symbol[i], leverage=leverage)
            i += 1
        except BinanceAPIException as e:
            if e == 'APIError(code=-4141): Symbol is closed.':
                print(f"Symbol: {symbol[i]}, error: {e}")
                symbol.pop(i)
            else:
                print(f"Error: {e}, removing symbol")
                symbol.pop(i)

    i = 0
    while i < len(symbol):
        try:
            DH.append(Data_Handler(symbol[i], i))
            streams.append(twm.start_kline_futures_socket(callback=DH[i].handle_socket_message, symbol=symbol[i],
                                                          interval=Interval))
            i += 1
        except:
            symbol.pop(i)

    pipe1, pipe2 = Pipe()  ##pipe to communicate between processes
    _thread = Thread(target=web_soc_process, args=(pipe1, twm))
    _thread.start()

    Bots: [Bot_Class.Bot] = []

    y = client.futures_exchange_info()['symbols']
    coin_info = [[x['pair'], x['pricePrecision'], x['quantityPrecision'], x['filters'][0]['tickSize'],
                  x['filters'][0]['minPrice']] for x in y]

    i = 0
    while i < len(symbol):
        print(f"Starting {symbol[i]} web socket")
        Coin_precision_temp = -99
        Order_precision_temp = -99
        tick_temp = -99
        min_price_temp = -99
        flag = 0
        for x in coin_info:
            if x[0] == symbol[i]:
                print(symbol[i], int(x[2]), int(x[1]))
                Coin_precision_temp = int(x[1])
                Order_precision_temp = int(x[2])
                tick_temp = float(x[3])
                min_price_temp = float(x[4])
                flag = 1
                break
        if flag == 1:
            Bots.append(Bot_Class.Bot(symbol=symbol[i], Open=[], Close=[], High=[], Low=[], Volume=[], Date=[],
                                      OP=Order_precision_temp, CP=Coin_precision_temp,
                                      index=i, tick=tick_temp, strategy=strategy, TP_SL_choice=TP_SL_choice,
                                      SL_mult=SL_mult, TP_mult=TP_mult))
            i += 1
        else:
            print(f"{symbol.pop(i)} no info found")
            try:
                symbol.pop(i)
                Bots.pop(i)
                twm.stop_socket(streams[i])
                streams.pop(i)
            except:
                pass

    P1 = Process(target=Check_for_signals, args=(
    pipe2, leverage, order_Size, buffer, Interval, Max_Number_Of_Trades, client, Bots, use_trailing_stop,
    use_market_orders, trading_threshold,
    trailing_stop_callback, symbol))
    P1.start()
    twm.join()  ##keep websockets running
