import numpy as np
from Logger import *
import BotClass

def get_all_symbols(client, coin_exclusion_list):
    ''' Function that returns the list of trade-able USDT symbols & removes coins you've added to your exclusion list in live_trading_config.py '''
    x = client.futures_exchange_info()['symbols']
    symbols_to_trade = [y['symbol'] for y in x if (y['status'] == 'TRADING' and
                                                   'USDT' in y['symbol'] and '_' not in y['symbol'] and
                                                   y['symbol'] not in coin_exclusion_list)]
    return symbols_to_trade


def compare_indicators(keys, indicators_buffer, indicators_actual):
    ''' Function to compare the indicators for calculating the required buffer size '''
    try:
        error_percent = []
        for key in keys:
            if isinstance(indicators_buffer[key]['values'], list):
                error_percent.append(abs(sum([(actual - buffer) / actual for actual, buffer in zip(indicators_actual[key]['values'][-30:], indicators_buffer[key]['values'][-30:])])))
            else:
                error_percent.append((indicators_actual[key]['values'] - indicators_buffer[key]['values']) / indicators_actual[key]['values'])
        return sum(error_percent) / len(keys)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        log.warning(f"compare_indicators() - Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")



def get_required_buffer(trading_strategy):
    ''' Function to calculate the buffer for your strategy to use, ensuring accurate signals '''
    log.info('get_required_buffer() - Calculating the required buffer for your strategy...')
    # Create an array of random float elements
    np.random.seed(5)
    ran_arr_open = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(300)
    ran_arr_close = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(44)
    ran_arr_high = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(29)
    ran_arr_low = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(78)
    ran_arr_volume = np.random.uniform(size=20000, low=2, high=100_000_000)

    actual_values_bot = BotClass.Bot('actual_values_bot', ran_arr_open, ran_arr_close, ran_arr_high,
                                      ran_arr_low, ran_arr_volume, [], 3, 4, 0, 1, trading_strategy, '%',
                                      1, 1, 1)
    buffer_bot: BotClass.Bot
    for i in range(30, 20000):
        try:
            ## Calculate indicators for this size of buffer
            buffer_bot = BotClass.Bot('buffer_bot', ran_arr_open[-i:], ran_arr_close[-i:], ran_arr_high[-i:],
                                       ran_arr_low[-i:], ran_arr_volume[-i:], [], 3, 4, 0, 1, trading_strategy,
                                       '%',
                                       1, 1, 1)
            ## Compare the indicators of actual_values_bot & buffer_bot until the error % is less than .1%
            keys = buffer_bot.indicators.keys()
            error_percent = compare_indicators(keys, buffer_bot.indicators, actual_values_bot.indicators)
            log.debug(f'Error Percent is {error_percent} with a buffer of {i} candles')
            if error_percent < .00001:
                return i
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f"get_required_buffer() - Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")