
class TradeEma(object):
    def __init__(self, value1, value2, period1, period2):
        self.value1 = value1
        self.value2 = value2
        self.period1 = period1
        self.period2 = period2

    def should_buy(self, index):
        if index < self.period1 or index < self.period2:
            return False
        if self.value1[index-1] is None or self.value2[index-1] is None:
            return False
        if self.value1[index-1] < self.value2[index-1] and self.value1[index] >= self.value2[index]:
            return True
        return False
    
    def should_sell(self, index):
        if index < self.period1 or index < self.period2:
            return False
        if self.value1[index-1] is None or self.value2[index-1] is None:
            return False
        if self.value1[index-1] > self.value2[index-1] and self.value1[index] <= self.value2[index]:
            return True
        return False

class TradeBb(object):
    def __init__(self, up, mid, down, n, k):
        self.up = up
        self.mid = mid
        self.down = down
        self.n = n
        self.k = k
    
    def should_buy(self, index, candles):
        if index < self.n:
            return False
        if self.up[index-1] is None or self.mid[index-1] is None or self.down[index-1] is None:
            return False
        if self.down[index-1] > candles[index-1].close and self.down[index] <= candles[index].close:
            return True
        return False
    
    def should_sell(self, index, candles):
        if index < self.n:
            return False
        if self.up[index-1] is None or self.mid[index-1] is None or self.down[index-1] is None:
            return False
        if self.up[index-1] < candles[index-1].close and self.up[index] >= candles[index].close:
            return True
        return False

class TradeIchimoku(object):
    def __init__(self, tenkan, base, pre1, pre2, delay):
        self.tenkan = tenkan
        self.base = base
        self.pre1 = pre1
        self.pre2 = pre2
        self.delay = delay
    
    def should_buy(self, index, candles):
        if index < 52:
            return False
        if self.tenkan[index] is None or self.base[index] is None or self.pre1[index] is None or self.pre2[index] is None or self.delay[index-1] is None:
            return False
        if (self.delay[index-1] < candles[index-1].high
                    and self.delay[index] >= candles[index].high
                    and self.pre1[index] < candles[index].low
                    and self.pre2[index] < candles[index].low
                    and self.tenkan[index] > self.base[index]):
            return True
        return False
    
    def should_sell(self, index, candles):
        if index < 52:
            return False
        if self.tenkan[index] is None or self.base[index] is None or self.pre1[index] is None or self.pre2[index] is None or self.delay[index-1] is None:
            return False
        if (self.delay[index-1] > candles[index-1].high
            and self.delay[index] <= candles[index].high
            and self.pre1[index] > candles[index].low
            and self.pre2[index] > candles[index].low
            and self.tenkan[index] < self.base[index]):
            return True
        return False

class TradeMacd(object):
    def __init__(self, macd, signal, histogram, short_period, long_period, signal_period):
        self.macd = macd
        self.signal = signal
        self.histogram = histogram
        self.short_period = short_period
        self.long_period = long_period
        self.signal_period = signal_period
    
    def should_buy(self, index):
        if index < self.long_period:
            return False
        if self.macd[index] is None or self.signal[index] is None or self.histogram[index-1] is None:
            return False
        if self.macd[index] < 0 and self.signal[index] < 0 and self.histogram[index-1] < 0 and self.histogram[index] >= 0:
            return True
        return False
    
    def should_sell(self, index):
        if index < self.long_period:
            return False
        if self.macd[index] is None or self.signal[index] is None or self.histogram[index-1] is None:
            return False
        if self.macd[index] > 0 and self.signal[index] > 0 and self.histogram[index-1] > 0 and self.histogram[index] <= 0:
            return True
        return False

class TradeRsi(object):
    def __init__(self, value, period, buy_thread, sell_thread):
        self.value = value
        self.preiod = period
        self.buy_thread = buy_thread
        self.sell_thread = sell_thread
    
    def should_buy(self, index):
        if index < self.preiod:
            return False
        if self.value[index-1] is None:
            return False
        if self.value[index-1] < self.buy_thread and self.value[index] >= self.buy_thread:
            return True
        return False
    
    def should_sell(self, index):
        if index < self.preiod:
            return False
        if self.value[index-1] is None:
            return False
        if self.value[index-1] > self.sell_thread and self.value[index] <= self.sell_thread:
            return True
        return False