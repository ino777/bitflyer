import logging
import datetime
import sqlite3


from . import base, dfcandle
from config import config
from bitflyer import bitflyer
from utils.logsettings import getLogger


logger = getLogger(__name__)


class Candle(object):
    def __init__(self, product_code, duration, time:datetime.datetime, open_v, close, high, low, volume):
        if not type(time) == datetime.datetime:
            raise TypeError('Type of Candle attribute "time" must be <class \'datetime.datetime\'>')
        self.product_code = product_code
        self.duration = duration
        self.table = self.table_name()
        self.time = time
        # 始値
        self.open = open_v
        # 終値
        self.close = close
        # 高値
        self.high = high
        # 安値
        self.low = low
        # 取引量
        self.volume = volume

    def table_name(self):
        return base.get_candle_table_name(self.product_code, self.duration)

    def get(self):
        conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
        curs = conn.cursor()

        curs.execute(
            '''
            select * from {} where time = ?;
            '''.format(self.table),
            (self.time.replace(tzinfo=None),)
        )
        rows = curs.fetchall()
        curs.close()
        conn.close()
        return rows

    def create(self):
        conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
        curs = conn.cursor()

        
        curs.execute(
            '''
            insert or replace into {} (time, open, close, high, low, volume) values (?, ?, ?, ?, ?, ?);
            '''.format(self.table),
            (self.time.replace(tzinfo=None), self.open, self.close, self.high, self.low, self.volume)
        )
        conn.commit()
        curs.close()
        conn.close()

    def save(self):
        conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
        curs = conn.cursor()


        curs.execute(
            '''
            update {} set open = ?, close = ?, high = ?, low = ?, volume = ? where time = ?;
            '''.format(self.table),
            (self.open, self.close, self.high, self.low, self.volume, self.time.replace(tzinfo=None))
        )

        conn.commit()
        curs.close()
        conn.close()
    

def get_candle(product_code, duration, date_time:datetime.datetime):
    '''
    Returns the candle whose time is date_time from the db table given by product_code and duration
    '''
    if not type(date_time) == datetime.datetime:
        raise TypeError('Type of "date_time" must be <class \'datetime.datetime\'>')
    table_name = base.get_candle_table_name(product_code, duration)
    conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    curs = conn.cursor()

    curs.execute(
        '''
        select time, open, close, high, low, volume from {} where time = ?;
        '''.format(table_name),
        (date_time.replace(tzinfo=None),)
    )
    row = curs.fetchone()
    if not row:
        return

    curs.close()
    conn.close()

    return Candle(
        product_code = product_code,
        duration = duration,
        time = row['time'],
        open_v = row['open'],
        close = row['close'],
        high = row['high'],
        low = row['low'],
        volume = row['volume']
    )

def create_or_update_candle(ticker:bitflyer.Ticker, product_code, duration):
    '''
    Return whether a candle is created. If a candle is updated, return False.
    '''
    current_candle = get_candle(product_code, duration, ticker.truncate_datetime(duration))
    price = ticker.get_mid_price()
    if current_candle is None:
        candle = Candle(
            product_code = product_code,
            duration = duration,
            time = ticker.truncate_datetime(duration),
            open_v = price,
            close = price,
            high = price,
            low = price,
            volume = ticker.volume
        )
        candle.create()
        return True
    
    if current_candle.high < price:
        current_candle.high = price
    elif current_candle.low > price:
        current_candle.low = price
    
    current_candle.volume += ticker.volume
    current_candle.close = price
    current_candle.save()
    return False


def get_all_candles(product_code, duration, limit):
    '''
    Returns the latest candles
    '''
    df = dfcandle.DataFrameCandle(product_code, duration, [])
    table_name = base.get_candle_table_name(product_code, duration)
    conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    curs = conn.cursor()

    curs.execute(
        '''
        select * from (
            select time, open, close, high, low, volume from {} order by time desc limit ?
        ) order by time asc;
        '''.format(table_name),
        (limit,)
    )
    rows = curs.fetchall()
    if not rows:
        return
    
    curs.close()
    conn.close()

    for i in range(len(rows)):
        df.candles.append(
            Candle(
                product_code = product_code,
                duration = duration,
                time = rows[i][0],
                open_v = rows[i][1],
                close = rows[i][2],
                high = rows[i][3],
                low = rows[i][4],
                volume = rows[i][5]
            )
        )
    return df


def delete_old_candles(product_code, duration, limit):
    '''
    Delete candles whose created time is before the time
    '''
    table_name = base.get_candle_table_name(product_code, duration)
    limit_time = datetime.datetime.now() - config.Config.durations[duration] * limit
    conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    curs = conn.cursor()

    curs.execute(
        '''
        delete from {} where time < ?
        '''.format(table_name),
        (limit_time,)
    )
    curs.close()
    conn.close()