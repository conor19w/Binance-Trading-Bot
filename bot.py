from ta.momentum import stochrsi_d, stochrsi_k, stoch, stoch_signal, rsi
from ta.trend import ema_indicator, macd_signal, macd, sma_indicator
from ta.volatility import average_true_range, bollinger_pband
import pandas as pd
import example_strategies as TS
from Logger import *
from trading_config import custom_tp_sl_functions, make_decision_options, wait_for_candle_close



class Bot:
    def __init__(self, symbol: str, Open: [float], Close: [float], High: [float], Low: [float], Volume: [float], Date: [str], OP: int, CP: int, index: int, tick: float,
                 strategy: str, TP_SL_choice: str, SL_mult: float, TP_mult: float, backtesting=0, signal_queue=None, print_trades_q=None):
        self.symbol = symbol
        self.Date = Date

        # Remove extra candle if present TODO check if needed
        shortest = min(len(Open), len(Close), len(High), len(Low), len(Volume))
        self.Open = Open[-shortest:]
        self.Close = Close[-shortest:]
        self.High = High[-shortest:]
        self.Low = Low[-shortest:]
        self.Volume = Volume[-shortest:]

        self.OP = OP
        self.CP = CP
        self.index = index
        self.add_hist_complete = 0
        self.Open_H, self.Close_H, self.High_H, self.Low_H = [], [], [], []
        self.tick_size = tick
        self.socket_failed = False
        self.backtesting = backtesting
        self.use_close_pos = False
        self.strategy = strategy
        self.TP_SL_choice = TP_SL_choice
        self.SL_mult = SL_mult
        self.TP_mult = TP_mult
        self.indicators = {}
        self.current_index = -1  ## -1 for live Bot to always reference the most recent candle, will update in Backtester
        self.take_profit_val, self.stop_loss_val = [], []
        self.peaks, self.troughs = [], []
        self.signal_queue = signal_queue
        if self.index == 0:
            self.print_trades_q = print_trades_q
        if backtesting:
            self.add_hist([], [], [], [], [], [])
            self.update_indicators()
            self.update_TP_SL()
        self.first_interval = False
        self.pop_previous_value = False

    def update_indicators(self):
        ## Calculate indicators
        try:
            match self.strategy:
                case 'StochRSIMACD':
                    CloseS = pd.Series(self.Close)
                    HighS = pd.Series(self.High)
                    LowS = pd.Series(self.Low)
                    self.indicators = {"fastd": {"values": list(stoch(close=CloseS, high=HighS, low=LowS)),
                                                 "plotting_axis": 3},
                                       "fastk": {"values": list(stoch_signal(close=CloseS, high=HighS, low=LowS)),
                                                 "plotting_axis": 3},
                                       "RSI": {"values": list(rsi(CloseS)),
                                               "plotting_axis": 4},
                                       "MACD": {"values": list(macd(CloseS)),
                                                "plotting_axis": 5},
                                       "macdsignal": {"values": list(macd_signal(CloseS)),
                                                      "plotting_axis": 5}
                    }
                case 'tripleEMAStochasticRSIATR':
                    CloseS = pd.Series(self.Close)
                    self.indicators = { "EMA_L": {"values": list(ema_indicator(CloseS, window=100)),
                                                  "plotting_axis": 1},
                                        "EMA_M": {"values": list(ema_indicator(CloseS, window=50)),
                                                  "plotting_axis": 1},
                                        "EMA_S": {"values": list(ema_indicator(CloseS, window=20)),
                                                  "plotting_axis": 1},
                                        "fastd": {"values": list(stochrsi_d(CloseS)),
                                                  "plotting_axis": 3},
                                        "fastk": {"values": list(stochrsi_k(CloseS)),
                                                  "plotting_axis": 3}
                    }
                case 'tripleEMA':
                    CloseS = pd.Series(self.Close)
                    self.indicators = {"EMA_L": {"values": list(ema_indicator(CloseS, window=50)),
                                                 "plotting_axis": 1},
                                       "EMA_M": {"values": list(ema_indicator(CloseS, window=20)),
                                                 "plotting_axis": 1},
                                       "EMA_S": {"values": list(ema_indicator(CloseS, window=5)),
                                                 "plotting_axis": 1}
                    }
                case 'breakout':
                    CloseS = pd.Series(self.Close)
                    VolumeS = pd.Series(self.Volume)
                    self.indicators ={"max Close % change": {"values": list(CloseS.rolling(10).max()),
                                                    "plotting_axis": 3},
                                      "min Close % change": {"values": list(CloseS.rolling(10).min()),
                                                    "plotting_axis": 3},
                                      "max Volume": {"values": list(VolumeS.rolling(10).max()),
                                                  "plotting_axis": 2}
                    }
                case 'stochBB':
                    CloseS = pd.Series(self.Close)
                    self.indicators = {"fastd": {"values": list(stochrsi_d(CloseS)),
                                                 "plotting_axis": 3},
                                       "fastk": {"values": list(stochrsi_k(CloseS)),
                                                 "plotting_axis": 3},
                                       "percent_B": {"values": list(bollinger_pband(CloseS)),
                                                     "plotting_axis": 4}
                    }
                case 'goldenCross':
                    CloseS = pd.Series(self.Close)
                    self.indicators = {"EMA_L": {"values": list(ema_indicator(CloseS, window=100)),
                                                 "plotting_axis": 1},
                                       "EMA_M": {"values": list(ema_indicator(CloseS, window=50)),
                                                 "plotting_axis": 1},
                                       "EMA_S": {"values": list(ema_indicator(CloseS, window=20)),
                                                 "plotting_axis": 1},
                                       "RSI": {"values": list(rsi(CloseS)),
                                               "plotting_axis": 3}
                    }
                case 'fibMACD':
                    CloseS = pd.Series(self.Close)
                    self.indicators = {"MACD_signal": {"values": list(macd_signal(CloseS)),
                                                       "plotting_axis": 3},
                                       "MACD": {"values": list(macd(CloseS)),
                                                "plotting_axis": 3},
                                       "EMA": {"values": list(sma_indicator(CloseS, window=200)),
                                               "plotting_axis": 1}
                    }
                case 'EMA_cross':
                    CloseS = pd.Series(self.Close)
                    self.indicators = {"EMA_S": {"values": list(ema_indicator(CloseS, window=5)),
                                                 "plotting_axis": 1},
                                       "EMA_L": {"values": list(ema_indicator(CloseS, window=20)),
                                                "plotting_axis": 1}
                    }
                case 'heikin_ashi_ema2':
                    CloseS = pd.Series(self.Close)
                    self.use_close_pos = True
                    self.indicators = {"fastd": {"values": list(stochrsi_d(CloseS)),
                                                 "plotting_axis": 3},
                                       "fastk": {"values": list(stochrsi_k(CloseS)),
                                                 "plotting_axis": 3},
                                       "EMA": {"values": list(ema_indicator(CloseS, window=200)),
                                               "plotting_axis": 1}
                    }
                case 'heikin_ashi_ema':
                    CloseS = pd.Series(self.Close)
                    self.use_close_pos = True
                    self.indicators = {"fastd": {"values": list(stochrsi_d(CloseS)),
                                                 "plotting_axis": 3},
                                       "fastk": {"values": list(stochrsi_k(CloseS)),
                                                 "plotting_axis": 3},
                                       "EMA": {"values": list(ema_indicator(CloseS, window=200)),
                                             "plotting_axis": 1}
                    }
                case 'ema_crossover':
                    CloseS = pd.Series(self.Close)
                    self.indicators = {"ema_short": {"values": list(ema_indicator(CloseS, window=20)),
                                                 "plotting_axis": 1},
                                       "ema_long": {"values": list(ema_indicator(CloseS, window=50)),
                                                 "plotting_axis": 1},
                                       }
                case _:
                    return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.error(f'update_indicators() - Error occurred with strategy: {self.strategy}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def update_TP_SL(self):
        ## Run Once in Backtester/ Run every candle in Live Bot
        try:
            match self.TP_SL_choice:
                case '%':
                    self.take_profit_val = [(self.TP_mult / 100) * self.Close[i] for i in range(len(self.Close))]
                    self.stop_loss_val = [(self.SL_mult / 100) * self.Close[i] for i in range(len(self.Close))]

                case 'x (ATR)':
                    ATR = average_true_range(self.High, self.Low, self.Close)
                    self.take_profit_val = [self.TP_mult * abs(ATR[i]) for i in range(len(ATR))]
                    self.stop_loss_val = [self.SL_mult * abs(ATR[i]) for i in range(len(ATR))]

                case 'x (Swing High/Low) level 1':
                    self.peaks = [0 if (i < 1 or i > len(self.High) - 2) else self.High[i] if (self.High[i - 1] < self.High[i] > self.High[i + 1]) else 0 for i in range(len(self.High))]

                    self.troughs = [0 if (i < 1 or i > len(self.High) - 2) else self.Low[i] if (self.Low[i - 1] > self.Low[i] < self.Low[i + 1]) else 0 for i in range(len(self.Low))]

                case 'x (Swing High/Low) level 2':
                    self.peaks = [0 if (i < 2 or i > len(self.High) - 3) else self.High[i] if (self.High[i - 1] < self.High[i] > self.High[i + 1]) and (self.High[i - 2] < self.High[i] > self.High[i + 2])
                                     else 0 for i in range(len(self.High))]

                    self.troughs = [0 if (i < 2 or i > len(self.Low) - 3) else self.Low[i] if (self.Low[i - 1] > self.Low[i] < self.Low[i + 1]) and (self.Low[i - 2] > self.Low[i] < self.Low[i + 2])
                                       else 0 for i in range(len(self.Low))]

                case 'x (Swing High/Low) level 3':
                    self.peaks = [0 if (i < 3 or i > len(self.High) - 4) else self.High[i] if (self.High[i - 1] < self.High[i] > self.High[i + 1]) and (self.High[i - 2] < self.High[i] > self.High[i + 2])
                                                                                              and (self.High[i - 3] < self.High[i] > self.High[i + 3]) else 0 for i in range(len(self.High))]

                    self.troughs = [0 if (i < 3 or i > len(self.Low) - 4) else self.Low[i] if (self.Low[i - 1] > self.Low[i] < self.Low[i + 1]) and (self.Low[i - 2] > self.Low[i] < self.Low[i + 2])
                                                                                              and (self.Low[i - 3] > self.Low[i] < self.Low[i + 3]) else 0 for i in range(len(self.Low))]

                case 'x (Swing Close) level 1':
                    self.peaks = [0 if (i < 1 or i > len(self.Close) - 2) else self.Close[i] if (self.Close[i - 1] < self.Close[i] > self.Close[i + 1]) else 0 for i in range(len(self.Close))]

                    self.troughs = [0 if (i < 1 or i > len(self.Close) - 2) else self.Close[i] if (self.Close[i - 1] > self.Close[i] < self.Close[i + 1]) else 0 for i in range(len(self.Close))]

                case 'x (Swing Close) level 2':
                    self.peaks = [0 if (i < 2 or i > len(self.Close) - 3) else self.Close[i] if (self.Close[i - 1] < self.Close[i] > self.Close[i + 1]) and
                                                                                                (self.Close[i - 2] < self.Close[i] > self.Close[i + 2]) else 0 for i in range(len(self.Close))]

                    self.troughs = [0 if (i < 2 or i > len(self.Close) - 3) else self.Close[i] if (self.Close[i - 1] > self.Close[i] < self.Close[i + 1]) and
                                                                                                  (self.Close[i - 2] > self.Close[i] < self.Close[i + 2]) else 0 for i in range(len(self.Close))]

                case 'x (Swing Close) level 3':
                    self.peaks = [0 if (i < 3 or i > len(self.Close) - 4) else self.Close[i] if (self.Close[i - 1] < self.Close[i] > self.Close[i + 1]) and
                                                                                                (self.Close[i - 2] < self.Close[i] > self.Close[i + 2]) and (self.Close[i - 3] < self.Close[i] > self.Close[i + 3])
                                     else 0 for i in range(len(self.Close))]

                    self.troughs = [0 if (i < 3 or i > len(self.Close) - 4) else self.Close[i] if (self.Close[i - 1] > self.Close[i] < self.Close[i + 1]) and
                                                                                                  (self.Close[i - 2] > self.Close[i] < self.Close[i + 2]) and (self.Close[i - 3] > self.Close[i] < self.Close[i + 3])
                                       else 0 for i in range(len(self.Close))]
                case _:
                    return
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.error(f'update_TP_SL() - Error occurred with tp_sl_choice: {self.TP_SL_choice}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def add_hist(self, Date_temp: [float], Open_temp: [float], Close_temp: [float], High_temp: [float], Low_temp: [float], Volume_temp: [str]):
        if not self.backtesting:
            try:
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
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.error(f'add_hist() - Error occurred joining historical and websocket data, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
        try:
            ## TODO verify these are correct
            self.Close_H.append((self.Open[0] + self.Close[0] + self.Low[0] + self.High[0]) / 4)
            self.Open_H.append((self.Close[0] + self.Open[0]) / 2)
            self.High_H.append(self.High[0])
            self.Low_H.append(self.Low[0])
            for i in range(1, len(self.Close)):
                self.Open_H.append((self.Open_H[i-1] + self.Close_H[i-1]) / 2)
                self.Close_H.append((self.Open[i] + self.Close[i] + self.Low[i] + self.High[i]) / 4)
                self.High_H.append(max(self.High[i], self.Open_H[i], self.Close_H[i]))
                self.Low_H.append(min(self.Low[i], self.Open_H[i], self.Close_H[i]))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.error(f'add_hist() - Error occurred creating heikin ashi candles, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
        self.add_hist_complete = 1

    def handle_socket_message(self, msg):
        try:
            if msg != '':
                payload = msg['k']
                if payload['x']:
                    if self.pop_previous_value:
                        self.remove_last_candle()
                    self.consume_new_candle(payload)
                    if self.add_hist_complete:
                        self.generate_new_heikin_ashi()
                        trade_direction, stop_loss_val, take_profit_val = self.make_decision()
                        if trade_direction != -99:
                            self.signal_queue.put([self.symbol, self.OP, self.CP, self.tick_size, trade_direction, self.index, stop_loss_val, take_profit_val])
                        self.remove_first_candle()
                    if self.index == 0:
                        self.print_trades_q.put(True)
                    if not self.first_interval:
                        self.first_interval = True
                    self.pop_previous_value = False
                elif not wait_for_candle_close and self.first_interval and self.add_hist_complete:
                    if self.pop_previous_value:
                        self.remove_last_candle()
                    self.pop_previous_value = True
                    self.consume_new_candle(payload)
                    self.generate_new_heikin_ashi()
                    trade_direction, stop_loss_val, take_profit_val = self.make_decision()
                    if trade_direction != -99:
                        self.signal_queue.put([self.symbol, self.OP, self.CP, self.tick_size, trade_direction, self.index, stop_loss_val, take_profit_val])

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f"handle_socket_message() - Error in handling of {self.symbol} websocket flagging for reconnection, msg: {msg}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")
            self.socket_failed = True


    def make_decision(self):
        self.update_indicators()
        ##Initialize vars:
        trade_direction = -99  ## Short (0), Long (1)
        stop_loss_val = -99
        take_profit_val = -99
        ## Strategies found in example_strategies.py:
        try:
            match self.strategy:
                case 'StochRSIMACD':
                    trade_direction = TS.StochRSIMACD(trade_direction, self.indicators["fastd"]["values"], self.indicators["fastk"]["values"],
                                                      self.indicators["RSI"]["values"], self.indicators["MACD"]["values"],
                                                      self.indicators["macdsignal"]["values"], self.current_index)
                case 'tripleEMAStochasticRSIATR':
                    trade_direction = TS.tripleEMAStochasticRSIATR(self.Close, trade_direction, self.indicators["EMA_L"]["values"],
                                                                   self.indicators["EMA_M"]["values"], self.indicators["EMA_S"]["values"],
                                                                   self.indicators["fastd"]["values"], self.indicators["fastk"]["values"], self.current_index)
                case 'tripleEMA':
                    trade_direction = TS.tripleEMA(trade_direction, self.indicators["EMA_S"]["values"],
                                                   self.indicators["EMA_M"]["values"], self.indicators["EMA_L"]["values"], self.current_index)
                case 'breakout':
                    trade_direction = TS.breakout(trade_direction, self.Close, self.Volume, self.indicators["max Close % change"]["values"],
                                                  self.indicators["min Close % change"]["values"], self.indicators["max Volume"]["values"],
                                                  self.current_index)
                case 'stochBB':
                    trade_direction = TS.stochBB(trade_direction, self.indicators["fastd"]["values"],
                                                 self.indicators["fastk"]["values"], self.indicators["percent_B"]["values"], self.current_index)
                case 'goldenCross':
                    trade_direction = TS.goldenCross(trade_direction, self.Close, self.indicators["EMA_L"]["values"],
                                                     self.indicators["EMA_M"]["values"], self.indicators["EMA_S"]["values"],
                                                     self.indicators["RSI"]["values"], self.current_index)
                case 'candle_wick':
                    trade_direction = TS.candle_wick(trade_direction, self.Close, self.Open, self.High, self.Low, self.current_index)
                case 'fibMACD':
                    trade_direction = TS.fibMACD(trade_direction, self.Close, self.Open, self.High, self.Low, self.indicators["MACD_signal"]["values"],
                                                 self.indicators["MACD"]["values"], self.indicators["EMA"]["values"], self.current_index)
                case 'EMA_cross':
                    trade_direction = TS.EMA_cross(trade_direction, self.indicators["EMA_S"]["values"],
                                                   self.indicators["EMA_L"]["values"], self.current_index)
                case 'heikin_ashi_ema2':
                    trade_direction, _ = TS.heikin_ashi_ema2(self.Open_H, self.High_H, self.Low_H, self.Close_H, trade_direction,
                                                             -99, 0, self.indicators["fastd"]["values"], self.indicators["fastk"]["values"],
                                                             self.indicators["EMA"]["values"], self.current_index)
                case 'heikin_ashi_ema':
                    trade_direction, _ = TS.heikin_ashi_ema(self.Open_H, self.Close_H, trade_direction, -99, 0,
                                                            self.indicators["fastd"]["values"],
                                                            self.indicators["fastk"]["values"],
                                                            self.indicators["EMA"]["values"], self.current_index)
                case "ema_crossover":
                    trade_direction = TS.ema_crossover(trade_direction, self.current_index,
                                                       self.indicators["ema_short"]["values"],
                                                       self.indicators["ema_long"]["values"])

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.error(f"make_decision() - Error with strategy: {self.strategy}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")
        try:
            if trade_direction != -99 and self.TP_SL_choice not in custom_tp_sl_functions:
                self.update_TP_SL()
                stop_loss_val = -99  ##the margin of increase/decrease that would stop us out/ be our take profit, NOT the price target.
                take_profit_val = -99  # That is worked out later by adding or subtracting:
                stop_loss_val, take_profit_val = TS.SetSLTP(self.stop_loss_val, self.take_profit_val, self.peaks,
                                                            self.troughs, self.Close, self.High, self.Low, trade_direction,
                                                            self.SL_mult,
                                                            self.TP_mult, self.TP_SL_choice,
                                                            self.current_index)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.error(
                f"make_decision() - Error with SetSLTP TP_SL_choice: {self.TP_SL_choice}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")

        return trade_direction, stop_loss_val, take_profit_val

    def check_close_pos(self, trade_direction):
            close_pos = 0
            try:
                match self.strategy:
                    case 'heikin_ashi_ema2':
                        _, close_pos = TS.heikin_ashi_ema2(self.Open_H, self.High_H, self.Low_H,
                                                           self.Close_H, -99, trade_direction,
                                                           0, self.indicators["fastd"]["values"], self.indicators["fastk"]["values"],
                                                           self.indicators["EMA"]["values"], self.current_index)
                    case 'heikin_ashi_ema':
                        _, close_pos = TS.heikin_ashi_ema(self.Open_H, self.Close_H, -99, trade_direction, 0,
                                                          self.indicators["fastd"]["values"], self.indicators["fastk"]["values"], self.indicators["EMA"]["values"], self.current_index)
                    case _:
                        return
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.error(f"check_close_pos() - Error with strategy: {self.strategy}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")
            return close_pos

    def remove_last_candle(self):
        self.Date.pop(-1)
        self.Close.pop(-1)
        self.Volume.pop(-1)
        self.High.pop(-1)
        self.Low.pop(-1)
        self.Open.pop(-1)
        self.Open_H.pop(-1)
        self.Close_H.pop(-1)
        self.High_H.pop(-1)
        self.Low_H.pop(-1)

    def remove_first_candle(self):
        self.Date.pop(0)
        self.Close.pop(0)
        self.Volume.pop(0)
        self.High.pop(0)
        self.Low.pop(0)
        self.Open.pop(0)
        self.Open_H.pop(0)
        self.Close_H.pop(0)
        self.Low_H.pop(0)
        self.High_H.pop(0)

    def consume_new_candle(self, payload):
        self.Date.append(int(payload['T']))
        self.Close.append(float(payload['c']))
        self.Volume.append(float(payload['q']))
        self.High.append(float(payload['h']))
        self.Low.append(float(payload['l']))
        self.Open.append(float(payload['o']))

    def generate_new_heikin_ashi(self):
        self.Open_H.append((self.Open_H[-1] + self.Close_H[-1]) / 2)
        self.Close_H.append((self.Open[-1] + self.Close[-1] + self.Low[-1] + self.High[-1]) / 4)
        self.High_H.append(max(self.High[-1], self.Open_H[-1], self.Close_H[-1]))
        self.Low_H.append(min(self.Low[-1], self.Open_H[-1], self.Close_H[-1]))