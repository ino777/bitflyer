import logging
import threading
import queue

from bitflyer import bitflyer
from config import config
from app.models import candle
from app.controllers import ai


logger = logging.getLogger(__name__)
''' Logger Config '''
handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(config.Config.log_stream_level)
stream_handler.setFormatter(handler_format)

logger.addHandler(stream_handler)


def stream_ingestion_data():
    ticker_q = queue.Queue()
    api_client = bitflyer.APIClient(config.Config.api_key, config.Config.api_secret)
    t = threading.Thread(target=api_client.get_realtime_ticker, args=(config.Config.product_code, ticker_q))
    t.setDaemon(True)
    t.start()
    while True:
        try:
            ticker = ticker_q.get()
            for duration in config.Config.durations.keys():
                is_created = candle.create_or_update_candle(ticker, config.Config.product_code, duration)
                if is_created == True and duration == config.Config.trade_duration:
                    ai.TRADE_AI.trade()
        except KeyboardInterrupt as err:
            logger.error({
                'error': err
            })
            break

