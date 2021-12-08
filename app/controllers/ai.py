import time
import datetime
import logging
import threading

from bitflyer import bitflyer
from config import config
from app.models import events, candle, dfcandle, trade
from utils import mathlib
from utils.logsettings import getLogger

logger = getLogger(__name__)

trade_logger = getLogger(__name__ + "trade", log_file=config.Config.trade_log_file, file_level=config.Config.trade_log_file_level)

API_FEE_PERCENT = 0.0012
BACKTEST_TRADE_SIZE = 1.0

class AI(object):
    '''
    自動売買システム
    '''
    def __init__(self, product_code, use_percent, duration, past_period, stop_limit_percent, back_test):
        # APIClient
        self.api = bitflyer.APIClient(config.Config.api_key, config.Config.api_secret)

        # Product code
        self.product_code = product_code
        # Coin code
        self.coin_code = product_code.split('_')[0]
        # currency code
        self.currency_code = product_code.split('_')[1]
        # Order settings
        self.use_percent = use_percent
        self.minute_to_expires = 1
        # duration
        self.duration = duration
        # Period
        self.past_period = past_period
        # Simulation version
        self.back_test = back_test
        if back_test:
            self.signal_events = events.SignalEvents([])
        else:
            self.signal_events = events.get_signal_events_by_count(1)

        # Semaphore
        self.trade_semaphore = threading.Semaphore(1)

        # Start trade time
        self.start_trade = datetime.datetime.now()
        # Last calculate candle time
        self.last_time = datetime.datetime.min
        # Stop limit
        self.stop_limit = 0.0
        self.stop_limit_percent = stop_limit_percent

        # Optimized parameters
        self.optimize_params = None


        self.update_optimize_params()
    
    def update_optimize_params(self):
        '''
        Update optimized trade parameters
        '''
        df = candle.get_all_candles(self.product_code, self.duration, self.past_period)
        self.optimize_params = df.optimize_params() if df else None
        logger.debug({
            'action': 'AI:update_optimize_params',
            'params': self.optimize_params
        })
    
    def buy(self, candle:candle.Candle):
        '''
        Buy bit coin
        '''
        # Simulation
        if self.back_test:
            trade_logger.debug({
                'status': 'try to order',
                'side': 'BUY',
                'price': candle.close,
                'size': BACKTEST_TRADE_SIZE,
                'back_test': True,
            })

            could_buy = self.signal_events.buy(self.product_code, candle.time, candle.close, BACKTEST_TRADE_SIZE, False)

            trade_logger.debug({
                'status': 'finish order',
                'side': 'BUY',
                'is_order_completed': could_buy
            })
            return '', could_buy
        
        # 以下, 実際に購入する手続き
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

        trade_logger.debug({
            'status': 'try to order',
            'side': 'BUY',
            'size': size,
            'back_test': False
        })

        resp = self.api.send_order(order)
        acceptance_id = resp.child_order_acceptance_id
        if not acceptance_id:
            logger.warning({
                'order': order.__dict__,
                'status': 'No ID'
            })
        
        is_order_completed = self.wait_until_order_complete(acceptance_id, candle.time)

        trade_logger.debug({
            'status': 'finish order',
            'side': 'BUY',
            'is_order_completed': is_order_completed
        })
        return acceptance_id, is_order_completed
    
    def sell(self, candle:candle.Candle):
        '''
        Sell bit coin
        '''
        # Simulation
        if self.back_test:
            trade_logger.debug({
                'status': 'try to order',
                'side': 'SELL',
                'price': candle.close,
                'size': BACKTEST_TRADE_SIZE,
                'back_test': True,
            })

            could_sell = self.signal_events.sell(self.product_code, candle.time, candle.close, BACKTEST_TRADE_SIZE, False)

            trade_logger.debug({
                'status': 'finish order',
                'side': 'SELL',
                'is_order_completed': could_sell
            })
            return '', could_sell
        
        # 以下, 実際の売却する手続き
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

        trade_logger.debug({
            'status': 'try to order',
            'side': 'SELL',
            'size': size,
            'back_test': False
        })
        resp = self.api.send_order(order)
        acceptance_id = resp.child_order_acceptance_id
        if not acceptance_id:
            logger.warning({
                'order': order.__dict__,
                'status': 'No ID'
            })
        
        is_order_completed = self.wait_until_order_complete(acceptance_id, candle.time)

        trade_logger.debug({
            'status': 'finish order',
            'side': 'SELL',
            'is_order_completed': is_order_completed
        })
        return acceptance_id, is_order_completed
    
    def trade(self):
        # セマフォ取得
        if not self.trade_semaphore.acquire(blocking=False):
            logger.warning({
                'action': 'AI:trade',
                'status': 'cannot acquire semaphore'
            })
            return

        params = self.optimize_params
        if params is None:
            logger.info('optimized params not found!')

            self.update_optimize_params()
            # セマフォ解放
            self.trade_semaphore.release()
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


        '''
        各candleに対して売買の計算をする
        '''
        for i in range(len(df.candles)):
            if self.last_time >= df.candles[i].time:
                continue

            buy_params, sell_params = {}, {}
            if params.ema_enable:
                ema_params = {'period1': ema_trade_model.period1, 'period2': ema_trade_model.period2}
                if ema_trade_model.should_buy(i):
                    buy_params['ema'] = ema_params
                if ema_trade_model.should_sell(i):
                    sell_params['ema'] = ema_params
            
            if params.bb_enable:
                bb_params = {'n': bb_trade_model.n, 'k': bb_trade_model.k}
                if bb_trade_model.should_buy(i, df.candles):
                    buy_params['bbands'] = bb_params
                if bb_trade_model.should_sell(i, df.candles):
                    sell_params['bbands'] = bb_params
            
            if params.macd_enable:
                macd_params = {'short_period1': macd_trade_model.short_period, 'long_period': macd_trade_model.long_period, 'signal_period': macd_trade_model.signal_period}
                if macd_trade_model.should_buy(i):
                    buy_params['macd'] = macd_params
                if macd_trade_model.should_sell(i):
                    sell_params['macd'] = macd_params
            
            if params.rsi_enable:
                rsi_params = {'period': rsi_trade_model.preiod}
                if rsi_trade_model.should_buy(i):
                    buy_params['rsi'] = rsi_params
                if rsi_trade_model.should_sell(i):
                    sell_params['rsi'] = rsi_params
            
            buy_point = len(buy_params.keys())
            sell_point = len(sell_params.keys())

            # buy_pointが0より大きいなら買い
            if buy_point > 0:
                _, is_order_completed = self.buy(df.candles[i])
                if is_order_completed:
                    self.stop_limit = df.candles[i].close * self.stop_limit_percent

                    trade_logger.info({
                        'status': 'order completed',
                        'side': 'BUY',
                        'time': df.candles[i].time,
                        'params': buy_params,
                        'stop_limit': self.stop_limit
                    })

            
            # sell_pointが0より大きい、または終値がstop limitを下回りそうなら売り
            loss_cut = df.candles[i].close < self.stop_limit
            if sell_point > 0 or loss_cut:
                _, is_order_completed = self.sell(df.candles[i])
                if is_order_completed:
                    self.stop_limit = 0.0

                    trade_logger.info({
                        'status': 'order completed',
                        'side': 'SELL',
                        'time': df.candles[i].time,
                        'params': sell_params,
                        'loss_cut': loss_cut
                    })

        self.last_time = df.candles[-1].time

        # セマフォ解放  
        self.trade_semaphore.release()



    def get_available_balance(self):
        '''
        利用可能な資産
        '''
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
