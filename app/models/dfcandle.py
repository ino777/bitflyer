import logging
from dataclasses import dataclass
from typing import List

from config import config
from utils import mathlib
from utils.logsettings import getLogger
from . import candle, events, trade


logger = getLogger(__name__)


@dataclass
class Sma(object):
    '''
    Simple moving average
    '''
    period: int
    values: List[float]

@dataclass
class Ema(object):
    '''
    Exponential moving average
    '''
    period: int
    values: List[float]

@dataclass
class Bbands(object):
    '''
    Bollinger Band
    '''
    n: int
    k: int
    up: List[float]
    mid: List[float]
    down: List[float]

@dataclass
class Ichimoku(object):
    '''
    Ichimoku clouds
    '''
    tenkan_period: int
    base_period: int
    pre1_shift: int
    pre2_period: int
    delay_period: int
    tenkan: List[float]
    base: List[float]
    pre1: List[float]
    pre2: List[float]
    delay: List[float]

@dataclass
class Rsi(object):
    '''
    Relative strength index
    '''
    period: int
    values: List[float]

@dataclass
class Macd(object):
    '''
    MACD
    '''
    short_period: int
    long_period: int
    signal_period: int
    macd: List[float]
    signal: List[float]
    histogram: List[float]


@dataclass
class HV(object):
    '''
    Historical Volatility
    '''
    period: int
    values: List[float]


@dataclass
class TradeParams(object):
    '''
    Trade Params
    '''
    ema_enable: bool
    ema_period1: int
    ema_period2: int

    bb_enable: bool
    bb_n: int
    bb_k: int

    ichimoku_enable: bool

    macd_enable: bool
    macd_short_period: int
    macd_long_period: int
    macd_signal_period: int

    rsi_enable: bool
    rsi_period: int
    rsi_buy_thread: int
    rsi_sell_thread: int


class Ranking(object):
    def __init__(self, performance, enable=False):
        self.performance = performance
        self.enable = enable

class Rankings(object):
    def __init__(self, rankings):
        self.rankings = []
        for ranking in rankings:
            if type(ranking) != Ranking:
                continue
            self.rankings.append(ranking)
    
    def _sort_by_performance(self, arr, reverse):
        if len(arr) <= 1:
            return arr
        before = []
        after = []
        base = arr[0]

        for e in arr:
            if e.performance < base.performance:
                before.append(e)
            elif e.performance > base.performance:
                after.append(e)
        
        before = self._sort_by_performance(before, reverse)
        after = self._sort_by_performance(after, reverse)

        if reverse:
            return after + [base] + before
        return before + [base] + after


    def sort_by_performance(self, reverse=True):
        dummy_rankings = self.rankings.copy()
        self.rankings = self._sort_by_performance(dummy_rankings, reverse)


class DataFrameCandle(object):
    '''
    Dataframe of candales
    '''
    def __init__(self, product_code, duration, candles):
        self.product_code = product_code
        self.duration = duration
        self.candles = candles
        self.events = None      # Signal Events
        self.smas = []          # [sma(period1), sma(period2), ...]
        self.emas = []          # [ema(period1), ema(period2), ...]
        self.bbands = None
        self.ichimoku = None
        self.rsi = None
        self.macd = None
        self.hvs = []            # [hv(period1), hv(period2), ...]


    def getall(self):
        data =  {
            'product_code': self.product_code,
            'duration': self.duration,
            'candles': [c.__dict__ for c in self.candles]
        }
        if self.events:
            data['events'] = self.events.data()
        if self.smas:
            data['smas'] = [sma.__dict__ for sma in self.smas]
        if self.emas:
            data['emas'] = [ema.__dict__ for ema in self.emas]
        if self.bbands:
            data['bbands'] = self.bbands.__dict__
        if self.ichimoku:
            data['ichimoku'] = self.ichimoku.__dict__
        if self.rsi:
            data['rsi'] = self.rsi.__dict__
        if self.macd:
            data['macd'] = self.macd.__dict__
        if self.hvs:
            data['hvs'] = [hv.__dict__ for hv in self.hvs]
        
        return data

    def times(self):
        return [c.time for c in self.candles]
    
    def opens(self):
        return [c.open for c in self.candles]

    def closes(self):
        return [c.close for c in self.candles]

    def highs(self):
        return [c.high for c in self.candles]
    
    def lows(self):
        return [c.low for c in self.candles]

    def volumes(self):
        return [c.volume for c in self.candles]
    
    def set_events(self, signal_events):
        if type(signal_events) != events.SignalEvents:
            raise TypeError('Require <class \'SignalEvents\'>')
        self.events = signal_events

    def add_events(self, time):
        signal_events = events.get_signal_events_after_time(time)
        if signal_events:
            self.events = signal_events
            return True
        return False

    def add_sma(self, period):
        if len(self.candles) > period:
            self.smas.append(
                Sma(period, mathlib.sma(period, self.closes()))
            )
            return True
        return False

    def add_ema(self, period):
        if len(self.candles) > period:
            self.emas.append(
                Ema(period, mathlib.ema(period, self.closes()))
            )
            return True
        return False
    
    def add_bbands(self, n, k):
        if len(self.candles) > n:
            up, mid, down = mathlib.bbands(n, k, self.closes())
            self.bbands = Bbands(n, k, up, mid, down)
            return True
        return False
    
    def add_ichimoku(self, tenkan_period, base_period, pre1_shift, pre2_period, delay_period):
        if len(self.candles) > max(tenkan_period, base_period, pre2_period, delay_period):
            tenkan, base, pre1, pre2, delay = mathlib.ichimoku(
                self.highs(), self.lows(), self.closes(), tenkan_period, base_period, pre1_shift, pre2_period, delay_period
            )
            self.ichimoku = Ichimoku(
                tenkan_period, base_period, pre1_shift, pre2_period, delay_period,
                tenkan, base, pre1, pre2, delay
            )
            return True
        return False
    
    def add_rsi(self, period):
        if len(self.candles) > period:
            values = mathlib.rsi(period, self.closes())
            self.rsi = Rsi(period, values)
            return True
        return False
    
    def add_macd(self, short_period, long_period, signal_period):
        if short_period >= long_period:
            logger.error({
                'action': 'DataFrameCandle:add_macd',
                'args': {'Short Period': short_period, 'Long Period' : long_period},
                'error': 'Short period must be shorter than long period'
            })
            return False
        if len(self.candles) > max(long_period, signal_period):
            macd, signal, histogram = mathlib.macd(short_period, long_period, signal_period, self.closes())
            self.macd = Macd(short_period, long_period, signal_period, macd, signal, histogram)
            return True
        return False
    
    def add_hv(self, period):
        if len(self.candles) > period:
            values = mathlib.historical_volatility(period, self.closes())
            self.hvs.append(
                HV(period, values)
            )
            return True
        return False

    def back_test_ema(self, period1, period2):
        '''
        EMA simulation
        '''
        len_candles = len(self.candles)
        if len_candles < period1 or len_candles < period2:
            return
        
        signal_events = events.SignalEvents([])
        ema_value1 = mathlib.ema(period1, self.closes())
        ema_value2 = mathlib.ema(period2, self.closes())

        trade_model = trade.TradeEma(ema_value1, ema_value2, period1, period2)

        for i in range(1, len_candles):
            if trade_model.should_buy(i):
                signal_events.buy(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
            
            if trade_model.should_sell(i):
                signal_events.sell(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
        return signal_events
    
    def optimize_ema(self):
        '''
        Obtains optimized EMA parameters by brute force method
        '''
        performance = 0.0
        best_period1 = 7
        best_period2 = 14

        for period1 in range(5, 12):
            for period2 in range(12, 20):
                signal_events = self.back_test_ema(period1, period2)
                if not signal_events or not signal_events.signals:
                    continue
                profit = signal_events.profit()
                if performance < profit:
                    performance = profit
                    best_period1 = period1
                    best_period2 = period2
        return performance, best_period1, best_period2

    def back_test_bb(self, n, k):
        '''
        bbands simulation
        '''
        len_candles = len(self.candles)
        if len_candles < n:
            return
        
        signal_events = events.SignalEvents([])
        bb_up, bb_mid, bb_down = mathlib.bbands(n, k, self.closes())

        trade_model = trade.TradeBb(bb_up, bb_mid, bb_down, n, k)

        for i in range(1, len_candles):
            if trade_model.should_buy(i, self.candles):
                signal_events.buy(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
            
            if trade_model.should_sell(i, self.candles):
                signal_events.sell(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
        return signal_events

    def optimize_bb(self):
        '''
        Obtains optimized bbands parameters by brute force method
        '''
        performance = 0.0
        best_n = 20
        best_k = 2.0

        for n in range(10, 20):
            for k in (i/10 for i in range(17, 23)):
                signal_events = self.back_test_bb(n, k)
                if not signal_events or not signal_events.signals:
                    continue
                profit = signal_events.profit()
                if performance < profit:
                    performance = profit
                    best_n = n
                    best_k = k
        return performance, best_n, best_k
    
    def back_test_ichimoku(self):
        '''
        Ichimoku simulation
        '''
        len_candles = len(self.candles)
        if len_candles < 52:
            return
        
        signal_events = events.SignalEvents([])
        tenkan, base, pre1, pre2, delay = mathlib.ichimoku(self.highs(), self.lows(), self.closes())

        trade_model = trade.TradeIchimoku(tenkan, base, pre1, pre2, delay)
        
        for i in range(1, len(delay)):
            if trade_model.should_buy(i, self.candles):
                signal_events.buy(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
            
            if trade_model.should_sell(i, self.candles):
                signal_events.sell(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
        return signal_events

    def optimize_ichimoku(self):
        signal_events = self.back_test_ichimoku()
        if not signal_events or not signal_events.signals:
            return 0.0
        return signal_events.profit()

    def back_test_macd(self, short_period, long_period, signal_period):
        '''
        MACD simulation
        '''
        len_candles = len(self.candles)
        if len_candles < long_period:
            return
        
        signal_events = events.SignalEvents([])
        macd, signal, histogram = mathlib.macd(short_period, long_period, signal_period, self.closes())

        trade_model = trade.TradeMacd(macd, signal, histogram, short_period, long_period, signal_period)

        for i in range(1, len_candles):
            if trade_model.should_buy(i):
                signal_events.buy(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
            
            if trade_model.should_sell(i):
                signal_events.sell(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
        return signal_events
    
    def optimize_macd(self):
        '''
        Obtains optimized MACD parameters by brute force method
        '''
        performance = 0.0
        best_short_period = 12
        best_long_period = 26
        best_signal_period = 9

        for short_p in range(10, 20):
            for long_p in range(20, 30):
                for signal_p in range(5, 15):
                    signal_events = self.back_test_macd(short_p, long_p, signal_p)
                    if not signal_events or not signal_events.signals:
                        continue
                    profit = signal_events.profit()
                    if performance < profit:
                        performance = profit
                        best_short_period = short_p
                        best_long_period = long_p
                        best_signal_period = signal_p
        return performance, best_short_period, best_long_period, best_signal_period

    def back_test_rsi(self, period, buy_thread, sell_thread):
        '''
        RSI simulation
        '''
        len_candles = len(self.candles)
        if len_candles < period:
            return
        
        signal_events = events.SignalEvents([])
        rsi_value = mathlib.rsi(period, self.closes())

        trade_model = trade.TradeRsi(rsi_value, period, buy_thread, sell_thread)
        
        for i in range(1, len_candles):
            if trade_model.should_buy(i):
                signal_events.buy(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
            
            if trade_model.should_sell(i):
                signal_events.sell(self.product_code, self.candles[i].time, self.candles[i].close, 1.0, False)
        return signal_events
    
    def optimize_rsi(self):
        '''
        Obtains optimiszed RSI parameters by brute force method
        '''
        performance = 0.0
        best_period = 14
        best_buy_thread = 30
        best_sell_thread = 70

        for period in range(10, 20):
            for buy_thread in range(27, 33):
                for sell_thread in range(67, 73):
                    signal_events = self.back_test_rsi(period, buy_thread, sell_thread)
                    if not signal_events or not signal_events.signals:
                        continue
                    profit = signal_events.profit()
                    if performance < profit:
                        performance = profit
                        best_period = period
                        best_buy_thread = buy_thread
                        best_sell_thread = sell_thread
        
        return performance, best_period, best_buy_thread, best_sell_thread
    
    def optimize_params(self):
        '''
        Returns optimized trade parameters.
        
        '''
        ema_performance, ema_period1, ema_period2 = self.optimize_ema()
        bb_performance, bb_n, bb_k = self.optimize_bb()
        macd_performance, macd_short_period, macd_long_period, macd_signal_period = self.optimize_macd()
        rsi_performance, rsi_period, rsi_buy_thread, rsi_sell_thread = self.optimize_rsi()

        ema_ranking = Ranking(ema_performance)
        bb_ranking = Ranking(bb_performance)
        macd_ranking = Ranking(macd_performance)
        rsi_ranking = Ranking(rsi_performance)

        rankings = Rankings([ema_ranking, bb_ranking, macd_ranking, rsi_ranking])
        rankings.sort_by_performance()
        
        is_enable = False
        for i, ranking in enumerate(rankings.rankings):
            if i >= config.Config.num_ranking:
                break
            if ranking.performance > 0:
                ranking.enable = True
                is_enable = True
        
        # If all indicators are not enable
        if not is_enable:
            return None

        trade_params = TradeParams(
            ema_enable = ema_ranking.enable,
            ema_period1 = ema_period1,
            ema_period2 = ema_period2,
            bb_enable = bb_ranking.enable,
            bb_n = bb_n,
            bb_k = bb_k,
            ichimoku_enable = False,
            macd_enable = macd_ranking.enable,
            macd_short_period = macd_short_period,
            macd_long_period = macd_long_period,
            macd_signal_period = macd_signal_period,
            rsi_enable = rsi_ranking.enable,
            rsi_period = rsi_period,
            rsi_buy_thread = rsi_buy_thread,
            rsi_sell_thread = rsi_sell_thread
        )

        return trade_params
