import math
import numpy as np


def sma(period, values):
    '''
    Simple moving average

    >>> sma(3, [3, 4, 5, 9])
    [None, None, 4.0, 6.0]

    '''
    length = len(values)
    result = [None for _ in range(length)]
    if period <= 0:
        return result
    for i in range(length):
        if i < period - 1:
            continue
        result[i] = sum([values[i-j] for j in range(period)]) / period
    return result


def ema(period, values):
    '''
    Exponental moving average

    >>> ema(3, [3, 4, 5, 9])
    [None, None, 4.0, 6.5]

    '''
    length = len(values)
    result = [None for _ in range(length)]
    a = 2 / (period + 1)
    for i in range(length):
        if i < period - 1:
            continue
        if i == period - 1:
            result[i] = sum([values[i-j] for j in range(period)]) / period
        else:
            result[i] = result[i-1] + a * (values[i] - result[i-1])
    return result


def bbands(n, k, values):
    '''
    Bollinger Bands

    n: period
    k: how far from mids
    e.g.) up = mid + k * sigma

    >>> bbands(3, 1, [3, 4, 5, 6])
    ([None, None, 5.0, 6.0], [None, None, 4.0, 5.0], [None, None, 3.0, 4.0])

    '''
    length = len(values)
    mid = sma(n, values)
    sigma = [None for _ in range(length)]
    up = [None for _ in range(length)]
    down = [None for _ in range(length)]
    for i in range(length):
        if i < n - 1:
            continue
        sq_total = sum([values[i-j]**2 for j in range(n)])
        total_sq = sum([values[i-j] for j in range(n)])**2
        sigma[i] = math.sqrt((n*sq_total - total_sq) / n / (n-1))

        up[i] = mid[i] + k * sigma[i]
        down[i] = mid[i] - k * sigma[i]
    return up, mid, down
    

def ichimoku(highs, lows, closes, tenkan_period=9, base_period=26, pre1_shift=26, pre2_period=52, delay_period=26):
    '''
    Ichimoku clouds
    '''
    length = len(closes)

    tenkan = [None for _ in range(length)]
    base = [None for _ in range(length)]
    pre1 = [None for _ in range(length)]
    pre2 = [None for _ in range(length)]

    for i in range(length):
        if i < max((tenkan_period, base_period, pre2_period)):
            continue
        mx = max(highs[i - tenkan_period: i])
        mn = min(lows[i - tenkan_period: i])
        tenkan[i] = (mx + mn) / 2

        mx = max(highs[i - base_period: i])
        mn = min(lows[i - base_period: i])
        base[i] = (mx + mn) / 2

        pre1[i] = (tenkan[i] + base[i]) / 2

        mx = max(highs[i - pre2_period: i])
        mn = min(lows[i - pre2_period: i])
        pre2[i] = (mx + mn) / 2
    
    pre1 = [None for _ in range(pre1_shift)] + pre1
    pre2 = [None for _ in range(pre1_shift)] + pre2

    delay = closes[delay_period:]

    return tenkan, base, pre1, pre2, delay

def rsi(period, values):
    '''
    RSI

    >>> rsi(3, [3, 4, 5, 6, 4])
    [None, None, None, 100.0, 50.0]
    '''
    length = len(values)
    result = [None for _ in range(length)]

    for i in range(length):
        if i < period:
            continue
        up_sum = 0
        down_sum = 0
        for j in range(period):
            diff = values[i-j] - values[i-j-1]
            if diff > 0:
                up_sum += diff
            else:
                down_sum += abs(diff)
        result[i] = (up_sum / (up_sum + down_sum + 10**-10) ) * 100   # avoid zero division
    return result

def macd(short_period, long_period, signal_period, values):
    '''
    MACD
    '''
    length = len(values)
    macd = [None for _ in range(length)]
    short_ema = ema(short_period, values)
    long_ema = ema(long_period, values)
    for i in range(length):
        if i < long_period:
            continue
        macd[i] = short_ema[i] - long_ema[i]
    
    signal = ema(signal_period, macd[long_period:])
    signal = [None for _ in range(long_period)] + signal

    histogram = [None for _ in range(length)]
    for i in range(length):
        if i < max(long_period, signal_period):
            continue

        if macd[i] is None or signal[i] is None:
            histogram[i] = None
        else:
            histogram[i] = macd[i] - signal[i]
    
    return macd, signal, histogram

def historical_volatility(period, values):
    '''
    Historical volatility
    '''
    lenght = len(values)
    result = [None for _ in range(lenght)]
    buffer = [None for _ in range(lenght)]
    for i in range(lenght):
        if i == 0:
            continue

        buffer[i] = math.log(values[i] - values[i-1]/values[i])

        if i < period:
            continue

        sq_mean = sum([buffer[i-j]**2 for j in range(period)]) / period
        mean_sq = (sum([buffer[i-j] for j in range(period)]) / period)**2
        result[i] = math.sqrt(sq_mean - mean_sq) * 100
    return result


if __name__ == '__main__':
    import doctest
    doctest.testmod()