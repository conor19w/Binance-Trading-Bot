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
from Config_File import *
from Config_File import symbol  #explicitly importing to remove a warning

time_delta = timedelta(hours=1)  ## GMT+1

streams = []  ##store streams allowing the option to start and stop streams if needed
new_candle_flag = 0
Data = {}
client = Client(api_key=API_KEY, api_secret=API_SECRET)

if Trade_All_Coins:
    x = client.futures_exchange_info()['symbols']
    symbol = [y['symbol'] for y in x if (y['status'] == 'TRADING' and 'USDT' in y['symbol'] and not '_' in y['symbol'])]

DH: [Data_Handler] = []


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
        if count > .9 * len(DH):
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


def Check_for_signals(pipe: Pipe, leverage, order_Size, Max_Number_Of_Trades, client: Client, use_trailing_stop, trailing_stop_callback):
    global new_candle_flag, symbol, Data
    pp = PrettyPrinter()  ## for printing json text cleanly (inspect binance API call returns)
    active_trades: [Trade] = []  ## List of active trades
    new_trades = []
    TM = Trade_Manager(client, use_trailing_stop, trailing_stop_callback)
    TS = Trade_Stats()
    Bots: [Bot_Class.Bot] = []

    y = client.futures_exchange_info()['symbols']
    coin_info = []
    for x in y:
        # z = x['filters'][0]
        coin_info.append([x['pair'], x['pricePrecision'], x['quantityPrecision'], x['filters'][0]['tickSize'],
                          x['filters'][0]['minPrice']])

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
                Coin_precision_temp = int(x[1])
                Order_precision_temp = int(x[2])
                tick_temp = float(x[3])
                min_price_temp = float(x[4])
                flag = 1
                break
        if flag == 1:
            Bots.append(Bot_Class.Bot(symbol[i], [], [], [], [], [], [], Order_precision_temp, Coin_precision_temp,
                                      i, use_heikin_ashi, tick=tick_temp))
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
    all_orders = []
    print_flag = 0
    print("Searching for Trade Entries...")
    account_balance = 0
    startup_account_balance = 0
    account_balance_info = client.futures_account_balance()
    for item in account_balance_info:
        if item['asset'] == 'USDT':
            account_balance = float(item['balance'])
            startup_account_balance = float(item['balance'])
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
                    ##Ensure Bot doesn't interfere with positions opened manually by the user
                    open_trades = []
                    position_info = client.futures_position_information()
                    for position in position_info:
                        if float(position['notional']) != 0.0:
                            open_trades.append(position['symbol'])

                    for i in range(len(Bots)):
                        trade_flag = 0
                        for t in active_trades:
                            if t.index == i:
                                trade_flag = 1
                                break
                        for s in open_trades:
                            if s == Bots[i].symbol:
                                trade_flag = 1
                                break
                        if trade_flag == 0:
                            temp_dec = Bots[i].Make_decision()
                            # print(Data[i].symbol,temp_dec)
                            if temp_dec[0] != -99:
                                new_trades.append([i, temp_dec])  ##[index,[trade_direction,SL,TP]]
            ##Sort out new trades to be opened
            while len(new_trades) > 0 and len(active_trades) < Max_Number_Of_Trades:
                account_balance = 0
                start_account_balance = 0
                account_balance_info = client.futures_account_balance()
                for item in account_balance_info:
                    if item['asset'] == 'USDT':
                        account_balance = float(item['balance'])
                        start_account_balance = float(item['balance'])
                        break
                [index, [trade_direction, stop_loss, take_profit]] = new_trades.pop(0)
                order_qty = leverage * order_Size * account_balance / Bots[index].Close[-1]
                order_id_temp, position_size_temp = TM.open_trade(Bots[index].symbol, trade_direction, order_qty,
                                                                  Bots[index].OP, Bots[index].Date[-1])

                ##Add on the trade which we will later Check on
                active_trades.append(Trade(index, position_size_temp, take_profit, stop_loss, trade_direction, order_id_temp,
                          Bots[index].symbol))
                if len(active_trades) >= Max_Number_Of_Trades:
                    new_trades = []  ##Don't Open any new positions

            ##Clear trades if trade list is full
            if len(active_trades) >= Max_Number_Of_Trades:
                new_trades = []  ##Don't Open any new positions

            rightnow = datetime.now().time()  ##time right now
            timer = timedelta(hours=0, minutes=0, seconds=15)  ##how often to run code below
            if (datetime.combine(date.today(), rightnow) - datetime.combine(yesterdate, start)) > timer:
                client.futures_ping()  ## ping the server to stay connected
                start = datetime.now().time()  ##reset start
                yesterdate = date.today()
                all_orders = client.futures_get_all_orders()

                ##Check if we are in a trade set compensation and TPs
                trade_index = 0
                while trade_index < len(active_trades):
                    pop_flag = 0
                    for order in all_orders:
                        if order['symbol'] == active_trades[trade_index].symbol and order['orderId'] == \
                                active_trades[trade_index].order_id and active_trades[trade_index].SL_id == '' and \
                                order['status'] == 'FILLED':

                            active_trades[trade_index].entry_price = float(client.futures_position_information(symbol=active_trades[trade_index].symbol)[0]['entryPrice'])
                            take_profit_val = 0
                            stop_loss_val = 0
                            if active_trades[trade_index].trade_direction:
                                take_profit_val = active_trades[trade_index].TP_val + active_trades[
                                    trade_index].entry_price
                                stop_loss_val = active_trades[trade_index].entry_price - active_trades[
                                    trade_index].SL_val
                            else:
                                take_profit_val = active_trades[trade_index].entry_price - active_trades[
                                    trade_index].TP_val
                                stop_loss_val = active_trades[trade_index].entry_price + active_trades[
                                    trade_index].SL_val

                            ##This position has been opened
                            if active_trades[trade_index].TP_id == '':
                                active_trades[trade_index].TP_id = TM.place_TP(active_trades[trade_index].symbol,[take_profit_val, active_trades[trade_index].position_size],
                                                                               active_trades[trade_index].trade_direction,Bots[active_trades[trade_index].index].CP,
                                                                               Bots[active_trades[trade_index].index].tick_size, Bots[trade_index].Date[-1])

                            active_trades[trade_index].SL_id = TM.place_SL(active_trades[trade_index].symbol,stop_loss_val, active_trades[trade_index].trade_direction,
                                                                           Bots[active_trades[trade_index].index].CP,Bots[active_trades[trade_index].index].tick_size, Bots[trade_index].Date[-1])
                            ##Order would trigger immediately so close the position
                            if active_trades[trade_index].SL_id == -1 or active_trades[trade_index].TP_id == -1:
                                TM.close_position(active_trades[trade_index].symbol,
                                                  active_trades[trade_index].trade_direction,
                                                  active_trades[trade_index].position_size)
                                print(f"Closed Trade on {active_trades[trade_index].symbol} as SL OR TP would have thrown a trigger immediately error")
                                pop_flag = 1
                                break
                    if pop_flag:
                        active_trades.pop(trade_index)
                    else:
                        trade_index += 1
                ##Check If trades have hit their TP values or SL value and move SL/Cancel open orders cause the trade is finished
                trade_index = 0
                while trade_index < len(active_trades):
                    pop_flag = 0
                    for order in all_orders:
                        if order['symbol'] == active_trades[trade_index].symbol and order['orderId'] == \
                                active_trades[trade_index].TP_id and order['status'] == 'FILLED':
                            ##Trading Statistics
                            TS.wins += 1
                            TS.total_number_of_trades += 1
                            account_balance = 0
                            account_balance_info = client.futures_account_balance()
                            for item in account_balance_info:
                                if item['asset'] == 'USDT':
                                    account_balance = float(item['balance'])
                                    break
                            ##Position Closed so cancel open orders and pop off list
                            try:
                                client.futures_cancel_all_open_orders(symbol=active_trades[trade_index].symbol)
                            except:
                                pass
                            pop_flag = 1  ##position Closed so pop instead of iterating
                            break
                        elif order['symbol'] == active_trades[trade_index].symbol and order['orderId'] == \
                                active_trades[trade_index].SL_id and order['status'] == 'FILLED':
                            ##Trading Statistics
                            TS.losses += 1
                            TS.total_number_of_trades += 1
                            account_balance = 0
                            account_balance_info = client.futures_account_balance()
                            for item in account_balance_info:
                                if item['asset'] == 'USDT':
                                    account_balance = float(item['balance'])
                                    break
                            ##We've hit our SL so close open orders and pop off list
                            try:
                                client.futures_cancel_all_open_orders(symbol=active_trades[trade_index].symbol)
                            except:
                                pass
                            pop_flag = 1  ##Pop off the list
                            break
                    if pop_flag == 1:
                        active_trades.pop(trade_index)
                    else:
                        trade_index += 1

                ##Check If positions have been closed manually by the user
                i = 0
                while i < len(active_trades):
                    position_info = client.futures_position_information(symbol=active_trades[i].symbol)[0]
                    if float(position_info['positionAmt']) == 0:
                        try:
                            client.futures_cancel_all_open_orders(symbol=active_trades[i].symbol) ##Close open orders on that symbol
                        except:
                            pass
                        active_trades.pop(i)
                    else:
                        i += 1

            if print_flag:
                i = 0
                while i < len(active_trades):
                    if Bots[active_trades[i].index].use_close_pos and not active_trades[i].same_candle:
                        ## Check each interval if the close position was met
                        close_pos = Bots[active_trades[i].index].check_close_pos(active_trades[i].trade_direction)
                        if close_pos:
                            TM.close_position(active_trades[i].symbol,
                                              active_trades[i].trade_direction,
                                              active_trades[i].position_size, Bots[active_trades[i].index].Date[-1])
                            close_pos = 0
                            print(f"Closed Trade on {active_trades[i].symbol} as Close Position condition was met")
                            active_trades.pop(i)
                        else:
                            i += 1
                    else:
                        active_trades[i].same_candle = False
                        break
                print_flag = 0
                temp_symbols = []
                for t in active_trades:
                    temp_symbols.append(t.symbol)
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


if __name__ == '__main__':
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
            streams.append(twm.start_kline_futures_socket(callback=DH[i].handle_socket_message, symbol=symbol[i], interval=Interval))
            i += 1
        except:
            symbol.pop(i)


    pipe1, pipe2 = Pipe()  ##pipe to communicate between processes
    _thread = Thread(target=web_soc_process, args=(pipe1, twm))
    _thread.start()

    P1 = Process(target=Check_for_signals, args=(pipe2, leverage, order_Size, Max_Number_Of_Trades, client, use_trailing_stop, trailing_stop_callback))
    P1.start()
    twm.join()  ##keep websockets running
