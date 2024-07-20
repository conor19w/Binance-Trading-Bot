from LiveTradingConfig import *
from Logger import *

def USDT_SL_TP(options):
    Q = round(1 / options['position_size'], 6)
    take_profit_val = TP_mult * Q
    stop_loss_val = SL_mult * Q
    return stop_loss_val, take_profit_val


def candle_wick(Trade_Direction, Close, Open, High, Low, current_index):
    if Close[current_index - 4] < Close[current_index - 3] < Close[current_index - 2] and Close[current_index - 1] < Open[current_index - 1] and (
            High[current_index - 1] - Open[current_index - 1] + Close[current_index - 1] - Low[current_index - 1]) > 10 * (Open[current_index - 1] - Close[current_index - 1]) and Close[current_index] < Close[current_index - 1]:
        ##3 green candles followed by a red candle with a huge wick
        Trade_Direction = 0
    elif Close[current_index - 4] > Close[current_index - 3] > Close[current_index - 2] and Close[current_index - 1] > Open[current_index - 1] and (
            High[current_index - 1] - Close[current_index - 1] + Open[current_index - 1] - Low[current_index - 1]) > 10 * (Close[current_index - 1] - Open[current_index - 1]) and Close[current_index] > Close[current_index - 1]:
        ##3 red candles followed by a green candle with a huge wick
        Trade_Direction = 1
    return Trade_Direction


def fibMACD(Trade_Direction, Close, Open, High, Low, MACD_signal, MACD, EMA200, current_index):
    period = 100  ##Record peaks and troughs in last period timesteps

    Close_peaks = []  ##Store peak values
    location_peaks = []  ##store current_index of peak value , used for debugging
    Close_troughs = []  ##store trough values
    location_troughs = []  ##store current_index of peak trough , used for debugging
    #####################Find peaks & troughs in Close ##############################
    for i in range(current_index - period, current_index - 2):
        if High[i] > High[i - 1] and High[i] > High[i + 1] and High[i] > High[i - 2] and High[i] > High[i + 2]:
            ##Weve found a peak:
            Close_peaks.append(High[i])
            location_peaks.append(i)
        elif Low[i] < Low[i - 1] and Low[i] < Low[i + 1] and Low[i] < Low[i - 2] and Low[i] < Low[i + 2]:
            ##Weve found a trough:
            Close_troughs.append(Low[i])
            location_troughs.append(i)

    trend = -99  ##indicate the direction of trend
    if Close[current_index] < EMA200[current_index]:
        trend = 0
    elif Close[current_index] > EMA200[current_index]:
        trend = 1
    max_pos = -99
    min_pos = -99
    if trend == 1:
        ##Find the start and end of the pullback
        max_Close = -9999999
        min_Close = 9999999
        max_flag = 0
        min_flag = 0
        for i in range(len(Close_peaks) - 1, -1, -1):
            if Close_peaks[i] > max_Close and max_flag < 2:
                max_Close = Close_peaks[i]
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
            if Close_troughs[i] < min_Close and min_flag < 2:
                min_Close = Close_troughs[i]
                min_pos = location_troughs[i]
                min_flag = 0
            elif min_flag == 2:
                break
            else:
                min_flag += 1
        ##fibonacci levels
        fib_level_0 = max_Close
        fib_level_1 = max_Close - .236 * (max_Close - min_Close)
        fib_level_2 = max_Close - .382 * (max_Close - min_Close)
        fib_level_3 = max_Close - .5 * (max_Close - min_Close)
        fib_level_4 = max_Close - .618 * (max_Close - min_Close)
        fib_level_5 = max_Close - .786 * (max_Close - min_Close)
        fib_level_6 = min_Close

        ##Take profit targets, Don't think this is configured properly so maybe have a look at fibonacci extensions and fix here, Right hand side is ment to be the corresponding extension level
        # fib_retracement_level_1 = fib_level_0 + 1.236 * (max_Close - min_Close) - Close[
        #     current_index]  ##target max_Close+1.236*(max_Close - min_Close)
        # fib_retracement_level_2 = fib_level_0 + 1.382 * (max_Close - min_Close) - Close[current_index]
        # fib_retracement_level_3 = fib_level_0 + 1.5 * (max_Close - min_Close) - Close[current_index]
        # fib_retracement_level_4 = fib_level_0 + 1.618 * (max_Close - min_Close) - Close[current_index]
        # fib_retracement_level_5 = fib_level_0 + 1.786 * (max_Close - min_Close) - Close[current_index]
        # fib_retracement_level_6 = fib_level_0 + 2 * (max_Close - min_Close) - Close[current_index]

        ## fib_level_0>Low[current_index - 2]>fib_level_1: recent low was between two of our levels
        ## Close[current_index - 3]>fib_level_1 and Close[current_index - 4]>fib_level_1 and Close[-6]>fib_level_1: Ensure the bottom level was respected  ie. no recent close below it
        if fib_level_0 > Low[current_index - 2] > fib_level_1 and Close[current_index - 3] > fib_level_1 and Close[current_index - 4] > fib_level_1 and Close[
            -6] > fib_level_1:
            if Close[current_index - 2] < Open[current_index - 2] < Close[current_index - 1] < Close[current_index] and (
                    (MACD_signal[current_index - 1] < MACD[current_index - 1] or MACD_signal[current_index - 2] < MACD[current_index - 2]) and MACD_signal[current_index] > MACD[
                current_index]):  ##Bullish Engulfing Candle and cross up on MACD
                # print("level 1")
                Trade_Direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_1  ##target the corresponding extensiuon level
                # stop_loss_val = Close[current_index] - fib_level_1 * 1.0001  ##stoploss below bottom level with a bit extra
        elif fib_level_1 > Low[current_index - 2] > fib_level_2 and Close[current_index - 3] > fib_level_2 and Close[current_index - 4] > fib_level_2 and Close[
            -6] > fib_level_2:
            if Close[current_index - 2] < Open[current_index - 2] < Close[current_index - 1] < Close[current_index] and (
                    (MACD_signal[current_index - 1] < MACD[current_index - 1] or MACD_signal[current_index - 2] < MACD[current_index - 2]) and MACD_signal[current_index] > MACD[
                current_index]):  ##Bullish Engulfing Candle and cross up on MACD
                # print("level 1")
                Trade_Direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_2
                # stop_loss_val = Close[current_index] - fib_level_2 * 1.0001

        elif fib_level_2 > Low[current_index - 1] > fib_level_3 and Close[current_index - 2] > fib_level_3 and Close[current_index - 3] > fib_level_3 and Close[
            current_index - 4] > fib_level_3:
            if Close[current_index - 1] < Open[current_index - 1] < Close[current_index] < Close[current_index] and (
                    (MACD_signal[current_index - 1] < MACD[current_index - 1] or MACD_signal[current_index - 2] < MACD[current_index - 2]) and MACD_signal[current_index] > MACD[
                current_index]):  ##Bullish Engulfing Candle and cross up on MACD
                # print("level 2")
                Trade_Direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_3
                # stop_loss_val = Close[current_index] - fib_level_3 * 1.0001

        elif fib_level_3 > Low[current_index - 1] > fib_level_4 and Close[current_index - 2] > fib_level_4 and Close[current_index - 3] > fib_level_4 and Close[
            current_index - 4] > fib_level_4:
            if Close[current_index - 1] < Open[current_index - 1] < Close[current_index] < Close[current_index] and (
                    (MACD_signal[current_index - 1] < MACD[current_index - 1] or MACD_signal[current_index - 2] < MACD[current_index - 2]) and MACD_signal[current_index] > MACD[
                current_index]):  ##Bullish Engulfing Candle and cross up on MACD
                # print("level 3")
                Trade_Direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_4
                # stop_loss_val = Close[current_index] - fib_level_4 * 1.0001
        elif fib_level_4 > Low[current_index - 1] > fib_level_5 and Close[current_index - 2] > fib_level_5 and Close[current_index - 3] > fib_level_5 and Close[
            current_index - 4] > fib_level_5:
            if Close[current_index - 1] < Open[current_index - 1] < Close[current_index] < Close[current_index] and (
                    (MACD_signal[current_index - 1] < MACD[current_index - 1] or MACD_signal[current_index - 2] < MACD[current_index - 2]) and MACD_signal[current_index] > MACD[
                current_index]):  ##Bullish Engulfing Candle and cross up on MACD
                # print("level 4")
                Trade_Direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_5
                # stop_loss_val = Close[current_index] - fib_level_5 * 1.0001
        elif fib_level_5 > Low[current_index - 1] > fib_level_6 and Close[current_index - 2] > fib_level_6 and Close[current_index - 3] > fib_level_6 and Close[
            current_index - 4] > fib_level_6:
            if Close[current_index - 1] < Open[current_index - 1] < Close[current_index] < Close[current_index] and (
                    (MACD_signal[current_index - 1] < MACD[current_index - 1] or MACD_signal[current_index - 2] < MACD[current_index - 2]) and MACD_signal[current_index] > MACD[
                current_index]):  ##Bullish Engulfing Candle and cross up on MACD
                # print("level 5")
                Trade_Direction = 1  ##signal a buy
                # take_profit_val = fib_retracement_level_6
                # stop_loss_val = Close[current_index] - fib_level_6 * 1.0001

    elif trend == 0:
        ##Find the start and end of the pullback
        max_Close = -9999999
        min_Close = 9999999
        max_flag = 0
        min_flag = 0
        for i in range(len(Close_troughs) - 1, -1, -1):
            if Close_troughs[i] < min_Close and min_flag < 2:
                min_Close = Close_troughs[i]
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
            if Close_peaks[i] > max_Close and max_flag < 2:
                max_Close = Close_peaks[i]
                max_pos = location_peaks[i]
                max_flag = 0
            elif max_flag == 2:
                break
            else:
                max_flag += 1
        ##fibonacci levels
        fib_level_0 = min_Close
        fib_level_1 = min_Close + .236 * (max_Close - min_Close)
        fib_level_2 = min_Close + .382 * (max_Close - min_Close)
        fib_level_3 = min_Close + .5 * (max_Close - min_Close)
        fib_level_4 = min_Close + .618 * (max_Close - min_Close)
        fib_level_5 = min_Close + .786 * (max_Close - min_Close)
        fib_level_6 = max_Close

        ##Take profit targets, Don't think this is configured properly so maybe have a look at fibonacci extensions and fix here, Right hand side is ment to be the corresponding extension level
        # fib_retracement_level_1 = Close[current_index] - (fib_level_0 + 1.236 * (max_Close - min_Close))
        # fib_retracement_level_2 = Close[current_index] - (fib_level_0 + 1.382 * (max_Close - min_Close))
        # fib_retracement_level_3 = Close[current_index] - (fib_level_0 + 1.5 * (max_Close - min_Close))
        # fib_retracement_level_4 = Close[current_index] - (fib_level_0 + 1.618 * (max_Close - min_Close))
        # fib_retracement_level_5 = Close[current_index] - (fib_level_0 + 1.786 * (max_Close - min_Close))
        # fib_retracement_level_6 = Close[current_index] - (fib_level_0 + 2 * (max_Close - min_Close))

        ## fib_level_0 < High[current_index - 2] < fib_level_1: recent low was between two of our levels
        ## Close[current_index - 3] < fib_level_1 and Close[current_index - 4] < fib_level_1 and Close[-6] < fib_level_1: Ensure the Top level was respected, ie no recent close above it
        if fib_level_0 < High[current_index - 2] < fib_level_1 and Close[current_index - 3] < fib_level_1 and Close[current_index - 4] < fib_level_1 and Close[
            -6] < fib_level_1:
            if Close[current_index - 2] > Open[current_index - 2] > Close[current_index - 1] > Close[current_index] and (
                    (MACD_signal[current_index - 1] > MACD[current_index - 1] or MACD_signal[current_index - 2] > MACD[current_index - 2]) and MACD_signal[current_index] < MACD[
                current_index]):  ##Bearish Engulfing Candle and cross down on MACD
                # print("level 1")
                Trade_Direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_1  ##target corresponding extension level
                # stop_loss_val = fib_level_1 * 1.0001 - Close[current_index]  ##stoploss above Top level with a bit extra
        elif fib_level_1 < High[current_index - 2] < fib_level_2 and Close[current_index - 3] < fib_level_2 and Close[current_index - 4] < fib_level_2 and Close[
            -6] < fib_level_2:
            if Close[current_index - 2] > Open[current_index - 2] > Close[current_index - 1] > Close[current_index] and (
                    (MACD_signal[current_index - 1] > MACD[current_index - 1] or MACD_signal[current_index - 2] > MACD[current_index - 2]) and MACD_signal[current_index] < MACD[
                current_index]):  ##Bearish Engulfing Candle and cross down on MACD
                # print("level 1")
                Trade_Direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_2
                # stop_loss_val = fib_level_2 * 1.0001 - Close[current_index]
        elif fib_level_2 < High[current_index - 2] < fib_level_3 and Close[current_index - 3] < fib_level_3 and Close[current_index - 4] < fib_level_3 and Close[
            -6] < fib_level_3:
            if Close[current_index - 2] > Open[current_index - 2] > Close[current_index - 1] > Close[current_index] and (
                    (MACD_signal[current_index - 1] > MACD[current_index - 1] or MACD_signal[current_index - 2] > MACD[current_index - 2]) and MACD_signal[current_index] < MACD[
                current_index]):  ##Bearish Engulfing Candle and cross down on MACD
                # print("level 1")
                Trade_Direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_3
                # stop_loss_val = fib_level_3 * 1.0001 - Close[current_index]
        elif fib_level_3 < High[current_index - 2] < fib_level_4 and Close[current_index - 3] < fib_level_4 and Close[current_index - 4] < fib_level_4 and Close[
            -6] < fib_level_4:
            if Close[current_index - 2] > Open[current_index - 2] > Close[current_index - 1] > Close[current_index] and (
                    (MACD_signal[current_index - 1] > MACD[current_index - 1] or MACD_signal[current_index - 2] > MACD[current_index - 2]) and MACD_signal[current_index] < MACD[
                current_index]):  ##Bearish Engulfing Candle and cross down on MACD
                # print("level 1")
                Trade_Direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_4
                # stop_loss_val = fib_level_4 * 1.0001 - Close[current_index]
        elif fib_level_4 < High[current_index - 2] < fib_level_5 and Close[current_index - 3] < fib_level_5 and Close[current_index - 4] < fib_level_5 and Close[
            -6] < fib_level_5:
            if Close[current_index - 2] > Open[current_index - 2] > Close[current_index - 1] > Close[current_index] and (
                    (MACD_signal[current_index - 1] > MACD[current_index - 1] or MACD_signal[current_index - 2] > MACD[current_index - 2]) and MACD_signal[current_index] < MACD[
                current_index]):  ##Bearish Engulfing Candle and cross down on MACD
                # print("level 1")
                Trade_Direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_5
                # stop_loss_val = fib_level_5 * 1.0001 - Close[current_index]
        elif fib_level_5 < High[current_index - 2] < fib_level_6 and Close[current_index - 3] < fib_level_6 and Close[current_index - 4] < fib_level_6 and Close[
            -6] < fib_level_6:
            if Close[current_index - 2] > Open[current_index - 2] > Close[current_index - 1] > Close[current_index] and (
                    (MACD_signal[current_index - 1] > MACD[current_index - 1] or MACD_signal[current_index - 2] > MACD[current_index - 2]) and MACD_signal[current_index] < MACD[
                current_index]):  ##Bearish Engulfing Candle and cross down on MACD
                # print("level 1")
                Trade_Direction = 0  ##signal a sell
                # take_profit_val = fib_retracement_level_6
                # stop_loss_val = fib_level_6 * 1.0001 - Close[current_index]

    return Trade_Direction #, stop_loss_val, take_profit_val


def goldenCross(Trade_Direction, Close, EMA100, EMA50, EMA20, RSI, current_index):
    if Close[current_index] > EMA100[current_index] and RSI[current_index] > 50:
        ##looking for long entries
        if (EMA20[current_index - 1] < EMA50[current_index - 1] and EMA20[current_index] > EMA50[current_index]) or (EMA20[current_index - 2] < EMA50[current_index - 2] and EMA20[current_index] > EMA50[current_index]) or (
                EMA20[current_index - 3] < EMA50[current_index - 3] and EMA20[current_index] > EMA50[current_index]):
            ##Cross up occured
            Trade_Direction = 1  ##buy
    elif Close[current_index] < EMA100[current_index] and RSI[current_index] < 50:
        ##looking for short entries
        if (EMA20[current_index - 1] > EMA50[current_index - 1] and EMA20[current_index] < EMA50[current_index]) or (EMA20[current_index - 2] > EMA50[current_index - 2] and EMA20[current_index] < EMA50[current_index]) or (
                EMA20[current_index - 3] > EMA50[current_index - 3] and EMA20[current_index] < EMA50[current_index]):
            ##Cross up occured
            Trade_Direction = 0  ##Sell

    return Trade_Direction


def StochRSIMACD(Trade_Direction, fastd, fastk, RSI, MACD, macdsignal, current_index):

    if ((fastd[current_index] < 20 and fastk[current_index] < 20 and RSI[current_index] > 50 and MACD[current_index] > macdsignal[current_index] and MACD[current_index - 1] < macdsignal[
        current_index - 1]) or
            (fastd[current_index - 1] < 20 and fastk[current_index - 1] < 20 and RSI[current_index] > 50 and MACD[current_index] > macdsignal[current_index] and MACD[current_index - 2] < macdsignal[
                current_index - 2] and fastd[current_index] < 80 and fastk[current_index] < 80) or
            (fastd[current_index - 2] < 20 and fastk[current_index - 2] < 20 and RSI[current_index] > 50 and MACD[current_index] > macdsignal[current_index] and MACD[current_index - 1] < macdsignal[
                current_index - 1] and fastd[current_index] < 80 and fastk[current_index] < 80) or
            (fastd[current_index - 3] < 20 and fastk[current_index - 3] < 20 and RSI[current_index] > 50 and MACD[current_index] > macdsignal[current_index] and MACD[current_index - 2] < macdsignal[
                current_index - 2] and fastd[current_index] < 80 and fastk[current_index] < 80)):
        Trade_Direction = 1
    elif ((fastd[current_index] > 80 and fastk[current_index] > 80 and RSI[current_index] < 50 and MACD[current_index] < macdsignal[current_index] and MACD[current_index - 1] > macdsignal[
        current_index - 1]) or
          (fastd[current_index - 1] > 80 and fastk[current_index - 1] > 80 and RSI[current_index] < 50 and MACD[current_index] < macdsignal[current_index] and MACD[current_index - 2] > macdsignal[
              current_index - 2] and fastd[current_index] > 20 and fastk[current_index] > 20) or
          (fastd[current_index - 2] > 80 and fastk[current_index - 2] > 80 and RSI[current_index] < 50 and MACD[current_index] < macdsignal[current_index] and MACD[current_index - 1] > macdsignal[
              current_index - 1] and fastd[current_index] > 20 and fastk[current_index] > 20) or
          (fastd[current_index - 3] > 80 and fastk[current_index - 3] > 80 and RSI[current_index] < 50 and MACD[current_index] < macdsignal[current_index] and MACD[current_index - 2] > macdsignal[
              current_index - 2] and fastd[current_index] > 20 and fastk[current_index] > 20)):
        Trade_Direction = 0
    return Trade_Direction


##############################################################################################################################
##############################################################################################################################
##############################################################################################################################


def tripleEMA(Trade_Direction, EMA3, EMA6, EMA9, current_index):

    if EMA3[current_index - 4] > EMA6[current_index - 4] and EMA3[current_index - 4] > EMA9[current_index - 4] \
            and EMA3[current_index - 3] > EMA6[current_index - 3] and EMA3[current_index - 3] > EMA9[current_index - 3] \
            and EMA3[current_index - 2] > EMA6[current_index - 2] and EMA3[current_index - 2] > EMA9[current_index - 2] \
            and EMA3[current_index - 1] > EMA6[current_index - 1] and EMA3[current_index - 1] > EMA9[current_index - 1] \
            and EMA3[current_index] < EMA6[current_index] and EMA3[current_index] < EMA9[current_index]:
        Trade_Direction = 0
    if EMA3[current_index - 4] < EMA6[current_index - 4] and EMA3[current_index - 4] < EMA9[current_index - 4] \
            and EMA3[current_index - 3] < EMA6[current_index - 3] and EMA3[current_index - 3] < EMA9[current_index - 3] \
            and EMA3[current_index - 2] < EMA6[current_index - 2] and EMA3[current_index - 2] < EMA9[current_index - 2] \
            and EMA3[current_index - 1] < EMA6[current_index - 1] and EMA3[current_index - 1] < EMA9[current_index - 1] \
            and EMA3[current_index] > EMA6[current_index] and EMA3[current_index] > EMA9[current_index]:
        Trade_Direction = 1
    return Trade_Direction


def heikin_ashi_ema2(OpenStream_H, High_H, Low_H, Close_H, Trade_Direction, CurrentPos, Close_pos, fastd, fastk, EMA200, current_index):
    if CurrentPos == -99:
        Trade_Direction = -99
        short_threshold = .7  ##If RSI falls below this don't open any shorts
        long_threshold = .3  ##If RSI goes above this don't open any longs

        ##Check Most recent Candles to see if we got a cross down and we are below 200EMA
        if fastk[current_index - 1] > fastd[current_index - 1] and fastk[current_index] < fastd[current_index] and Close_H[current_index] < EMA200[current_index]:
            for i in range(10, 2, -1):
                ##Find Bearish Meta Candle
                if Close_H[-i] < OpenStream_H[-i] and OpenStream_H[-i] == High_H[-i]:
                    for j in range(i, 2, -1):
                        ##Find cross below EMA200
                        if Close_H[-j] > EMA200[-j] and Close_H[-j + 1] < EMA200[-j + 1] and OpenStream_H[-j] > Close_H[
                            -j]:
                            ##Now look for Overbought signal
                            flag = 1
                            for r in range(j, 0, -1):
                                if fastd[-r] < short_threshold or fastk[-r] < short_threshold:
                                    flag = 0
                            if flag:
                                ##Open a trade
                                Trade_Direction = 0
                                break  ##break out of current loop
                    if Trade_Direction == 0:
                        break
        ##Check Most recent Candles to see if we got a cross up and we are above 200EMA
        elif fastk[current_index - 1] < fastd[current_index - 1] and fastk[current_index] > fastd[current_index] and Close_H[current_index] > EMA200[current_index]:
            for i in range(10, 2, -1):
                ##Find Bullish Meta Candle
                if Close_H[-i] > OpenStream_H[-i] and OpenStream_H[-i] == Low_H[-i]:
                    for j in range(i, 2, -1):
                        ##Find cross above EMA200
                        if Close_H[-j] < EMA200[-j] and Close_H[-j + 1] > EMA200[-j + 1] and OpenStream_H[-j] < Close_H[
                            -j]:
                            ##Now look for OverSold signal
                            flag = 1
                            for r in range(j, 0, -1):
                                if fastd[-r] > long_threshold or fastk[-r] > long_threshold:
                                    flag = 0
                            if flag:
                                ##Open a trade
                                Trade_Direction = 1
                                break  ##break out of current loop
                    if Trade_Direction == 1:
                        break

    elif CurrentPos == 1 and Close_H[current_index] < OpenStream_H[current_index]:
        Close_pos = 1
    elif CurrentPos == 0 and Close_H[current_index] > OpenStream_H[current_index]:
        Close_pos = 1
    else:
        Close_pos = 0
    return Trade_Direction, Close_pos


def heikin_ashi_ema(OpenStream_H, Close_H, Trade_Direction, CurrentPos, Close_pos, fastd, fastk, EMA200, current_index):
    if CurrentPos == -99:
        Trade_Direction = -99

        short_threshold = .8  ##If RSI falls below this don't open any shorts
        long_threshold = .2  ##If RSI goes above this don't open any longs
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
                            if Close_H[current_index - 2] > EMA200[current_index - 2] and Close_H[current_index - 1] < EMA200[current_index - 1] and flag:
                                ##closed below 200EMA
                                if Close_H[current_index] < OpenStream_H[current_index]:
                                    ##bearish candle
                                    ##all conditions met so open a short
                                    Trade_Direction = 0
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
                            if Close_H[current_index - 2] < EMA200[current_index - 2] and Close_H[current_index - 1] > EMA200[current_index - 1] and flag:
                                ##closed above 200EMA
                                if Close_H[current_index] > OpenStream_H[current_index]:
                                    ##bullish candle
                                    ##all conditions met so open a long
                                    Trade_Direction = 1
                                else:
                                    break  ##break out of the current for loop
                            else:
                                break  ##break out of the current for loop
    elif CurrentPos == 1 and Close_H[current_index] < OpenStream_H[current_index]:
        Close_pos = 1
    elif CurrentPos == 0 and Close_H[current_index] > OpenStream_H[current_index]:
        Close_pos = 1
    else:
        Close_pos = 0
    return Trade_Direction, Close_pos


def tripleEMAStochasticRSIATR(Close, Trade_Direction, EMA50, EMA14, EMA8, fastd, fastk, current_index):
    ##buy signal
    if (Close[current_index] > EMA8[current_index] > EMA14[current_index] > EMA50[current_index]) and \
            ((fastk[current_index] > fastd[current_index]) and (fastk[current_index - 1] < fastd[current_index - 1])):  # and (fastk[current_index]<80 and fastd[current_index]<80):
        Trade_Direction = 1
    elif (Close[current_index] < EMA8[current_index] < EMA14[current_index] < EMA50[current_index]) and\
            ((fastk[current_index] < fastd[current_index]) and (fastk[current_index - 1] > fastd[current_index - 1])):  # and (fastk[current_index]>20 and fastd[current_index]>20):
        Trade_Direction = 0

    return Trade_Direction

##############################################################################################################################
##############################################################################################################################
##############################################################################################################################


# def RSIStochEMA(Trade_Direction, Close, High, Low, signal1, currentPos, SL, TP, TP_choice, SL_choice):
#     period = 60
#     CloseS = pd.Series(Close)
#     Close = np.array(Close)
#     # High = np.array(High)
#     # Low = np.array(Low)
#     fastk = np.array(stoch_signal(pd.Series(High), pd.Series(Low), pd.Series(Close)))
#     fastd = np.array(stoch(pd.Series(High), pd.Series(Low), pd.Series(Close)))
#     RSI = np.array(rsi(CloseS))
#     EMA200 = np.array(ema_indicator(CloseS, window=200))
#     peaks_RSI = []
#     corresponding_Close_peaks = []
#     location_peaks = []
#     troughs_RSI = []
#     corresponding_Close_troughs = []
#     location_troughs = []
#     #####################Find peaks & troughs in RSI ##############################
#     for i in range(len(RSI) - period, len(RSI) - 2):
#         if RSI[i] > RSI[i - 1] and RSI[i] > RSI[i + 1] and RSI[i] > RSI[i - 2] and RSI[i] > RSI[i + 2]:
#             ##Weve found a peak:
#             peaks_RSI.append(RSI[i])
#             corresponding_Close_peaks.append(Close[i])
#             location_peaks.append(i)
#         elif RSI[i] < RSI[i - 1] and RSI[i] < RSI[i + 1] and RSI[i] < RSI[i - 2] and RSI[i] < RSI[i + 2]:
#             ##Weve found a trough:
#             troughs_RSI.append(RSI[i])
#             corresponding_Close_troughs.append(Close[i])
#             location_troughs.append(i)
#     ##Lower High Price & Higher High RSI => Bearish Divergence
#     ##Higher Low Price & Lower low RSI => Bullish Divergence
#     length = 0
#     if len(peaks_RSI) > len(troughs_RSI):
#         length = len(peaks_RSI)
#     else:
#         length = len(troughs_RSI)
#     loc1 = -99
#     loc2 = -99
#     if length != 0:
#         for i in range(length - 1):
#             if i < len(peaks_RSI):
#                 ##Check for hidden Bearish Divergence
#                 if peaks_RSI[i] < peaks_RSI[current_index] and corresponding_Close_peaks[i] > corresponding_Close_peaks[current_index] and \
#                         peaks_RSI[current_index] - peaks_RSI[i] > 1:
#                     for j in range(i + 1, len(peaks_RSI) - 1):
#                         if peaks_RSI[j] > peaks_RSI[i]:
#                             break
#                         elif j == len(peaks_RSI) - 2:
#                             loc1 = location_peaks[i]
#
#             if i < len(troughs_RSI):
#                 ##Check for hidden Bullish Divergence
#                 if troughs_RSI[i] > troughs_RSI[current_index] and corresponding_Close_troughs[i] < corresponding_Close_troughs[
#                     current_index] and troughs_RSI[i] - troughs_RSI[current_index] > 1:
#                     for j in range(i + 1, len(troughs_RSI) - 1):
#                         if troughs_RSI[j] < troughs_RSI[i]:
#                             break
#                         elif j == len(troughs_RSI) - 2:
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
#     if signal1 == 1 and (fastk[current_index] > fastd[current_index] and (fastk[current_index - 1] < fastd[current_index - 1] or fastk[current_index - 2] < fastd[current_index - 2])) and Close[current_index] > \
#             EMA200[current_index]:
#         Trade_Direction = 1
#         signal1 = -99
#
#     ##Bearish Divergence
#     elif signal1 == 0 and (fastk[current_index] < fastd[current_index] and (fastk[current_index - 1] > fastd[current_index - 1] or fastk[current_index - 2] > fastd[current_index - 2])) and Close[current_index] < \
#             EMA200[current_index]:
#         Trade_Direction = 0
#         signal1 = -99
#
#     if currentPos != -99:
#         signal1 = -99
#         Trade_Direction = -99
#     stop_loss_val, take_profit_val = SetSLTP(-99, -99, Close, High, Low, Trade_Direction, SL, TP, TP_choice, SL_choice, current_index)
#     return Trade_Direction, signal1, stop_loss_val, take_profit_val


##############################################################################################################

def stochBB(Trade_Direction, fastd, fastk, percent_B, current_index):
    percent_B1 = percent_B[current_index]
    percent_B2 = percent_B[current_index - 1]
    percent_B3 = percent_B[current_index - 2]
    # print(percent_B)

    if fastk[current_index] < .2 and fastd[current_index] < .2 and (fastk[current_index] > fastd[current_index] and fastk[current_index - 1] < fastd[current_index - 1]) and (
            percent_B1 < 0 or percent_B2 < 0 or percent_B3 < 0):  # or percent_B3<0):# or percent_B2<.05):
        Trade_Direction = 1
    elif fastk[current_index] > .8 and fastd[current_index] > .8 and (fastk[current_index] < fastd[current_index] and fastk[current_index - 1] > fastd[current_index - 1]) and (
            percent_B1 > 1 or percent_B2 > 1 or percent_B3 > 1):  # or percent_B3>1):# or percent_B2>1):
        Trade_Direction = 0
    return Trade_Direction


def breakout(Trade_Direction, Close, VolumeStream, max_Close, min_Close, max_Vol, current_index):
    invert = 0  ## switch shorts and longs, basically fakeout instead of breakout
    if invert:
        if Close[current_index] >= max_Close.iloc[current_index] and VolumeStream[current_index] >= max_Vol.iloc[current_index]:
            Trade_Direction = 0
        elif Close[current_index] <= min_Close.iloc[current_index] and VolumeStream[current_index] >= max_Vol.iloc[current_index]:
            Trade_Direction = 1
    else:
        if Close[current_index] >= max_Close.iloc[current_index] and VolumeStream[current_index] >= max_Vol.iloc[current_index]:
            Trade_Direction = 1
        elif Close[current_index] <= min_Close.iloc[current_index] and VolumeStream[current_index] >= max_Vol.iloc[current_index]:
            Trade_Direction = 0
    return Trade_Direction

def ema_crossover(Trade_Direction, current_index, ema_short, ema_long):
    if ema_short[current_index-1] > ema_long[current_index-1] and ema_short[current_index] < ema_long[current_index]:
        Trade_Direction = 0
    elif ema_short[current_index-1] < ema_long[current_index-1] and ema_short[current_index] > ema_long[current_index]:
        Trade_Direction = 1
    return Trade_Direction

# def fakeout(Trade_Direction, Close, VolumeStream, High, Low, SL, TP, TP_choice, SL_choice):
#     invert = 1
#     # if symbol == 'BTCUSDT' or symbol == 'ETHUSDT':
#     #    invert = 0
#     Close = pd.Series(Close)  # .pct_change() ##get size of bars in a percentage
#     Volume = pd.Series(VolumeStream[:current_index])
#     max_Close = Close.iloc[:current_index].rolling(15).max()
#     min_Close = Close.iloc[:current_index].rolling(15).min()
#     max_Vol = Volume.rolling(15).max()
#     if invert:
#         if Close.iloc[current_index] > max_Close.iloc[current_index] and VolumeStream[current_index] < max_Vol.iloc[current_index]:
#             Trade_Direction = 0
#         elif Close.iloc[current_index] < min_Close.iloc[current_index] and VolumeStream[current_index] < max_Vol.iloc[current_index]:
#             Trade_Direction = 1
#     else:
#         if Close.iloc[current_index] > max_Close.iloc[current_index] and VolumeStream[current_index] < max_Vol.iloc[current_index]:
#             Trade_Direction = 1
#         elif Close.iloc[current_index] < min_Close.iloc[current_index] and VolumeStream[current_index] < max_Vol.iloc[current_index]:
#             Trade_Direction = 0
#     stop_loss_val, take_profit_val = SetSLTP(-99, -99, Close, High, Low, Trade_Direction, SL, TP, TP_choice, SL_choice, current_index)
#     return Trade_Direction, stop_loss_val, take_profit_val


def EMA_cross(Trade_Direction, EMA_short, EMA_long, current_index):
    if EMA_short[current_index - 4] > EMA_long[current_index - 4] \
            and EMA_short[current_index - 3] > EMA_long[current_index - 3] \
            and EMA_short[current_index - 2] > EMA_long[current_index - 2] \
            and EMA_short[current_index - 1] > EMA_long[current_index - 1] \
            and EMA_short[current_index] < EMA_long[current_index]:
        Trade_Direction = 0

    if EMA_short[current_index - 4] < EMA_long[current_index - 4] \
            and EMA_short[current_index - 3] < EMA_long[current_index - 3] \
            and EMA_short[current_index - 2] < EMA_long[current_index - 2] \
            and EMA_short[current_index - 1] < EMA_long[current_index - 1] \
            and EMA_short[current_index] > EMA_long[current_index]:
        Trade_Direction = 1

    return Trade_Direction

'''def pairTrading(Trade_Direction,Close1,Close2,log=0,TPSL=0,percent_TP=0,percent_SL=0):
    new_Close = []
    
    #multiplier = Close1[0]/Close2[0]
    if not log:
        multiplier = (sm.OLS(Close1, Close2).fit()).params[0]
        for i in range(len(Close1)current_index - 20,len(Close1)):
            new_Close.append(Close1[i]-multiplier*Close2[i])
    else:
        log_close1 = []
        log_close2 = []
        for i in range(len(Close1)current_index - 20,len(Close1)):
            log_close1.append(math.log(Close1[i]))
            log_close2.append(math.log(Close2[i]))
        multiplier = (sm.OLS(log_close1, log_close2).fit()).params[0]
        for i in range(len(log_close1)):
            new_Close.append(log_close1[i] - multiplier * log_close2[i])
    BB =np.array(bollinger_pband(pd.Series(new_Close),window_dev=3))
    #BB1 = np.array(bollinger_hband(pd.Series(new_Close),window_dev=3))
    #BB2 = np.array(bollinger_lband(pd.Series(new_Close), window_dev=3))
    #SMA20 = np.array(bollinger_mavg(pd.Series(new_Close)))
    #print(BB[current_index])
    if BB[current_index]>1:
        Trade_Direction = [0,1]  # [1,0]
        
    elif BB[current_index]<0:
        Trade_Direction = [1,0] # [0,1]
        
    return Trade_Direction,[9,9] #,Close1_TP,Close2_TP,Close1_SL,Close2_SL


def pairTrading_Crossover(Trade_Direction, Close1, Close2, CurrentPos, percent_SL=0):
    new_Close = []
    Close_pos=0
    Close1_SL = 0
    Close2_SL = 0
    multiplier = (sm.OLS(Close1, Close2).fit()).params[0]
    for i in range(len(Close1)current_index - 20,len(Close1)):
        new_Close.append(Close1[i]-multiplier*Close2[i])
    BB =np.array(bollinger_pband(pd.Series(new_Close),window_dev=3))
    SMA20 = np.array(bollinger_mavg(pd.Series(new_Close)))
    if BB[current_index]>1:
        Trade_Direction = [0,1]
        Close1_SL = Close1[current_index] * percent_SL
        Close2_SL = Close2[current_index] * percent_SL
    elif BB[current_index]<0:
        Trade_Direction = [1,0]
        Close1_SL = Close1[current_index] * percent_SL
        Close2_SL = Close2[current_index] * percent_SL
    if CurrentPos!=-99:
        if (new_Close[current_index]>SMA20[current_index] and (new_Close[current_index - 1]<SMA20[current_index - 1] or new_Close[current_index - 2]<SMA20[current_index - 2])) or (new_Close[current_index]<SMA20[current_index] and (new_Close[current_index - 1]>SMA20[current_index - 1] or new_Close[current_index - 2]>SMA20[current_index - 2])):
            ##Price has crossed up or down over the Moving average so close the position
            Close_pos=1
    return Trade_Direction,Close1_SL,Close2_SL,Close_pos'''


def SetSLTP(stop_loss_val_arr, take_profit_val_arr, peaks, troughs, Close, High, Low, Trade_Direction, SL, TP, TP_SL_choice, current_index):
    take_profit_val = -99
    stop_loss_val = -99
    match TP_SL_choice:
        case '%':
            take_profit_val = take_profit_val_arr[current_index]
            stop_loss_val = stop_loss_val_arr[current_index]

        case 'x (ATR)':
            take_profit_val = take_profit_val_arr[current_index]
            stop_loss_val = stop_loss_val_arr[current_index]

        case 'x (Swing High/Low) level 1':
            high_swing = High[current_index]
            low_swing = Low[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(TP_SL_choice[-1]), -1, -1):
                if High[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if Low[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and Trade_Direction == 0) or (low_flag == 1 and Trade_Direction == 1):
                    break

            if Trade_Direction == 0:
                print("TP margin:", Close[current_index] - low_swing, 'low_swing:', low_swing, 'Close:', Close[current_index])
                stop_loss_val = SL * (high_swing - Close[current_index])
                take_profit_val = TP * stop_loss_val
            elif Trade_Direction == 1:
                print("TP margin:", high_swing - Close[current_index], 'high_swing:', high_swing, 'Close:', Close[current_index])
                stop_loss_val = SL * (Close[current_index] - low_swing)
                take_profit_val = TP * stop_loss_val

        case 'x (Swing High/Low) level 2':
            high_swing = High[current_index]
            low_swing = Low[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(TP_SL_choice[-1]), -1, -1):
                if High[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if Low[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and Trade_Direction == 0) or (low_flag == 1 and Trade_Direction == 1):
                    break

            if Trade_Direction == 0:
                print("TP margin:", Close[current_index] - low_swing, 'low_swing:', low_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (high_swing - Close[current_index])
                take_profit_val = TP * stop_loss_val
            elif Trade_Direction == 1:
                print("TP margin:", high_swing - Close[current_index], 'high_swing:', high_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (Close[current_index] - low_swing)
                take_profit_val = TP * stop_loss_val

        case 'x (Swing High/Low) level 3':
            high_swing = High[current_index]
            low_swing = Low[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(TP_SL_choice[-1]), -1, -1):
                if High[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if Low[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and Trade_Direction == 0) or (low_flag == 1 and Trade_Direction == 1):
                    break

            if Trade_Direction == 0:
                print("TP margin:", Close[current_index] - low_swing, 'low_swing:', low_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (high_swing - Close[current_index])
                take_profit_val = TP * stop_loss_val
            elif Trade_Direction == 1:
                print("TP margin:", high_swing - Close[current_index], 'high_swing:', high_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (Close[current_index] - low_swing)
                take_profit_val = TP * stop_loss_val

        case 'x (Swing Close) level 1':
            high_swing = Close[current_index]
            low_swing = Close[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(TP_SL_choice[-1]), -1, -1):
                if Close[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if Close[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and Trade_Direction == 0) or (low_flag == 1 and Trade_Direction == 1):
                    break

            if Trade_Direction == 0:
                print("TP margin:", Close[current_index] - low_swing, 'low_swing:', low_swing, 'Close:', Close[current_index])
                stop_loss_val = SL * (high_swing - Close[current_index])
                take_profit_val = TP * stop_loss_val
            elif Trade_Direction == 1:
                print("TP margin:", high_swing - Close[current_index], 'high_swing:', high_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (Close[current_index] - low_swing)
                take_profit_val = TP * stop_loss_val

        case 'x (Swing Close) level 2':
            high_swing = Close[current_index]
            low_swing = Close[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(TP_SL_choice[-1]), -1, -1):
                if Close[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if Close[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and Trade_Direction == 0) or (low_flag == 1 and Trade_Direction == 1):
                    break

            if Trade_Direction == 0:
                print("TP margin:", Close[current_index] - low_swing, 'low_swing:', low_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (high_swing - Close[current_index])
                take_profit_val = TP * stop_loss_val
            elif Trade_Direction == 1:
                print("TP margin:", high_swing - Close[current_index], 'high_swing:', high_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (Close[current_index] - low_swing)
                take_profit_val = TP * stop_loss_val

        case 'x (Swing Close) level 3':
            high_swing = Close[current_index]
            low_swing = Close[current_index]
            high_flag = 0
            low_flag = 0
            ## Check last 300 candles for Swing high/ low
            for i in range(current_index - int(TP_SL_choice[-1]), -1, -1):
                if Close[i] > high_swing and high_flag == 0:
                    if peaks[i] > high_swing and peaks[i] != 0 and high_flag == 0:
                        high_swing = peaks[i]
                        high_flag = 1
                if Close[i] < low_swing and low_flag == 0:
                    if troughs[i] < low_swing and troughs[i] != 0 and low_flag == 0:
                        low_swing = troughs[i]
                        low_flag = 1

                if (high_flag == 1 and Trade_Direction == 0) or (low_flag == 1 and Trade_Direction == 1):
                    break

            if Trade_Direction == 0:
                print("TP margin:", Close[current_index] - low_swing, 'low_swing:', low_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (high_swing - Close[current_index])
                take_profit_val = TP * stop_loss_val
            elif Trade_Direction == 1:
                print("TP margin:", high_swing - Close[current_index], 'high_swing:', high_swing, 'Close:',
                      Close[current_index])
                stop_loss_val = SL * (Close[current_index] - low_swing)
                take_profit_val = TP * stop_loss_val

        case _:
            return

    return stop_loss_val, take_profit_val
