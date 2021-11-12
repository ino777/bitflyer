import logging
import sqlite3


from config import config


logger = logging.getLogger(__name__)
''' Logger Config '''
handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(config.Config.log_stream_level)
stream_handler.setFormatter(handler_format)

logger.addHandler(stream_handler)


TABLE_NAME_SIGNAL_EVENTS = 'signal_events'


def get_candle_table_name(product_code, duration):
    return '{}_{}'.format(product_code, duration)


def init():
    try:
        # Need sqlite3.PARSE_DECLTYPES to deal with datetime
        conn = sqlite3.connect(config.Config.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    except FileNotFoundError as ex:
        logger.error(ex)

    curs = conn.cursor()

    # time column is UTC
    curs.execute(
        '''
        create table if not exists {}(
            time timestamp primary key not null,
            product_code string,
            side string,
            price float,
            size float
        )
        '''.format(TABLE_NAME_SIGNAL_EVENTS)
    )

    for duration in config.Config.durations.keys():
        # e.g. table_name = BTC_JPY_1m
        table_name = get_candle_table_name(config.Config.product_code, duration)
        # time column is UTC timestamp
        curs.execute(
            '''
            create table if not exists {}(
                time timestamp primary key not null,
                open float,
                close float,
                high float,
                low float,
                volume float
            )
            '''.format(table_name)
        )

    conn.commit()

    curs.close()
    conn.close()