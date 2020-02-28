import logging
import sys
import datetime
import configparser


logger = logging.getLogger(__name__)

''' Logger Config '''
logger.setLevel(logging.DEBUG)
handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(handler_format)

logger.addHandler(stream_handler)


def str2bool(s):
    if s == 'true' or s == 'True':
        return True
    return False

class ConfigList(object):
    '''
    api_key,
    api_secret,
    log_file,
    product_code,
    timezone,
    trade_duration,
    durations,
    db_name,
    sqldriver,
    port
    '''
    def __init__(
            self, api_key, api_secret, log_file, log_stream_level, log_file_level, product_code, timezone, trade_duration,
            durations, db_name, sqldriver, port,
            back_test, use_percent, data_limit, stop_limit_percent, num_ranking):
        self.api_key = api_key
        self.api_secret = api_secret
        self.log_file = log_file
        self.log_stream_level = log_stream_level
        self.log_file_level = log_file_level
        self.product_code = product_code
        self.timezone = timezone
        self.trade_duration = trade_duration
        
        self.durations = durations
        self.db_name = db_name
        self.sqldriver = sqldriver
        self.port = port

        self.back_test = back_test
        self.use_percent = use_percent
        self.data_limit = data_limit
        self.stop_limit_percent = stop_limit_percent
        self.num_ranking = num_ranking

cfg = configparser.ConfigParser()

try:
    cfg.read('config.ini')
except FileNotFoundError as error:
    logger.error(error)
    sys.exit(1)

log_levels ={
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR
}

durations = {
    '1s': datetime.timedelta(seconds=1),
    '1m': datetime.timedelta(minutes=1),
    '1h': datetime.timedelta(hours=1),
    '1d': datetime.timedelta(days=1),
    # '1w': datetime.timedelta(weeks=1)
}

Config = ConfigList(
    api_key = cfg['bitflyer']['api_key'],
    api_secret = cfg['bitflyer']['api_secret'],
    log_file = cfg['trading']['log_file'],
    log_stream_level = log_levels[cfg['trading']['log_stream_level']],
    log_file_level = log_levels[cfg['trading']['log_file_level']],
    product_code = cfg['trading']['product_code'],
    timezone = cfg['trading']['timezone'],
    trade_duration = cfg['trading']['trade_duration'],
    durations = durations,
    db_name = cfg['db']['name'],
    sqldriver = cfg['db']['driver'],
    port = cfg['web']['port'],
    back_test = cfg['trading'].getboolean('back_test'),
    use_percent = cfg['trading'].getfloat('use_percent'),
    data_limit = cfg['trading'].getint('data_limit'),
    stop_limit_percent = cfg['trading'].getfloat('stop_limit_percent'),
    num_ranking = cfg['trading'].getint('num_ranking')
)