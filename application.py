import queue
import threading

from config import config
from utils.logsettings import getLogger


logger = getLogger(__name__)


def create_app():
    from bitflyer import bitflyer
    from app.models import base, candle, events
    base.init()
    
    from app.controllers import streamdata
    
    t = threading.Thread(target=streamdata.stream_ingestion_data)
    t.setDaemon(True)
    t.start()

    from app.controllers.webserver import app
    app.debug = False

    return app

app = create_app()


if __name__ == '__main__':
    app.run()
