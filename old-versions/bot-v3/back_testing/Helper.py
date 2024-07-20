import numpy as np
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import *
from datetime import datetime
from pprint import PrettyPrinter
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from matplotlib import pyplot as plt

import Bot_Class
from Config_File import API_KEY, API_SECRET
from joblib import load, dump
import sys, os
from tabulate import tabulate
import multiprocessing

client = Client(api_key=API_KEY, api_secret=API_SECRET)  ##Binance keys needed to Trade on an account, can remove keys if backtesting
price_data_path = '.'

class Data_Handler:
    def __init__(self, symbol: str, index: int):
        self.symbol = symbol
        self.index = index
        self.new_data = False
        self.socket_failed = False
        self.next_candle = {'Date': 0, 'Close': 0.0, 'Open': 0.0, 'High': 0.0, 'Low': 0.0, 'Volume': 0.0}

    def handle_socket_message(self, msg):
        try:
            if msg != '':
                payload = msg['k']
                if payload['x']:
                    self.next_candle['Date'] = payload['T']
                    self.next_candle['Close'] = float(payload['c'])
                    self.next_candle['Volume'] = float(payload['q'])
                    self.next_candle['High'] = float(payload['h'])
                    self.next_candle['Low'] = float(payload['l'])
                    self.next_candle['Open'] = float(payload['o'])
                    # print(self.symbol_data)
                    self.new_data = True
        except Exception as e:
            print(f"Error in handling of websocket, Error: {e}")
            self.socket_failed = True

class Data_Handler_multi:
    def __init__(self, symbol):
        self.new_data = False
        self.price_data = {s: {'Date': None, 'Close': None,
                                    'Open': None, 'High': None, 'Low': None,
                                    'Volume': None, 'new_candle': False}
                           for s in symbol}


    def handle_socket_message(self, msg):
        try:
            if msg != '':
                payload = msg['k']
                if payload['x']:
                    if msg['ps'] not in self.price_data:
                        self.price_data[msg['ps']] = {'Date': payload['T'], 'Close': float(payload['c']),
                                                          'Open': float(payload['o']), 'High': float(payload['h']), 'Low': float(payload['l']),
                                                          'Volume': float(payload['q']), 'new_candle': True}
                    else:
                        self.price_data[msg['ps']]['Date'] = payload['T']
                        self.price_data[msg['ps']]['Close'] = float(payload['c'])
                        self.price_data[msg['ps']]['Open'] = float(payload['o'])
                        self.price_data[msg['ps']]['High'] = float(payload['h'])
                        self.price_data[msg['ps']]['Low'] = float(payload['l'])
                        self.price_data[msg['ps']]['Volume'] = float(payload['q'])
                        self.price_data[msg['ps']]['new_candle'] = True
                    #print(self.price_data)
        except Exception as e:
            print(f"Error in handling of websocket, Error: {e}")

class Trade_Stats:
    def __init__(self):
        self.total_number_of_trades = 0
        self.wins = 0
        self.losses = 0


class trade_info:
    def __init__(self, symbol, TP_price, SL_price, trade_direction):
        self.slippage = None
        self.symbol = symbol
        self.entry_price = None
        self.TP_price = TP_price
        self.SL_price = SL_price
        self.trade_direction = trade_direction
        self.trade_success = False
        self.trade_start_index = -99
        self.indicators = {}
        self.candles = {}
        self.start_time = ''

class Trade:
    def __init__(self, index: int, position_size: float, take_profit_val: float, stop_loss_val: float, trade_direction: int, order_id_temp: int, symbol: str):
        self.index = index
        self.symbol = symbol
        self.entry_price = -99
        self.position_size = position_size
        self.TP_val = take_profit_val
        self.SL_val = stop_loss_val
        self.trade_direction = trade_direction
        self.order_id = order_id_temp
        self.TP_id = ''
        self.SL_id = ''
        self.trade_status = 0  ## hasn't started
        self.trade_start = ''
        self.Highest_val = -999999
        self.Lowest_val = 999999
        self.trail_activated = False
        self.same_candle = True
        self.trade_info: trade_info = trade_info(symbol, take_profit_val, stop_loss_val, trade_direction)
    def print_vals(self):
        return self.symbol, self.entry_price, self.position_size, self.TP_val, self.SL_val, self.trade_direction, self.trade_status, self.Highest_val, self.Lowest_val


def log_error(e):
    with open('errors.txt', 'a') as O:
        O.write(e + "\n")


class Trade_Manager:
    def __init__(self, client: Client, use_trailing_stop: bool, trailing_stop_callback: float, use_market: bool):
        self.client = client
        self.use_trailing_stop = use_trailing_stop
        self.trailing_stop_callback = trailing_stop_callback
        self.use_market = use_market

    def open_trade_check_threshold(self, symbol: str, trade_direction: int, order_notional: float, CP: int, OP: int, tick_size: float, time: int, close: float, trading_threshold: float, orderID: int = '', old_entry_price: float = 0):
        order_book = self.client.futures_order_book(symbol=symbol)
        bids = order_book['bids']
        asks = order_book['asks']
        entry_price = 0
        if trade_direction == 1:
            entry_price = float(bids[0][0])
        elif trade_direction == 0:
            entry_price = float(asks[0][0])

        if self.use_market:
            order_qty = order_notional / close
            ## Conditions to cancel the opening of a trade
            if old_entry_price != 0 and (close - entry_price) / close > trading_threshold and trade_direction == 0:
                return '', order_qty, entry_price, -99
            elif old_entry_price != 0 and (entry_price - close) / close > trading_threshold and trade_direction == 1:
                return '', order_qty, entry_price, -99

            try:
                if OP == 0:
                    order_qty = round(order_qty)
                else:
                    order_qty = round(order_qty, OP)
                ##Could Make limit orders but for now the entry is a market
                if trade_direction == 0:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        type=FUTURE_ORDER_TYPE_MARKET,
                        quantity=order_qty)
                    orderID = order['orderId']
                if trade_direction == 1:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_BUY,
                        type=FUTURE_ORDER_TYPE_MARKET,
                        quantity=order_qty)
                    orderID = order['orderId']
            except BinanceAPIException as e:
                log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: Error in open_trade(), Error: {e}")
                print(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: Error in open_trade(), Error: ", e, order_qty, CP, OP)
            except Exception as e:
                print(e)
                log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: {e}")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)

            entry_price = float(self.client.futures_position_information(symbol=symbol)[0]['entryPrice'])
            return orderID, order_qty, entry_price, 1

        else:
            order_qty = 0
            try:
                if OP == 0:
                    order_qty = round(order_notional / entry_price)
                else:
                    order_qty = round(order_notional / entry_price, OP)
                if CP == 0:
                    entry_price = round(entry_price)
                else:
                    entry_price = round(round(entry_price / tick_size) * tick_size, CP)

                ## Conditions to cancel the opening of a trade
                if old_entry_price != 0 and (old_entry_price - entry_price) / old_entry_price > trading_threshold and trade_direction == 0:
                    return '', order_qty, entry_price, -99
                elif old_entry_price != 0 and (entry_price - old_entry_price) / old_entry_price > trading_threshold and trade_direction == 1:
                    return '', order_qty, entry_price, -99
                if order_qty == 0:
                    return '', order_qty, entry_price, -99

                if orderID == '':
                    if trade_direction == 0:
                        order = self.client.futures_create_order(
                            symbol=symbol,
                            side=SIDE_SELL,
                            type=FUTURE_ORDER_TYPE_LIMIT,
                            price=entry_price,
                            timeInForce=TIME_IN_FORCE_GTC,
                            quantity=order_qty)
                        orderID = order['orderId']
                    if trade_direction == 1:
                        order = self.client.futures_create_order(
                            symbol=symbol,
                            side=SIDE_BUY,
                            type=FUTURE_ORDER_TYPE_LIMIT,
                            price=entry_price,
                            timeInForce=TIME_IN_FORCE_GTC,
                            quantity=order_qty)
                        orderID = order['orderId']

                return orderID, order_qty, entry_price, 0
            except BinanceAPIException as e:
                print(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: Error in open_trade(), Error: ", e, order_qty, entry_price, CP, OP)
                return '', 0, 0, 0
            except Exception as e:
                print(e)
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)

    def place_TP(self, symbol: str, TP: [float, float], trade_direction: int, CP: int, tick_size: float, time: int):
        TP_ID = ''
        try:
            TP_val = 0
            order = ''
            order_side = ''
            if CP == 0:
                TP_val = round(TP[0])
            else:
                TP_val = round(round(TP[0] / tick_size) * tick_size, CP)
            if trade_direction == 1:
                order_side = SIDE_SELL
            elif trade_direction == 0:
                order_side = SIDE_BUY
            if not self.use_trailing_stop:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=order_side,
                    type=FUTURE_ORDER_TYPE_LIMIT,
                    price=TP_val,
                    timeInForce=TIME_IN_FORCE_GTC,
                    reduceOnly='true',
                    quantity=TP[1])
                TP_ID = order['orderId']
            else:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=order_side,
                    type='TRAILING_STOP_MARKET',
                    ActivationPrice=TP_val,
                    callbackRate=self.trailing_stop_callback,
                    quantity=TP[1])
                TP_ID = order['orderId']
        except BinanceAPIException as e:
            log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: Error in place_TP(), Error: {e}")
            print(f"\n{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: Error in place_TP(), Error: {e}")
            print(f"symbol: {symbol} TP: {TP}\n")
            return -1
        except Exception as e:
            print(e)
            log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: {e}")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
        return TP_ID

    def place_SL(self, symbol: str, SL: float, trade_direction: int, CP: int, tick_size: float, time: int):
        order_ID = ''
        try:
            if CP == 0:
                SL = round(SL)
            else:
                SL = round(round(SL / tick_size) * tick_size, CP)

            if trade_direction == 1:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                    stopPrice=SL,
                    closePosition='true')
                order_ID = order['orderId']
            else:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                    stopPrice=SL,
                    closePosition='true')
                order_ID = order['orderId']

        except BinanceAPIException as e:
            log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: Error in place_SL(), Error: {e}")
            print(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: Error in place_SL(), Error: {e}")
            print(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: symbol: {symbol} SL: {SL}\n")
            return -1
        except Exception as e:
            log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {e}")
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        return order_ID

    def close_position(self, symbol: str, trade_direction: int, total_position_size: float, time: int):
        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)  ##cancel orders for this symbol
            if trade_direction == 0:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_BUY,
                    type=FUTURE_ORDER_TYPE_MARKET,
                    quantity=total_position_size)
            if trade_direction == 1:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=FUTURE_ORDER_TYPE_MARKET,
                    quantity=total_position_size)

        except BinanceAPIException as e:
            log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: Error in close_position(), Error: {e}")
            print(f"{symbol}: Error in close_position(), Error: {e}")
        except Exception as e:
            print(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {e}")
            log_error(f"{str(datetime.utcfromtimestamp(round(time/1000)))}: {symbol}: {e}")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)


def get_TIME_INTERVAL(TIME_INTERVAL):
    ##Convert String to minutes
    if TIME_INTERVAL[1] == 'm':
        TIME_INTERVAL = int(TIME_INTERVAL[0])
    elif TIME_INTERVAL[1] == 'h':
        TIME_INTERVAL = int(TIME_INTERVAL[0]) * 60
    elif TIME_INTERVAL[1] == 'd':
        TIME_INTERVAL = int(TIME_INTERVAL[0]) * 1440
    elif TIME_INTERVAL[1] == 'w':
        TIME_INTERVAL = int(TIME_INTERVAL[0]) * 1440 * 7
    elif TIME_INTERVAL[1] == 'M':
        TIME_INTERVAL = int(TIME_INTERVAL[0]) * 1440 * 7 * 4
    elif TIME_INTERVAL[2] == 'm':
        TIME_INTERVAL = int(TIME_INTERVAL[0]) * 10 + int(TIME_INTERVAL[1])
    elif TIME_INTERVAL[2] == 'h':
        TIME_INTERVAL = int(TIME_INTERVAL[0]) * 10 * 60 + int(TIME_INTERVAL[1]) * 60
    return TIME_INTERVAL


def get_Klines(symbol, start_str, end_str, path):
    ## Manipulate dates to american format:
    start_date = f'{start_str[3:5]}-{start_str[0:2]}-{start_str[6:]}'
    end_date = f'{end_str[3:5]}-{end_str[0:2]}-{end_str[6:]}'
    print(f"Downloading CandleStick Data for {symbol}...")
    price_data = {'High_1m': [], 'Low_1m': [], 'Close_1m': [],
                  'Open_1m': [], 'Date_1m': [], 'Volume_1m': [],
                  'High_3m': [], 'Low_3m': [], 'Close_3m': [],
                  'Open_3m': [], 'Date_3m': [], 'Volume_3m': [],
                  'High_5m': [], 'Low_5m': [], 'Close_5m': [],
                  'Open_5m': [], 'Date_5m': [], 'Volume_5m': [],
                  'High_15m': [], 'Low_15m': [], 'Close_15m': [],
                  'Open_15m': [], 'Date_15m': [], 'Volume_15m': [],
                  'High_30m': [], 'Low_30m': [], 'Close_30m': [],
                  'Open_30m': [], 'Date_30m': [], 'Volume_30m': [],
                  'High_1h': [], 'Low_1h': [], 'Close_1h': [],
                  'Open_1h': [], 'Date_1h': [], 'Volume_1h': [],
                  'High_2h': [], 'Low_2h': [], 'Close_2h': [],
                  'Open_2h': [], 'Date_2h': [], 'Volume_2h': [],
                  'High_4h': [], 'Low_4h': [], 'Close_4h': [],
                  'Open_4h': [], 'Date_4h': [], 'Volume_4h': [],
                  'High_6h': [], 'Low_6h': [], 'Close_6h': [],
                  'Open_6h': [], 'Date_6h': [], 'Volume_6h': [],
                  'High_8h': [], 'Low_8h': [], 'Close_8h': [],
                  'Open_8h': [], 'Date_8h': [], 'Volume_8h': [],
                  'High_12h': [], 'Low_12h': [], 'Close_12h': [],
                  'Open_12h': [], 'Date_12h': [], 'Volume_12h': [],
                  'High_1d': [], 'Low_1d': [], 'Close_1d': [],
                  'Open_1d': [], 'Date_1d': [], 'Volume_1d': []}

    for kline in client.futures_historical_klines(symbol, '1m', start_str=start_date, end_str=end_date):
        #:return: list of OHLCV values (Open time, Open, High, Low, Close, Volume, Close time, Quote asset volume, Number of trades, Taker buy base asset volume, Taker buy quote asset volume, Ignore)
        candle_open = datetime.utcfromtimestamp(round(kline[0] / 1000))
        candle_close = datetime.utcfromtimestamp((round(kline[6] / 1000)))
        price_data['Open_1m'].append(float(kline[1]))
        price_data['High_1m'].append(float(kline[2]))
        price_data['Low_1m'].append(float(kline[3]))
        price_data['Close_1m'].append(float(kline[4]))
        price_data['Volume_1m'].append(round(float(kline[7])))
        price_data['Date_1m'].append(candle_open)

        for unit in [3, 5, 15, 30]:
            try:
                ## Construct the 3m, 5m, 15m, and 30m candles
                if int(str(candle_open)[-5:-3]) % unit == 0:
                    ##Candle open
                    price_data[f'Date_{unit}m'].append(candle_open)
                    price_data[f'Open_{unit}m'].append(price_data['Open_1m'][-1])
                    price_data[f'High_{unit}m'].append(price_data['High_1m'][-1])  ##initialize as highest
                    price_data[f'Low_{unit}m'].append(price_data['Low_1m'][-1])  ##initialize as lowest
                    price_data[f'Volume_{unit}m'].append(price_data['Volume_1m'][-1])  ##initialize
                if int(str(candle_close)[-5:-3]) % unit == 0:
                    ##Candle close time
                    price_data[f'Close_{unit}m'].append(price_data['Close_1m'][-1])
                    ##Check if higher high or lower low present:
                    if price_data['High_1m'][-1] > price_data[f'High_{unit}m'][-1]:
                        price_data[f'High_{unit}m'][-1] = price_data['High_1m'][-1]  ##update as highest
                    if price_data['Low_1m'][-1] < price_data[f'Low_{unit}m'][-1]:
                        price_data[f'Low_{unit}m'][-1] = price_data['Low_1m'][-1]  ##update as lowest
                    price_data[f'Volume_{unit}m'][-1] += price_data['Volume_1m'][-1]  ## add on volume
                    price_data[f'Volume_{unit}m'][-1] = round(price_data[f'Volume_{unit}m'][-1])
                elif not int(str(candle_open)[-5:-3]) % unit == 0 and not int(str(candle_close)[-5:-3]) % unit == 0:
                    ## Check for higher and lower candle inbetween:
                    if price_data['High_1m'][-1] > price_data[f'High_{unit}m'][-1]:
                        price_data[f'High_{unit}m'][-1] = price_data['High_1m'][-1]  ##update as highest
                    if price_data['Low_1m'][-1] < price_data[f'Low_{unit}m'][-1]:
                        price_data[f'Low_{unit}m'][-1] = price_data['Low_1m'][-1]  ##update as lowest
                    price_data[f'Volume_{unit}m'][-1] += price_data['Volume_1m'][-1]  ## add on volume

            except Exception as e:
                print(f"Error in {unit}m candles should be fine just for debugging purposes, {e}")
        for unit in [1, 2, 4, 6, 8, 12]:
            try:
                ## Construct the 1h, 2h, 4h, 6h, 8h and 12h candles
                if int(str(candle_open)[-8:-6]) % unit == 0 and int(str(candle_open)[-5:-3]) == 0:
                    ##Candle open
                    price_data[f'Date_{unit}h'].append(candle_open)
                    price_data[f'Open_{unit}h'].append(price_data['Open_1m'][-1])
                    price_data[f'High_{unit}h'].append(price_data['High_1m'][-1])  ##initialize as highest
                    price_data[f'Low_{unit}h'].append(price_data['Low_1m'][-1])  ##initialize as lowest
                    price_data[f'Volume_{unit}h'].append(price_data['Volume_1m'][-1])  ##initialize
                if int(str(candle_close)[-8:-6]) % unit == 0 and int(str(candle_close)[-5:-3]) == 0:
                    ##Candle close time
                    price_data[f'Close_{unit}h'].append(price_data['Close_1m'][-1])
                    ##Check if higher high or lower low present:
                    if price_data['High_1m'][-1] > price_data[f'High_{unit}h'][-1]:
                        price_data[f'High_{unit}h'][-1] = price_data['High_1m'][-1]  ##update as highest
                    if price_data['Low_1m'][-1] < price_data[f'Low_{unit}h'][-1]:
                        price_data[f'Low_{unit}h'][-1] = price_data['Low_1m'][-1]  ##update as lowest
                    price_data[f'Volume_{unit}h'][-1] += price_data['Volume_1m'][-1]  ## add on volume
                    price_data[f'Volume_{unit}h'][-1] = round(price_data[f'Volume_{unit}h'][-1])
                elif not (int(str(candle_open)[-8:-6]) % unit == 0 and int(str(candle_open)[-5:-3]) == 0) and \
                        not (int(str(candle_close)[-8:-6]) % unit == 0 and int(str(candle_close)[-5:-3]) == 0):
                    ## Check for higher and lower candle inbetween:
                    if price_data['High_1m'][-1] > price_data[f'High_{unit}h'][-1]:
                        price_data[f'High_{unit}h'][-1] = price_data['High_1m'][-1]  ##update as highest
                    if price_data['Low_1m'][-1] < price_data[f'Low_{unit}h'][-1]:
                        price_data[f'Low_{unit}h'][-1] = price_data['Low_1m'][-1]  ##update as lowest
                    price_data[f'Volume_{unit}h'][-1] += price_data['Volume_1m'][-1]  ## add on volume
            except Exception as e:
                print(f"Error in {unit}h candles should be fine just for debugging purposes, {e}")
    ## Clean up the extra candles
    for unit in [3, 5, 15, 30]:
        price_data[f'Open_{unit}m'].pop(-1)  ## remove the last candle
        price_data[f'High_{unit}m'].pop(-1)  ## remove the last candle
        price_data[f'Low_{unit}m'].pop(-1)  ## remove the last candle
        price_data[f'Date_{unit}m'].pop(-1)  ## remove the last candle
        price_data[f'Volume_{unit}m'].pop(-1)  ## remove the last candle
        if len(price_data[f'Date_{unit}m']) < len(price_data[f'Close_{unit}m']):
            price_data[f'Close_{unit}m'].pop(-1)  ## remove the last candle

    for unit in [1, 2, 4, 6, 8, 12]:
        price_data[f'Open_{unit}h'].pop(-1)  ## remove the last candle
        price_data[f'High_{unit}h'].pop(-1)  ## remove the last candle
        price_data[f'Low_{unit}h'].pop(-1)  ## remove the last candle
        price_data[f'Date_{unit}h'].pop(-1)  ## remove the last candle
        price_data[f'Volume_{unit}h'].pop(-1)  ## remove the last candle
        if len(price_data[f'Date_{unit}h']) < len(price_data[f'Close_{unit}h']):
            price_data[f'Close_{unit}h'].pop(-1)  ## remove the last candle


    try:
        for kline in client.futures_historical_klines(symbol, '1d', start_str=start_date, end_str=end_date):
            price_data['Date_1d'].append(datetime.utcfromtimestamp((round(kline[0] / 1000))))
            price_data['Open_1d'].append(float(kline[1]))
            price_data['High_1d'].append(float(kline[2]))
            price_data['Low_1d'].append(float(kline[3]))
            price_data['Close_1d'].append(float(kline[4]))
    except Exception as e:
        print("Error downloading daily candles:",e)

    try:
        print("Saving Price data")
        dump(price_data, path)  ## address of where you will keep the data,
    except:
        print("Failed to save data")

    return price_data


def get_historical(symbol: str, start_string: str, Interval: str):
    Open = []
    High = []
    Low = []
    Close = []
    Volume = []
    Date = []
    try:
        for kline in client.futures_historical_klines(symbol, Interval, start_str=start_string):
            #Date.append(str(datetime.utcfromtimestamp(round(kline[6] / 1000))))
            Date.append(kline[6])
            Open.append(float(kline[1]))
            Close.append(float(kline[4]))
            High.append(float(kline[2]))
            Low.append(float(kline[3]))
            Volume.append(float(kline[7]))
    except BinanceAPIException as e:
        print(e)
    return Date, Open, Close, High, Low, Volume


def align_Datasets(Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume):
    print("Aligning Data Sets... This may take a few minutes")
    start_date = [Date[0][0], 0]  ##get 1st date of first coin
    end_date = [Date[0][-1], 0]  ##get last date of first coin
    for i in range(len(Date)):
        if Date[i][0] < start_date[0]:  ##Check if any other coin has an earlier date to find the earliest date
            start_date = [Date[i][0], i]  ##Date,index of start date
        if Date[i][-1] > end_date[0]:  ##Check if any other coin has a later date to find the latest date
            end_date = [Date[i][-1], i]  ##Date, index of end date
    for i in range(len(Date_1min)):
        len_infront = 0  ##count how many dates we move along until we find the date at the current index's start, used to repeat the data until size is the same
        len_behind = 0  ##count how many dates we move along until we find the date at the current index's end, used to repeat the data until size is the same
        for j in range(len(Date_1min[start_date[1]])):
            if Date_1min[start_date[1]][j] != Date_1min[i][0]:
                len_infront += 1
            else:
                break
        for j in range(len(Date_1min[end_date[1]]) - 1, -1, -1):
            if Date_1min[end_date[1]][j] != Date_1min[i][-1]:
                len_behind += 1
            else:
                break
        for j in range(len_infront):
            Date_1min[i].insert(0, "Data Set hasn't started yet")
            High_1min[i].insert(0, High_1min[i][0])
            Low_1min[i].insert(0, Low_1min[i][0])
            Close_1min[i].insert(0, Close_1min[i][0])
            Open_1min[i].insert(0, Open_1min[i][0])
        for j in range(len_behind):
            Date_1min[i].append("Data Set Ended")
            High_1min[i].append(High_1min[i][-1])
            Low_1min[i].append(Low_1min[i][-1])
            Close_1min[i].append(Close_1min[i][-1])
            Open_1min[i].append(Open_1min[i][-1])
    for i in range(len(Date)):
        len_infront = 0
        len_behind = 0
        for j in range(len(Date[start_date[1]])):
            if Date[start_date[1]][j] != Date[i][0]:
                len_infront += 1
            else:
                break
        for j in range(len(Date[end_date[1]]) - 1, -1, -1):
            if Date[end_date[1]][j] != Date[i][-1]:
                len_behind += 1
            else:
                break
        for j in range(len_infront):
            Date[i].insert(0, "Data Set hasn't started yet")
            High[i].insert(0, High[i][0])
            Low[i].insert(0, Low[i][0])
            Close[i].insert(0, Close[i][0])
            Open[i].insert(0, Open[i][0])
            Volume[i].insert(0, Volume[i][0])
        for j in range(len_behind):
            Date[i].append("Data Set Ended")
            High[i].append(High[i][-1])
            Low[i].append(Low[i][-1])
            Close[i].append(Close[i][-1])
            Open[i].append(Open[i][-1])
            Volume[i].insert(0, Volume[i][-1])

    return Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume


def get_CAGR(start, end):
    return (int(end[0:2]) - int(start[0:2]) + 30 * (int(end[3:5]) - int(start[3:5])) + 365 * (
            int(end[6:]) - int(start[6:]))) / 365


def align_Datasets_easy(Date, Close, Open):
    start_date = [Date[0][0], 0]
    end_date = [Date[0][-1], 0]
    for i in range(len(Date)):
        if Date[i][0] < start_date[0]:
            start_date = [Date[i][0], i]  ##Date,index of start date
        if Date[i][-1] > end_date[0]:
            end_date = [Date[i][-1], i]  ##Date, index of end date
    for i in range(len(Date)):
        len_infront = 0
        len_behind = 0
        for j in range(len(Date[start_date[1]])):
            if Date[start_date[1]][j] != Date[i][0]:
                len_infront += 1
            else:
                break
        for j in range(len(Date[end_date[1]]) - 1, -1, -1):
            if Date[end_date[1]][j] != Date[i][-1]:
                len_behind += 1
            else:
                break
        for j in range(len_infront):
            Date[i].insert(0, "Data Set hasn't started yet")
            Close[i].insert(0, Close[i][0])
            Open[i].insert(0, Open[i][0])
        for j in range(len_behind):
            Date[i].append("Data Set Ended")
            Close[i].append(Close[i][-1])
            Open[i].append(Open[i][-1])

    return Date, Close, Open


def get_heikin_ashi(Open, Close, High, Low):
    Open_heikin = []
    Close_heikin = []
    High_heikin = []
    Low_heikin = []
    for i in range(len(Close)):
        Open_heikin.append([])
        Close_heikin.append([])
        High_heikin.append([])
        Low_heikin.append([])
        for j in range(len(Close[i])):
            Close_heikin[i].append((Open[i][j] + Close[i][j] + Low[i][j] + High[i][j]) / 4)
            if j == 0:
                Open_heikin[i].append((Close_heikin[i][j] + Open[i][j]) / 2)
                High_heikin[i].append(High[i][j])
                Low_heikin[i].append(Low[i][j])
            else:
                Open_heikin[i].append((Open_heikin[i][j - 1] + Close_heikin[i][j - 2]) / 2)
                High_heikin[i].append(max(High[i][j], Open_heikin[i][j], Close_heikin[i][j]))
                Low_heikin[i].append(min(Low[i][j], Open_heikin[i][j], Close_heikin[i][j]))
    return Open_heikin, Close_heikin, High_heikin, Low_heikin


def get_aligned_candles(Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume,
                        symbol, TIME_INTERVAL, start, end, use_multiprocessing=False, index=0, return_dict=None):
    i = 0

    price_data_path = '.'
    if not os.path.exists(price_data_path + f'//price_data//'):
        os.makedirs(price_data_path + f'//price_data//')
    while i < len(symbol):
        print(f"Loading {symbol[i]}")
        path = f"{price_data_path}//price_data//{symbol[i]}_{start}_{end}.joblib"
        try:
            price_data = load(path)
            Date.append(price_data[f'Date_{TIME_INTERVAL}'])
            Open.append(price_data[f'Open_{TIME_INTERVAL}'])
            Close.append(price_data[f'Close_{TIME_INTERVAL}'])
            High.append(price_data[f'High_{TIME_INTERVAL}'])
            Low.append(price_data[f'Low_{TIME_INTERVAL}'])
            Volume.append(price_data[f'Volume_{TIME_INTERVAL}'])
            High_1min.append(price_data['High_1m'])
            Low_1min.append(price_data['Low_1m'])
            Close_1min.append(price_data['Close_1m'])
            Open_1min.append(price_data['Open_1m'])
            Date_1min.append(price_data['Date_1m'])
            i += 1
        except:
            try:
                print(f"Data doesnt exist in path: {path}, Downloading Data to specified path now...")
                price_data = get_Klines(symbol[i], start, end, path)
                Date.append(price_data[f'Date_{TIME_INTERVAL}'])
                Open.append(price_data[f'Open_{TIME_INTERVAL}'])
                Close.append(price_data[f'Close_{TIME_INTERVAL}'])
                High.append(price_data[f'High_{TIME_INTERVAL}'])
                Low.append(price_data[f'Low_{TIME_INTERVAL}'])
                Volume.append(price_data[f'Volume_{TIME_INTERVAL}'])
                High_1min.append(price_data['High_1m'])
                Low_1min.append(price_data['Low_1m'])
                Close_1min.append(price_data['Close_1m'])
                Open_1min.append(price_data['Open_1m'])
                Date_1min.append(price_data['Date_1m'])
                print("Download Successful, Loading Data now")
                i += 1
            except BinanceAPIException as e:
                if str(e) == 'APIError(code=-1121): Invalid symbol.':
                    print(f"Invalid Symbol: {symbol[i]}, removing from data set")
                    symbol.pop(i)
                else:
                    print(f"Wrong path specified in Helper.py,error: {e}")
                    symbol.pop(i)
                    print("Fix path issue or else turn off load_data")
                    print("Contact me if still stuck @ wconor539@gmail.com")

    i = 0
    while i < len(Close):
        if len(Close[i]) == 0:
            Date.pop(i)
            Open.pop(i)
            Close.pop(i)
            High.pop(i)
            Low.pop(i)
            Volume.pop(i)
            High_1min.pop(i)
            Low_1min.pop(i)
            Close_1min.pop(i)
            Open_1min.pop(i)
            Date_1min.pop(i)
            print(f"Not enough candleStick data for {symbol[i]} removing from dataset...")
            symbol.pop(i)
            i -= 1
        i += 1
    if not use_multiprocessing:
        Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume = \
            align_Datasets(Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume)
    if use_multiprocessing:
        return_dict[index] = [Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol]
        return
    return Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol


def multiprocess_get_candles(symbol, TIME_INTERVAL, start, end):
    Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume = [], [], [], [], [], [], [], [], [], [], []
    if len(symbol) > 2:
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        jobs = []
        for i in range(3):
            if i != 2:
                p = multiprocessing.Process(target=get_aligned_candles, args=(
                    [], [], [], [], [], [], [], [], [], [], [],
                    symbol[round(i * (len(symbol) / 3)):round((i + 1) * (len(symbol) / 3))],
                    TIME_INTERVAL, start, end, True, i, return_dict))
            else:
                p = multiprocessing.Process(target=get_aligned_candles, args=(
                    [], [], [], [], [], [], [], [], [], [], [],
                    symbol[round(i * (len(symbol) / 3)):],
                    TIME_INTERVAL, start, end, True, i, return_dict))
            jobs.append(p)
            p.start()

        for proc in jobs:
            proc.join()
        print("Joining Data From multiple Processes")
        python_list = [None, None, None]
        python_list[0] = list(return_dict[0])
        del return_dict[0]
        python_list[1] = list(return_dict[1])
        del return_dict[1]
        python_list[2] = list(return_dict[2])
        del return_dict[2]
        manager.shutdown()
        Date_1min = python_list[0][0] + python_list[1][0] + python_list[2][0]
        High_1min = python_list[0][1] + python_list[1][1] + python_list[2][1]
        Low_1min = python_list[0][2] + python_list[1][2] + python_list[2][2]
        Close_1min = python_list[0][3] + python_list[1][3] + python_list[2][3]
        Open_1min = python_list[0][4] + python_list[1][4] + python_list[2][4]
        Date = python_list[0][5] + python_list[1][5] + python_list[2][5]
        Open = python_list[0][6] + python_list[1][6] + python_list[2][6]
        Close = python_list[0][7] + python_list[1][7] + python_list[2][7]
        High = python_list[0][8] + python_list[1][8] + python_list[2][8]
        Low = python_list[0][9] + python_list[1][9] + python_list[2][9]
        Volume = python_list[0][10] + python_list[1][10] + python_list[2][10]
        symbol = python_list[0][11] + python_list[1][11] + python_list[2][11]
        Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume = \
            align_Datasets(Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume)
    else:
        Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol = \
            get_aligned_candles([], [], [], [], [], [], [], [], [], [], [], symbol, TIME_INTERVAL, start, end)

    return Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol


def check_TP(t: Trade, account_balance, High, Low, fee, use_trailing_stop, trailing_stop_callback, CP, printing_on=1):
    if not use_trailing_stop:
        if t.TP_val < High and t.trade_direction == 1:
            if printing_on:
                print(f"Take Profit hit on {t.symbol}")
            account_balance += ((t.TP_val - t.entry_price) * t.position_size - t.TP_val * fee * t.position_size)  ## fee + profit
            t.trade_status = 2

        elif t.TP_val > Low and t.trade_direction == 0:
            if printing_on:
                print(f"Take Profit hit on {t.symbol}")
            account_balance += ((t.entry_price - t.TP_val) * t.position_size - t.TP_val * fee * t.position_size)  ## fee + profit
            t.trade_status = 2
    else:
        if t.trail_activated and t.trade_direction == 0 and High > t.TP_val:
            if printing_on:
                print(f"Trailing Stop hit on {t.symbol}")
            account_balance += ((t.entry_price - t.TP_val) * t.position_size - t.TP_val * fee * t.position_size)  ## fee + profit
            t.trade_status = 2
        elif t.trail_activated and t.trade_direction == 1 and Low < t.TP_val:
            if printing_on:
                print(f"Trailing Stop hit on {t.symbol}")
            account_balance += ((t.TP_val - t.entry_price) * t.position_size - t.TP_val * fee * t.position_size)  ## fee + profit
            t.trade_status = 2
        elif not t.trail_activated and t.trade_direction == 0 and Low < t.TP_val:
            t.trail_activated = True
            if CP == 0:
                t.TP_val = round(Low * (1 + trailing_stop_callback))
            else:
                t.TP_val = round(Low * (1 + trailing_stop_callback), CP)
            if printing_on:
                print(f"Trailing Stop updated on {t.symbol} to {t.TP_val}")
        elif not t.trail_activated and t.trade_direction == 1 and High > t.TP_val:
            t.trail_activated = True
            if CP == 0:
                t.TP_val = round(High * (1 - trailing_stop_callback))
            else:
                t.TP_val = round(High * (1 - trailing_stop_callback), CP)
            if printing_on:
                print(f"Trailing Stop updated on {t.symbol} to {t.TP_val}")
        elif t.trail_activated and t.trade_direction == 0 and Low * (1 + trailing_stop_callback) < t.TP_val:
            if CP == 0:
                t.TP_val = round(Low * (1 + trailing_stop_callback))
            else:
                t.TP_val = round(Low * (1 + trailing_stop_callback), CP)
            if printing_on:
                print(f"Trailing Stop updated on {t.symbol} to {t.TP_val}")
        elif t.trail_activated and t.trade_direction == 1 and High * (1 - trailing_stop_callback) > t.TP_val:
            if CP == 0:
                t.TP_val = round(High * (1 - trailing_stop_callback))
            else:
                t.TP_val = round(High * (1 - trailing_stop_callback), CP)
            if printing_on:
                print(f"Trailing Stop updated on {t.symbol} to {t.TP_val}")

    return t, account_balance


def check_SL(t: Trade, account_balance, High, Low, fee, printing_on=1):
    if t.SL_val < High and t.trade_direction == 0:
        if printing_on:
            print(f"Stop Loss hit on {t.symbol}")
        account_balance -= ((t.SL_val - t.entry_price) * t.position_size + t.SL_val * fee * t.position_size)  ## fee + stop loss
        t.trade_status = 3

    elif t.SL_val > Low and t.trade_direction == 1:
        if printing_on:
            print(f"Stop Loss hit on {t.symbol}")
        account_balance -= ((t.entry_price - t.SL_val) * t.position_size + t.SL_val * fee * t.position_size)  ## fee + stop loss
        t.trade_status = 3

    return t, account_balance


def open_trade(symbol, Order_Notional, account_balance, Open, fee, OP, CP, Trade_Direction, slippage, printing_on=1):
    if Trade_Direction == 0:
        if CP == 0:
            entry_price = round(Open * (1 - slippage))
        else:
            entry_price = round(Open * (1 - slippage), CP)
    else:
        if CP == 0:
            entry_price = round(Open * (1 + slippage))
        else:
            entry_price = round(Open * (1 + slippage), CP)

    if OP == 0:
        order_qty = round(Order_Notional / entry_price)
    else:
        order_qty = round(Order_Notional / entry_price, OP)


    if order_qty > 0:
        account_balance -= Order_Notional * fee
        if printing_on:
            print(f"Trade Opened Successfully on {symbol}")
    return order_qty, entry_price, account_balance


def close_pos(t, account_balance, fee, Close):
    if t.trade_direction == 0:
        account_balance += ((t.entry_price - Close) * t.position_size + Close * fee * t.position_size)  ## fee + stop loss

    elif t.trade_direction == 1:
        account_balance += ((Close - t.entry_price) * t.position_size + Close * fee * t.position_size)  ## fee + stop loss

    return t, account_balance


def print_trades(active_trades: [Trade], trade_price, Date, account_balance, change_occurred, print_to_csv, csv_name, path, csv_path, time_delta):
    ###########################################################################################################
    #####################               PRINT TRADE DETAILS                          ##########################
    ###########################################################################################################

    info = {}
    symbol_info = []
    entry_price_info = []
    position_size_info = []
    TP_vals_info = []
    SL_val_info = []
    trade_direction_info = []
    trade_status_info = []
    trade_highest_info = []
    trade_lowest_info = []
    for k in range(len(active_trades)):
        symbol_info_temp, entry_price_info_temp, position_size_info_temp, TP_vals_info_temp, SL_val_info_temp, \
        trade_direction_info_temp, trade_status_info_temp, trade_highest_temp, trade_lowest_temp = \
            active_trades[k].print_vals()
        symbol_info.append(symbol_info_temp)
        entry_price_info.append(entry_price_info_temp)
        position_size_info.append(position_size_info_temp)
        TP_vals_info.append(TP_vals_info_temp)
        SL_val_info.append(SL_val_info_temp)

        if trade_direction_info_temp == 0:
            trade_direction_info.append('Short')
        elif trade_direction_info_temp == 1:
            trade_direction_info.append('Long')
        elif trade_direction_info_temp == -99:
            trade_direction_info.append('Closed')

        if trade_status_info_temp == 0:
            trade_status_info.append('New position Opened')
        elif trade_status_info_temp == 1:
            trade_status_info.append('In Progress')
        elif trade_status_info_temp == 2:
            trade_status_info.append('Take Profit Hit')
        elif trade_status_info_temp == 3:
            trade_status_info.append('Stop Loss Hit')
        elif trade_status_info_temp == 4:
            trade_status_info.append('Closed on Condition')

        if trade_highest_temp != -999999:
            trade_highest_info.append(trade_highest_temp)
        else:
            trade_highest_info.append('N/A')

        if trade_lowest_temp != 999999:
            trade_lowest_info.append(trade_lowest_temp)
        else:
            trade_lowest_info.append('N/A')

    trade_pnl = []
    for i in range(len(active_trades)):
        if active_trades[i].trade_direction == 0:
            trade_pnl.append((entry_price_info[i] - trade_price[i]) * (position_size_info[i]))
        elif active_trades[i].trade_direction == 1:
            trade_pnl.append((trade_price[i] - entry_price_info[i]) * (position_size_info[i]))
    info['Symbol'] = symbol_info
    info['trade direction'] = trade_direction_info
    info['entry price'] = entry_price_info
    info['current price'] = trade_price
    info['Size'] = position_size_info
    info['Next TP'] = TP_vals_info
    info['SL'] = SL_val_info
    info['PNL'] = trade_pnl
    info['trade status'] = trade_status_info
    info['Highest Candle'] = trade_highest_info
    info['Lowest Candle'] = trade_lowest_info

    if change_occurred and len(account_balance) == 1:
        print(f"\nTime: {Date + time_delta} , Account Balance: {account_balance[0]}")
        print(tabulate(info, headers='keys', tablefmt='fancy_grid'))
        print(f"Time: {Date + time_delta} , Account Balance: {account_balance[0]}")
        print("------------------------------------------------------------\n")
        if print_to_csv:
            with open(csv_path+csv_name, 'a') as O:
                for i in range(len(active_trades)):
                    O.write(
                        f'{Date + time_delta},{account_balance[0]},{symbol_info[i]},{entry_price_info[i]},{position_size_info[i]},'
                        f'{trade_price[i]},{TP_vals_info[i]},{SL_val_info[i]},{trade_direction_info[i]},{trade_highest_info[i]},{trade_lowest_info[i]},{trade_status_info[i]}\n')
        total_pnl = 0
        for x in trade_pnl:
            total_pnl += x

        if total_pnl + account_balance[0] < 0:
            return total_pnl, 1, False
        else:
            return total_pnl, 0, False
    elif change_occurred and len(account_balance) > 1:
        account_balance_info = []
        for t in active_trades:
            account_balance_info.append(account_balance[t.index])
        info['Account Balance'] = account_balance_info
        print(f"\nTime: {Date + time_delta}")
        print(tabulate(info, headers='keys', tablefmt='fancy_grid'))
        print(f"Time: {Date + time_delta}")
        print("------------------------------------------------------------\n")
        if print_to_csv:
            with open(csv_path+csv_name, 'a') as O:
                for i in range(len(active_trades)):
                    O.write(
                        f'{Date + time_delta},{account_balance_info[i]},{symbol_info[i]},{entry_price_info[i]},{position_size_info[i]},'
                        f'{trade_price[i]},{TP_vals_info[i]},{SL_val_info[i]},{trade_direction_info[i]},{trade_highest_info[i]},{trade_lowest_info[i]},{trade_status_info[i]}\n')

    return 0, 0, False


def log_info(active_trades: [Trade], trade_price, Dates, account_balance, csv_name, indicators):
    ###########################################################################################################
    #####################               Log Details                          ##########################
    ###########################################################################################################

    info = {}
    symbol_info = []
    entry_price_info = []
    position_size_info = []
    TP_vals_info = []
    SL_val_info = []
    trade_direction_info = []
    for k in range(len(active_trades)):
        symbol_info_temp, entry_price_info_temp, position_size_info_temp, TP_vals_info_temp, SL_val_info_temp, \
            trade_direction_info_temp, trade_status_info_temp, trade_highest_temp, trade_lowest_temp = \
            active_trades[k].print_vals()
        symbol_info.append(symbol_info_temp)
        entry_price_info.append(entry_price_info_temp)
        position_size_info.append(position_size_info_temp)
        TP_vals_info.append(TP_vals_info_temp)
        SL_val_info.append(SL_val_info_temp)

        if trade_direction_info_temp == 0:
            trade_direction_info.append('Short')
        elif trade_direction_info_temp == 1:
            trade_direction_info.append('Long')
        elif trade_direction_info_temp == -99:
            trade_direction_info.append('Closed')

    trade_pnl = []
    for i in range(len(active_trades)):
        if active_trades[i].trade_direction == 0:
            trade_pnl.append((entry_price_info[i] - trade_price[i]) * (position_size_info[i]))
        elif active_trades[i].trade_direction == 1:
            trade_pnl.append((trade_price[i] - entry_price_info[i]) * (position_size_info[i]))
    info['Date'] = Dates
    info['Symbol'] = symbol_info
    info['Direction'] = trade_direction_info
    info['Entry'] = entry_price_info
    info['Close'] = trade_price
    info['Size'] = position_size_info
    info['TP'] = TP_vals_info
    info['SL'] = SL_val_info
    info['PNL'] = trade_pnl
    for x in indicators:
        info[f'{x[0]}'] = x[1]


    print(f"\nAccount Balance: {account_balance}")
    print(tabulate(info, headers='keys', tablefmt='fancy_grid'))
    print(f"Account Balance: {account_balance}")
    print("------------------------------------------------------------\n")

    with open(csv_name, 'a') as O:
        for i in range(len(active_trades)):
            O.write(f"Account Balance: {account_balance}" + "\n" + tabulate(info, headers='keys', tablefmt='fancy_grid') + "\n")



def generate_trade_graphs1(trades: [trade_info], graph_before, trade_graph_folder):
    # pp = PrettyPrinter()
    os.makedirs(f'{trade_graph_folder}//losing_trades')
    os.makedirs(f'{trade_graph_folder}//winning_trades')
    for trade, i in zip(trades, range(len(trades))):
        if not os.path.exists(f'{trade_graph_folder}//losing_trades//{trade.symbol}'):
            os.makedirs(f'{trade_graph_folder}//losing_trades//{trade.symbol}')
        if not os.path.exists(f'{trade_graph_folder}//winning_trades//{trade.symbol}'):
            os.makedirs(f'{trade_graph_folder}//winning_trades//{trade.symbol}')

        # define width of candlestick elements
        width = .2
        width2 = .05

        # define up and down prices
        up_close = []
        up_open = []
        up_high = []
        up_low = []
        up_index = []
        down_index = []
        down_close = []
        down_open = []
        down_high = []
        down_low = []
        dates = []
        for j in range(len(trade.candles["Close"])):
            if trade.candles["Close"][j] >= trade.candles["Open"][j]:
                dates.append(str(trade.candles["Date"][j])[-8:])
                up_index.append(str(trade.candles["Date"][j])[-8:])
                up_close.append(trade.candles["Close"][j])
                up_open.append(trade.candles["Open"][j])
                up_high.append(trade.candles["High"][j])
                up_low.append(trade.candles["Low"][j])

            else:
                dates.append(str(trade.candles["Date"][j])[-8:])
                down_index.append(str(trade.candles["Date"][j])[-8:])
                down_close.append(trade.candles["Close"][j])
                down_open.append(trade.candles["Open"][j])
                down_high.append(trade.candles["High"][j])
                down_low.append(trade.candles["Low"][j])
        up_close = np.array(up_close)
        up_open = np.array(up_open)
        up_high = np.array(up_high)
        up_low = np.array(up_low)

        down_close = np.array(down_close)
        down_open = np.array(down_open)
        down_high = np.array(down_high)
        down_low = np.array(down_low)

        # define colors to use
        col1 = 'green'
        col2 = 'red'

        up_i = 0
        down_i = 0
        up_flag = False
        down_flag = False
        plt.axhline(y=trade.entry_price, color='y', linestyle='dotted', linewidth=1, label=f'entry price={trade.entry_price}')
        plt.axhline(y=trade.TP_price, color='g', linestyle='dotted', linewidth=1, label=f'TP={trade.TP_price}')
        plt.axhline(y=trade.SL_price, color='r', linestyle='dotted', linewidth=1, label=f'SL={trade.SL_price}')
        while (up_i < len(up_index) and not up_flag) or (down_i < len(down_index) and not down_flag):
            if up_index[up_i] < down_index[down_i] and not up_flag:
                plt.bar(up_index[up_i], up_close[up_i] - up_open[up_i], width, bottom=up_open[up_i], color=col1)
                plt.bar(up_index[up_i], up_high[up_i] - up_close[up_i], width2, bottom=up_close[up_i],
                           color=col1)
                plt.bar(up_index[up_i], up_low[up_i] - up_open[up_i], width2, bottom=up_open[up_i], color=col1)
                up_i += 1
                if up_i == len(up_index):
                    up_i -= 1
                    up_flag = True
            elif down_flag:
                plt.bar(up_index[up_i], up_close[up_i] - up_open[up_i], width, bottom=up_open[up_i], color=col1)
                plt.bar(up_index[up_i], up_high[up_i] - up_close[up_i], width2, bottom=up_close[up_i],color=col1)
                plt.bar(up_index[up_i], up_low[up_i] - up_open[up_i], width2, bottom=up_open[up_i], color=col1)
                up_i += 1
                if up_i == len(up_index):
                    up_i -= 1
                    up_flag = True
            elif up_index[up_i] > down_index[down_i] and not down_flag:
                plt.bar(down_index[down_i], down_close[down_i] - down_open[down_i], width, bottom=down_open[down_i],color=col2)
                plt.bar(down_index[down_i], down_high[down_i] - down_open[down_i], width2, bottom=down_open[down_i],color=col2)
                plt.bar(down_index[down_i], down_low[down_i] - down_close[down_i], width2, bottom=down_close[down_i],color=col2)
                down_i += 1
                if down_i == len(down_index):
                    down_i -= 1
                    down_flag = True
            elif up_flag:
                plt.bar(down_index[down_i], down_close[down_i] - down_open[down_i], width, bottom=down_open[down_i],color=col2)
                plt.bar(down_index[down_i], down_high[down_i] - down_open[down_i], width2, bottom=down_open[down_i],color=col2)
                plt.bar(down_index[down_i], down_low[down_i] - down_close[down_i], width2, bottom=down_close[down_i],color=col2)
                down_i += 1
                if down_i == len(down_index):
                    down_i -= 1
                    down_flag = True

        if trade.trade_direction == 1:
            plt.plot(dates[graph_before + 1], trade.candles["Low"][graph_before + 1] * .999, '^', markersize=4,color='g')
        else:
            plt.plot(dates[graph_before + 1], trade.candles["High"][graph_before + 1] * 1.001, 'v', markersize=4,color='r')

        plt.gcf().autofmt_xdate()
        # rotate x-axis tick labels
        plt.xticks(fontsize=4,rotation=60, ha='right')
        # create legend
        plt.legend(fontsize=5, loc="upper left")
        if trade.trade_success == 1:
            plt.title(f'{trade.start_time}: {trade.symbol} Winning Trade')
            plt.savefig(f'{trade_graph_folder}//winning_trades//{trade.symbol}//{trade.start_time}.png', dpi=500)
            plt.close()
        else:
            plt.title(f'{trade.start_time}: {trade.symbol} Losing Trade')
            plt.savefig(f'{trade_graph_folder}//losing_trades//{trade.symbol}//{trade.start_time}.png', dpi=500)
            plt.close()
        print(f"Trade Graph {i+1} of {len(trades)} complete")


def get_candles_for_graphing(Bot: Bot_Class.Bot, trade:Trade, graph_before, graph_after):
    try:
        if Bot.using_heikin_ashi:
            trade.trade_info.candles = {"Date": Bot.Date[trade.trade_info.trade_start_index - graph_before:
                                                         Bot.current_index + graph_after],
                                        "Open": Bot.Open_H[trade.trade_info.trade_start_index - graph_before:
                                                         Bot.current_index + graph_after],
                                        "Close": Bot.Close_H[trade.trade_info.trade_start_index - graph_before:
                                                           Bot.current_index + graph_after],
                                        "High": Bot.High_H[trade.trade_info.trade_start_index - graph_before:
                                                         Bot.current_index + graph_after],
                                        "Low": Bot.Low_H[trade.trade_info.trade_start_index - graph_before:
                                                       Bot.current_index + graph_after],
                                        "Volume": Bot.Volume[trade.trade_info.trade_start_index - graph_before:
                                                             Bot.current_index + graph_after], }
        else:
            trade.trade_info.candles = {"Date": Bot.Date[trade.trade_info.trade_start_index - graph_before:
                                                Bot.current_index + graph_after],
                                        "Open": Bot.Open[trade.trade_info.trade_start_index - graph_before:
                                                Bot.current_index + graph_after],
                                        "Close": Bot.Close[trade.trade_info.trade_start_index - graph_before:
                                                Bot.current_index + graph_after],
                                        "High": Bot.High[trade.trade_info.trade_start_index - graph_before:
                                               Bot.current_index + graph_after],
                                        "Low": Bot.Low[trade.trade_info.trade_start_index - graph_before:
                                              Bot.current_index + graph_after],
                                        "Volume": Bot.Volume[trade.trade_info.trade_start_index - graph_before:
                                                 Bot.current_index + graph_after], }
    except:
        if Bot.using_heikin_ashi:
            trade.trade_info.candles = {
                "Date": Bot.Date[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                "Open": Bot.Open_H[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                "Close": Bot.Close_H[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                "High": Bot.High_H[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                "Low": Bot.Low_H[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                "Volume": Bot.Volume[trade.trade_info.trade_start_index - graph_before:Bot.current_index], }
        else:
            trade.trade_info.candles = {"Date": Bot.Date[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                                        "Open": Bot.Open[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                                        "Close": Bot.Close[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                                        "High": Bot.High[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                                        "Low": Bot.Low[trade.trade_info.trade_start_index - graph_before:Bot.current_index],
                                        "Volume": Bot.Volume[trade.trade_info.trade_start_index - graph_before:Bot.current_index], }

    return trade

def generate_trade_graphs(trades: [trade_info], trade_graph_folder, auto_open_graph_images):
    print("Generating Trade Graphs...")
    os.makedirs(f'{trade_graph_folder}//losing_trades')
    os.makedirs(f'{trade_graph_folder}//winning_trades')
    for trade in trades:
        if not os.path.exists(f'{trade_graph_folder}//losing_trades//{trade.symbol}'):
            os.makedirs(f'{trade_graph_folder}//losing_trades//{trade.symbol}')
        if not os.path.exists(f'{trade_graph_folder}//winning_trades//{trade.symbol}'):
            os.makedirs(f'{trade_graph_folder}//winning_trades//{trade.symbol}')

        data = {"Date": trade.candles["Date"],
                "Close": trade.candles["Close"],
                "Open": trade.candles["Open"],
                "High": trade.candles["High"],
                "Low": trade.candles["Low"],
        }
        df = pd.DataFrame(data)
        keys = list(trade.indicators.keys())
        max_number_of_axis = 2
        for key in keys:
            if trade.indicators[key]['plotting_axis'] > max_number_of_axis:
                max_number_of_axis = trade.indicators[key]['plotting_axis']

        row_heights = [.5,.1]
        sub_height = 0
        specs = [[{"type": "Candlestick"}], [{"type": "scatter"}]]
        if len(row_heights)<max_number_of_axis:
            sub_height = (1 - row_heights[0]) / (max_number_of_axis - 1)
        while len(row_heights)<max_number_of_axis:
            row_heights.append(sub_height)
            specs.append([{"type": "scatter"}])

        fig = make_subplots(
            rows=max_number_of_axis, cols=1,
            row_heights=row_heights,
            specs=specs, shared_xaxes=True)

        fig.add_candlestick(x=df['Date'],
                            open=df['Open'],
                            close=df['Close'],
                            high=df['High'],
                            low=df['Low'],
                            name='Candles')

        if trade.trade_direction == 1:
            fig.add_trace(
                go.Scatter(x=[trade.start_time],
                           y=[trade.entry_price],
                           mode='markers',
                           name='Long',
                           marker=go.scatter.Marker(size=20,
                                            symbol="triangle-up",
                                            color="green")
                           ), row=1, col=1)
        else:
            fig.add_trace(
                go.Scatter(x=[trade.start_time],
                           y=[trade.entry_price],
                           mode='markers',
                           name='Short',
                           marker=go.scatter.Marker(size=20,
                                            symbol="triangle-down",
                                            color="red")
                                     ), row=1, col=1)
        fig.add_trace(
            go.Scatter(x=df['Date'],
                       y=trade.candles['Volume'],
                       name="Volume",
                       ), row=2, col=1)
        for key in keys:
            fig.add_trace(
                go.Scatter(x=df['Date'],
                           y=trade.indicators[key]['values'],
                           name=key,
                           ), row=trade.indicators[key]['plotting_axis'], col=1)

        fig.add_hline(y=trade.TP_price, line_color='lightseagreen', name="TP", row=1, col=1)
        fig.add_hline(y=trade.SL_price, line_color='red', name="SL", row=1, col=1 )

        if trade.trade_success == 1:
            fig.update_layout(title=f'{trade.start_time}: {trade.symbol} Winning Trade',
                              xaxis_rangeslider_visible=False, template='plotly_dark')
            plotly.offline.plot(fig, filename=f"{trade_graph_folder}//winning_trades//{trade.symbol}//{str(trade.start_time).replace(' ','_').replace(':','_')}.html", auto_open=auto_open_graph_images)
        else:
            fig.update_layout(title=f'{trade.start_time}: {trade.symbol} Losing Trade',
                              xaxis_rangeslider_visible=False, template='plotly_dark')
            plotly.offline.plot(fig, filename=f"{trade_graph_folder}//losing_trades//{trade.symbol}//{str(trade.start_time).replace(' ','_').replace(':','_')}.html", auto_open=auto_open_graph_images)

    print("Finished Generating Trade Graphs")



def get_indicators_for_graphing(indicators:{}, trade:Trade, graph_before, graph_after, current_index):
    keys = list(indicators.keys())

    ## Graphing indicators on other axis, matplotlib can't draw these correctly most of the time so leaving for now
    for key in keys:
        try:
            trade.trade_info.indicators[key] = {}
            trade.trade_info.indicators[key]["values"] = indicators[key]["values"][trade.trade_info.trade_start_index - graph_before:
                                                               current_index + graph_after]
            trade.trade_info.indicators[key]["plotting_axis"] = indicators[key]["plotting_axis"]
        except:
            trade.trade_info.indicators[key] = {}
            trade.trade_info.indicators[key]["values"] = indicators[key]["values"][trade.trade_info.trade_start_index - graph_before: current_index]
            trade.trade_info.indicators[key]["plotting_axis"] = indicators[key]["plotting_axis"]

    return trade