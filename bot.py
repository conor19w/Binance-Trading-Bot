from ta.momentum import stochrsi_d, stochrsi_k, stoch, stoch_signal, rsi
from ta.trend import ema_indicator, macd_signal, macd, sma_indicator
from ta.volatility import average_true_range, bollinger_pband
import pandas as pd
import example_strategies as TS
from logger import *
from trading_config import custom_tp_sl_functions, make_decision_options, wait_for_candle_close, trading_strategy, tp_sl_choice, sl_mult, tp_mult


class Bot:
    def __init__(self, symbol: str, open_price: [float], close_price: [float], high_price: [float], low_price: [float], volume: [float], time_open: [str], time_close: [str],
                 order_precision: int, coin_precision: int, index: int, tick_size: float, backtesting=0, signal_queue=None, print_trades_q=None):
        self.symbol = symbol
        self.time_open = time_open
        self.time_close = time_close
        self.open = open_price
        self.close = close_price
        self.high = high_price
        self.low = low_price
        self.volume = volume

        self.order_precision = order_precision
        self.coin_precision = coin_precision
        self.index = index
        self.add_hist_complete = 0
        self.open_h, self.close_h, self.high_h, self.low_h = [], [], [], []
        self.tick_size = tick_size
        self.socket_failed = False
        self.backtesting = backtesting
        self.use_close_pos = False
        self.strategy = trading_strategy
        self.tp_sl_choice = tp_sl_choice
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.indicators = {}
        self.current_index = -1  # -1 for live Bot to always reference the most recent candle, will update in Backtester
        self.take_profit_val, self.stop_loss_val = [], []
        self.peaks, self.troughs = [], []
        self.signal_queue = signal_queue
        if self.index == 0:
            self.print_trades_q = print_trades_q
        if backtesting:
            self.add_hist([], [], [], [], [], [], [])
            self.update_indicators()
            self.update_tp_sl()
        self.first_interval = False
        self.pop_previous_value = False

    @log.catch_errors()
    def update_indicators(self):
        ## Calculate indicators
        match self.strategy:
            case 'stoch_rsi_macd':
                close_series = pd.Series(self.close)
                high_series = pd.Series(self.high)
                low_series = pd.Series(self.low)
                self.indicators = {"fastd": {"values": list(stoch(close=close_series, high=high_series, low=low_series)),
                                             "plotting_axis": 3},
                                   "fastk": {"values": list(stoch_signal(close=close_series, high=high_series, low=low_series)),
                                             "plotting_axis": 3},
                                   "rsi": {"values": list(rsi(close_series)),
                                           "plotting_axis": 4},
                                   "macd": {"values": list(macd(close_series)),
                                            "plotting_axis": 5},
                                   "macdsignal": {"values": list(macd_signal(close_series)),
                                                  "plotting_axis": 5}
                }
            case 'triple_ema_stochastic_rsi_atr':
                close_series = pd.Series(self.close)
                self.indicators = { "EMA_L": {"values": list(ema_indicator(close_series, window=100)),
                                              "plotting_axis": 1},
                                    "EMA_M": {"values": list(ema_indicator(close_series, window=50)),
                                              "plotting_axis": 1},
                                    "EMA_S": {"values": list(ema_indicator(close_series, window=20)),
                                              "plotting_axis": 1},
                                    "fastd": {"values": list(stochrsi_d(close_series)),
                                              "plotting_axis": 3},
                                    "fastk": {"values": list(stochrsi_k(close_series)),
                                              "plotting_axis": 3}
                }
            case 'triple_ema':
                close_series = pd.Series(self.close)
                self.indicators = {"EMA_L": {"values": list(ema_indicator(close_series, window=50)),
                                             "plotting_axis": 1},
                                   "EMA_M": {"values": list(ema_indicator(close_series, window=20)),
                                             "plotting_axis": 1},
                                   "EMA_S": {"values": list(ema_indicator(close_series, window=5)),
                                             "plotting_axis": 1}
                }
            case 'breakout':
                close_series = pd.Series(self.close)
                volume_series = pd.Series(self.volume)
                self.indicators ={"max Close % change": {"values": list(close_series.rolling(10).max()),
                                                "plotting_axis": 3},
                                  "min Close % change": {"values": list(close_series.rolling(10).min()),
                                                "plotting_axis": 3},
                                  "max Volume": {"values": list(volume_series.rolling(10).max()),
                                              "plotting_axis": 2}
                }
            case 'stoch_bb':
                close_series = pd.Series(self.close)
                self.indicators = {"fastd": {"values": list(stochrsi_d(close_series)),
                                             "plotting_axis": 3},
                                   "fastk": {"values": list(stochrsi_k(close_series)),
                                             "plotting_axis": 3},
                                   "percent_B": {"values": list(bollinger_pband(close_series)),
                                                 "plotting_axis": 4}
                }
            case 'golden_cross':
                close_series = pd.Series(self.close)
                self.indicators = {"EMA_L": {"values": list(ema_indicator(close_series, window=100)),
                                             "plotting_axis": 1},
                                   "EMA_M": {"values": list(ema_indicator(close_series, window=50)),
                                             "plotting_axis": 1},
                                   "EMA_S": {"values": list(ema_indicator(close_series, window=20)),
                                             "plotting_axis": 1},
                                   "RSI": {"values": list(rsi(close_series)),
                                           "plotting_axis": 3}
                }
            case 'fib_macd':
                close_series = pd.Series(self.close)
                self.indicators = {"MACD_signal": {"values": list(macd_signal(close_series)),
                                                   "plotting_axis": 3},
                                   "MACD": {"values": list(macd(close_series)),
                                            "plotting_axis": 3},
                                   "EMA": {"values": list(sma_indicator(close_series, window=200)),
                                           "plotting_axis": 1}
                }
            case 'ema_cross':
                close_series = pd.Series(self.close)
                self.indicators = {"EMA_S": {"values": list(ema_indicator(close_series, window=5)),
                                             "plotting_axis": 1},
                                   "EMA_L": {"values": list(ema_indicator(close_series, window=20)),
                                            "plotting_axis": 1}
                }
            case 'heikin_ashi_ema2':
                close_series = pd.Series(self.close)
                self.use_close_pos = True
                self.indicators = {"fastd": {"values": list(stochrsi_d(close_series)),
                                             "plotting_axis": 3},
                                   "fastk": {"values": list(stochrsi_k(close_series)),
                                             "plotting_axis": 3},
                                   "EMA": {"values": list(ema_indicator(close_series, window=200)),
                                           "plotting_axis": 1}
                }
            case 'heikin_ashi_ema':
                close_series = pd.Series(self.close)
                self.use_close_pos = True
                self.indicators = {"fastd": {"values": list(stochrsi_d(close_series)),
                                             "plotting_axis": 3},
                                   "fastk": {"values": list(stochrsi_k(close_series)),
                                             "plotting_axis": 3},
                                   "EMA": {"values": list(ema_indicator(close_series, window=200)),
                                         "plotting_axis": 1}
                }
            case 'ema_crossover':
                close_series = pd.Series(self.close)
                self.indicators = {"ema_short": {"values": list(ema_indicator(close_series, window=20)),
                                             "plotting_axis": 1},
                                   "ema_long": {"values": list(ema_indicator(close_series, window=50)),
                                             "plotting_axis": 1},
                                   }
            case _:
                return

    @log.catch_errors()
    def update_tp_sl(self):
        match self.tp_sl_choice:
            case '%':
                self.take_profit_val = [(self.tp_mult / 100) * self.close[i] for i in range(len(self.close))]
                self.stop_loss_val = [(self.sl_mult / 100) * self.close[i] for i in range(len(self.close))]

            case 'x (ATR)':
                atr = average_true_range(self.high, self.low, self.close)
                self.take_profit_val = [self.tp_mult * abs(atr[i]) for i in range(len(atr))]
                self.stop_loss_val = [self.sl_mult * abs(atr[i]) for i in range(len(atr))]

            case 'x (Swing High/Low) level 1':
                self.peaks = [0 if (i < 1 or i > len(self.high) - 2) else self.high[i] if (self.high[i - 1] < self.high[i] > self.high[i + 1]) else 0 for i in range(len(self.high))]

                self.troughs = [0 if (i < 1 or i > len(self.high) - 2) else self.low[i] if (self.low[i - 1] > self.low[i] < self.low[i + 1]) else 0 for i in range(len(self.low))]

            case 'x (Swing High/Low) level 2':
                self.peaks = [0 if (i < 2 or i > len(self.high) - 3) else self.high[i] if (self.high[i - 1] < self.high[i] > self.high[i + 1]) and (self.high[i - 2] < self.high[i] > self.high[i + 2])
                                 else 0 for i in range(len(self.high))]

                self.troughs = [0 if (i < 2 or i > len(self.low) - 3) else self.low[i] if (self.low[i - 1] > self.low[i] < self.low[i + 1]) and (self.low[i - 2] > self.low[i] < self.low[i + 2])
                                   else 0 for i in range(len(self.low))]

            case 'x (Swing High/Low) level 3':
                self.peaks = [0 if (i < 3 or i > len(self.high) - 4) else self.high[i] if (self.high[i - 1] < self.high[i] > self.high[i + 1]) and (self.high[i - 2] < self.high[i] > self.high[i + 2])
                                                                                          and (self.high[i - 3] < self.high[i] > self.high[i + 3]) else 0 for i in range(len(self.high))]

                self.troughs = [0 if (i < 3 or i > len(self.low) - 4) else self.low[i] if (self.low[i - 1] > self.low[i] < self.low[i + 1]) and (self.low[i - 2] > self.low[i] < self.low[i + 2])
                                                                                          and (self.low[i - 3] > self.low[i] < self.low[i + 3]) else 0 for i in range(len(self.low))]

            case 'x (Swing Close) level 1':
                self.peaks = [0 if (i < 1 or i > len(self.close) - 2) else self.close[i] if (self.close[i - 1] < self.close[i] > self.close[i + 1]) else 0 for i in range(len(self.close))]

                self.troughs = [0 if (i < 1 or i > len(self.close) - 2) else self.close[i] if (self.close[i - 1] > self.close[i] < self.close[i + 1]) else 0 for i in range(len(self.close))]

            case 'x (Swing Close) level 2':
                self.peaks = [0 if (i < 2 or i > len(self.close) - 3) else self.close[i] if (self.close[i - 1] < self.close[i] > self.close[i + 1]) and
                                                                                            (self.close[i - 2] < self.close[i] > self.close[i + 2]) else 0 for i in range(len(self.close))]

                self.troughs = [0 if (i < 2 or i > len(self.close) - 3) else self.close[i] if (self.close[i - 1] > self.close[i] < self.close[i + 1]) and
                                                                                              (self.close[i - 2] > self.close[i] < self.close[i + 2]) else 0 for i in range(len(self.close))]

            case 'x (Swing Close) level 3':
                self.peaks = [0 if (i < 3 or i > len(self.close) - 4) else self.close[i] if (self.close[i - 1] < self.close[i] > self.close[i + 1]) and
                                                                                            (self.close[i - 2] < self.close[i] > self.close[i + 2]) and (self.close[i - 3] < self.close[i] > self.close[i + 3])
                                 else 0 for i in range(len(self.close))]

                self.troughs = [0 if (i < 3 or i > len(self.close) - 4) else self.close[i] if (self.close[i - 1] > self.close[i] < self.close[i + 1]) and
                                                                                              (self.close[i - 2] > self.close[i] < self.close[i + 2]) and (self.close[i - 3] > self.close[i] < self.close[i + 3])
                                   else 0 for i in range(len(self.close))]
            case _:
                return

    def add_hist(self, time_open: [int], time_close: [int], open_price: [float], close_price: [float], high_price: [float], low_price: [float], volume_price: [str]):
        try:
            if not self.backtesting:
                while not len(self.time_open) == 0:
                    if self.time_open[0] > time_open[-1]:
                        time_open.append(self.time_open.pop(0))
                        time_close.append(self.time_close.pop(0))
                        open_price.append(self.open.pop(0))
                        close_price.append(self.close.pop(0))
                        high_price.append(self.high.pop(0))
                        low_price.append(self.low.pop(0))
                        volume_price.append(self.volume.pop(0))
                    elif self.time_open[0] == time_open[-1]:
                        time_open[-1] = self.time_open.pop(0)
                        time_close[-1] = self.time_close.pop(0)
                        open_price[-1] = self.open.pop(0)
                        close_price[-1] = self.close.pop(0)
                        high_price[-1] = self.high.pop(0)
                        low_price[-1] = self.low.pop(0)
                        volume_price[-1] = self.volume.pop(0)
                    else:
                        self.time_open.pop(0)
                        self.time_close.pop(0)
                        self.open.pop(0)
                        self.close.pop(0)
                        self.high.pop(0)
                        self.low.pop(0)
                        self.volume.pop(0)
                self.time_open = time_open
                self.open = open_price
                self.close = close_price
                self.high = high_price
                self.low = low_price
                self.volume = volume_price

            # TODO verify these are correct
            self.close_h.append((self.open[0] + self.close[0] + self.low[0] + self.high[0]) / 4)
            self.open_h.append((self.close[0] + self.open[0]) / 2)
            self.high_h.append(self.high[0])
            self.low_h.append(self.low[0])
            for i in range(1, len(self.close)):
                self.open_h.append((self.open_h[i-1] + self.close_h[i-1]) / 2)
                self.close_h.append((self.open[i] + self.close[i] + self.low[i] + self.high[i]) / 4)
                self.high_h.append(max(self.high[i], self.open_h[i], self.close_h[i]))
                self.low_h.append(min(self.low[i], self.open_h[i], self.close_h[i]))
            self.add_hist_complete = 1
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.error(f'{__name__}() - Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def handle_socket_message(self, msg):
        # TODO look at refactoring this
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
                            self.signal_queue.put([self.symbol, self.order_precision, self.coin_precision, self.tick_size, trade_direction, self.index, stop_loss_val, take_profit_val])
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
                        self.signal_queue.put([self.symbol, self.order_precision, self.coin_precision, self.tick_size, trade_direction, self.index, stop_loss_val, take_profit_val])
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f"handle_socket_message() - Error in handling of {self.symbol} websocket flagging for reconnection, msg: {msg}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")
            self.socket_failed = True

    @log.catch_errors()
    def make_decision(self):
        self.update_indicators()
        ##Initialize vars:
        trade_direction = -99  ## Short (0), Long (1)
        stop_loss_val = -99
        take_profit_val = -99
        
        match self.strategy:
            case 'stoch_rsi_macd':
                trade_direction = TS.stoch_rsi_macd(trade_direction, self.indicators["fastd"]["values"], self.indicators["fastk"]["values"],
                                                  self.indicators["RSI"]["values"], self.indicators["MACD"]["values"],
                                                  self.indicators["macdsignal"]["values"], self.current_index)
            case 'triple_ema_stochastic_rsi_atr':
                trade_direction = TS.triple_ema_stochastic_rsi_atr(self.close, trade_direction, self.indicators["EMA_L"]["values"],
                                                               self.indicators["EMA_M"]["values"], self.indicators["EMA_S"]["values"],
                                                               self.indicators["fastd"]["values"], self.indicators["fastk"]["values"], self.current_index)
            case 'triple_ema':
                trade_direction = TS.triple_ema(trade_direction, self.indicators["EMA_S"]["values"],
                                                self.indicators["EMA_M"]["values"], self.indicators["EMA_L"]["values"], self.current_index)
            case 'breakout':
                trade_direction = TS.breakout(trade_direction, self.close, self.volume, self.indicators["max Close % change"]["values"],
                                              self.indicators["min Close % change"]["values"], self.indicators["max Volume"]["values"],
                                              self.current_index)
            case 'stoch_bb':
                trade_direction = TS.stoch_bb(trade_direction, self.indicators["fastd"]["values"],
                                              self.indicators["fastk"]["values"], self.indicators["percent_B"]["values"], self.current_index)
            case 'golden_cross':
                trade_direction = TS.golden_cross(trade_direction, self.close, self.indicators["EMA_L"]["values"],
                                                  self.indicators["EMA_M"]["values"], self.indicators["EMA_S"]["values"],
                                                  self.indicators["RSI"]["values"], self.current_index)
            case 'candle_wick':
                trade_direction = TS.candle_wick(trade_direction, self.close, self.open, self.high, self.low, self.current_index)
            case 'fib_macd':
                trade_direction = TS.fib_macd(trade_direction, self.close, self.open, self.high, self.low, self.indicators["MACD_signal"]["values"],
                                              self.indicators["MACD"]["values"], self.indicators["EMA"]["values"], self.current_index)
            case 'ema_cross':
                trade_direction = TS.ema_cross(trade_direction, self.indicators["EMA_S"]["values"],
                                               self.indicators["EMA_L"]["values"], self.current_index)
            case 'heikin_ashi_ema2':
                trade_direction, _ = TS.heikin_ashi_ema2(self.open_h, self.high_h, self.low_h, self.close_h, trade_direction,
                                                         -99, 0, self.indicators["fastd"]["values"], self.indicators["fastk"]["values"],
                                                         self.indicators["EMA"]["values"], self.current_index)
            case 'heikin_ashi_ema':
                trade_direction, _ = TS.heikin_ashi_ema(self.open_h, self.close_h, trade_direction, -99, 0,
                                                        self.indicators["fastd"]["values"],
                                                        self.indicators["fastk"]["values"],
                                                        self.indicators["EMA"]["values"], self.current_index)
            case "ema_crossover":
                trade_direction = TS.ema_crossover(trade_direction, self.current_index,
                                                   self.indicators["ema_short"]["values"],
                                                   self.indicators["ema_long"]["values"])

        if trade_direction != -99 and self.tp_sl_choice not in custom_tp_sl_functions:
            self.update_tp_sl()
            stop_loss_val = -99  # the margin of increase/decrease that would stop us out/ be our take profit, NOT the price target.
            take_profit_val = -99  # That is worked out later by adding or subtracting:
            stop_loss_val, take_profit_val = TS.set_sl_tp(self.stop_loss_val, self.take_profit_val, self.peaks,
                                                          self.troughs, self.close, self.high, self.low, trade_direction,
                                                          self.sl_mult,
                                                          self.tp_mult, self.tp_sl_choice,
                                                          self.current_index)

        return trade_direction, stop_loss_val, take_profit_val

    @log.catch_errors()
    def check_close_pos(self, trade_direction):
        close_pos = 0
        match self.strategy:
            case 'heikin_ashi_ema2':
                _, close_pos = TS.heikin_ashi_ema2(self.open_h, self.high_h, self.low_h,
                                                   self.close_h, -99, trade_direction,
                                                   0, self.indicators["fastd"]["values"], self.indicators["fastk"]["values"],
                                                   self.indicators["EMA"]["values"], self.current_index)
            case 'heikin_ashi_ema':
                _, close_pos = TS.heikin_ashi_ema(self.open_h, self.close_h, -99, trade_direction, 0,
                                                  self.indicators["fastd"]["values"], self.indicators["fastk"]["values"], self.indicators["EMA"]["values"], self.current_index)
            case _:
                pass
        return close_pos

    def remove_last_candle(self):
        self.time_open.pop(-1)
        self.close.pop(-1)
        self.volume.pop(-1)
        self.high.pop(-1)
        self.low.pop(-1)
        self.open.pop(-1)
        self.open_h.pop(-1)
        self.close_h.pop(-1)
        self.high_h.pop(-1)
        self.low_h.pop(-1)

    def remove_first_candle(self):
        self.time_open.pop(0)
        self.close.pop(0)
        self.volume.pop(0)
        self.high.pop(0)
        self.low.pop(0)
        self.open.pop(0)
        self.open_h.pop(0)
        self.close_h.pop(0)
        self.low_h.pop(0)
        self.high_h.pop(0)

    def consume_new_candle(self, payload):
        self.time_open.append(int(payload['T']))  # TODO fix this, this is the time close
        self.close.append(float(payload['c']))
        self.volume.append(float(payload['q']))
        self.high.append(float(payload['h']))
        self.low.append(float(payload['l']))
        self.open.append(float(payload['o']))

    def generate_new_heikin_ashi(self):
        self.open_h.append((self.open_h[-1] + self.close_h[-1]) / 2)
        self.close_h.append((self.open[-1] + self.close[-1] + self.low[-1] + self.high[-1]) / 4)
        self.high_h.append(max(self.high[-1], self.open_h[-1], self.close_h[-1]))
        self.low_h.append(min(self.low[-1], self.open_h[-1], self.close_h[-1]))
