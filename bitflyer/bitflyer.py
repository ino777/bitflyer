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


import requests
import datetime_truncate


from config import config


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


BASE_URL = 'https://api.bitflyer.com/v1/'



class Balance(object):
    '''
    Asset balance (資産残高)
    '''
    def __init__(self, currency_code, amount, available):
        self.currency_code = currency_code
        self.amount = amount
        self.available = available


class Ticker(object):
    def __init__(
            self, product_code, timestamp, tick_id, best_bid, best_ask, best_bid_size, best_ask_size,
            total_bid_depth, total_ask_depth, ltp, volume, volume_by_product):
        # Cast the types because received data is json parsed
        self.product_code = str(product_code)
        self.timestamp = str(timestamp)
        self.tick_id = int(tick_id)
        self.best_bid = float(best_bid)
        self.best_ask = float(best_ask)
        self.best_bid_size = float(best_bid_size)
        self.best_ask_size = float(best_ask_size)
        self.total_bid_depth = float(total_bid_depth)
        self.total_ask_depth = float(total_ask_depth)
        self.ltp = float(ltp)
        self.volume = float(volume)
        self.volume_by_product = float(volume_by_product)

    def get_mid_price(self):
        return (self.best_bid + self.best_ask) / 2

    def datetime(self):
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
        duration: str (1s, 1m, 1h, 1d, 1w)
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


class Order(object):
    def __init__(self, product_code, child_order_type, side, size, price=0, minute_to_expire=0, time_in_force='GTC'):
        self.product_code = product_code
        self.child_order_type = child_order_type
        self.side = side
        self.size = size
        if self.child_order_type == 'LIMIT':
            self.price = price
        if minute_to_expire:
            self.minute_to_expire = minute_to_expire
        self.time_in_force = time_in_force



class ResponseSendChildOrder(object):
    def __init__(self, child_order_acceptance_id):
        self.child_order_acceptance_id = child_order_acceptance_id


class ResponseGetChildOrder(object):
    def __init__(self, id, child_order_id, product_code, child_order_type, side, size,
            child_order_state, expire_date, child_order_date, child_order_acceptance_id,
            outstanding_size, cancel_size, executed_size, total_commission, price=0, avarege_price=0):
        self.id = id
        self.child_order_id = child_order_id
        self.product_code = product_code
        self.child_order_type = child_order_type
        self.side = side
        self.size = size
        self.child_order_state = child_order_state
        self.expire_date = expire_date
        self.child_order_date = child_order_date
        self.child_order_acceptance_id = child_order_acceptance_id
        self.outstanding_size = outstanding_size
        self.cancel_size = cancel_size
        self.executed_size = executed_size
        self.total_commission = total_commission
        if price:
            self.price = price
        if avarege_price:
            self.avarage_price = avarege_price


class APIClient(object):
    def __init__(self, key, secret):
        self.key = str(key)
        self.secret = str(secret)

    def header(self, method, endpoint, body):
        '''
        Create header

        method: method(GET, POST...)
        endpoint: url
        body: byte data
        '''
        timestamp = time.time()
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
        logger.info({
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
                'response': r.json()
            })
            return
        return balances

    def get_ticker(self, product_code):
        url = 'ticker'
        query = {'product_code': product_code}
        r = self.do_request('GET', url, query=query)
        logger.info({
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
        logger.info({
            'action': 'get_realtime_ticker',
            'status': 'websocket starts in another thread'
        })
        
        while True:
            try:
                ticker_q.put(Ticker(**resp_q.get()))
            except TypeError as err:
                logger.warning({
                    'action': 'APIClient:get_realtime_ticker',
                    'error': err
                })
                return
    
    def send_order(self, order:Order):
        url = 'me/sendchildorder'
        data = json.dumps(order.__dict__).encode('utf-8')
        r = self.do_request('POST', url, query={}, data=data)
        logger.info({
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
        url = 'me/getchildorders'
        r = self.do_request('GET', url, query=query)
        logger.info({
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
    ''' websocket '''
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