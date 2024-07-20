import os
import sys
from datetime import datetime
import time
from ta.momentum import stochrsi_d, stochrsi_k, stoch, stoch_signal, rsi, awesome_oscillator
from ta.trend import ema_indicator, macd_signal, macd, sma_indicator, adx, sma_indicator, cci
from ta.volatility import average_true_range, bollinger_pband, bollinger_hband, bollinger_lband, bollinger_mavg
from ta.volume import ease_of_movement, on_balance_volume, force_index, money_flow_index
from ta.momentum import tsi
from ta.trend import stc
import numpy as np
import pandas as pd
import TradingStrats as TS
class Bot:
    def __init__(self, symbol, Open, Close, High, Low, Volume, Date, OP, CP, index, generate_heikin_ashi, tick,
                 backtesting=0):
        self.symbol = symbol
        self.Open = Open
        self.Close = Close
        self.High = High
        self.Low = Low
        self.Volume = Volume
        self.Date = Date
        self.OP = OP
        self.CP = CP
        self.index = index
        self.add_hist_complete = 0
        self.new_data = 0
        self.generate_heikin_ashi = generate_heikin_ashi
        self.Open_H = []
        self.Close_H = []
        self.High_H = []
        self.Low_H = []
        self.tick_size = tick
        self.socket_failed = False
        self.backtesting = backtesting
        self.use_close_pos = False

    def add_hist(self, Date_temp, Open_temp, Close_temp, High_temp, Low_temp, Volume_temp):
        if not self.backtesting:
            while 0 < len(self.Date):
                if self.Date[0] > Date_temp[-1]:
                    Date_temp.append(self.Date.pop(0))
                    Open_temp.append(self.Open.pop(0))
                    Close_temp.append(self.Close.pop(0))
                    High_temp.append(self.High.pop(0))
                    Low_temp.append(self.Low.pop(0))
                    Volume_temp.append(self.Volume.pop(0))
                else:
                    self.Date.pop(0)
                    self.Open.pop(0)
                    self.Close.pop(0)
                    self.High.pop(0)
                    self.Low.pop(0)
                    self.Volume.pop(0)
            self.Date = Date_temp
            self.Open = Open_temp
            self.Close = Close_temp
            self.High = High_temp
            self.Low = Low_temp
            self.Volume = Volume_temp
        if self.generate_heikin_ashi:
            ##Create Heikin Ashi bars
            for i in range(len(self.Close)):
                self.Close_H.append((self.Open[i] + self.Close[i] + self.Low[i] + self.High[i]) / 4)
                if i == 0:
                    self.Open_H.append((self.Close[i] + self.Open[i]) / 2)
                    self.High_H.append(self.High[i])
                    self.Low_H.append(self.Low[i])
                else:
                    self.Open_H.append((self.Open_H[i - 1] + self.Close_H[i - 2]) / 2)
                    self.High_H.append(max(self.High[i], self.Open_H[i], self.Close_H[i]))
                    self.Low_H.append(min(self.Low[i], self.Open_H[i], self.Close_H[i]))
        self.add_hist_complete = 1
        #for i in range(len(self.Date)):
        #    print(f"Date: {self.Date[i]}, Open_H: {self.Open_H[i]}, Close_H: {self.Close_H[i]}, High_H: {self.High_H[i]}, Low_H: {self.Low_H[i]}")

    def handle_socket_message(self, Data, Date=0, Close=0, Volume=0, Open=0, High=0, Low=0):
        try:
            if Data == -99:
                self.Date.append(Date)
                self.Close.append(Close)
                self.Volume.append(Volume)
                self.High.append(High)
                self.Low.append(Low)
                self.Open.append(Open)
                if self.add_hist_complete:
                    self.Date.pop(0)
                    self.Close.pop(0)
                    self.Volume.pop(0)
                    self.High.pop(0)
                    self.Low.pop(0)
                    self.Open.pop(0)
                    if self.generate_heikin_ashi:
                        self.Close_H.append((self.Open[-1] + self.Close[-1] + self.Low[-1] + self.High[-1]) / 4)
                        self.Open_H.append((self.Open_H[-1] + self.Close_H[-2]) / 2)
                        self.High_H.append(max(self.High[-1], self.Open_H[-1], self.Close_H[-1]))
                        self.Low_H.append(min(self.Low[-1], self.Open_H[-1], self.Close_H[-1]))
                        self.Open_H.pop(0)
                        self.Close_H.pop(0)
                        self.Low_H.pop(0)
                        self.High_H.pop(0)
                    self.new_data = 1
            elif Data['Date'] != -99:
                self.Date.append(Data['Date'])
                self.Close.append(Data['Close'])
                self.Volume.append(Data['Volume'])
                self.High.append(Data['High'])
                self.Low.append(Data['Low'])
                self.Open.append(Data['Open'])
                if self.add_hist_complete:
                    self.Date.pop(0)
                    self.Close.pop(0)
                    self.Volume.pop(0)
                    self.High.pop(0)
                    self.Low.pop(0)
                    self.Open.pop(0)
                    if self.generate_heikin_ashi:
                        self.Close_H.append((self.Open[-1] + self.Close[-1] + self.Low[-1] + self.High[-1]) / 4)
                        self.Open_H.append((self.Open_H[-1] + self.Close_H[-2]) / 2)
                        self.High_H.append(max(self.High[-1], self.Open_H[-1], self.Close_H[-1]))
                        self.Low_H.append(min(self.Low[-1], self.Open_H[-1], self.Close_H[-1]))
                        self.Open_H.pop(0)
                        self.Close_H.pop(0)
                        self.Low_H.pop(0)
                        self.High_H.pop(0)
                    self.new_data = 1
        # except Exception as e:
        #     print(e)
        #     exc_type, exc_obj, exc_tb = sys.exc_info()
        #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        #     print(exc_type, fname, exc_tb.tb_lineno) ## Can add this except statement in to code to figure out what line the error was thrown on
        except Exception as e:
            print(f"Error in {self.symbol}.handle_socket_message(): ", e)
            self.socket_failed = True

    def Make_decision(self):
        ##Initialize vars:
        Trade_Direction = -99  ## Short (0), Long (1)
        stop_loss_val = -99  ##the margin of increase/decrease that would stop us out/ be our take profit, NOT the price target.
        take_profit_val = -99  # That is worked out later by adding or subtracting:
        ## Strategies found in example_strategies.py:
        # Trade_Direction,stop_loss_val, take_profit_val = TS.StochRSIMACD(Trade_Direction, self.Close,self.High,self.Low)
        Trade_Direction,stop_loss_val, take_profit_val = TS.tripleEMAStochasticRSIATR(self.Close,self.High,self.Low,Trade_Direction)
        # Trade_Direction, stop_loss_val, take_profit_val = TS.tripleEMA(self.Close, self.High, self.Low, Trade_Direction)
        # Trade_Direction, stop_loss_val, take_profit_val = TS.breakout(Trade_Direction,self.Close,self.Volume,self.High, self.Low)
        # Trade_Direction,stop_loss_val,take_profit_val = TS.stochBB(Trade_Direction,self.Close, self.High, self.Low)
        # Trade_Direction, stop_loss_val, take_profit_val = TS.goldenCross(Trade_Direction,self.Close, self.High, self.Low)
        # Trade_Direction , stop_loss_val, take_profit_val = TS.candle_wick(Trade_Direction,self.Close,self.Open,self.High,self.Low)
        # Trade_Direction,stop_loss_val,take_profit_val = TS.fibMACD(Trade_Direction, self.Close, self.Open,self.High,self.Low)
        #Trade_Direction, stop_loss_val, take_profit_val = TS.EMA_cross(Trade_Direction, self.Close, self.High, self.Low)

        ## need to set self.use_close_pos = True if you want to use the close position on condition functionality of the strategies below
        ##  And also need to uncomment the corresponding strategy below in check_close_pos()
        #self.use_close_pos = True
        # Trade_Direction, stop_loss_val, take_profit_val, _ = TS.heikin_ashi_ema2(self.Close, self.Open_H, self.High_H, self.Low_H, self.Close_H, Trade_Direction, stop_loss_val, take_profit_val, -99, 0)
        #Trade_Direction,stop_loss_val,take_profit_val,_ = TS.heikin_ashi_ema(self.Close, self.Open_H, self.Close_H, Trade_Direction, stop_loss_val,take_profit_val, -99, 0)
        return Trade_Direction, stop_loss_val, take_profit_val

    def check_close_pos(self, current_pos):
        ## need to uncomment corresponding strategy in here too if using close position on condition functionality
        close_pos = 0
        Trade_Direction = -99  ## Short (0), Long (1)
        stop_loss_val = -99  ##the margin of increase/decrease that would stop us out/ be our take profit, NOT the price target.
        take_profit_val = -99  # That is worked out later by adding or subtracting:
        #_, _, _, close_pos = TS.heikin_ashi_ema2(self.Close, self.Open_H, self.High_H, self.Low_H, self.Close_H, Trade_Direction, stop_loss_val, take_profit_val, current_pos, 0)
        #_,_,_,close_pos = TS.heikin_ashi_ema(self.Close, self.Open_H, self.Close_H, Trade_Direction, stop_loss_val,take_profit_val, current_pos, 0)
        return close_pos
