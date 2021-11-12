import logging
import sys
import datetime
import configparser
from dataclasses import dataclass


logger = logging.getLogger(__name__)

''' Logger Config '''
logger.setLevel(logging.DEBUG)
handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(handler_format)

logger.addHandler(stream_handler)



@dataclass
class ConfigList(object):
    # API Key
    api_key: str
    api_secret: str

    # Logger Settings
    log_file: str
    log_stream_level: int
    log_file_level: int

    # Product code (e.g. JPY)
    product_code: str

    # Timezone (e.g. Asia/Tokyo)
    timezone: str

    # Trade Duration (1s, 1m, 1d)
    trade_duration: str
    durations: dict

    # DB
    db_name: str
    sqldriver: str

    # Port
    port: int

    # Simulation
    back_test: bool

    # Simulation parameters
    use_percent: float
    data_limit: int
    stop_limit_percent: float
    num_ranking: int

cfg = configparser.ConfigParser()

try:
    cfg.read('config.ini')
except FileNotFoundError as error:
    logger.error(error)
    sys.exit(1)

# Log Levels
log_levels ={
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR
}

# Durations
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