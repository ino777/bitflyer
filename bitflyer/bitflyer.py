import logging
import re
import time
import datetime
from pytz import timezone
import json
import hashlib
import hmac
import secrets
import socket
import websocket
import urllib.parse
import threading
import queue
from dataclasses import dataclass

import requests
import datetime_truncate


from config import config


logger = logging.getLogger(__name__)

''' Logger Config '''
handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(config.Config.log_stream_level)
stream_handler.setFormatter(handler_format)

file_handler = logging.FileHandler(config.Config.log_file)
file_handler.setLevel(config.Config.log_file_level)
file_handler.setFormatter(handler_format)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)


BASE_URL = 'https://api.bitflyer.com/v1/'


@dataclass
class Balance(object):
    '''
    Asset balance (資産残高)

    https://lightning.bitflyer.com/docs#%E8%B3%87%E7%94%A3%E6%AE%8B%E9%AB%98%E3%82%92%E5%8F%96%E5%BE%97
    '''
    currency_code: str
    amount: int
    available: int

@dataclass
class Ticker(object):
    '''
    Ticker

    https://lightning.bitflyer.com/docs#ticker
    '''
    product_code: str
    state: str
    timestamp: str
    tick_id: int

    # 買値, 売値
    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    total_bid_depth: float
    total_ask_depth: float
    market_bid_size: float
    market_ask_size: float

    # 最終取引価格
    ltp: float

    # 24時間の取引量
    volume: float
    volume_by_product: float

    def get_mid_price(self):
        return (self.best_bid + self.best_ask) / 2

    def datetime(self):
        '''
        Get datetime from timestamp of ticker
        '''
        # timestamp validation
        # timestamp format %Y-%m-%dT%H:%M:%S.%f%z 
        m = re.match(
            r'(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)T(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)\.(?P<float>\d+)(?P<tz>\w*)',
            self.timestamp)
        if not m:
            raise TypeError('{} is invalid timestamp'.format(self.timestamp))

        d = m.groupdict()
        # The length of %f in datetime format must be 1 to 6 integers
        if len(d['float']) > 6:
            d['float'] = d['float'][:6-len(d['float'])]

        timestamp = '{year}-{month}-{day}T{hour}:{minute}:{second}.{float}{tz}'.format(**d)
        try:
            dt = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(timezone('UTC'))
        except ValueError as v_error:
            try:
                dt = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f').astimezone(timezone('UTC'))
            except Exception as ex:
                logger.error({
                    'action': 'Ticker:datetime',
                    'exeption': ex
                })
        return dt

    def truncate_datetime(self, duration):
        '''
        Tcuncate datetime

        duration: str
            (1s, 1m, 1h, 1d, 1w)
        '''
        if duration == '1s':
            dt = self.datetime().replace(microsecond=0)
        elif duration == '1m':
            dt = self.datetime().replace(second=0, microsecond=0)
        elif duration == '1h':
            dt = self.datetime().replace(minute=0, second=0, microsecond=0)
        elif duration == '1d':
            dt = self.datetime().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            raise TypeError('unsupported duration: ' + duration)
        return dt


@dataclass
class Order(object):
    '''
    新規注文を出す

    https://lightning.bitflyer.com/docs#%E6%96%B0%E8%A6%8F%E6%B3%A8%E6%96%87%E3%82%92%E5%87%BA%E3%81%99
    '''
    # Produce code
    product_code: str

    # 指値注文の場合は'LIMIT', 成行注文の場合は'MARKET'
    child_order_type: str
    # 買い注文の場合は'BUY', 売り注文の場合は'SELL'
    side: str
    # 注文数量
    size: float
    # 価格, child_order_typeに'LIMI'を指定した場合は必須
    price: float = 0
    # 期限切れまでの時間を分で指定
    minute_to_expire: float = 0
    #  執行数量条件 を 'GTC', 'IOC', 'FOK' のいずれかで指定
    time_in_force: str = 'GTC'


@dataclass
class ResponseSendChildOrder(object):
    '''
    新規注文(Order)のレスポンス
    '''
    child_order_acceptance_id: str


@dataclass
class ResponseGetChildOrder(object):
    '''
    注文の一覧取得のレスポンス
    '''
    id: int
    child_order_id: str
    product_code: str
    child_order_type: str
    side: str
    size: float
    child_order_state: str
    expire_date: str
    child_order_date: str
    child_order_acceptance_id: str
    outstanding_size: float
    cancel_size: float
    executed_size: float
    total_commission: float
    price: float = 0
    avarage_price: float = 0


class APIClient(object):
    '''
    APIClient
    '''
    def __init__(self, key, secret):
        self.key = str(key)
        self.secret = str(secret)

    def header(self, method, endpoint, body):
        '''
        Create header

        https://lightning.bitflyer.com/docs#%E8%AA%8D%E8%A8%BC

        method: method(GET, POST...)
        endpoint: url
        body: request body
        '''
        timestamp = time.time()
        # ACCESS-SIGNは, ACCESS-TIMESTAMP, HTTP メソッド, リクエストのパス, リクエストボディ を文字列として連結したものを、 API secret で HMAC-SHA256 署名
        message = str(timestamp) + method + endpoint + str(body)
        sign = hmac.new(self.secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
        return {
            'ACCESS-KEY': self.key,
            'ACCESS-TIMESTAMP': str(timestamp),
            'ACCESS-SIGN': sign,
            'Content-Type': 'application/json'
        }

    def do_request(self, method, urlpath, query={}, data=bytes()):
        '''
        Do request
        '''
        baseurl = BASE_URL
        if len(urllib.parse.urlparse(baseurl).netloc) == 0:
            return
        apiurl = urlpath
        if len(urllib.parse.urlparse(apiurl).path) == 0:
            return
        endpoint = urllib.parse.urljoin(baseurl, apiurl)
        logger.debug({
            'action': 'do_request',
            'endpoint': endpoint,
        })

        if method == 'GET':
            r = requests.get(endpoint, query, headers=self.header(method, endpoint, data))
        elif method == 'POST':
            r = requests.post(endpoint, data, headers=self.header(method, endpoint, data))
        else:
            logger.error('invalid method {}'.format(method))

        return r

    def get_balance(self):
        url = 'me/getbalance'
        r = self.do_request('GET', url)
        logger.debug({
            'action': 'get_balance',
            'response': r.json()
        })

        results = r.json()
        balances = []
        try:
            for result in results:
                balances.append(Balance(**result))
        except TypeError as err:
            logger.warning({
                'action': 'APIClient:get_balance',
                'error': err,
                'response': results
            })
            return
        return balances

    def get_ticker(self, product_code):
        url = 'ticker'
        query = {'product_code': product_code}
        r = self.do_request('GET', url, query=query)
        logger.debug({
            'action': 'ticker',
            'response': r.json()
        })

        try:
            ticker = Ticker(**r.json())
        except TypeError as err:
            logger.warning({
                'action': 'APIClient:get_ticker',
                'error': err,
                'response': r.json()
            })
            return
        return ticker

    def get_realtime_ticker(self, product_code, ticker_q:queue.Queue):
        '''
        Returns realtime ticker over WebSocket

        https://bf-lightning-api.readme.io/docs/realtime-ticker
        '''
        endpoint = 'wss://ws.lightstream.bitflyer.com/json-rpc'

        param = json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'subscribe',
                    'params': {'channel': 'lightning_ticker_' + product_code}
                })

        resp_q = queue.Queue()
        c = RealTimeAPI(endpoint, param, queue=resp_q)
        t = threading.Thread(target=c.start)
        t.setDaemon(True)
        t.start()
        logger.debug({
            'action': 'get_realtime_ticker',
            'status': 'websocket starts in another thread'
        })
        
        while True:
            try:
                ticker_q.put(Ticker(**resp_q.get()))
            except TypeError as err:
                logger.warning({
                    'action': 'APIClient:get_realtime_ticker',
                    'content': resp_q.get(),
                    'error': err
                })
                return
    
    def send_order(self, order:Order):
        '''
        Send Order
        '''
        url = 'me/sendchildorder'
        data = json.dumps(order.__dict__).encode('utf-8')
        r = self.do_request('POST', url, query={}, data=data)
        logger.debug({
            'action': 'send_order',
            'resp': r.json(),
            'status': 'done'
        })

        try:
            resp_child_order = ResponseSendChildOrder(**r.json())
        except TypeError as err:
            logger.error({
                'action': 'APIClient:send_order',
                'error': err,
                'response': r.json()
            })
            return
        return resp_child_order

    def list_order(self, query):
        '''
        Returns order list
        '''
        url = 'me/getchildorders'
        r = self.do_request('GET', url, query=query)
        logger.debug({
            'action': 'list_orders',
            'resp': r.json()
        })

        try:
            orders = [ResponseGetChildOrder(**d) for d in r.json()]
        except TypeError as err:
            logger.error({
                'action': 'APIClient:list_order',
                'error': err,
                'response': r.json()
            })
            return
        return orders


class RealTimeAPI(object):
    '''
    Websocket API
    '''
    def __init__(self, url, param, queue):
        self.param = param
        self.queue = queue
        self.results = []
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            url, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.ws.on_open = self.on_open
    
    def start(self):
        logger.info('### websocket run ###')
        self.ws.run_forever()

    def on_message(self, message):
        resp = json.loads(message)
        self.queue.put(resp['params']['message'])


    def on_error(self, error):
        logger.error({
            'action': 'RealTimeAPI:on_error',
            'error': error
        })

    def on_close(self):
        logger.info('### websocket closed ###')
    
    def on_open(self):
        def run(*args):
            self.ws.send(self.param)
        t = threading.Thread(target=run)
        t.setDaemon(True)
        t.start()


#### ReaitimeAPI authentication
        # timestamp = time.time()
        # nonce = secrets.token_hex(16)
        # message = str(timestamp) + nonce
        # sign = hmac.new(self.secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()