import time
from copy import copy
from datetime import datetime
from ta.trend import ema_indicator, macd_signal, macd, sma_indicator, adx, sma_indicator, cci, ichimoku_a, ichimoku_b, \
    ichimoku_base_line, ichimoku_conversion_line
from numpy import random
import pandas as pd
from binance import Client, ThreadedWebsocketManager

import Helper
symbol = ['ETHUSDT']
start = '10-01-23'
end = '23-01-23'
client = Client()

'''

Test the candles I generate are the same as the ones binance feeds us

'''
for TIME_INTERVAL in ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h']:
    Date_binance, Open_binance, Close_binance, High_binance, Low_binance, Volume_binance = [], [], [], [], [], []

    _, _, _, _, _, Date_created, Open_created, Close_created, High_created, Low_created, Volume_created, symbol = \
        Helper.get_aligned_candles([], [], [], [], [], [], [], [], [], [], [], symbol, TIME_INTERVAL, start, end)
    print("Done Aligning")
    for kline in client.futures_historical_klines(symbol[0], TIME_INTERVAL, start_str=f'{start[3:5]}-{start[0:2]}-{start[6:]}', end_str=f'{end[3:5]}-{end[0:2]}-{end[6:]}'):
        Open_binance.append(float(kline[1]))
        High_binance.append(float(kline[2]))
        Low_binance.append(float(kline[3]))
        Close_binance.append(float(kline[4]))
        Volume_binance.append(round(float(kline[7])))
        Date_binance.append(datetime.utcfromtimestamp((round(kline[0] / 1000))))

    if not (Date_binance[:len(Date_created[0])] == Date_created[0] and Open_binance[:len(Open_created[0])] == Open_created[0] and Close_binance[:len(Close_created[0])] == Close_created[0] and
            High_binance[:len(High_created[0])] == High_created[0] and Low_binance[:len(Low_created[0])] == Low_created[0]) and TIME_INTERVAL == '1m':
        print(f"Price Data is incorrect for the {TIME_INTERVAL} time frame on some values")
    elif not (Date_binance[:len(Date_created[0])] == Date_created[0] and Open_binance[:len(Open_created[0])] == Open_created[0] and Close_binance[:len(Close_created[0])] == Close_created[0] and
            High_binance[:len(High_created[0])] == High_created[0] and Low_binance[:len(Low_created[0])] == Low_created[0]) and TIME_INTERVAL != '1m':
        print(f"Price Data is incorrect for the {TIME_INTERVAL} time frame on some values")
    else:
        print(f"Price Data is correct for all values on the {TIME_INTERVAL} time frame")
    if not Volume_binance[:len(Volume_created[0])] == Volume_created[0] and TIME_INTERVAL == '1m':
        print(f"Volume Data is incorrect for the {TIME_INTERVAL} time frame on some values")
    elif not Volume_binance[:len(Volume_created[0])] == Volume_created[0] and TIME_INTERVAL != '1m':
        print(f"Volume Data is incorrect for the {TIME_INTERVAL} time frame on some values due to rounding")


'''

Test alignment of data in backtester is correct

'''
# buffer = 20
# for TIME_INTERVAL in ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h']:
#     Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol = \
#         Helper.get_aligned_candles([], [], [], [], [], [], [], [], [], [], [], symbol, TIME_INTERVAL, start, end)
#     flag = 0
#     TIME_INTERVAL_prev = copy(TIME_INTERVAL)
#     TIME_INTERVAL = Helper.get_TIME_INTERVAL(TIME_INTERVAL)
#     for i in range((buffer-1)*TIME_INTERVAL, len(Close_1min[0]) - (len(Close_1min[0])-len(Close[0])*TIME_INTERVAL)):
#         if ((i + 1) % TIME_INTERVAL == 0 or TIME_INTERVAL == 1) and Date_1min[0][i] != Date[0][int(i/TIME_INTERVAL)] or Close_1min[0][i] != Close[0][int(i/TIME_INTERVAL)]:
#             flag = 1
#     if flag == 0:
#         print(f"Aligned candles are CORRECT for the {TIME_INTERVAL_prev} timeframe")
#     else:
#         print(f"****** Aligned candles are INCORRECT for the {TIME_INTERVAL_prev} timeframe ******")


'''

Test Live Data is correct, manual Check against charts

Part 1

'''
# Interval = '1m'
# start = '13-09-22'
# end = '14-09-22'
# DH: [Helper.Data_Handler] = [Helper.Data_Handler('ETHUSDT', 0)]
# twm = ThreadedWebsocketManager()
# twm.start()
# #twm.start_aggtrade_futures_socket(callback=DH[0].handle_socket_message, symbol='ETHUSDT')#, interval=Interval)
# twm.start_kline_futures_socket(callback=DH[0].handle_socket_message, symbol='ETHUSDT', interval=Interval)
# print(DH)
# while True:
#     ##Check if all coins we are trading have received a new data point
#     count = 0
#     for data in DH:
#         if data.new_data:
#             print(f"{str(datetime.utcfromtimestamp(round(data.next_candle['Date']/1000)))}, Open: {data.next_candle['Open']}, Close: {data.next_candle['Close']}, High: {data.next_candle['High']}, Low: {data.next_candle['Low']}, Volume: {data.next_candle['Volume']}")
#             data.new_data = False

'''

Test Live Data is correct, manual Check against charts

Part 2 for checking the live data against the historical, need to run the websocket for a bit to get some candles and then run this part to confirm they are the same

'''
## Print klines returned from function call

# Date_1min, High_1min, Low_1min, Close_1min, Open_1min, Date, Open, Close, High, Low, Volume, symbol = \
#          Helper.get_aligned_candles([], [], [], [], [], [], [], [], [], [], [], symbol, Interval, start, end)
# for d, o, c, h, l, v in zip(Date[0], Open[0], Close[0], High[0], Low[0], Volume[0]):
#     print(f"{d}, Open: {o}, Close: {c}, High: {h}, Low: {l}, Volume: {v}")

'''Test the Error in EMA when we throw away old-versions values
Error is quite large at times, reduce by using a larger buffer by increasing the buffer_mult'''
window_size = 1650
buffer_mult = 1
buffer = window_size*buffer_mult + 1

x = random.randint(100, size=10000)

EMA_easy = list(ema_indicator(pd.Series(x), window=window_size))
print(EMA_easy)
j = -1
for i in range(10000):
    try:
        EMA_hard = list(ema_indicator(pd.Series(x[i-buffer:i]), window=window_size, fillna=True))
        print(EMA_easy[j], EMA_hard[-1], f"Error: {round(100*(EMA_easy[j] - EMA_hard[-1])/EMA_easy[j], 4)}%")
    except Exception as e:
        print(e)
    j+=1


'''Test the Error in SMA when we throw away old-versions values,
    There is no error with SMAs'''
#
# window_size = 1650
# buffer_mult = 1
# buffer = window_size*buffer_mult + 1
#
# x = random.randint(100, size=10000)
#
# EMA_easy = list(sma_indicator(pd.Series(x), window=window_size))
# print(EMA_easy)
# j = -1
# for i in range(10000):
#     try:
#         EMA_hard = list(sma_indicator(pd.Series(x[i-buffer:i]), window=window_size, fillna=True))
#         print(EMA_easy[j], EMA_hard[-1], f"Error: {round(100*(EMA_easy[j] - EMA_hard[-1])/EMA_easy[j], 4)}%")
#     except Exception as e:
#         print(e)
#     j+=1