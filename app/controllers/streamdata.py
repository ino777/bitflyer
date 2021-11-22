import threading
import queue

from bitflyer import bitflyer
from config import config
from app.models import candle
from app.controllers import ai
from utils.logsettings import getLogger


logger = getLogger(__name__)


def stream_ingestion_data():
    # リアルタイムに取得したTickerのバッファ
    ticker_q = queue.Queue()
    # APIClient
    api_client = bitflyer.APIClient(config.Config.api_key, config.Config.api_secret)

    # リアルタイムにTickerを取得するスレッド
    t = threading.Thread(target=api_client.get_realtime_ticker, args=(config.Config.product_code, ticker_q))
    t.setDaemon(True)
    t.start()

    while True:
        try:
            ticker = ticker_q.get() # Tickerを取得
            # 各duration毎にcandleを作成or更新
            for duration in config.Config.durations.keys():
                is_created = candle.create_or_update_candle(ticker, config.Config.product_code, duration)
                # candleが作成されたらtradeを実行
                if is_created and duration == config.Config.trade_duration:
                    logger.debug({
                        'action': 'stream_ingestion_data',
                        'status': 'start ai trade'
                    })
                    ai.TRADE_AI.trade()
        except KeyboardInterrupt as err:
            logger.error({
                'error': err
            })
            break

