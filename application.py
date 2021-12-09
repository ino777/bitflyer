import queue
import threading

from config import config
from utils.logsettings import getLogger
from app.controllers.webserver import app

logger = getLogger(__name__)

if __name__ == 'main':
    app.debug = False
    app.run()
