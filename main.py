import logging
import queue
import threading

from config import config
from bitflyer import bitflyer
from app.models import base, candle, events
from app.controllers import streamdata, webserver


logger = logging.getLogger(__name__)

''' Logger Config '''
logger.setLevel(logging.DEBUG)
handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(config.Config.log_stream_level)
stream_handler.setFormatter(handler_format)

file_handler = logging.FileHandler(config.Config.log_file)
file_handler.setLevel(config.Config.log_file_level)
file_handler.setFormatter(handler_format)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)


if __name__ == '__main__':
    base.init()
    t = threading.Thread(target=streamdata.stream_ingestion_data)
    t.setDaemon(True)
    t.start()
    webserver.start_webserver()
