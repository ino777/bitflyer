import datetime
from pytz import timezone
import sqlite3
import json


from config import config


TABLE_NAME_SIGNAL_EVENTS = 'signal_events'


class SignalEvent(object):
    '''
    Event signal
    'BUY' or 'SELL'
    '''
    def __init__(self, time:datetime.datetime, product_code, side, price, size):
        if not type(time) == datetime.datetime:
            raise TypeError('Type of SignalEvent attribute "time" must be <class \'datetime.datetime\'>')
        self.time = time
        self.product_code = product_code
        self.side = side
        self.price = price
        self.size = size
    
    def save(self):
        conn = sqlite3.connect(config.Config.db_name)
        curs = conn.cursor()

        curs.execute(
            '''
            insert or replace into {} (time, product_code, side, price, size) values (?, ?, ?, ?, ?)
            '''.format(TABLE_NAME_SIGNAL_EVENTS),
            (self.time.replace(tzinfo=None), self.product_code, self.side, self.price, self.size)
        )
        
        conn.commit()
        curs.close()
        conn.close()


class SignalEvents(object):
    def __init__(self, signals):
        self.signals = signals

    def data(self):
        return {
            'signals': [s.__dict__ for s in self.signals],
            'profit': self.profit()
        }

    def can_buy(self, time:datetime.datetime):
        '''
        現在買いが可能か
        '''

        if not self.signals:
            return True
        
        last_signal = self.signals[-1]
        if last_signal.side == 'SELL' and last_signal.time < time:
            return True
        return False

    def can_sell(self, time:datetime.datetime):
        '''
        現在売りが可能か
        '''
        if not self.signals:
            return False

        last_signal = self.signals[-1]
        if last_signal.side == 'BUY' and last_signal.time < time:
            return True
        return False
    
    def buy(self, product_code, time:datetime.datetime, price, size, should_save):
        '''
        買いのシグナルを作成
        '''
        if not self.can_buy(time):
            return False
        signal_event = SignalEvent(time, product_code, 'BUY', price, size)
        if should_save:
            signal_event.save()
        self.signals.append(signal_event)
        return True

    def sell(self, product_code, time:datetime.datetime, price, size, should_save):
        '''
        売りのシグナルを作成
        '''
        if not self.can_sell(time):
            return False
        signal_event = SignalEvent(time, product_code, 'SELL', price, size)
        if should_save:
            signal_event.save()
        self.signals.append(signal_event)
        return True
    
    def profit(self):
        '''
        損益計算
        '''
        total = 0.0
        before_sell = 0.0
        is_holding = False
        for i, signal_event in enumerate(self.signals):
            if i == 0 and signal_event.side == 'SELL':
                continue
            if signal_event.side == 'BUY':
                total -= signal_event.price * signal_event.size
                is_holding = True
            if signal_event.side == 'SELL':
                total += signal_event.price * signal_event.size
                is_holding = False
                before_sell = total
        
        # Before you sell(i.e. while you hold bitcoin), the profit is not confirmed.
        if is_holding:
            return before_sell
        return total
    
    def collect_after(self, time:datetime.datetime):
        for i, signal_event in enumerate(self.signals):
            if signal_event.time < time:
                continue
            return SignalEvents(self.signals[i:])
        return SignalEvents([])


def get_signal_events_by_count(load_events):
    '''
    Returns the latest signal events
    '''
    conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    curs = conn.cursor()

    curs.execute(
        '''
        select * from (
            select time, product_code, side, price, size from {} where product_code = ? order by time desc limit ?
        ) order by time asc;
        '''.format(TABLE_NAME_SIGNAL_EVENTS),
        (config.Config.product_code, load_events)
    )

    rows = curs.fetchall()
    if not rows:
        return
    
    curs.close()
    conn.close()

    signal_events = SignalEvents([])

    for row in rows:
        signal_events.signals.append(
            SignalEvent(
                time = row['time'],
                product_code = row['product_code'] ,
                side = row['side'],
                price = row['price'],
                size = row['size']
            )
        )

    return signal_events


def get_signal_events_after_time(time):
    '''
    Returns the signal events after given time
    '''
    conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    curs = conn.cursor()

    curs.execute(
        '''
        select * from (
            select time, product_code, side, price, size from {} where time >= ? order by time desc
        ) order by time asc;
        '''.format(TABLE_NAME_SIGNAL_EVENTS),
        (time,)
    )

    rows = curs.fetchall()
    if not rows:
        return
    
    curs.close()
    conn.close()

    signal_events = SignalEvents([])
    for row in rows:
        signal_events.signals.append(
            SignalEvent(
                time = row['time'],
                product_code = row['product_code'],
                side = row['side'],
                price = row['price'],
                size = row['size']
            )
        )
    return signal_events

