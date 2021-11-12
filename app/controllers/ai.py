import time
import datetime
import logging
import threading

from bitflyer import bitflyer
from config import config
from app.models import events, candle, dfcandle, trade
from utils import mathlib


logger = logging.getLogger(__name__)
''' Logger Config '''
handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(config.Config.log_stream_level)
stream_handler.setFormatter(handler_format)

logger.addHandler(stream_handler)


API_FEE_PERCENT = 0.0012

class AI(object):
    '''
    自動売買システム
    '''
    def __init__(self, product_code, use_percent, duration, past_period, stop_limit_percent, back_test):
        self.api = bitflyer.APIClient(config.Config.api_key, config.Config.api_secret)
        self.product_code = product_code
        self.coin_code = product_code.split('_')[0]
        self.currency_code = product_code.split('_')[1]
        self.use_percent = use_percent
        self.minute_to_expires = 1
        self.duration = duration
        self.past_period = past_period
        if back_test:
            self.signal_events = events.SignalEvents([])
        else:
            self.signal_events = events.get_signal_events_by_count(1)
        self.trade_semaphore = threading.Semaphore(1)
        self.back_test = back_test
        self.start_trade = datetime.datetime.now()
        self.stop_limit = 0.0
        self.stop_limit_percent = stop_limit_percent

        self.optimize_params = None
        self.update_optimize_params(False)
    
    def update_optimize_params(self, is_continue):
        df = candle.get_all_candles(self.product_code, self.duration, self.past_period)
        self.optimize_params = df.optimize_params() if df else None
        if self.optimize_params is None and is_continue and not self.back_test:
            time.sleep(10*config.Config.durations[self.duration])
            self.update_optimize_params(is_continue)
    
    def buy(self, candle:candle.Candle):
        if self.back_test:
            could_buy = self.signal_events.buy(self.product_code, candle.time, candle.close, 1.0, False)
            return '', could_buy
        
        if self.start_trade > candle.time:
            return
        if not self.signal_events.can_buy(candle.time):
            return
        
        available_currency, _ = self.get_available_balance()
        use_currency = available_currency * self.use_percent
        ticker = self.api.get_ticker(self.product_code)
        size = use_currency / ticker.best_ask
        size = self.adjust_size(size)

        order = bitflyer.Order(
            product_code = self.product_code,
            child_order_type = 'MARKET',
            side = 'BUY',
            size = size,
            minute_to_expire = self.minute_to_expires,
            time_in_force = 'GTC'
        )
        resp = self.api.send_order(order)
        acceptance_id = resp.child_order_acceptance_id
        if not acceptance_id:
            logger.warning({
                'order': order.__dict__,
                'status': 'No ID'
            })
        
        is_order_completed = self.wait_until_order_complete(acceptance_id, candle.time)
        return acceptance_id, is_order_completed
    
    def sell(self, candle:candle.Candle):
        if self.back_test:
            could_sell = self.signal_events.sell(self.product_code, candle.time, candle.close, 1.0, False)
            return '', could_sell
        
        if self.start_trade > candle.time:
            return
        if not self.signal_events.can_sell(candle.time):
            return
        
        _, available_coin = self.get_available_balance()
        size = self.adjust_size(available_coin)
        order = bitflyer.Order(
            product_code = self.product_code,
            child_order_type = 'MARKET',
            side = 'SELL',
            size = size,
            minute_to_expire = self.minute_to_expires,
            time_in_force = 'GTC'
        )
        resp = self.api.send_order(order)
        acceptance_id = resp.child_order_acceptance_id
        if not acceptance_id:
            logger.warning({
                'order': order.__dict__,
                'status': 'No ID'
            })
        
        is_order_completed = self.wait_until_order_complete(acceptance_id, candle.time)
        return acceptance_id, is_order_completed
    
    def trade(self):
        if not self.trade_semaphore.acquire(blocking=False):
            return
        params = self.optimize_params
        if params is None:
            logger.error('optimized params not found!')
            return
        logger.debug({
            'action': 'AI:trade',
            'params': params.__dict__
        })
        df = candle.get_all_candles(self.product_code, self.duration, self.past_period)

        # Calculate indicator values
        if params.ema_enable:
            ema_value1 = mathlib.ema(params.ema_period1, df.closes())
            ema_value2 = mathlib.ema(params.ema_period2, df.closes())
            ema_trade_model = trade.TradeEma(ema_value1, ema_value2, params.ema_period1, params.ema_period2)
        
        if params.bb_enable:
            bb_up, bb_mid, bb_down = mathlib.bbands(params.bb_n, params.bb_k, df.closes())
            bb_trade_model = trade.TradeBb(bb_up, bb_mid, bb_down, params.bb_n, params.bb_k)
        
        if params.ichimoku_enable:
            ichimoku_tenkan, ichimoku_base, ichimoku_pre1, ichimoku_pre2, ichimoku_delay = mathlib.ichimoku(df.highs(), df.lows(), df.closes())
            ichimoku_trade_model = trade.TradeIchimoku(ichimoku_tenkan, ichimoku_base, ichimoku_pre1, ichimoku_pre2, ichimoku_delay)
        
        if params.macd_enable:
            macd, macd_signal, macd_histogram = mathlib.macd(
                params.macd_short_period, params.macd_long_period, params.macd_signal_period, df.closes())
            macd_trade_model = trade.TradeMacd(macd, macd_signal, macd_histogram, params.macd_short_period, params.macd_long_period, params.macd_signal_period)
        
        if params.rsi_enable:
            rsi_value = mathlib.rsi(params.rsi_period, df.closes())
            rsi_trade_model = trade.TradeRsi(rsi_value, params.rsi_period, params.rsi_buy_thread, params.rsi_sell_thread)
        
        # Count buy/sell point
        for i in range(len(df.candles)):
            buy_poinst, sell_point = 0, 0
            if params.ema_enable:
                if ema_trade_model.should_buy(i):
                    buy_poinst += 1
                if ema_trade_model.should_sell(i):
                    sell_point += 1
            
            if params.bb_enable:
                if bb_trade_model.should_buy(i, df.candles):
                    buy_poinst += 1
                if bb_trade_model.should_sell(i, df.candles):
                    sell_point += 1
            
            if params.ichimoku_enable:
                if ichimoku_trade_model.should_buy(i, df.candles):
                    buy_poinst += 1
                if ichimoku_trade_model.should_sell(i, df.candles):
                    sell_point += 1
            
            if params.macd_enable:
                if macd_trade_model.should_buy(i):
                    buy_poinst += 1
                if macd_trade_model.should_sell(i):
                    sell_point += 1
            
            if params.rsi_enable:
                if rsi_trade_model.should_buy(i):
                    buy_poinst += 1
                if rsi_trade_model.should_sell(i):
                    sell_point += 1
            
            if buy_poinst > 0:
                _, is_order_complited = self.buy(df.candles[i])
                if not is_order_complited:
                    continue
                self.stop_limit = df.candles[i].close * self.stop_limit_percent
            
            if sell_point > 0 or df.candles[i].close < self.stop_limit:
                _, is_order_complited = self.sell(df.candles[i])
                if not is_order_complited:
                    continue
                self.stop_limit = 0.0
                self.update_optimize_params(True)
            
        self.trade_semaphore.release()
    
    def get_available_balance(self):
        balances = self.api.get_balance()
        for balance in balances:
            if balance.currency_code == self.currency_code:
                available_currency = balance.available
            elif balance.currency_code == self.coin_code:
                available_coin = balance.amount
        return available_currency, available_coin
    
    def adjust_size(self, size):
        fee = size * API_FEE_PERCENT
        size = size - fee
        return int(size*10000) / 10000
    
    def is_order_completed(self, query, execute_time):
        list_orders = self.api.list_order(query)
        if not list_orders:
            logger.info('List order is empty')
            return False
        order = list_orders[0]
        if order.child_order_state == 'COMPLETED':
            if order.side == 'BUY':
                could_buy = self.signal_events.buy(self.product_code, execute_time, order.avarage_price, order.size, True)
                if not could_buy:
                    logger.warning({
                        'status': 'buy',
                        'order': order.__dict__
                    })
                return could_buy
            if order.side == 'SELL':
                could_sell = self.signal_events.sell(self.product_code, execute_time, order.avarage_price, order.size, True)
                if not could_buy:
                    logger.warning({
                        'stauts': 'sell',
                        'order': order.__dict__
                    })
                return could_sell
        return False
    
    def wait_until_order_complete(self, child_order_acceptance_id, execute_time):
        params = {
            'product_code': self.product_code,
            'child_order_acceptance_id': child_order_acceptance_id
        }
        expire_sec = 60
        interval_sec = 15
        expire = threading.Thread(target=time.sleep, args=(expire_sec,))
        expire.setDaemon(True)
        expire.start()
        interval = threading.Thread(target=time.sleep, args=(interval_sec,))
        interval.setDaemon(True)
        interval.start()
        
        while expire.is_alive():
            if not interval.is_alive():
                if self.is_order_completed(params, execute_time):
                    return True
                interval = threading.Thread(target=time.sleep, args=(interval_sec,))
                interval.setDaemon(True)
                interval.start()
        return False

                

        


TRADE_AI = AI(
    config.Config.product_code, config.Config.use_percent, config.Config.trade_duration,
    config.Config.data_limit, config.Config.stop_limit_percent, config.Config.back_test)
