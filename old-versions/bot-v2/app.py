import tkinter as tk
from tkinter import *
import os
import webbrowser
from Backtester import run_backtester
from Live_Bot import *
from threading import Thread
from multiprocessing import Process
from binance.client import Client

if __name__ == "__main__":
    profit_required, start_balance, leverage, order_size, start, end, isolated_test, only_show_profitable_coins, particular_drawdown, min_dd, slippage, trading_threshold, use_market_orders, use_multiprocessing = None, None, None, None, None, None, None, None, None, None, None, None, None, None
    API_KEY, API_SECRET, buffer = None, None, None
    P: [Process] = []
    client = Client()
    valid_symbols = []  ## reset symbol before we fill with all symbols below
    symbol = []
    x = client.futures_ticker()  # [0]
    for y in x:
        valid_symbols.append(y['symbol'])
    valid_symbols = [x for x in valid_symbols if 'USDT' in x]
    valid_symbols = [x for x in valid_symbols if not '_' in x]

    def go_to_github():
        webbrowser.open_new(r"https://github.com/sponsors/conor19w?frequency=recurring&sponsor=conor19w")

    def go_to_trello():
        webbrowser.open_new(r"https://trello.com/b/iagTNiv0/github-bot")

    def live_mode():
        global leverage, order_size, API_KEY, API_SECRET, buffer, trading_threshold, use_market_orders
        for child in frame.winfo_children():
            child.destroy()
        Live_Bot.configure(bg="light blue", fg="black")
        Backtester.configure(bg="#457E81", fg='white')
        host.configure(bg="#457E81", fg="white")

        header = tk.Label(frame, text="Live Trading", bg="light blue")
        header.place(relx=0.45, rely=.06)

        label1 = tk.Label(frame, text="API Key:", bg="light blue")
        label1.place(relx=.01, rely=.1)
        API_KEY = tk.Entry(frame)
        API_KEY.place(relx=.1, rely=.1, relwidth=.2)

        label2 = tk.Label(frame, text="API Secret:", bg="light blue")
        label2.place(relx=.01, rely=.15)
        API_SECRET = tk.Entry(frame)
        API_SECRET.place(relx=.1, rely=.15, relwidth=.2)

        label6 = tk.Label(frame, text="Order Size (% of account):", bg="light blue")
        label6.place(relx=.01, rely=.3)
        order_size = tk.Entry(frame)
        order_size.insert(0, "2.5")
        order_size.place(relx=.2, rely=.3, relwidth=.075)

        label7 = tk.Label(frame, text="leverage:", bg="light blue")
        label7.place(relx=.01, rely=.335)
        leverage = tk.Entry(frame)
        leverage.insert(0, "10")
        leverage.place(relx=.08, rely=.335, relwidth=.075)

        label15 = tk.Label(frame, text="buffer:", bg="light blue")
        label15.place(relx=.28, rely=.2)
        buffer = tk.Entry(frame)
        buffer.insert(0, "2 days ago")
        buffer.place(relx=.33, rely=.2, relwidth=.1)

        save_api = tk.Button(frame, text="Save Keys", fg='white', bg="#457E81",
                            activebackground="light blue",
                            cursor="trek", command=save_keys)
        save_api.place(relwidth=(1 / 10), relheight=(1 / 30), relx=.315, rely=.1)

        load_api = tk.Button(frame, text="Load Keys", fg='white', bg="#457E81",
                             activebackground="light blue",
                             cursor="trek", command=load_keys)
        load_api.place(relwidth=(1 / 10), relheight=(1 / 30), relx=.315, rely=.15)

        label16 = tk.Label(frame, text="Trading Threshold (%):", bg="light blue")
        label16.place(relx=.3, rely=.3)
        trading_threshold = tk.Entry(frame)
        trading_threshold.insert(0, ".1")
        trading_threshold.place(relx=.47, rely=.3, relwidth=.075)

        use_market_orders = BooleanVar()
        use_market_orders_checkbox = Checkbutton(frame, text="Use Market Orders",
                                    variable=use_market_orders, bg="light blue", activebackground="light blue")
        use_market_orders_checkbox.place(relx=.3, rely=.34)

        run_bot = tk.Button(frame, text="Run Bot", fg='white', bg="#457E81",
                            activebackground="light blue",
                            cursor="trek", command=run_live_bot)
        run_bot.place(relwidth=(1 / 3), relheight=(1 / 8), relx=(1 / 3), rely=(2 / 3))

    def backtest_mode():
        global profit_required, start_balance, leverage, order_size, start, end, isolated_test, only_show_profitable_coins, particular_drawdown, min_dd, slippage, use_multiprocessing
        for child in frame.winfo_children():
            child.destroy()
        ## Set up initial input boxes
        header = tk.Label(frame, text="Backtesting", bg="light blue")
        header.place(relx=0.45, rely=.06)

        label1 = tk.Label(frame, text="Start (dd-mm-yy):", bg="light blue")
        label1.place(relx=.01, rely=.1)
        start = tk.Entry(frame)
        start.insert(0, "19-10-22")
        start.place(relx=.16, rely=.1, relwidth=.085)

        label2 = tk.Label(frame, text="End (dd-mm-yy):", bg="light blue")
        label2.place(relx=.01, rely=.15)
        end = tk.Entry(frame)
        end.insert(0, "26-10-22")
        end.place(relx=.16, rely=.15, relwidth=.085)
        Live_Bot.configure(bg="#457E81", fg='white')
        Backtester.configure(bg="light blue", fg="black")
        host.configure(bg="#457E81", fg="white")

        label5 = tk.Label(frame, text="Starting Balance:", bg="light blue")
        label5.place(relx=.25, rely=.1)
        start_balance = tk.Entry(frame)
        start_balance.place(relx=.375, rely=.1, relwidth=.075)
        start_balance.insert(0, "87")

        label6 = tk.Label(frame, text="Order Size (% of account):", bg="light blue")
        label6.place(relx=.25, rely=.15)
        order_size = tk.Entry(frame)
        order_size.insert(0, "1.25")
        order_size.place(relx=.43, rely=.15, relwidth=.075)

        label7 = tk.Label(frame, text="leverage:", bg="light blue")
        label7.place(relx=.25, rely=.2)
        leverage = tk.Entry(frame)
        leverage.insert(0, "10")
        leverage.place(relx=.33, rely=.2, relwidth=.075)

        use_multiprocessing = BooleanVar(value=True)
        use_multiprocessing_checkbox = Checkbutton(frame,
                                             text="Use Multiprocessing for downloading Data. \n (Turn off if running more than one bot locally)",
                                             variable=use_multiprocessing, bg="light blue", activebackground="light blue")
        use_multiprocessing_checkbox.place(relx=.01, rely=.5)

        isolated_test = BooleanVar()
        isolated_test_checkbox = Checkbutton(frame,
                                             text="Isolated Test: (If on strategy will be evaluated on each coin with a separate balance.\n Good for finding coins that get good signals from the strategy)",
                                             variable=isolated_test, bg="light blue", activebackground="light blue")
        isolated_test_checkbox.place(relx=.01, rely=.305)

        only_show_profitable_coins = BooleanVar()
        only_show_profitable_coins_checkbox = Checkbutton(frame, variable=only_show_profitable_coins,
                                                          text="Profit Required:\t\t\t\t\n\n(Only Show coins that Profit more than this %)",
                                                          bg="light blue", activebackground="light blue")
        only_show_profitable_coins_checkbox.place(relx=.43, rely=.42)
        profit_required = tk.Entry(frame)
        profit_required.place(relx=.6, rely=.423, relwidth=.075)
        profit_required.insert(0, "0.0")

        particular_drawdown = BooleanVar()
        particular_drawdown_checkbox = Checkbutton(frame, variable=particular_drawdown,
                                                          text="Use Min DD:\t\t\t\t\n\n(Only Show coins that have DD less than this %)",
                                                          bg="light blue", activebackground="light blue")
        particular_drawdown_checkbox.place(relx=.43, rely=.52)
        min_dd = tk.Entry(frame)
        min_dd.place(relx=.6, rely=.523, relwidth=.075)
        min_dd.insert(0, "0.0")

        label15 = tk.Label(frame, text="Slippage (%):", bg="light blue")
        label15.place(relx=.63, rely=.375)
        slippage = tk.Entry(frame)
        slippage.place(relx=.75, rely=.375, relwidth=.075)
        slippage.insert(0, "0.1")

        run_Backtest = tk.Button(frame, text="Run Backtest", fg='white', bg="#457E81",
                                 activebackground="light blue",
                                 cursor="trek", command=run_backtest)
        run_Backtest.place(relwidth=(1 / 3), relheight=(1 / 8), relx=(1 / 3), rely=(2 / 3))


    def host_mode():
        pass
        #Live_Bot.configure(bg="#457E81", fg="white")
        #Backtester.configure(bg="#457E81", fg='white')
        #host.configure(bg="light blue", fg="black")


    # noinspection PyUnresolvedReferences
    def run_backtest():
        global P
        if symbol == [] and not trade_all_coins.get():
            print("Add some coins to the list or tick trade all coins before running a backtest")
            return
        start_date = start.get()
        end_date = end.get()
        if start_date == '' or end_date == '' or ((int(start_date[-2:]) > int(end_date[-2:])) or
                                                  ((int(start_date[-5:-3]) > int(end_date[-5:-3])) and (int(start_date[-2:]) == int(end_date[-2:]))) or
                                                  ((int(start_date[:-6]) > int(end_date[:-6])) and (int(start_date[-5:-3]) == int(end_date[-5:-3])) and (int(start_date[-2:]) == int(end_date[-2:])))):
            print("Invalid Start/End parameters fix them before running a backtest")
            return

        if len(P) > 0:
            i = 0
            while i < len(P):
                if not P[i].is_alive():
                    P.pop(i)
                else:
                    i += 1


        if len(P) == 0:
            profit_req = 0
            min_dd_req = 0
            slip = 0
            if profit_required.get() != '':
                profit_req = float(profit_required.get())
            if min_dd.get() != '':
                min_dd_req = float(min_dd.get())
            if slippage.get() != '':
                slip = float(slippage.get())

            P.append(Process(target=run_backtester, args=(float(start_balance.get()), int(leverage.get()), float(order_size.get()), start.get(), end.get(),
                     candle_length.get(), int(number_of_trades.get()), trade_all_coins.get(), isolated_test.get(), only_show_profitable_coins.get(),
                     profit_req, particular_drawdown.get(), min_dd_req, symbol, use_trail_stop.get(), float(trail_stop.get()), slip,
                     strategy.get(), TP_SL.get(), float(SL.get()), float(TP.get()), use_multiprocessing.get())))
            P[-1].start()


    # noinspection PyUnresolvedReferences
    def run_live_bot():
        global P

        if len(P) > 0:
            i = 0
            while i < len(P):
                if not P[i].is_alive():
                    P.pop(i)
                else:
                    i += 1
        if len(P) == 0:

            P.append(Process(target=run_bot, args=(API_KEY.get(), API_SECRET.get(), int(leverage.get()),
                     float(order_size.get()), buffer.get(), candle_length.get(), int(number_of_trades.get()),
                     use_trail_stop.get(), round(float(trail_stop.get()), 1), symbol, strategy.get(), TP_SL.get(),
                     float(SL.get()), float(TP.get()), trade_all_coins.get(), use_market_orders.get(), float(trading_threshold.get()))))
            P[-1].start()

    def save_keys():
        if API_KEY.get() != '' and API_SECRET.get() != '':
            ## Remove previous text
            with open('keys.txt', 'w') as o:
                o.write("")

            with open('keys.txt', 'a') as o:
                o.write(API_KEY.get() + '\n')
                o.write(API_SECRET.get())
            print("Keys Saved to text file in the directory")

    def load_keys():
        try:
            with open('keys.txt', 'r') as o:
                trades = o.readlines()
            API_KEY.insert(0, trades[0].strip('\\n').strip())
            API_SECRET.insert(0, trades[1])
        except Exception as e:
            print("No Keys present to load in")



    def add_new_coin():
        global symbol
        ## append to symbol
        new = new_coin.get()
        new = new.upper()
        new_coin.delete(0, END)
        if new in valid_symbols and new not in symbol:
            symbol.append(new)
            print("Coins:", symbol)
        else:
            print(f"Invalid symbol/ duplicate symbol, valid symbol examples: {valid_symbols[:10]}")
            print("Coins:", symbol)

    def remove_last_coin():
        global symbol
        try:
            symbol.pop(-1)
            print("Coins:", symbol)
        except:
            print("No Coin in list to remove")

    def reset_coins():
        global symbol
        symbol = []
        print("Coins:", symbol)


    root = tk.Tk()
    root.title("Binance Futures Bot (gui v1)                                                    Developed by Conor White")
    photo = tk.PhotoImage(file="./icon.png")
    root.iconphoto(False, photo)
    root.maxsize(800, 700)
    root.minsize(800, 700)
    frame = Frame(root)
    frame.pack()
    frame.config(height=700, width=800, bg="light blue")

    Live_Bot = tk.Button(root, text="Live Trading", fg='white', bg='#457E81', activebackground="light blue", cursor="trek", command=live_mode)
    Live_Bot.place(relwidth=(1/4), relheight=(1/20), relx=0, rely=.95)
    Backtester = tk.Button(root, text="Backtester", fg='black', bg="light blue", activebackground="light blue", cursor="trek", command=backtest_mode)
    Backtester.place(relwidth=(1/4), relheight=(1/20), relx=(1/4), rely=.95)
    host = tk.Button(root, text="Web App", fg='white', bg="#457E81", activebackground="light blue", cursor="trek", command=host_mode)
    host.place(relwidth=(1/4), relheight=(1/20), relx=(2/4), rely=.95)
    host = tk.Button(root, text="Suggestions", fg='white', bg="#457E81", activebackground="light blue", cursor="trek", command=go_to_trello)
    host.place(relwidth=(1 / 4), relheight=(1 / 20), relx=(3 / 4), rely=.95)
    donate = tk.Button(root, text="Support This Project :)", fg='white', bg="#457E81", activebackground="light blue", command=go_to_github, cursor="trek")
    donate.place(relheight=.05, relwidth=1)


    backtest_mode()  ##start in Backtest Mode

    label3 = tk.Label(root, text="Candle Length:", bg="light blue")
    label3.place(relx=.01, rely=.2)
    options_candles = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]
    candle_length = StringVar()
    candle_length.set("1m")
    options_candles_dropdown = tk.OptionMenu(root, candle_length, *options_candles)
    options_candles_dropdown.place(relx=.16, rely=.2, relheight=.03)

    label4 = tk.Label(root, text="Strategy:", bg="light blue")
    label4.place(relx=.55, rely=.1)
    strategy_options = ["StochRSIMACD", "tripleEMAStochasticRSIATR", "tripleEMA", "breakout", "stochBB", "goldenCross",
                        "candle_wick", "fibMACD", "EMA_cross", "heikin_ashi_ema2", "heikin_ashi_ema", "ema_crossover"]
    strategy = StringVar()
    strategy.set("StochRSIMACD")
    strategy_options_dropdown = tk.OptionMenu(root, strategy, *strategy_options)
    strategy_options_dropdown.place(relx=.62, rely=.1, relheight=.03)

    label13 = tk.Label(root, text="SL:", bg="light blue")
    label13.place(relx=.63, rely=.2)
    SL = tk.Entry(root)
    SL.place(relx=.66, rely=.2, relwidth=.03)
    SL.insert(0, "1")
    TP_SL = StringVar()
    TP_SL_options = ['%', 'x (ATR)', 'x (Swing High/Low) level 1', 'x (Swing Close) level 1',
                      'x (Swing High/Low) level 2', 'x (Swing Close) level 2', 'x (Swing High/Low) level 3',
                      'x (Swing Close) level 3']
    TP_SL.set("%")
    TP_SL_choice_dropdown = tk.OptionMenu(root, TP_SL, *TP_SL_options)
    TP_SL_choice_dropdown.place(relx=.7, rely=.225, relheight=.03)

    label14 = tk.Label(root, text="TP:", bg="light blue")
    label14.place(relx=.63, rely=.25)
    TP = tk.Entry(root)
    TP.place(relx=.66, rely=.25, relwidth=.03)
    TP.insert(0, "1.5")

    label8 = tk.Label(root, text="Max Number of Trades:", bg="light blue")
    label8.place(relx=.55, rely=.15)
    number_of_trades = tk.Entry(root)
    number_of_trades.place(relx=.72, rely=.15, relwidth=.075)
    number_of_trades.insert(0, "6")

    use_trail_stop = BooleanVar()
    use_trail_stop_checkbox = Checkbutton(root,
                                          text="Use Trailing Stop",
                                          variable=use_trail_stop, bg="light blue", activebackground="light blue")
    use_trail_stop_checkbox.place(relx=.01, rely=.25)

    label9 = tk.Label(root, text="Trailing Stop Callback rate (%)",
                      bg="light blue")
    label9.place(relx=.2, rely=.253)
    trail_stop = tk.Entry(root)
    trail_stop.place(relx=.42, rely=.253, relwidth=.075)
    trail_stop.insert(0, "0.0")

    trade_all_coins = BooleanVar()
    coin_checkbox = Checkbutton(root, text="Trade All Coins: (If off you must input coins below)",
                                variable=trade_all_coins, bg="light blue", activebackground="light blue")
    coin_checkbox.place(relx=.01, rely=.37)

    label11 = tk.Label(root, text="Input Coins Here:", bg="light blue")
    label11.place(relx=.01, rely=.42)
    new_coin = tk.Entry(root)
    new_coin.place(relx=.16, rely=.42, relwidth=.075)
    add_coin = tk.Button(root, text="Add Coin", fg='white', bg="#457E81", activebackground="light blue",
                         cursor="trek", command=add_new_coin)
    add_coin.place(relx=.16, rely=.46, relwidth=.075, relheight=.03)
    remove_last = tk.Button(root, text="Remove last", fg="white", bg="#E34234", activebackground="light blue",
                            cursor="trek", command=remove_last_coin)
    remove_last.place(relx=.24, rely=.42, relwidth=.09, relheight=.03)
    clear_all = tk.Button(root, text="Clear Coins", fg="white", bg="#E34234", activebackground="light blue",
                          cursor="trek", command=reset_coins)
    clear_all.place(relx=.24, rely=.46, relwidth=.09, relheight=.03)

    # print(candle_length.get()) ## get the value later on to pass to the backtester
    root.mainloop()
