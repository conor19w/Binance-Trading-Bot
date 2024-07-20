from logger import *
from trading_config import *


def usdt_sl_tp(options):
    q = round(1 / options['position_size'], 6)
    take_profit_val = tp_mult * q
    stop_loss_val = sl_mult * q
    return stop_loss_val, take_profit_val


def candle_wick(trade_direction, close_price, open_price, high_price, low_price, current_index):
    if close_price[current_index - 4] < close_price[current_index - 3] < close_price[current_index - 2] and close_price[current_index - 1] < open_price[current_index - 1] and (
            high_price[current_index - 1] - open_price[current_index - 1] + close_price[current_index - 1] - low_price[current_index - 1]) > 10 * (open_price[current_index - 1] - close_price[current_index - 1]) and close_price[current_index] < close_price[current_index - 1]:
        ##3 green candles followed by a red candle with a huge wick
        trade_direction = 0
    elif close_price[current_index - 4] > close_price[current_index - 3] > close_price[current_index - 2] and close_price[current_index - 1] > open_price[current_index - 1] and (
            high_price[current_index - 1] - close_price[current_index - 1] + open_price[current_index - 1] - low_price[current_index - 1]) > 10 * (close_price[current_index - 1] - open_price[current_index - 1]) and close_price[current_index] > close_price[current_index - 1]:
        ##3 red candles followed by a green candle with a huge wick
        trade_direction = 1
    return trade_direction


def fib_macd(trade_direction, close_price, open_price, high_price, low_price, macd_signal, macd, ema_200, current_index):
    period = 100  ##Record peaks and troughs in last period timesteps

    close_price_peaks = []  ##Store peak values
    location_peaks = []  ##store current_index of peak value , used for debugging
    close_price_troughs = []  ##store trough values
    location_troughs = []  ##store current_index of peak trough , used for debugging
    #####################Find peaks & troughs in close_price ##############################
    for i in range(current_index - period, current_index - 2):
        if high_price[i] > high_price[i - 1] and high_price[i] > high_price[i + 1] and high_price[i] > high_price[i - 2] and high_price[i] > high_price[i + 2]:
            ##Weve found a peak:
            close_price_peaks.append(high_price[i])
            location_peaks.append(i)
        elif low_price[i] < low_price[i - 1] and low_price[i] < low_price[i + 1] and low_price[i] < low_price[i - 2] and low_price[i] < low_price[i + 2]:
            ##Weve found a trough:
            close_price_troughs.append(low_price[i])
            location_troughs.append(i)

    trend = -99  ##indicate the direction of trend
    if close_price[current_index] < ema_200[current_index]:
        trend = 0
    elif close_price[current_index] > ema_200[current_index]:
        trend = 1
    max_pos = -99
    min_pos = -99
    if trend == 1:
        ##Find the start and end of the pullback
        max_close_price = -9999999
        min_close_price = 9999999
        max_flag = 0
        min_flag = 0
        for i in range(len(close_price_peaks) - 1, -1, -1):
            if close_price_peaks[i] > max_close_price and max_flag < 2:
                max_close_price = close_price_peaks[i]
                max_pos = location_peaks[i]
                max_flag = 0
            elif max_flag == 2:
                break
            else:
                max_flag += 1
        ##Find the start and end of the pullback
        startpoint = -99
        for i in range(len(location_troughs)):
            if location_troughs[i] < max_pos:
                startpoint = i
            else:
                break
        for i in range(startpoint, -1, -1):
            if close_price_troughs[i] < min_close_price and min_flag < 2:
                min_close_price = close_price_troughs[i]
                min_pos = location_troughs[i]
                min_flag = 0
            elif min_flag == 2:
                break
            else:
                min_flag += 1
        ##fibonacci levels
        fib_level_0 = max_close_price
        fib_level_1 = max_close_price - .236 * (max_close_price - min_close_price)
        fib_level_2 = max_close_price - .382 * (max_close_price - min_close_price)
        fib_level_3 = max_close_price - .5 * (max_close_price - min_close_price)
        fib_level_4 = max_close_price - .618 * (max_close_price - min_close_price)
        fib_level_5 = max_close_price - .786 * (max_close_price - min_close_price)
        fib_level_6 = min_close_price

        ##Take profit targets, Don't think this is configured properly so maybe have a look at fibonacci extensions and fix here, Right hand side is ment to be the corresponding extension level
        # fib_retracement_level_1 = fib_level_0 + 1.236 * (max_close_price - min_close_price) - close_price[
        #     current_index]  ##target max_close_price+1.236*(max_close_price - min_close_price)
        # fib_retracement_level_2 = fib_level_0 + 1.382 * (max_close_price - min_close_price) - close_price[current_index]
        # fib_retracement_level_3 = fib_level_0 + 1.5 * (max_close_price - min_close_price) - close_price[current_index]
        # fib_retracement_level_4 = fib_level_0 + 1.618 * (max_close_price - min_close_price) - close_price[current_index]
        # fib_retracement_level_5 = fib_level_0 + 1.786 * (max_close_price - min_close_price) - close_price[current_index]
        # fib_retracement_level_6 = fib_level_0 + 2 * (max_close_price - min_close_price) - close_price[current_index]

        ## fib_level_0>low_price[current_index - 2]>fib_level_1: recent low was between two of our levels
        ## close_price[current_index - 3]>fib_level_1 and close_price[current_index - 4]>fib_level_1 and close_price[-6]>fib_level_1: Ensure the bottom level was respected  ie. no recent close below it
        if fib_level_0 > low_price[current_index - 2] > fib_level_1 and close_price[current_index - 3] > fib_level_1 and close_price[current_index - 4] > fib_level_1 and close_price[
            -6] > fib_level_1:
            if close_price[current_index - 2] < open_price[current_index - 2] < close_price[current_index - 1] < close_price[current_index] and (
                    (macd_signal[current_index - 1] < macd[current_index - 1] or macd_signal[current_index - 2] < macd[current_index - 2]) and macd_signal[current_index] > macd[
                current_index]):  ##Bullish Engulfing Candle and cross up on macd
                # print("level 1")
                trade_direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_1  ##target the corresponding extensiuon level
                # stop_loss_val = close_price[current_index] - fib_level_1 * 1.0001  ##stoploss below bottom level with a bit extra
        elif fib_level_1 > low_price[current_index - 2] > fib_level_2 and close_price[current_index - 3] > fib_level_2 and close_price[current_index - 4] > fib_level_2 and close_price[
            -6] > fib_level_2:
            if close_price[current_index - 2] < open_price[current_index - 2] < close_price[current_index - 1] < close_price[current_index] and (
                    (macd_signal[current_index - 1] < macd[current_index - 1] or macd_signal[current_index - 2] < macd[current_index - 2]) and macd_signal[current_index] > macd[
                current_index]):  ##Bullish Engulfing Candle and cross up on macd
                # print("level 1")
                trade_direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_2
                # stop_loss_val = close_price[current_index] - fib_level_2 * 1.0001

        elif fib_level_2 > low_price[current_index - 1] > fib_level_3 and close_price[current_index - 2] > fib_level_3 and close_price[current_index - 3] > fib_level_3 and close_price[
            current_index - 4] > fib_level_3:
            if close_price[current_index - 1] < open_price[current_index - 1] < close_price[current_index] < close_price[current_index] and (
                    (macd_signal[current_index - 1] < macd[current_index - 1] or macd_signal[current_index - 2] < macd[current_index - 2]) and macd_signal[current_index] > macd[
                current_index]):  ##Bullish Engulfing Candle and cross up on macd
                # print("level 2")
                trade_direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_3
                # stop_loss_val = close_price[current_index] - fib_level_3 * 1.0001

        elif fib_level_3 > low_price[current_index - 1] > fib_level_4 and close_price[current_index - 2] > fib_level_4 and close_price[current_index - 3] > fib_level_4 and close_price[
            current_index - 4] > fib_level_4:
            if close_price[current_index - 1] < open_price[current_index - 1] < close_price[current_index] < close_price[current_index] and (
                    (macd_signal[current_index - 1] < macd[current_index - 1] or macd_signal[current_index - 2] < macd[current_index - 2]) and macd_signal[current_index] > macd[
                current_index]):  ##Bullish Engulfing Candle and cross up on macd
                # print("level 3")
                trade_direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_4
                # stop_loss_val = close_price[current_index] - fib_level_4 * 1.0001
        elif fib_level_4 > low_price[current_index - 1] > fib_level_5 and close_price[current_index - 2] > fib_level_5 and close_price[current_index - 3] > fib_level_5 and close_price[
            current_index - 4] > fib_level_5:
            if close_price[current_index - 1] < open_price[current_index - 1] < close_price[current_index] < close_price[current_index] and (
                    (macd_signal[current_index - 1] < macd[current_index - 1] or macd_signal[current_index - 2] < macd[current_index - 2]) and macd_signal[current_index] > macd[
                current_index]):  ##Bullish Engulfing Candle and cross up on macd
                # print("level 4")
                trade_direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_5
                # stop_loss_val = close_price[current_index] - fib_level_5 * 1.0001
        elif fib_level_5 > low_price[current_index - 1] > fib_level_6 and close_price[current_index - 2] > fib_level_6 and close_price[current_index - 3] > fib_level_6 and close_price[
            current_index - 4] > fib_level_6:
            if close_price[current_index - 1] < open_price[current_index - 1] < close_price[current_index] < close_price[current_index] and (
                    (macd_signal[current_index - 1] < macd[current_index - 1] or macd_signal[current_index - 2] < macd[current_index - 2]) and macd_signal[current_index] > macd[
                current_index]):  ##Bullish Engulfing Candle and cross up on macd
                # print("level 5")
                trade_direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_6
                # stop_loss_val = close_price[current_index] - fib_level_6 * 1.0001

    elif trend == 0:
        ##Find the start and end of the pullback
        max_close_price = -9999999
        min_close_price = 9999999
        max_flag = 0
        min_flag = 0
        for i in range(len(close_price_troughs) - 1, -1, -1):
            if close_price_troughs[i] < min_close_price and min_flag < 2:
                min_close_price = close_price_troughs[i]
                min_pos = location_troughs[i]
                min_flag = 0
            elif min_flag == 2:
                break
            else:
                min_flag += 1

        ##Find the start and end of the pullback
        startpoint = -99
        for i in range(len(location_peaks)):
            if location_peaks[i] < min_pos:
                startpoint = i
            else:
                break
        for i in range(startpoint, -1, -1):
            if close_price_peaks[i] > max_close_price and max_flag < 2:
                max_close_price = close_price_peaks[i]
                max_pos = location_peaks[i]
                max_flag = 0
            elif max_flag == 2:
                break
            else:
                max_flag += 1
        ##fibonacci levels
        fib_level_0 = min_close_price
        fib_level_1 = min_close_price + .236 * (max_close_price - min_close_price)
        fib_level_2 = min_close_price + .382 * (max_close_price - min_close_price)
        fib_level_3 = min_close_price + .5 * (max_close_price - min_close_price)
        fib_level_4 = min_close_price + .618 * (max_close_price - min_close_price)
        fib_level_5 = min_close_price + .786 * (max_close_price - min_close_price)
        fib_level_6 = max_close_price

        ##Take profit targets, Don't think this is configured properly so maybe have a look at fibonacci extensions and fix here, Right hand side is ment to be the corresponding extension level
        # fib_retracement_level_1 = close_price[current_index] - (fib_level_0 + 1.236 * (max_close_price - min_close_price))
        # fib_retracement_level_2 = close_price[current_index] - (fib_level_0 + 1.382 * (max_close_price - min_close_price))
        # fib_retracement_level_3 = close_price[current_index] - (fib_level_0 + 1.5 * (max_close_price - min_close_price))
        # fib_retracement_level_4 = close_price[current_index] - (fib_level_0 + 1.618 * (max_close_price - min_close_price))
        # fib_retracement_level_5 = close_price[current_index] - (fib_level_0 + 1.786 * (max_close_price - min_close_price))
        # fib_retracement_level_6 = close_price[current_index] - (fib_level_0 + 2 * (max_close_price - min_close_price))

        ## fib_level_0 < high_price[current_index - 2] < fib_level_1: recent low was between two of our levels
        ## close_price[current_index - 3] < fib_level_1 and close_price[current_index - 4] < fib_level_1 and close_price[-6] < fib_level_1: Ensure the Top level was respected, ie no recent close above it
        if fib_level_0 < high_price[current_index - 2] < fib_level_1 and close_price[current_index - 3] < fib_level_1 and close_price[current_index - 4] < fib_level_1 and close_price[
            -6] < fib_level_1:
            if close_price[current_index - 2] > open_price[current_index - 2] > close_price[current_index - 1] > close_price[current_index] and (
                    (macd_signal[current_index - 1] > macd[current_index - 1] or macd_signal[current_index - 2] > macd[current_index - 2]) and macd_signal[current_index] < macd[
                current_index]):  ##Bearish Engulfing Candle and cross down on macd
                # print("level 1")
                trade_direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_1  ##target corresponding extension level
                # stop_loss_val = fib_level_1 * 1.0001 - close_price[current_index]  ##stoploss above Top level with a bit extra
        elif fib_level_1 < high_price[current_index - 2] < fib_level_2 and close_price[current_index - 3] < fib_level_2 and close_price[current_index - 4] < fib_level_2 and close_price[
            -6] < fib_level_2:
            if close_price[current_index - 2] > open_price[current_index - 2] > close_price[current_index - 1] > close_price[current_index] and (
                    (macd_signal[current_index - 1] > macd[current_index - 1] or macd_signal[current_index - 2] > macd[current_index - 2]) and macd_signal[current_index] < macd[
                current_index]):  ##Bearish Engulfing Candle and cross down on macd
                # print("level 1")
                trade_direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_2
                # stop_loss_val = fib_level_2 * 1.0001 - close_price[current_index]
        elif fib_level_2 < high_price[current_index - 2] < fib_level_3 and close_price[current_index - 3] < fib_level_3 and close_price[current_index - 4] < fib_level_3 and close_price[
            -6] < fib_level_3:
            if close_price[current_index - 2] > open_price[current_index - 2] > close_price[current_index - 1] > close_price[current_index] and (
                    (macd_signal[current_index - 1] > macd[current_index - 1] or macd_signal[current_index - 2] > macd[current_index - 2]) and macd_signal[current_index] < macd[
                current_index]):  ##Bearish Engulfing Candle and cross down on macd
                # print("level 1")
                trade_direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_3
                # stop_loss_val = fib_level_3 * 1.0001 - close_price[current_index]
        elif fib_level_3 < high_price[current_index - 2] < fib_level_4 and close_price[current_index - 3] < fib_level_4 and close_price[current_index - 4] < fib_level_4 and close_price[
            -6] < fib_level_4:
            if close_price[current_index - 2] > open_price[current_index - 2] > close_price[current_index - 1] > close_price[current_index] and (
                    (macd_signal[current_index - 1] > macd[current_index - 1] or macd_signal[current_index - 2] > macd[current_index - 2]) and macd_signal[current_index] < macd[
                current_index]):  ##Bearish Engulfing Candle and cross down on macd
                # print("level 1")
                trade_direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_4
                # stop_loss_val = fib_level_4 * 1.0001 - close_price[current_index]
        elif fib_level_4 < high_price[current_index - 2] < fib_level_5 and close_price[current_index - 3] < fib_level_5 and close_price[current_index - 4] < fib_level_5 and close_price[
            -6] < fib_level_5:
            if close_price[current_index - 2] > open_price[current_index - 2] > close_price[current_index - 1] > close_price[current_index] and (
                    (macd_signal[current_index - 1] > macd[current_index - 1] or macd_signal[current_index - 2] > macd[current_index - 2]) and macd_signal[current_index] < macd[
                current_index]):  ##Bearish Engulfing Candle and cross down on macd
                # print("level 1")
                trade_direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_5
                # stop_loss_val = fib_level_5 * 1.0001 - close_price[current_index]
        elif fib_level_5 < high_price[current_index - 2] < fib_level_6 and close_price[current_index - 3] < fib_level_6 and close_price[current_index - 4] < fib_level_6 and close_price[
            -6] < fib_level_6:
            if close_price[current_index - 2] > open_price[current_index - 2] > close_price[current_index - 1] > close_price[current_index] and (
                    (macd_signal[current_index - 1] > macd[current_index - 1] or macd_signal[current_index - 2] > macd[current_index - 2]) and macd_signal[current_index] < macd[
                current_index]):  ##Bearish Engulfing Candle and cross down on macd
                # print("level 1")
                trade_direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_6
                # stop_loss_val = fib_level_6 * 1.0001 - close_price[current_index]

    return trade_direction #, stop_loss_val, take_profit_val


def golden_cross(trade_direction, close_price, ema_100, ema_50, ema_20, rsi, current_index):
    if close_price[current_index] > ema_100[current_index] and rsi[current_index] > 50:
        ##looking for long entries
        if (ema_20[current_index - 1] < ema_50[current_index - 1] and ema_20[current_index] > ema_50[current_index]) or (ema_20[current_index - 2] < ema_50[current_index - 2] and ema_20[current_index] > ema_50[current_index]) or (
                ema_20[current_index - 3] < ema_50[current_index - 3] and ema_20[current_index] > ema_50[current_index]):
            ##Cross up occured
            trade_direction = 1  ##buy
    elif close_price[current_index] < ema_100[current_index] and rsi[current_index] < 50:
        ##looking for short entries
        if (ema_20[current_index - 1] > ema_50[current_index - 1] and ema_20[current_index] < ema_50[current_index]) or (ema_20[current_index - 2] > ema_50[current_index - 2] and ema_20[current_index] < ema_50[current_index]) or (
                ema_20[current_index - 3] > ema_50[current_index - 3] and ema_20[current_index] < ema_50[current_index]):
            ##Cross up occured
            trade_direction = 0  ##Sell

    return trade_direction


def stoch_rsi_macd(trade_direction, fastd, fastk, rsi, macd, macdsignal, current_index):

    if ((fastd[current_index] < 20 and fastk[current_index] < 20 and rsi[current_index] > 50 and macd[current_index] > macdsignal[current_index] and macd[current_index - 1] < macdsignal[
        current_index - 1]) or
            (fastd[current_index - 1] < 20 and fastk[current_index - 1] < 20 and rsi[current_index] > 50 and macd[current_index] > macdsignal[current_index] and macd[current_index - 2] < macdsignal[
                current_index - 2] and fastd[current_index] < 80 and fastk[current_index] < 80) or
            (fastd[current_index - 2] < 20 and fastk[current_index - 2] < 20 and rsi[current_index] > 50 and macd[current_index] > macdsignal[current_index] and macd[current_index - 1] < macdsignal[
                current_index - 1] and fastd[current_index] < 80 and fastk[current_index] < 80) or
            (fastd[current_index - 3] < 20 and fastk[current_index - 3] < 20 and rsi[current_index] > 50 and macd[current_index] > macdsignal[current_index] and macd[current_index - 2] < macdsignal[
                current_index - 2] and fastd[current_index] < 80 and fastk[current_index] < 80)):
        trade_direction = 1
    elif ((fastd[current_index] > 80 and fastk[current_index] > 80 and rsi[current_index] < 50 and macd[current_index] < macdsignal[current_index] and macd[current_index - 1] > macdsignal[
        current_index - 1]) or
          (fastd[current_index - 1] > 80 and fastk[current_index - 1] > 80 and rsi[current_index] < 50 and macd[current_index] < macdsignal[current_index] and macd[current_index - 2] > macdsignal[
              current_index - 2] and fastd[current_index] > 20 and fastk[current_index] > 20) or
          (fastd[current_index - 2] > 80 and fastk[current_index - 2] > 80 and rsi[current_index] < 50 and macd[current_index] < macdsignal[current_index] and macd[current_index - 1] > macdsignal[
              current_index - 1] and fastd[current_index] > 20 and fastk[current_index] > 20) or
          (fastd[current_index - 3] > 80 and fastk[current_index - 3] > 80 and rsi[current_index] < 50 and macd[current_index] < macdsignal[current_index] and macd[current_index - 2] > macdsignal[
              current_index - 2] and fastd[current_index] > 20 and fastk[current_index] > 20)):
        trade_direction = 0
    return trade_direction


##############################################################################################################################
##############################################################################################################################
##############################################################################################################################


def triple_ema(trade_direction, ema_3, ema_6, ema_9, current_index):

    if ema_3[current_index - 4] > ema_6[current_index - 4] and ema_3[current_index - 4] > ema_9[current_index - 4] \
            and ema_3[current_index - 3] > ema_6[current_index - 3] and ema_3[current_index - 3] > ema_9[current_index - 3] \
            and ema_3[current_index - 2] > ema_6[current_index - 2] and ema_3[current_index - 2] > ema_9[current_index - 2] \
            and ema_3[current_index - 1] > ema_6[current_index - 1] and ema_3[current_index - 1] > ema_9[current_index - 1] \
            and ema_3[current_index] < ema_6[current_index] and ema_3[current_index] < ema_9[current_index]:
        trade_direction = 0
    if ema_3[current_index - 4] < ema_6[current_index - 4] and ema_3[current_index - 4] < ema_9[current_index - 4] \
            and ema_3[current_index - 3] < ema_6[current_index - 3] and ema_3[current_index - 3] < ema_9[current_index - 3] \
            and ema_3[current_index - 2] < ema_6[current_index - 2] and ema_3[current_index - 2] < ema_9[current_index - 2] \
            and ema_3[current_index - 1] < ema_6[current_index - 1] and ema_3[current_index - 1] < ema_9[current_index - 1] \
            and ema_3[current_index] > ema_6[current_index] and ema_3[current_index] > ema_9[current_index]:
        trade_direction = 1
    return trade_direction


def heikin_ashi_ema2(open_price_h, high_price_h, low_price_h, close_price_h, trade_direction, current_position, close_price_pos, fastd, fastk, ema_200, current_index):
    if current_position == -99:
        trade_direction = -99
        short_threshold = .7  ##If rsi falls below this don't open any shorts
        long_threshold = .3  ##If rsi goes above this don't open any longs

        ##Check Most recent Candles to see if we got a cross down and we are below 200EMA
        if fastk[current_index - 1] > fastd[current_index - 1] and fastk[current_index] < fastd[current_index] and close_price_h[current_index] < ema_200[current_index]:
            for i in range(10, 2, -1):
                ##Find Bearish Meta Candle
                if close_price_h[-i] < open_price_h[-i] and open_price_h[-i] == high_price_h[-i]:
                    for j in range(i, 2, -1):
                        ##Find cross below ema_200
                        if close_price_h[-j] > ema_200[-j] and close_price_h[-j + 1] < ema_200[-j + 1] and open_price_h[-j] > close_price_h[
                            -j]:
                            ##Now look for Overbought signal
                            flag = 1
                            for r in range(j, 0, -1):
                                if fastd[-r] < short_threshold or fastk[-r] < short_threshold:
                                    flag = 0
                            if flag:
                                ##open_price a trade
                                trade_direction = 0
                                break  ##break out of current loop
                    if trade_direction == 0:
                        break
        ##Check Most recent Candles to see if we got a cross up and we are above 200EMA
        elif fastk[current_index - 1] < fastd[current_index - 1] and fastk[current_index] > fastd[current_index] and close_price_h[current_index] > ema_200[current_index]:
            for i in range(10, 2, -1):
                ##Find Bullish Meta Candle
                if close_price_h[-i] > open_price_h[-i] and open_price_h[-i] == low_price_h[-i]:
                    for j in range(i, 2, -1):
                        ##Find cross above ema_200
                        if close_price_h[-j] < ema_200[-j] and close_price_h[-j + 1] > ema_200[-j + 1] and open_price_h[-j] < close_price_h[
                            -j]:
                            ##Now look for OverSold signal
                            flag = 1
                            for r in range(j, 0, -1):
                                if fastd[-r] > long_threshold or fastk[-r] > long_threshold:
                                    flag = 0
                            if flag:
                                ##open_price a trade
                                trade_direction = 1
                                break  ##break out of current loop
                    if trade_direction == 1:
                        break

    elif current_position == 1 and close_price_h[current_index] < open_price_h[current_index]:
        close_price_pos = 1
    elif current_position == 0 and close_price_h[current_index] > open_price_h[current_index]:
        close_price_pos = 1
    else:
        close_price_pos = 0
    return trade_direction, close_price_pos


def heikin_ashi_ema(open_price_h, close_price_h, trade_direction, current_position, close_price_pos, fastd, fastk, ema_200, current_index):
    if current_position == -99:
        trade_direction = -99

        short_threshold = .8  ##If rsi falls below this don't open any shorts
        long_threshold = .2  ##If rsi goes above this don't open any longs
        ##look for shorts
        if fastk[current_index] > short_threshold and fastd[current_index] > short_threshold:
            ##Check last 10 candles, a bit overkill
            for i in range(10, 2, -1):
                if fastd[-i] >= .8 and fastk[-i] >= .8:
                    ##both oscillators in the overbought position
                    for j in range(i, 2, -1):
                        ##now check if we get a cross on the in the next few candles
                        if fastk[-j] > fastd[-j] and fastk[-j + 1] < fastd[-j + 1]:
                            flag = 1
                            for r in range(j, 2, -1):
                                ##we passed the threshold
                                if fastk[r] < short_threshold or fastd[r] < short_threshold:
                                    flag = 0
                                    break
                            ##Cross down on the k and d lines, look for the candle stick pattern
                            if close_price_h[current_index - 2] > ema_200[current_index - 2] and close_price_h[current_index - 1] < ema_200[current_index - 1] and flag:
                                ##closed below 200EMA
                                if close_price_h[current_index] < open_price_h[current_index]:
                                    ##bearish candle
                                    ##all conditions met so open a short
                                    trade_direction = 0
                                else:
                                    break  ##break out of the current for loop
                            else:
                                break  ##break out of the current for loop
        ##Look for longs
        elif fastk[current_index] < long_threshold and fastd[current_index] < long_threshold:
            ##Check last 10 candles, a bit overkill
            for i in range(10, 2, -1):
                if fastd[-i] <= .2 and fastk[-i] <= .2:
                    ##both oscillators in the overbought position
                    for j in range(i, 2, -1):
                        ##now check if we get a cross on the in the next few candles
                        if fastk[-j] < fastd[-j] and fastk[-j + 1] > fastd[-j + 1] and fastk[current_index] < long_threshold and \
                                fastd[current_index] < long_threshold:
                            flag = 1
                            for r in range(j, 2, -1):
                                ##we passed the threshold
                                if fastk[r] > long_threshold or fastd[r] > long_threshold:
                                    flag = 0
                                    break
                            ##Cross up on the k and d lines, look for the candle stick pattern
                            ##candle crosses 200EMA
                            if close_price_h[current_index - 2] < ema_200[current_index - 2] and close_price_h[current_index - 1] > ema_200[current_index - 1] and flag:
                                ##closed above 200EMA
                                if close_price_h[current_index] > open_price_h[current_index]:
                                    ##bullish candle
                                    ##all conditions met so open a long
                                    trade_direction = 1
                                else:
                                    break  ##break out of the current for loop
                            else:
                                break  ##break out of the current for loop
    elif current_position == 1 and close_price_h[current_index] < open_price_h[current_index]:
        close_price_pos = 1
    elif current_position == 0 and close_price_h[current_index] > open_price_h[current_index]:
        close_price_pos = 1
    else:
        close_price_pos = 0
    return trade_direction, close_price_pos


def triple_ema_stochastic_rsi_atr(close_price, trade_direction, ema_50, ema_14, ema_8, fastd, fastk, current_index):
    ##buy signal
    if (close_price[current_index] > ema_8[current_index] > ema_14[current_index] > ema_50[current_index]) and \
            ((fastk[current_index] > fastd[current_index]) and (fastk[current_index - 1] < fastd[current_index - 1])):  # and (fastk[current_index]<80 and fastd[current_index]<80):
        trade_direction = 1
    elif (close_price[current_index] < ema_8[current_index] < ema_14[current_index] < ema_50[current_index]) and\
            ((fastk[current_index] < fastd[current_index]) and (fastk[current_index - 1] > fastd[current_index - 1])):  # and (fastk[current_index]>20 and fastd[current_index]>20):
        trade_direction = 0

    return trade_direction

##############################################################################################################################
##############################################################################################################################
##############################################################################################################################


# def rsiStochEMA(trade_direction, close_price, high_price, low_price, signal1, currentPos, SL, TP, TP_choice, SL_choice):
#     period = 60
#     close_priceS = pd.Series(close_price)
#     close_price = np.array(close_price)
#     # high_price = np.array(high_price)
#     # low_price = np.array(low_price)
#     fastk = np.array(stoch_signal(pd.Series(high_price), pd.Series(low_price), pd.Series(close_price)))
#     fastd = np.array(stoch(pd.Series(high_price), pd.Series(low_price), pd.Series(close_price)))
#     rsi = np.array(rsi(close_priceS))
#     ema_200 = np.array(ema_indicator(close_priceS, window=200))
#     peaks_rsi = []
#     corresponding_close_price_peaks = []
#     location_peaks = []
#     troughs_rsi = []
#     corresponding_close_price_troughs = []
#     location_troughs = []
#     #####################Find peaks & troughs in rsi ##############################
#     for i in range(len(rsi) - period, len(rsi) - 2):
#         if rsi[i] > rsi[i - 1] and rsi[i] > rsi[i + 1] and rsi[i] > rsi[i - 2] and rsi[i] > rsi[i + 2]:
#             ##Weve found a peak:
#             peaks_rsi.append(rsi[i])
#             corresponding_close_price_peaks.append(close_price[i])
#             location_peaks.append(i)
#         elif rsi[i] < rsi[i - 1] and rsi[i] < rsi[i + 1] and rsi[i] < rsi[i - 2] and rsi[i] < rsi[i + 2]:
#             ##Weve found a trough:
#             troughs_rsi.append(rsi[i])
#             corresponding_close_price_troughs.append(close_price[i])
#             location_troughs.append(i)
#     ##low_priceer high_price Price & high_priceer high_price rsi => Bearish Divergence
#     ##high_priceer low_price Price & low_priceer low rsi => Bullish Divergence
#     length = 0
#     if len(peaks_rsi) > len(troughs_rsi):
#         length = len(peaks_rsi)
#     else:
#         length = len(troughs_rsi)
#     loc1 = -99
#     loc2 = -99
#     if length != 0:
#         for i in range(length - 1):
#             if i < len(peaks_rsi):
#                 ##Check for hidden Bearish Divergence
#                 if peaks_rsi[i] < peaks_rsi[current_index] and corresponding_close_price_peaks[i] > corresponding_close_price_peaks[current_index] and \
#                         peaks_rsi[current_index] - peaks_rsi[i] > 1:
#                     for j in range(i + 1, len(peaks_rsi) - 1):
#                         if peaks_rsi[j] > peaks_rsi[i]:
#                             break
#                         elif j == len(peaks_rsi) - 2:
#                             loc1 = location_peaks[i]
#
#             if i < len(troughs_rsi):
#                 ##Check for hidden Bullish Divergence
#                 if troughs_rsi[i] > troughs_rsi[current_index] and corresponding_close_price_troughs[i] < corresponding_close_price_troughs[
#                     current_index] and troughs_rsi[i] - troughs_rsi[current_index] > 1:
#                     for j in range(i + 1, len(troughs_rsi) - 1):
#                         if troughs_rsi[j] < troughs_rsi[i]:
#                             break
#                         elif j == len(troughs_rsi) - 2:
#                             loc2 = location_troughs[i]
#         if loc1 == loc2:
#             signal1 = -99
#         elif loc1 > loc2:  # and 300-loc1<15:
#             signal1 = 0
#             # print(300-loc1)
#         else:  # 300-loc2<15:
#             # print(300-loc2)
#             signal1 = 1
#         '''else:
#             signal1=-99'''
#
#     ##Bullish Divergence
#     if signal1 == 1 and (fastk[current_index] > fastd[current_index] and (fastk[current_index - 1] < fastd[current_index - 1] or fastk[current_index - 2] < fastd[current_index - 2])) and close_price[current_index] > \
#             ema_200[current_index]:
#         trade_direction = 1
#         signal1 = -99
#
#     ##Bearish Divergence
#     elif signal1 == 0 and (fastk[current_index] < fastd[current_index] and (fastk[current_index - 1] > fastd[current_index - 1] or fastk[current_index - 2] > fastd[current_index - 2])) and close_price[current_index] < \
#             ema_200[current_index]:
#         trade_direction = 0
#         signal1 = -99
#
#     if currentPos != -99:
#         signal1 = -99
#         trade_direction = -99
#     stop_loss_val, take_profit_val = SetSLTP(-99, -99, close_price, high_price, low_price, trade_direction, SL, TP, TP_choice, SL_choice, current_index)
#     return trade_direction, signal1, stop_loss_val, take_profit_val


##############################################################################################################

def stoch_bb(trade_direction, fastd, fastk, percent_band, current_index):
    percent_band1 = percent_band[current_index]
    percent_band2 = percent_band[current_index - 1]
    percent_band3 = percent_band[current_index - 2]
    # print(percent_band)

    if fastk[current_index] < .2 and fastd[current_index] < .2 and (fastk[current_index] > fastd[current_index] and fastk[current_index - 1] < fastd[current_index - 1]) and (
            percent_band1 < 0 or percent_band2 < 0 or percent_band3 < 0):  # or percent_band3<0):# or percent_band2<.05):
        trade_direction = 1
    elif fastk[current_index] > .8 and fastd[current_index] > .8 and (fastk[current_index] < fastd[current_index] and fastk[current_index - 1] > fastd[current_index - 1]) and (
            percent_band1 > 1 or percent_band2 > 1 or percent_band3 > 1):  # or percent_band3>1):# or percent_band2>1):
        trade_direction = 0
    return trade_direction


def breakout(trade_direction, close_price, volume, max_close_price, min_close_price, max_vol, current_index):
    invert = 0  # switch shorts and longs, basically fakeout instead of breakout
    if invert:
        if close_price[current_index] >= max_close_price.iloc[current_index] and volume[current_index] >= max_vol.iloc[current_index]:
            trade_direction = 0
        elif close_price[current_index] <= min_close_price.iloc[current_index] and volume[current_index] >= max_vol.iloc[current_index]:
            trade_direction = 1
    else:
        if close_price[current_index] >= max_close_price.iloc[current_index] and volume[current_index] >= max_vol.iloc[current_index]:
            trade_direction = 1
        elif close_price[current_index] <= min_close_price.iloc[current_index] and volume[current_index] >= max_vol.iloc[current_index]:
            trade_direction = 0
    return trade_direction

def ema_crossover(trade_direction, current_index, ema_short, ema_long):
    if ema_short[current_index-1] > ema_long[current_index-1] and ema_short[current_index] < ema_long[current_index]:
        trade_direction = 0
    elif ema_short[current_index-1] < ema_long[current_index-1] and ema_short[current_index] > ema_long[current_index]:
        trade_direction = 1
    return trade_direction

# def fakeout(trade_direction, close_price, volume, high_price, low_price, SL, TP, TP_choice, SL_choice):
#     invert = 1
#     # if symbol == 'BTCUSDT' or symbol == 'ETHUSDT':
#     #    invert = 0
#     close_price = pd.Series(close_price)  # .pct_change() ##get size of bars in a percentage
#     volume = pd.Series(volume[:current_index])
#     max_close_price = close_price.iloc[:current_index].rolling(15).max()
#     min_close_price = close_price.iloc[:current_index].rolling(15).min()
#     max_vol = volume.rolling(15).max()
#     if invert:
#         if close_price.iloc[current_index] > max_close_price.iloc[current_index] and volume[current_index] < max_vol.iloc[current_index]:
#             trade_direction = 0
#         elif close_price.iloc[current_index] < min_close_price.iloc[current_index] and volume[current_index] < max_vol.iloc[current_index]:
#             trade_direction = 1
#     else:
#         if close_price.iloc[current_index] > max_close_price.iloc[current_index] and volume[current_index] < max_vol.iloc[current_index]:
#             trade_direction = 1
#         elif close_price.iloc[current_index] < min_close_price.iloc[current_index] and volume[current_index] < max_vol.iloc[current_index]:
#             trade_direction = 0
#     stop_loss_val, take_profit_val = SetSLTP(-99, -99, close_price, high_price, low_price, trade_direction, SL, TP, TP_choice, SL_choice, current_index)
#     return trade_direction, stop_loss_val, take_profit_val


def ema_cross(trade_direction, ema_short, ema_long, current_index):
    if ema_short[current_index - 4] > ema_long[current_index - 4] \
            and ema_short[current_index - 3] > ema_long[current_index - 3] \
            and ema_short[current_index - 2] > ema_long[current_index - 2] \
            and ema_short[current_index - 1] > ema_long[current_index - 1] \
            and ema_short[current_index] < ema_long[current_index]:
        trade_direction = 0

    if ema_short[current_index - 4] < ema_long[current_index - 4] \
            and ema_short[current_index - 3] < ema_long[current_index - 3] \
            and ema_short[current_index - 2] < ema_long[current_index - 2] \
            and ema_short[current_index - 1] < ema_long[current_index - 1] \
            and ema_short[current_index] > ema_long[current_index]:
        trade_direction = 1

    return trade_direction

'''def pairTrading(trade_direction,close_price1,close_price2,log=0,TPSL=0,percent_TP=0,percent_SL=0):
    new_close_price = []
    
    #multiplier = close_price1[0]/close_price2[0]
    if not log:
        multiplier = (sm.OLS(close_price1, close_price2).fit()).params[0]
        for i in range(len(close_price1)current_index - 20,len(close_price1)):
            new_close_price.append(close_price1[i]-multiplier*close_price2[i])
    else:
        log_close1 = []
        log_close2 = []
        for i in range(len(close_price1)current_index - 20,len(close_price1)):
            log_close1.append(math.log(close_price1[i]))
            log_close2.append(math.log(close_price2[i]))
        multiplier = (sm.OLS(log_close1, log_close2).fit()).params[0]
        for i in range(len(log_close1)):
            new_close_price.append(log_close1[i] - multiplier * log_close2[i])
    BB =np.array(bollinger_pband(pd.Series(new_close_price),window_dev=3))
    #BB1 = np.array(bollinger_hband(pd.Series(new_close_price),window_dev=3))
    #BB2 = np.array(bollinger_lband(pd.Series(new_close_price), window_dev=3))
    #SMA20 = np.array(bollinger_mavg(pd.Series(new_close_price)))
    #print(BB[current_index])
    if BB[current_index]>1:
        trade_direction = [0,1]  # [1,0]
        
    elif BB[current_index]<0:
        trade_direction = [1,0] # [0,1]
        
    return trade_direction,[9,9] #,close_price1_TP,close_price2_TP,close_price1_SL,close_price2_SL


def pairTrading_Crossover(trade_direction, close_price1, close_price2, current_position, percent_SL=0):
    new_close_price = []
    close_price_pos=0
    close_price1_SL = 0
    close_price2_SL = 0
    multiplier = (sm.OLS(close_price1, close_price2).fit()).params[0]
    for i in range(len(close_price1)current_index - 20,len(close_price1)):
        new_close_price.append(close_price1[i]-multiplier*close_price2[i])
    BB =np.array(bollinger_pband(pd.Series(new_close_price),window_dev=3))
    SMA20 = np.array(bollinger_mavg(pd.Series(new_close_price)))
    if BB[current_index]>1:
        trade_direction = [0,1]
        close_price1_SL = close_price1[current_index] * percent_SL
        close_price2_SL = close_price2[current_index] * percent_SL
    elif BB[current_index]<0:
        trade_direction = [1,0]
        close_price1_SL = close_price1[current_index] * percent_SL
        close_price2_SL = close_price2[current_index] * percent_SL
    if current_position!=-99:
        if (new_close_price[current_index]>SMA20[current_index] and (new_close_price[current_index - 1]<SMA20[current_index - 1] or new_close_price[current_index - 2]<SMA20[current_index - 2])) or (new_close_price[current_index]<SMA20[current_index] and (new_close_price[current_index - 1]>SMA20[current_index - 1] or new_close_price[current_index - 2]>SMA20[current_index - 2])):
            ##Price has crossed up or down over the Moving average so close the position
            close_price_pos=1
    return trade_direction,close_price1_SL,close_price2_SL,close_price_pos'''


def set_sl_tp(stop_loss_val_arr, take_profit_val_arr, peaks, troughs, close_price, high_price, low_price, trade_direction, sl, tp, tp_sl_choice, current_index):
    take_profit_val = -99
    stop_loss_val = -99
    match tp_sl_choice:
        case '%':
            take_profit_val = take_profit_val_arr[current_index]
            stop_loss_val = stop_loss_val_arr[current_index]

        case 'x (ATR)':
            take_profit_val = take_profit_val_arr[current_index]
            stop_loss_val = stop_loss_val_arr[current_index]

        case 'x (Swing high_price/low_price) level 1':
            high_swing = high_price[current_index]
            low_swing = low_price[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(tp_sl_choice[-1]), -1, -1):
                if high_price[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if low_price[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and trade_direction == 0) or (low_flag == 1 and trade_direction == 1):
                    break

            if trade_direction == 0:
                print("TP margin:", close_price[current_index] - low_swing, 'low_swing:', low_swing, 'close_price:', close_price[current_index])
                stop_loss_val = sl * (high_swing - close_price[current_index])
                take_profit_val = tp * stop_loss_val
            elif trade_direction == 1:
                print("TP margin:", high_swing - close_price[current_index], 'high_swing:', high_swing, 'close_price:', close_price[current_index])
                stop_loss_val = sl * (close_price[current_index] - low_swing)
                take_profit_val = tp * stop_loss_val

        case 'x (Swing high_price/low_price) level 2':
            high_swing = high_price[current_index]
            low_swing = low_price[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(tp_sl_choice[-1]), -1, -1):
                if high_price[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if low_price[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and trade_direction == 0) or (low_flag == 1 and trade_direction == 1):
                    break

            if trade_direction == 0:
                print("TP margin:", close_price[current_index] - low_swing, 'low_swing:', low_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (high_swing - close_price[current_index])
                take_profit_val = tp * stop_loss_val
            elif trade_direction == 1:
                print("TP margin:", high_swing - close_price[current_index], 'high_swing:', high_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (close_price[current_index] - low_swing)
                take_profit_val = tp * stop_loss_val

        case 'x (Swing high_price/low_price) level 3':
            high_swing = high_price[current_index]
            low_swing = low_price[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(tp_sl_choice[-1]), -1, -1):
                if high_price[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if low_price[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and trade_direction == 0) or (low_flag == 1 and trade_direction == 1):
                    break

            if trade_direction == 0:
                print("TP margin:", close_price[current_index] - low_swing, 'low_swing:', low_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (high_swing - close_price[current_index])
                take_profit_val = tp * stop_loss_val
            elif trade_direction == 1:
                print("TP margin:", high_swing - close_price[current_index], 'high_swing:', high_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (close_price[current_index] - low_swing)
                take_profit_val = tp * stop_loss_val

        case 'x (Swing close_price) level 1':
            high_swing = close_price[current_index]
            low_swing = close_price[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(tp_sl_choice[-1]), -1, -1):
                if close_price[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if close_price[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and trade_direction == 0) or (low_flag == 1 and trade_direction == 1):
                    break

            if trade_direction == 0:
                print("TP margin:", close_price[current_index] - low_swing, 'low_swing:', low_swing, 'close_price:', close_price[current_index])
                stop_loss_val = sl * (high_swing - close_price[current_index])
                take_profit_val = tp * stop_loss_val
            elif trade_direction == 1:
                print("TP margin:", high_swing - close_price[current_index], 'high_swing:', high_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (close_price[current_index] - low_swing)
                take_profit_val = tp * stop_loss_val

        case 'x (Swing close_price) level 2':
            high_swing = close_price[current_index]
            low_swing = close_price[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(tp_sl_choice[-1]), -1, -1):
                if close_price[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if close_price[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and trade_direction == 0) or (low_flag == 1 and trade_direction == 1):
                    break

            if trade_direction == 0:
                print("TP margin:", close_price[current_index] - low_swing, 'low_swing:', low_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (high_swing - close_price[current_index])
                take_profit_val = tp * stop_loss_val
            elif trade_direction == 1:
                print("TP margin:", high_swing - close_price[current_index], 'high_swing:', high_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (close_price[current_index] - low_swing)
                take_profit_val = tp * stop_loss_val

        case 'x (Swing close_price) level 3':
            high_swing = close_price[current_index]
            low_swing = close_price[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(tp_sl_choice[-1]), -1, -1):
                if close_price[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if close_price[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and trade_direction == 0) or (low_flag == 1 and trade_direction == 1):
                    break

            if trade_direction == 0:
                print("TP margin:", close_price[current_index] - low_swing, 'low_swing:', low_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (high_swing - close_price[current_index])
                take_profit_val = tp * stop_loss_val
            elif trade_direction == 1:
                print("TP margin:", high_swing - close_price[current_index], 'high_swing:', high_swing, 'close_price:',
                      close_price[current_index])
                stop_loss_val = sl * (close_price[current_index] - low_swing)
                take_profit_val = tp * stop_loss_val

        case _:
            return

    return stop_loss_val, take_profit_val
