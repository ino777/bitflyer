import queue
import threading

from config import config
from utils.logsettings import getLogger
from app.controllers.webserver import app

logger = getLogger(__name__)


from bitflyer import bitflyer
from app.models import base, candle, events
base.init()

from app.controllers import streamdata, webserver

t = threading.Thread(target=streamdata.stream_ingestion_data)
t.setDaemon(True)
t.start()

app.debug = False
app.run()
