import os
import pprint
import time
from datetime import timedelta, datetime

from binance.client import Client
import matplotlib.pyplot as plt
from copy import copy
import pandas as pd
import numpy as np
import Helper
from Bot_Class import Bot
from Config_File import API_KEY, API_SECRET
from Helper import Trade
import matplotlib
time_delta = timedelta(hours=1)  ## Adjust time for printing based off GMT (This is GMT+1)

def run_backtester(account_balance_start, leverage, order_size,  start, end, TIME_INTERVAL, Number_Of_Trades,
                   Trade_All_Symbols, Trade_Each_Coin_With_Separate_Accounts, only_show_profitable_coins,
                   percent_gain_threshold, particular_drawdown, min_dd, symbol, use_trailing_stop,
                   trailing_stop_callback, slippage, strategy='', TP_SL_choice='',
                   SL_mult:float=1, TP_mult:float=1, use_multiprocessing_for_downloading_data=False,
                   graph_folder_location='./', plot_graphs_to_folder=True, auto_open_graph_images=False, print_to_csv=True, fee=.00036,
                   printing_on=True, add_delay=False, buffer=2000, trading_on=True, quick_test=True, graph_buys_and_sells = True,
                   graph_before=10, graph_after=10):
    if plot_graphs_to_folder:
        ## Top of script:
        matplotlib.use("Agg")
    order_size = round(order_size/100, 4)
    slippage = round(slippage / 100, 4)
    min_dd = round(min_dd, 3)
    percent_gain_threshold = round(percent_gain_threshold / 100, 3)
    trailing_stop_callback = round(trailing_stop_callback / 100, 3)

    trades_for_graphing: [Helper.trade_info] = []  ## trades: [symbol, entry_price, TP_price, SL_price, indicators, candles]
    path = f'{graph_folder_location}Backtests//{strategy}//{start}_{end}//'  ## where you want to store the graphs
    now = datetime.now()
    os.makedirs(path + f'{TIME_INTERVAL}//Backtest_{now.day}-{now.month}-{now.year}_{now.hour}_{now.minute}_{now.second}')
    backtest_path = path + f'{TIME_INTERVAL}//Backtest_{now.day}-{now.month}-{now.year}_{now.hour}_{now.minute}_{now.second}//'
    csv_name = "trade_log.csv"
    ####################################################################################################
    ####################################################################################################

    if print_to_csv:
        with open(backtest_path+csv_name, 'x') as O:
            O.write('Date,Account Balance,symbol,Entry Price,Position Size,Current Price,TP val,SL val,Trade Direction,Highest Candle,Lowest Candle,Trade Status\n')

    client = Client(api_key=API_KEY, api_secret=API_SECRET)
    if Trade_All_Symbols:
        symbol = []  ## reset symbol before we fill with all symbols below
        x = client.futures_ticker()  # [0]
        for y in x:
            symbol.append(y['symbol'])
        symbol = [x for x in symbol if 'USDT' in x]
        symbol = [x for x in symbol if not '_' in x]
    y = client.futures_exchange_info()['symbols']
    coin_info = []
    for x in y:
        coin_info.append([x['pair'], x['pricePrecision'], x['quantityPrecision'], x['filters'][0]['tickSize'],
                          x['filters'][0]['minPrice']])

    if trailing_stop_callback < .001 and use_trailing_stop:
        trailing_stop_callback = .001
        print("*********************************\nCallback rate must be >= .001, I have set callback rate to .001 for you\n*********************************")
    trailing_stop_callback = round(trailing_stop_callback, 3) ##Traling stop can only be a multiple of .1% ie 3 decimals
    print(f"Coins Tradeable : {symbol}")
    pp = pprint.PrettyPrinter()
    change_occurred = False
    time_CAGR = Helper.get_CAGR(start, end)
    if Trade_Each_Coin_With_Separate_Accounts:
        Number_Of_Trades = len(symbol)
    Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume = [], [], [], [], [], [], [], [], [], [], []
    print("Loading Price Data")
    if use_multiprocessing_for_downloading_data:
        Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol = Helper.multiprocess_get_candles(symbol, TIME_INTERVAL, start, end)
    else:
        Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol = \
            Helper.get_aligned_candles([], [], [], [], [], [], [], [], [], [], [], symbol, TIME_INTERVAL, start, end)
    print(symbol)

    if printing_on:
        print(f"{TIME_INTERVAL} OHLC Candle Sticks from {start} to {end}")

    Bots: [Bot] = []

    original_time_interval = copy(TIME_INTERVAL)
    TIME_INTERVAL = Helper.get_TIME_INTERVAL(TIME_INTERVAL)  ##Convert string to an integer for the rest of the script
    if len(Open[0]) < 300:
        print("Not Enough Candles Increase the period over which you are running a backtest")
        time.sleep(20)
    wins_and_lossses = {}
    for k in range(len(symbol)):
        Coin_precision_temp = -99
        Order_precision_temp = -99
        tick_temp = -99
        for x in coin_info:
            if x[0] == symbol[k]:
                Coin_precision_temp = int(x[1])
                Order_precision_temp = int(x[2])
                tick_temp = float(x[3])
                wins_and_lossses[symbol[k]] = {'wins': 0, 'losses': 0, 'trades': 0}
                break
        if quick_test:
            Bots.append(Bot(symbol[k], Open[k], Close[k], High[k], Low[k], Volume[k], Date[k],
                        Order_precision_temp, Coin_precision_temp, k, tick_temp, strategy, TP_SL_choice, SL_mult, TP_mult, 1))
        else:
            Bots.append(Bot(symbol[k], Open[k][:buffer], Close[k][:buffer], High[k][:buffer], Low[k][:buffer], Volume[k][:buffer], Date[k][:buffer],
                            Order_precision_temp, Coin_precision_temp, k, tick_temp, strategy, TP_SL_choice, SL_mult,
                            TP_mult, 1))
        Bots[k].add_hist([], [], [], [], [], [])

    # Initialize vars for profit calculation
    tradeNO = 0  ##number of trades
    active_trades: [Trade] = []
    new_trades = []
    account_balance = []
    Daily_return = []
    winning_trades = []
    losing_trades = []
    closed_on_condition = []
    profitgraph = []  # for graphing the profit change over time
    for i in range(len(symbol)):
        account_balance.append(account_balance_start)
        profitgraph.append([account_balance_start])
        Daily_return.append([])
    originalBalance = copy(account_balance)

    if printing_on:
        print("Account Balance: ", account_balance[0])
    for i in range((buffer - 1)*TIME_INTERVAL, len(Close_1min[0]) - 1 - TIME_INTERVAL * 2):
        if account_balance[0] < 0 and not Trade_Each_Coin_With_Separate_Accounts:
            if printing_on:
                print("Negative Balance")
            break
        ##give each coin next piece of data
        if (i + 1) % TIME_INTERVAL == 0 or TIME_INTERVAL == 1:
            for k in range(len(symbol)):
                if quick_test:
                    Bots[k].current_index = int(i / TIME_INTERVAL)
                else:
                    try:
                        Bots[k].handle_socket_message(-99, Date[k][int(i / TIME_INTERVAL)], Close[k][int(i / TIME_INTERVAL)],
                                                      Volume[k][int(i / TIME_INTERVAL)], Open[k][int(i / TIME_INTERVAL)],
                                                      High[k][int(i / TIME_INTERVAL)], Low[k][int(i / TIME_INTERVAL)])
                    except Exception as e:
                        print(f"Error at handle_socket_message: {e}")
            if not trading_on and str(Date[0][int(i / TIME_INTERVAL)]) == start_trading_date:
                trading_on = True
                print("Trading Started")

            for k in range(len(Bots)):
                trade_flag = 0
                for t in active_trades:
                    if t.index == k:
                        trade_flag = 1
                        break
                if trade_flag == 0 and (len(Bots[k].Date) > i / TIME_INTERVAL or not quick_test):
                    temp_dec = Bots[k].Make_decision()
                    if temp_dec[0] != -99:
                        new_trades.append([k, temp_dec])

        if len(active_trades) == Number_Of_Trades:
            new_trades = []
            ##Sort out new trades to be opened
        while len(new_trades) > 0 and len(active_trades) < Number_Of_Trades and trading_on:
            [index, [trade_direction, stop_loss, take_profit]] = new_trades.pop(0)
            order_qty = 0
            entry_price = 0
            if Trade_Each_Coin_With_Separate_Accounts:
                Order_Notional = account_balance[index] * leverage * order_size
                order_qty, entry_price, account_balance[index] = Helper.open_trade(Bots[index].symbol, Order_Notional,
                                                                        account_balance[index], Open_1min[index][i+1],
                                                                        fee, Bots[index].OP, Bots[index].CP, trade_direction, slippage)
            else:
                Order_Notional = account_balance[0] * leverage * order_size
                order_qty, entry_price, account_balance[0] = Helper.open_trade(Bots[index].symbol, Order_Notional,
                                                                               account_balance[0],
                                                                               Open_1min[index][i+1],
                                                                               fee, Bots[index].OP, Bots[index].CP, trade_direction, slippage)

            take_profit_val = -99
            stop_loss_val = -99
            ## Calculate the prices for TP and SL
            if trade_direction == 1:
                take_profit_val = take_profit + entry_price
                stop_loss_val = entry_price - stop_loss
            elif trade_direction == 0:
                take_profit_val = entry_price - take_profit
                stop_loss_val = entry_price + stop_loss

            ## Round to the coins specific coin precision
            if Bots[index].CP == 0:
                take_profit_val = round(take_profit_val)
                stop_loss_val = round(stop_loss_val)
            else:
                take_profit_val = round(take_profit_val, Bots[index].CP)
                stop_loss_val = round(stop_loss_val, Bots[index].CP)
            if order_qty > 0:
                tradeNO += 1
                ## Append new trade, to our trade list
                ## (index, position_size, tp_val, stop_loss_val, trade_direction, order_id_temp, symbol)
                active_trades.append(Trade(index, order_qty, take_profit_val, stop_loss_val, trade_direction, 0, Bots[index].symbol))
                active_trades[-1].entry_price = entry_price
                active_trades[-1].trade_start = Date_1min[index][i]
                active_trades[-1].trade_info.entry_price = entry_price
                active_trades[-1].trade_info.trade_start_index = Bots[index].current_index
                active_trades[-1].trade_info.start_time = Date_1min[index][i+1]
                change_occurred = True
                ##Empty the list of trades
                if len(active_trades) == Number_Of_Trades:
                    new_trades = []

        for t in active_trades:
            ## stuff for csv
            if t.trade_status == 1:
                if t.Highest_val < High_1min[t.index][i]:
                    t.Highest_val = High_1min[t.index][i]
                if t.Lowest_val > Low_1min[t.index][i]:
                    t.Lowest_val = Low_1min[t.index][i]
            ## Check SL Hit
            if t.trade_status == 1:
                if Trade_Each_Coin_With_Separate_Accounts:
                    t, account_balance[t.index] = Helper.check_SL(t, account_balance[t.index], High_1min[t.index][i], Low_1min[t.index][i], fee)
                else:
                    t, account_balance[0] = Helper.check_SL(t, account_balance[0], High_1min[t.index][i], Low_1min[t.index][i], fee)
                if t.trade_status != 1:
                    change_occurred = True
            ##Check if TP Hit
            if t.trade_status == 1:
                if Trade_Each_Coin_With_Separate_Accounts:
                    t, account_balance[t.index] = Helper.check_TP(t, account_balance[t.index], High_1min[t.index][i], Low_1min[t.index][i], fee, use_trailing_stop, trailing_stop_callback, Bots[t.index].CP)
                else:
                    t, account_balance[0] = Helper.check_TP(t, account_balance[0], High_1min[t.index][i], Low_1min[t.index][i], fee, use_trailing_stop, trailing_stop_callback, Bots[t.index].CP)
                if t.trade_status != 1:
                    change_occurred = True
            if Bots[t.index].use_close_pos and t.trade_status == 1 and (i % TIME_INTERVAL == 0 or TIME_INTERVAL == 1):
                ## Check each interval if the close position was met
                close_pos = Bots[t.index].check_close_pos(t.trade_direction)
                if close_pos:
                    if Trade_Each_Coin_With_Separate_Accounts:
                        t, account_balance[t.index] = Helper.close_pos(t, account_balance[t.index], fee, Close_1min[t.index][i])
                    else:
                        t, account_balance[0] = Helper.close_pos(t, account_balance[0], fee, Close_1min[t.index][i])
                    close_pos = 0
                    print(f"Closing Trade on {t.symbol} as Close Position condition was met")
                    t.trade_status = 4  ## Closed on condition
                    change_occurred = True

        ## Check PNL here as well as print the current trades:
        if printing_on:
            trade_price = []
            for t in active_trades:
                trade_price.append(Bots[t.index].Close[Bots[t.index].current_index])
            if Trade_Each_Coin_With_Separate_Accounts:
                pnl, negative_balance_flag, change_occurred = Helper.print_trades(active_trades, trade_price, Date_1min[0][i],
                                                                                  account_balance, change_occurred, print_to_csv, csv_name, path, backtest_path, time_delta)
            else:
                pnl, negative_balance_flag, change_occurred = Helper.print_trades(active_trades, trade_price, Date_1min[0][i],
                                                                                  [account_balance[0]], change_occurred, print_to_csv, csv_name, path, backtest_path, time_delta)
            if negative_balance_flag and not Trade_Each_Coin_With_Separate_Accounts:
                print("**************** You have been liquidated *******************")
                profitgraph[0].append(0)
                account_balance[0] = 0
                break  ## break out of loop as we've been liquidated
            if add_delay:
                time.sleep(1)

        k = 0
        while k < len(active_trades):
            if active_trades[k].trade_status == 2:
                ## Win
                winning_trades.append([active_trades[k].symbol, f'{active_trades[k].trade_start}'])
                if Trade_Each_Coin_With_Separate_Accounts:
                    profitgraph[active_trades[k].index].append(account_balance[active_trades[k].index])
                    wins_and_lossses[active_trades[k].symbol]['wins'] += 1
                    wins_and_lossses[active_trades[k].symbol]['trades'] += 1
                else:
                    profitgraph[0].append(account_balance[0])
                active_trades[k].trade_info.trade_success = True
                active_trades[k] = Helper.get_candles_for_graphing(Bots[active_trades[k].index], active_trades[k], graph_before, graph_after)
                active_trades[k] = Helper.get_indicators_for_graphing(Bots[active_trades[k].index].indicators, active_trades[k], graph_before,
                                                                      graph_after, Bots[active_trades[k].index].current_index)
                trades_for_graphing.append(active_trades[k].trade_info)
                active_trades.pop(k)
            elif active_trades[k].trade_status == 3:
                ## Loss
                losing_trades.append([active_trades[k].symbol, f'{active_trades[k].trade_start}'])
                if Trade_Each_Coin_With_Separate_Accounts:
                    profitgraph[active_trades[k].index].append(account_balance[active_trades[k].index])
                    wins_and_lossses[active_trades[k].symbol]['losses'] += 1
                    wins_and_lossses[active_trades[k].symbol]['trades'] += 1
                else:
                    profitgraph[0].append(account_balance[0])
                active_trades[k] = Helper.get_candles_for_graphing(Bots[active_trades[k].index], active_trades[k],
                                                                   graph_before, graph_after)
                active_trades[k] = Helper.get_indicators_for_graphing(Bots[active_trades[k].index].indicators,
                                                                      active_trades[k], graph_before, graph_after,
                                                                      Bots[active_trades[k].index].current_index)
                trades_for_graphing.append(active_trades[k].trade_info)
                active_trades.pop(k)
            elif active_trades[k].trade_status == 4:
                if (active_trades[k].entry_price < Close[active_trades[k].index][Bots[active_trades[k].index].current_index] and active_trades[k].trade_direction == 1) \
                or (active_trades[k].entry_price > Close[active_trades[k].index][Bots[active_trades[k].index].current_index] and active_trades[k].trade_direction == 0):
                    winning_trades.append([active_trades[k].symbol, f'{active_trades[k].trade_start}'])
                    active_trades[k].trade_info.trade_success = True
                    active_trades[k] = Helper.get_candles_for_graphing(Bots[active_trades[k].index], active_trades[k],
                                                                       graph_before, graph_after)
                    active_trades[k] = Helper.get_indicators_for_graphing(Bots[active_trades[k].index].indicators,
                                                                          active_trades[k], graph_before, graph_after,
                                                                          Bots[active_trades[k].index].current_index)
                    trades_for_graphing.append(active_trades[k].trade_info)
                else:
                    losing_trades.append([active_trades[k].symbol, f'{active_trades[k].trade_start}'])
                    active_trades[k] = Helper.get_candles_for_graphing(Bots[active_trades[k].index], active_trades[k],
                                                                       graph_before, graph_after)
                    active_trades[k] = Helper.get_indicators_for_graphing(Bots[active_trades[k].index].indicators,
                                                                          active_trades[k], graph_before, graph_after,
                                                                          Bots[active_trades[k].index].current_index)
                    trades_for_graphing.append(active_trades[k].trade_info)
                if Trade_Each_Coin_With_Separate_Accounts:
                    profitgraph[active_trades[k].index].append(account_balance[active_trades[k].index])
                else:
                    profitgraph[0].append(account_balance[0])
                active_trades.pop(k)
            else:
                if active_trades[k].trade_status == 0:
                    active_trades[k].trade_status = 1
                k += 1

        if i == len(Close_1min[0]) - 2:
            for x in Date_1min:
                print(f"Data Set Finished: {x[i]}")
        if i % 1440 == 0 and i != 0:
            for j in range(len(symbol)):
                Daily_return[j].append(account_balance[j])  # (day_return/day_start_equity)
            # day_return=0
            # day_start_equity=AccountBalance
        elif i == len(Close_1min[0]) - 1:
            for j in range(len(symbol)):
                Daily_return[j].append(account_balance[j])  # (day_return/day_start_equity)
    print("\n")
    if not Trade_Each_Coin_With_Separate_Accounts:
        average = 0
        num_wins = 0
        for i in range(1, len(profitgraph[0])):
            if profitgraph[0][i] > profitgraph[0][i - 1]:
                num_wins += 1
                average += (profitgraph[0][i] - profitgraph[0][i - 1]) / profitgraph[0][i]

        if num_wins != 0:
            average /= num_wins
        CAGR = 0
        vol = 0
        Sharpe_ratio = 0
        sortino_ratio = 0
        calmar_ratio = 0
        risk_free_rate = 1.41  ##10 year treasury rate
        df = pd.DataFrame({'Account_Balance': Daily_return[0]})
        df['daily_return'] = df['Account_Balance'].pct_change()
        df['cum_return'] = (1 + df['daily_return']).cumprod()
        df['cum_roll_max'] = df['cum_return'].cummax()
        df['drawdown'] = df['cum_roll_max'] - df['cum_return']
        df['drawdown %'] = df['drawdown'] / df['cum_roll_max']
        max_dd = df['drawdown %'].max() * 100
        try:
            # cum_ret = np.array(df['cum_return'])
            CAGR = ((df['cum_return'].iloc[-1]) ** (1 / time_CAGR) - 1) * 100  # ((df['cum_return'].iloc[-1])**(1/time_CAGR)-1)*100
            vol = (df['daily_return'].std() * np.sqrt(365)) * 100
            neg_vol = (df[df['daily_return'] < 0]['daily_return'].std() * np.sqrt(365)) * 100
            Sharpe_ratio = (CAGR - risk_free_rate) / vol
            sortino_ratio = (CAGR - risk_free_rate) / neg_vol
            calmar_ratio = CAGR / max_dd
        except:
            pass

        print("\nSettings:")
        print('leverage:', leverage)
        print('order_size:', order_size)
        print('fee:', fee)
        print("\nSymbol(s):", symbol, "fee:", fee)
        print(f"{original_time_interval} OHLC Candle Sticks from {start} to {end}")
        print("Account Balance:", account_balance[0])
        print("% Gain on Account:", ((account_balance[0] - originalBalance[0]) * 100) / originalBalance[0])
        print("Total Returns:", account_balance[0] - originalBalance[0], "\n")

        print(f"Annualized Volatility: {round(vol, 4)}%")
        print(f"CAGR: {round(CAGR, 4)}%")
        print("Sharpe Ratio:", round(Sharpe_ratio, 4))
        print("Sortino Ratio:", round(sortino_ratio, 4))
        print("Calmar Ratio:", round(calmar_ratio, 4))
        print(f"Max Drawdown: {round(max_dd, 4)}%")

        print(f"Average Win: {round(average * 100, 4)}%")
        print("Trades Made: ", tradeNO)
        print("Accuracy: ", f"{(len(winning_trades) / tradeNO) * 100}%", "\n")
        print(f"Winning Trades:\n {len(winning_trades)}")
        print(f"Losing Trades:\n {len(losing_trades)}")
        plt.plot(profitgraph[0])
        if Trade_All_Symbols:
            plt.title(f"All Coins: {original_time_interval} from {start} to {end}")
        else:
            plt.title(f"{symbol}: {original_time_interval} from {start} to {end}")
        plt.ylabel('Account Balance')
        plt.xlabel('Number of Trades')
        if plot_graphs_to_folder:
            if not os.path.exists(path + f'{original_time_interval}'):
                os.makedirs(path + f'{original_time_interval}')
            plt.savefig(f'{backtest_path}equity_curve.png', dpi=300)
            plt.close()
        else:
            plt.show()

    else:
        useful_coins = []
        num_wins_total = 0
        for j in range(len(symbol)):
            if (only_show_profitable_coins and account_balance[j] > originalBalance[j]*(1 + percent_gain_threshold)) or (not only_show_profitable_coins):
                average = 0
                num_wins = 0
                for i in range(1, len(profitgraph[j])):
                    if profitgraph[j][i] > profitgraph[j][i - 1]:
                        num_wins += 1
                        average += (profitgraph[j][i] - profitgraph[j][i - 1]) / profitgraph[j][i]
                if num_wins != 0:
                    average /= num_wins
                num_wins_total += num_wins
                risk_free_rate = 1.41  ##10 year treasury rate
                try:
                    df = pd.DataFrame({'Account_Balance': Daily_return[j]})
                    df['daily_return'] = df['Account_Balance'].pct_change()
                    df['cum_return'] = (1 + df['daily_return']).cumprod()
                    df['cum_roll_max'] = df['cum_return'].cummax()
                    df['drawdown'] = df['cum_roll_max'] - df['cum_return']
                    df['drawdown %'] = df['drawdown'] / df['cum_roll_max']
                    max_dd = df['drawdown %'].max() * 100

                    # cum_ret = np.array(df['cum_return'])
                    CAGR = ((df['cum_return'].iloc[-1]) ** (
                                1 / time_CAGR) - 1) * 100  # ((df['cum_return'].iloc[-1])**(1/time_CAGR)-1)*100
                    vol = (df['daily_return'].std() * np.sqrt(365)) * 100
                    neg_vol = (df[df['daily_return'] < 0]['daily_return'].std() * np.sqrt(365)) * 100
                    Sharpe_ratio = (CAGR - risk_free_rate) / vol
                    sortino_ratio = (CAGR - risk_free_rate) / neg_vol
                    calmar_ratio = CAGR / max_dd
                    if (particular_drawdown and max_dd < min_dd) or not particular_drawdown:
                        accuracy = (wins_and_lossses[symbol[j]]['wins']*100)/wins_and_lossses[symbol[j]]['trades']
                        check_accuracy_percent = False
                        accuracy_percent = 90
                        if accuracy_percent < accuracy and check_accuracy_percent or not check_accuracy_percent:
                            useful_coins.append(symbol[j])
                            print("Symbol:", symbol[j], "fee:", fee)
                            print(f"{original_time_interval} OHLC Candle Sticks from {start} to {end}")
                            print("Account Balance:", account_balance[j])
                            print("% Gain on Account:", ((account_balance[j] - originalBalance[j]) * 100) / originalBalance[j])
                            print("Total Returns:", account_balance[j] - originalBalance[j])
                            print(f"Annualized Volatility: {round(vol, 4)}%")
                            print(f"CAGR: {round(CAGR, 4)}%")
                            print(f"Accuracy: {accuracy}%")
                            print(f"Trades Taken: {wins_and_lossses[symbol[j]]['trades']}")
                            print("Sharpe Ratio:", round(Sharpe_ratio, 4))
                            print("Sortino Ratio:", round(sortino_ratio, 4))
                            print("Calmar Ratio:", round(calmar_ratio, 4))
                            print(f"Max Drawdown: {round(max_dd, 4)}%")
                            print(f"Average Win: {round(average * 100, 4)}%\n")
                        if plot_graphs_to_folder:
                            if not os.path.exists(path + f'{original_time_interval}'):
                                os.makedirs(path + f'{original_time_interval}')
                            plt.plot(profitgraph[j])
                            plt.title(f"{symbol[j]}: {original_time_interval} from {start} to {end}")
                            plt.ylabel('Account Balance')
                            plt.xlabel('Number of Trades')
                            plt.savefig(f'{backtest_path}{symbol[j]}_equity_curve.png', dpi=300, bbox_inches='tight')
                            plt.close()
                except Exception as e:
                    print(e)
        print("\nSettings:")
        print('leverage:', leverage)
        print('order_size:', order_size)
        print('fee:', fee)
        print(f"symbol = {useful_coins}")
        print("\nOverall Stats based on all coins")
        print("Trades Made: ", tradeNO)
        print("Accuracy: ", f"{(len(winning_trades) / tradeNO) * 100}%", "\n")
        print(f"Winning Trades:\n {len(winning_trades)}")
        print(f"Losing Trades:\n {len(losing_trades)}")
        print(f"Trades Closed on Condition:\n {closed_on_condition}")

    if graph_buys_and_sells:
        Helper.generate_trade_graphs(trades_for_graphing, backtest_path, auto_open_graph_images) ## trades: [symbol, entry_price, TP_price, SL_price, indicators, candles]


if __name__ == "__main__":
    start = "01-11-22"
    end = "01-12-22"
    buffer = 500 ## candlestick buffer, should be 5x your largest EMA length
    account_balance = 100  ## Starting account size
    fee = .00036 ## .036%
    leverage = 10
    order_size = 1.25  ## 1.25% of account balance per trade with 10x leverage the position size would be 12.5%
    TIME_INTERVAL = '5m'  ## valid intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d
    Number_Of_Trades = 5  ## max amount of trades the bot will have open at any time
    slippage = .01  ## .01% recommended to use at least .01% slippage, the more slippage the strategy can survive the better the signals
    TP_SL_choice = '%'  ## type of TP/SL used in backtest, list of valid values: '%', 'x (ATR)', 'x (Swing High/Low) level 1', 'x (Swing Close) level 1', 'x (Swing High/Low) level 2', 'x (Swing Close) level 2', 'x (Swing High/Low) level 3', 'x (Swing Close) level 3'
    SL_mult = .5  ## multiplier for the 'TP_SL_choice' above
    TP_mult = 1  ## multiplier for the 'TP_SL_choice' above
    strategy = 'StochRSIMACD'  ##name of strategy you want to run

    use_trailing_stop = False  ## flag to use the trailing stop with callback distance defined below
    trailing_stop_callback = 1  ## 1% keep the trailing stop this percent away from the last high/ low
    Trade_Each_Coin_With_Separate_Accounts = False  ## Isolated test will generate graphs for each coin as if it was trading separately from the other coins
    only_show_profitable_coins = False  # flag for the below percentage
    percent_gain_threshold = 1  ## percentage for 'only_show_profitable_coins' flag, will only show coins at the end of the backtest that have made this amount of profit or more
    particular_drawdown = False  ## Flag for minimum drawdown below
    min_dd = 1  ## 1%, Only print coins which have had less than this drawdown when the above flag 'particular_drawdown' is True

    symbol = ['BTCUSDT', 'BAKEUSDT']  ## list of coins to trade, example: ['ETHUSDT', 'BNBUSDT']
    Trade_All_Symbols = False  ## will test on all coins on exchange if true

    '''
     Trade Graphing Settings
    '''
    graph_buys_and_sells = True
    auto_open_graph_images = False ## Set to true to open all the trade graphs on completion (Caution this may use up a lot of memory)
    graph_buys_and_sells_window_before = 5 ## graph 5 candles before the trade opened
    graph_buys_and_sells_window_after = 5 ## graph 5 candles after the trade opened

    ## Variables you probably don't need to change:
    trading_on = True  ## Set to false to use the trading start time below, CAUTION ensure trading is withing start and end or you will get errors
    start_trading_date = '2022-10-24 18:00:00'  ## Particular time to start trading at not used if trading_on = True
    use_multiprocessing_for_downloading_data = True ## use multiprocessing for quicker backtesting

    run_backtester(account_balance, leverage, order_size, start, end, TIME_INTERVAL, Number_Of_Trades,
                   Trade_All_Symbols, Trade_Each_Coin_With_Separate_Accounts, only_show_profitable_coins,
                   percent_gain_threshold, particular_drawdown, min_dd,
                   symbol, use_trailing_stop, trailing_stop_callback, slippage, strategy, TP_SL_choice,
                   SL_mult, TP_mult, use_multiprocessing_for_downloading_data, graph_folder_location='./',
                   plot_graphs_to_folder=True, print_to_csv=True, fee=fee, printing_on=True, add_delay=False,
                   buffer=buffer, trading_on=trading_on, quick_test=True, graph_buys_and_sells=graph_buys_and_sells,
                   auto_open_graph_images=auto_open_graph_images, graph_before=graph_buys_and_sells_window_before,
                   graph_after=graph_buys_and_sells_window_after)
