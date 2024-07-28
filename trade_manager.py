import time
from threading import Thread

from binance import ThreadedWebsocketManager
from binance.client import Client
from binance.enums import SIDE_SELL, SIDE_BUY, FUTURE_ORDER_TYPE_MARKET, FUTURE_ORDER_TYPE_LIMIT, TIME_IN_FORCE_GTC, \
    FUTURE_ORDER_TYPE_STOP_MARKET, FUTURE_ORDER_TYPE_TAKE_PROFIT
from binance.helpers import get_loop
from tabulate import tabulate

import example_strategies
from trading_config import *
from helper import Trade
from logger import *


def calculate_custom_tp_sl(options):
    '''
    Function for custom TP SL values that need trade information before calculating, may be needed depending on your TP SL Function
    Otherwise you can go the usual route and configure a TP SL function in Bot_Class.Bot.update_TP_SL() & TradingStrats.SetSLTP()
    '''
    stop_loss_val = -99
    take_profit_val = -99
    match tp_sl_choice:
        case 'USDT':
            stop_loss_val, take_profit_val = example_strategies.usdt_sl_tp(options)

    return stop_loss_val, take_profit_val


class TradeManager:
    def __init__(self, client: Client, new_trades_q, print_trades_q, user_socket_q):
        self.client = client
        self.active_trades: [Trade] = []
        self.use_trailing_stop = use_trailing_stop
        self.trailing_stop_callback = trailing_stop_callback
        self.use_market_orders = use_market_orders
        self.new_trades_q = new_trades_q
        self.print_trades_q = print_trades_q
        self.user_socket_queue = user_socket_q
        self.total_profit = 0
        self.number_of_wins = 0
        self.number_of_losses = 0

        # self.twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
        # self.twm.start()
        # self.user_socket = self.twm.start_futures_user_socket(callback=self.monitor_trades)
        # event_loop = get_loop()
        # event_loop.create_task(self.check_threshold_loop())
        # event_loop.create_task(self.log_trades_loop())
        # event_loop.create_task(self.monitor_orders_by_polling_api())
        # event_loop.create_task(self.monitor_trades())

        check_threshold_loop = Thread(target=self.check_threshold_loop)
        check_threshold_loop.start()

        log_trades_loop = Thread(target=self.log_trades_loop)
        log_trades_loop.start()

        monitor_orders_by_polling_api = Thread(target=self.monitor_orders_by_polling_api)
        monitor_orders_by_polling_api.start()

        monitor_trades = Thread(target=self.monitor_trades)
        monitor_trades.start()

    def monitor_orders_by_polling_api(self):
        '''
        Loop that runs constantly to catch trades that opened when packet loss occurs
        to ensure that SL & TPs are placed on all positions
        '''
        while True:
            time.sleep(15)
            open_positions = self.get_all_open_positions()
            if open_positions is not None:
                continue
            try:
                for trade in self.active_trades:
                    if trade.symbol in open_positions and trade.trade_status == 0:
                        i = self.active_trades.index(trade)
                        trade.trade_status = self.place_tp_sl(trade.symbol, trade.trade_direction, trade.coin_precision, trade.tick_size, trade.entry_price, i)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.warning(f'monitor_orders_by_polling_api() - error occurred, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def new_trades_loop(self):
        ''' Loop that constantly runs and opens new trades as they come in '''
        while True:
            self.check_for_new_orders()

    @log.catch_errors()
    def check_for_new_orders(self):
        [symbol, order_precision, coin_precision, tick_size, trade_direction, index, stop_loss_val, take_profit_val] = self.new_trades_q.get()
        open_trades = self.get_all_open_or_pending_trades()
        if open_trades is not None and symbol not in open_trades and len(self.active_trades) < max_number_of_positions and self.check_margin_sufficient() is True:
            order_id, order_qty, entry_price, trade_status = self.open_trade(symbol, trade_direction, order_precision, tick_size)
            if tp_sl_choice in custom_tp_sl_functions and trade_status != -1:
                options = {'position_size': order_qty}  # If you have a need to add additional inputs to calculate_custom_tp_sl() you can do so by adding to this dict
                stop_loss_val, take_profit_val = calculate_custom_tp_sl(options)
            if trade_status is not None:
                self.active_trades.append(Trade(index, entry_price, order_qty, take_profit_val, stop_loss_val, trade_direction, order_id, symbol, coin_precision, tick_size))
            if trade_status == 1:
                self.active_trades[-1].trade_status = self.place_tp_sl(symbol, trade_direction, coin_precision, tick_size, entry_price, -1)
            elif trade_status == 0:
                log.info(f'new_trades_loop() - Order placed on {symbol}, Entry price: {entry_price}, order quantity: {order_qty}, Side: {"Long" if trade_direction else "Short"}')

    def monitor_trades(self):
        '''
        Callback for user socket that places TP and SL and marks completed trades for removal
        Any logic to update trades based on hitting TPs should be performed here example: moving the LS after a TP is hit
        '''
        while True:
            try:
                msg = self.user_socket_queue.get()
                trades_to_update = []
                # for i in range(len(self.active_trades)):
                for trade in self.active_trades:
                    if msg['e'] == 'ORDER_TRADE_UPDATE' and msg['o']['s'] == trade.symbol and msg['o']['X'] == 'FILLED':
                        i = self.active_trades.index(trade)
                        if float(msg['o']['rp']) > 0 and msg['o']['i'] == trade.tp_id:
                            self.total_profit += float(msg['o']['rp'])
                            self.number_of_wins += 1
                            trades_to_update.append([i, 4])
                        elif float(msg['o']['rp']) < 0 and msg['o']['i'] == trade.sl_id:
                            self.total_profit += float(msg['o']['rp'])
                            self.number_of_losses += 1
                            trades_to_update.append([i, 5])
                        elif msg['o']['i'] == trade.order_id:
                            status = self.place_tp_sl(trade.symbol, trade.trade_direction, trade.coin_precision, trade.tick_size, trade.entry_price, i)
                            trades_to_update.append([i, status])
                    elif msg['e'] == 'ACCOUNT_UPDATE':
                        i = self.active_trades.index(trade)
                        for position in msg['a']['P']:
                            if position['s'] == trade.symbol and position['pa'] == '0':
                                trades_to_update.append([i, 6])
                for [index, status] in trades_to_update:
                    self.active_trades[index].trade_status = status
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.warning(f'monitor_trades() - error occurred, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def place_tp_sl(self, symbol, trade_direction, coin_precision, tick_size, entry_price, index):
        ''' Opens TP and SL positions '''
        try:
            # Cancel any open orders to get around an issue with partially filled orders
            self.client.futures_coin_cancel_all_open_orders(symbol=symbol)
        except:
            pass
        self.active_trades[index].position_size = abs([float(position['positionAmt']) for position in self.client.futures_position_information() if position['symbol'] == symbol][0])
        self.active_trades[index].sl_id = self.place_sl(symbol, self.active_trades[index].sl_val, trade_direction, coin_precision, tick_size, self.active_trades[index].position_size)
        self.active_trades[index].tp_id = self.place_tp(symbol, [self.active_trades[index].tp_val, self.active_trades[index].position_size], trade_direction, coin_precision, tick_size)
        if self.active_trades[index].sl_id is not None and self.active_trades[index].tp_id is not None:
            log.info(f'new_trades_loop() - Position opened on {symbol}, orderId: {self.active_trades[-1].order_id}, Entry price: {entry_price},'
                     f' order quantity: {self.active_trades[index].position_size}, Side: {"Long" if trade_direction else "Short"}\n'
                     f' Take Profit & Stop loss have been placed')
            self.print_trades_q.put(True)
            return 1
        else:
            return 3  # Signals to close the trade as it doesn't have either a Take Profit or a Stop Loss

    @log.catch_errors()
    def get_all_open_or_pending_trades(self):
        ''' Gets all opened trades, User opened positions + Bot opened trades + Pending Bot trades '''
        open_trades_symbols = [position['symbol'] for position in self.client.futures_position_information() if float(position['notional']) != 0.0]  # All open Trades
        active_trade_symbols = [trade.symbol for trade in self.active_trades]
        return open_trades_symbols + active_trade_symbols

    @log.catch_errors()
    def get_all_open_positions(self):
        ''' Gets all open positions from binance '''
        return [position['symbol'] for position in self.client.futures_position_information() if float(position['notional']) != 0.0] ## TODO convert this to a hashmap perhaps {symbol: position_size,...}

    @log.catch_errors()
    def check_margin_sufficient(self):
        ''' Checks if we have sufficient margin remaining to open a new trade '''
        account_info = self.client.futures_account()
        return float(account_info['totalMarginBalance']) > (float(account_info['totalWalletBalance']) * (1 - order_size / 100)) / leverage

    def check_threshold_loop(self):
        ''' Checks if any trades have gone past our specified threshold in live_trading_config.py '''
        while True:
            time.sleep(15)
            self.check_trading_threshold()
            self.cancel_and_remove_trades()

    @log.catch_errors()
    def check_trading_threshold(self):
        # Check trading threshold for each trade
        for trade in self.active_trades:
            if trade.trade_status == 0:
                current_price = float(self.client.futures_symbol_ticker(symbol=trade.symbol)['price'])
                if trade.trade_direction == 1 and ((current_price - trade.entry_price) / trade.entry_price) > trading_threshold / 100:
                    trade.current_price = current_price
                    trade.trade_status = 2
                elif trade.trade_direction == 0 and ((trade.entry_price - current_price) / trade.entry_price) > trading_threshold / 100:
                    trade.current_price = current_price
                    trade.trade_status = 2

    def cancel_and_remove_trades(self):
        ''' Function that removes finished trades from the active_trades list '''
        i = 0
        open_trades = self.get_all_open_positions()
        while i < len(self.active_trades):
            if self.active_trades[i].trade_status == 2 and open_trades is not None:
                try:
                    pop_trade = self.check_position_and_cancel_orders(self.active_trades[i], open_trades)
                    if pop_trade:
                        log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as price surpassed the trading threshold set in live_trading_config.py\n '
                                 f'Current Price was: {self.active_trades[i].current_price}, Attempted entry price was: {self.active_trades[i].entry_price}, % moved: {abs(100*(self.active_trades[i].entry_price-self.active_trades[i].current_price)/self.active_trades[i].entry_price)}')
                        self.active_trades.pop(i)
                    else:
                        self.active_trades[i].trade_status = 0
                        i += 1
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred cancelling a trade on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 3:
                try:
                    self.close_position(self.active_trades[i].symbol, self.active_trades[i].trade_direction, self.active_trades[i].position_size)
                    if self.active_trades[i].sl_id == -1:
                        log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as there was an issue placing the Stop loss')
                    else:
                        log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as there was an issue placing the Take Profit')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred cancelling a trade on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 4:
                try:
                    self.client.futures_cancel_all_open_orders(symbol=self.active_trades[i].symbol)
                    log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as Take Profit was hit')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred closing open orders on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 5:
                try:
                    self.client.futures_cancel_all_open_orders(symbol=self.active_trades[i].symbol)
                    log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as Stop loss was hit')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred closing open orders on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 6:
                try:
                    self.client.futures_cancel_all_open_orders(symbol=self.active_trades[i].symbol)
                    log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as trade was closed, possibly by the user')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred cancelling a trade on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            else:
                i += 1

    @log.catch_errors()
    def open_trade(self, symbol, trade_direction, order_precision, tick_size):
        ''' Function to open a new trade '''
        order_id = ''
        order_book = self.client.futures_order_book(symbol=symbol)

        bids = order_book['bids']
        asks = order_book['asks']
        entry_price = 0
        if trade_direction == 1:
            entry_price = float(bids[0][0])
        elif trade_direction == 0:
            entry_price = float(asks[0][0])
        account_balance = self.get_account_balance()
        order_notional = leverage * account_balance * (order_size/100)
        order_qty = order_notional / entry_price
        market_entry_price = 0
        if order_precision == 0:
            order_qty = round(order_qty)
        else:
            order_qty = round(order_qty, order_precision)
        if self.use_market_orders:
            if trade_direction == 0:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_MARKET,
                    quantity=order_qty)
                order_id = order['orderId']
            if trade_direction == 1:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_MARKET,
                    quantity=order_qty)
                order_id = order['orderId']
            market_entry_price = float(self.client.futures_position_information(symbol=symbol)[0]['entryPrice'])
            return order_id, order_qty, market_entry_price, 1
        else:
            if trade_direction == 0:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_LIMIT,
                    price=entry_price,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=order_qty)
                order_id = order['orderId']
            if trade_direction == 1:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_LIMIT,
                    price=entry_price,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=order_qty)
                order_id = order['orderId']
            return order_id, order_qty, entry_price, 0

    @log.catch_errors()
    def get_account_balance(self):
        ''' Function that returns the USDT balance of the account '''
        account_balance_info = self.client.futures_account_balance()
        for x in account_balance_info:
            if x['asset'] == 'USDT':
                return float(x['balance'])

    @log.catch_errors()
    def place_tp(self, symbol: str, tp: [float, float], trade_direction: int, coin_precision: int, tick_size: float):
        ''' Function that places a new TP order '''
        tp_id = ''
        tp_val = 0
        order = ''
        order_side = ''
        if coin_precision == 0:
            tp_val = round(tp[0])
        else:
            tp_val = round(round(tp[0] / tick_size) * tick_size, coin_precision)
        if trade_direction == 1:
            order_side = SIDE_SELL
        elif trade_direction == 0:
            order_side = SIDE_BUY
        if not self.use_trailing_stop:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type=FUTURE_ORDER_TYPE_TAKE_PROFIT,
                price=tp_val,
                stopPrice=tp_val,
                timeInForce=TIME_IN_FORCE_GTC,
                reduceOnly='true',
                quantity=tp[1])
            tp_id = order['orderId']
        else:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='TRAILING_STOP_MARKET',
                ActivationPrice=tp_val,
                callbackRate=self.trailing_stop_callback,
                quantity=tp[1])
            tp_id = order['orderId']

        return tp_id

    @log.catch_errors()
    def place_sl(self, symbol: str, sl: float, trade_direction: int, coin_precision: int, tick_size: float, quantity: float):
        ''' Function that places a new SL order '''
        if coin_precision == 0:
            sl = round(sl)
        else:
            sl = round(round(sl / tick_size) * tick_size, coin_precision)
        order_side = ''
        if trade_direction == 1:
            order_side = SIDE_SELL
        elif trade_direction == 0:
            order_side = SIDE_BUY

        order = self.client.futures_create_order(
            symbol=symbol,
            side=order_side,
            type=FUTURE_ORDER_TYPE_STOP_MARKET,
            reduceOnly='true',
            stopPrice=sl,
            quantity=quantity)
        order_id = order['orderId']

        return order_id

    @log.catch_errors()
    def close_position(self, symbol: str, trade_direction: int, total_position_size: float):
        '''
        Function for closing an open position, used when something goes wrong with a trade
        Can also be used to close a position based off a condition met in your strategy
        '''
        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)  ##cancel orders for this symbol
        except:
            log.warning(f'close_position() issue cancelling open orders on {symbol} potentially there were no open orders')
        if trade_direction == 0:
            self.client.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=total_position_size)
        if trade_direction == 1:
            self.client.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=total_position_size)

    def check_position_and_cancel_orders(self, trade: Trade, open_trades: [str]):
        ''' Function that checks we haven't entered a position before cancelling it '''
        if trade.symbol not in open_trades:
            self.client.futures_cancel_all_open_orders(symbol=trade.symbol)
            return True
        else:
            return False

    def log_trades_loop(self):
        ''' Loop that runs constantly and updates the logs for the user when something happens or when a new candle is received '''
        while True:
            self.log_trades()

    @log.catch_errors()
    def log_trades(self):
        self.print_trades_q.get()
        position_information = [position for position in self.client.futures_position_information() if
                                float(position['notional']) != 0.0]
        win_loss = 'Not available yet'
        if self.number_of_losses != 0:
            win_loss = round(self.number_of_wins / self.number_of_losses, 4)
        if len(position_information) != 0:
            info = {'Symbol': [], 'Position Size': [], 'Direction': [], 'Entry Price': [], 'Market Price': [],
                    'TP': [], 'SL': [], 'Distance to TP (%)': [], 'Distance to SL (%)': [], 'PNL': []}
            orders = self.client.futures_get_open_orders()
            open_orders = {f'{str(order["symbol"]) + "_TP"}': float(order['price']) for order in orders if
                           order['reduceOnly'] is True and order['type'] == 'TAKE_PROFIT'}
            open_orders_sl = {f'{str(order["symbol"]) + "_SL"}': float(order['stopPrice']) for order in orders if
                              order['origType'] == 'STOP_MARKET'}
            open_orders.update(open_orders_sl)
            for position in position_information:
                info['Symbol'].append(position['symbol'])
                info['Position Size'].append(position['positionAmt'])
                if float(position['notional']) > 0:
                    info['Direction'].append('LONG')
                else:
                    info['Direction'].append('SHORT')
                info['Entry Price'].append(position['entryPrice'])
                info['Market Price'].append(position['markPrice'])
                try:
                    info['TP'].append(open_orders[f'{position["symbol"]}_TP'])
                    info['Distance to TP (%)'].append(round(abs(((float(info['Market Price'][-1]) - float(
                        info['TP'][-1])) / float(info['Market Price'][-1])) * 100), 3))
                except:
                    info['TP'].append('Not opened yet')
                    info['Distance to TP (%)'].append('Not available yet')
                try:
                    info['SL'].append(open_orders[f'{position["symbol"]}_SL'])
                    info['Distance to SL (%)'].append(round(abs(((float(info['Market Price'][-1]) - float(
                        info['SL'][-1])) / float(info['Market Price'][-1])) * 100), 3))
                except:
                    info['SL'].append('Not opened yet')
                    info['Distance to SL (%)'].append('Not available yet')
                info['PNL'].append(float(position['unRealizedProfit']))
            log.info(
                f'Account Balance: ${round(self.get_account_balance(), 3)}, Total profit: ${round(self.total_profit, 3)}, PNL: ${round(sum(info["PNL"]), 3)}, Wins: {self.number_of_wins}, Losses: {self.number_of_losses}, Win/Loss ratio: {win_loss}, Open Positions: {len(info["Symbol"])}\n' + tabulate(
                    info, headers='keys', tablefmt='github'))
        else:
            log.info(
                f'Account Balance: ${round(self.get_account_balance(), 3)}, Total profit: ${round(self.total_profit, 3)}, Wins: {self.number_of_wins}, Losses: {self.number_of_losses}, Win/Loss ratio: {win_loss},  No Open Positions')


def start_new_trades_loop_multiprocess(client: Client, new_trades_q, print_trades_q, user_socket_q):
    trade_manager = TradeManager(client, new_trades_q, print_trades_q, user_socket_q)
    event_loop = get_loop()
    event_loop.create_task(trade_manager.new_trades_loop())
    # trade_manager.new_trades_loop()
