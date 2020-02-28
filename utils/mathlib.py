import math
import numpy as np


def sma(period, values):
    length = len(values)
    result = [None for _ in range(length)]
    for i in range(length):
        if i >= period:
            tmp = 0
            for j in range(period):
                tmp += values[i-j]
            result[i] = tmp / period
    return result


def ema(period, values):
    length = len(values)
    result = [None for _ in range(length)]
    a = 2 / (period + 1)
    start = period
    for i in range(length):
        if i < start:
            continue

        tmp = 0
        if i == start:
            if values[i - period] is None:
                start += 1
                continue
            for j in range(period):
                tmp += values[i - j]
            tmp /= period
        else:
            tmp = result[i-1] + a * (values[i] - result[i-1])
        result[i] = tmp
    return result


def bbands(n, k, values):
    """
    n: period
    k: how far from mids
    e.g.) up = mid + k * sigma
    """
    length = len(values)
    mid = sma(n, values)
    sigma = [None for _ in range(length)]
    for i in range(length):
        if i >= n:
            tmp1 = 0
            tmp2 = 0
            for j in range(n):
                tmp1 += values[i - j]**2
                tmp2 += values[i - j]
            sq_mean = tmp1
            mean_sq = tmp2**2
            sigma[i] = math.sqrt((n*sq_mean - mean_sq) / n / (n-1))
        
    up = [None for _ in range(length)]
    down = [None for _ in range(length)]
    for i in range(length):
        if i >= n:
            up[i] = mid[i] + k * sigma[i]
            down[i] = mid[i] - k * sigma[i]
    return up, mid, down
    

def ichimoku(highs, lows, closes, tenkan_period=9, base_period=26, pre1_shift=26, pre2_period=52, delay_period=26):
    length = len(closes)

    tenkan = [None for _ in range(length)]
    base = [None for _ in range(length)]
    pre1 = [None for _ in range(length)]
    pre2 = [None for _ in range(length)]

    for i in range(length):
        if i >= tenkan_period:
            mx = max(highs[i - tenkan_period: i])
            mn = min(lows[i - tenkan_period: i])
            tenkan[i] = (mx + mn) / 2

        if i >= base_period:
            mx = max(highs[i - base_period: i])
            mn = min(lows[i - base_period: i])
            base[i] = (mx + mn) / 2

        if i >= max(tenkan_period, base_period):
            pre1[i] = (tenkan[i] + base[i]) / 2

        if i >= pre2_period:
            mx = max(highs[i - pre2_period: i])
            mn = min(lows[i - pre2_period: i])
            pre2[i] = (mx + mn) / 2
    
    pre1.reverse()
    pre1.extend([None for _ in range(pre1_shift)])
    pre1.reverse()
    pre2.reverse()
    pre2.extend([None for _ in range(pre1_shift)])
    pre2.reverse()

    delay = closes[delay_period:]

    return tenkan, base, pre1, pre2, delay

def rsi(period, values):
    length = len(values)
    result = [None for _ in range(length)]

    for i in range(length):
        if i >= period:
            up_sum = 0
            down_sum = 0
            for j in range(period):
                diff = values[i-j] - values[i-j-1]
                if diff > 0:
                    up_sum += diff
                else:
                    down_sum += abs(diff)
            result[i] = (up_sum / (up_sum + down_sum) ) * 100
    return result

def macd(short_period, long_period, signal_period, values):
    length = len(values)
    macd = [None for _ in range(length)]
    short_ema = ema(short_period, values)
    long_ema = ema(long_period, values)
    for i in range(length):
        if i >= long_period:
            macd[i] = short_ema[i] - long_ema[i]
    
    signal = ema(signal_period, macd.copy())

    histogram = [None for _ in range(length)]
    for i in range(length):
        if i >= max(long_period, signal_period):
            if macd[i] is None or signal[i] is None:
                histogram[i] = None
            else:
                histogram[i] = macd[i] - signal[i]
    
    return macd, signal, histogram

def historical_volatility(period, values):
    lenght = len(values)
    result = [None for _ in range(lenght)]
    buffer = [None for _ in range(lenght)]
    for i in range(lenght):
        if i >= 1:
            buffer[i] = math.log(values[i]/values[i-1])
        if i >= period:
            tmp1 = 0
            tmp2 = 0
            for j in range(period):
                tmp1 += buffer[i-j]**2
                tmp2 += buffer[i-j]
            sq_mean = tmp1 / period
            mean_sq = (tmp2 / period)**2
            result[i] = math.sqrt(math.sqrt(sq_mean - mean_sq)) * 100
    return result