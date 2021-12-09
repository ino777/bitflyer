import os
import logging
import http.server
import urllib.parse
import json
from jinja2 import FileSystemLoader
from flask import Flask, request, jsonify, render_template


from config import config
from app.models import candle
from app.controllers import ai
from utils.logsettings import getLogger


logger = getLogger(__name__)


VIEW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'views')
MAX_LIMIT = 1000

# Preprocessing
def prepare_app():
    from bitflyer import bitflyer
    from app.models import base, candle, events
    base.init()

    from app.controllers import streamdata, webserver
    import threading

    t = threading.Thread(target=streamdata.stream_ingestion_data)
    t.setDaemon(True)
    t.start()
        
    app = Flask(__name__, static_url_path='', static_folder=os.path.join(VIEW_DIR, 'static'))
    # Set a searchpath for template files
    app.jinja_loader = FileSystemLoader(VIEW_DIR)

    return app

app = prepare_app()


### utils #####

# Cast strings digits to int type.
def str2int(strs, defaults):
    if not len(strs) == len(defaults):
        raise IndexError
    result = []
    for i in range(len(strs)):
        try:
            result.append(int(strs[i]))
        except ValueError:
            result.append(defaults[i])
        except TypeError:
            result.append(defaults[i])
        result[i] = result[i] if result[i] > 0 else defaults[i]
    return result


### Page ###

@app.route('/', methods=['GET'])
def view_candle():
    product_code = request.args.get('product_code', config.Config.product_code)
    duration = request.args.get('duration', config.Config.trade_duration)
    
    str_limit = request.args.get('limit', '100')
    try:
        limit = int(str_limit)
    except ValueError as e:
        limit = MAX_LIMIT
    if limit < 0 or limit > MAX_LIMIT:
        limit = MAX_LIMIT
    
    df = candle.get_all_candles(product_code, duration, limit)
    return render_template('index.html')


### API ####

@app.route('/api/candle', methods=['GET'])
def api_get_candle():
    '''
    Returns dataframe candles
    '''
    product_code = request.args.get('product_code', config.Config.product_code)
    duration = request.args.get('duration', config.Config.trade_duration)
    
    str_limit = request.args.get('limit', '100')
    try:
        limit = int(str_limit)
    except ValueError as e:
        limit = MAX_LIMIT
    if limit < 0 or limit > MAX_LIMIT:
        limit = MAX_LIMIT
    
    df = candle.get_all_candles(product_code, duration, limit)
    if not df:
        return jsonify({'message': 'DataFrameCandle is not found.', 'code': 500}), 500
    
    # Signal Events
    events = request.args.get('events')
    if events:
        if config.Config.back_test:
            df.set_events(ai.TRADE_AI.signal_events.collect_after(df.candles[0].time))
        else:
            first_time = df.candles[0].time
            df.add_events(first_time)

    # SMA
    sma = request.args.get('sma')
    if sma:
        str_sma_period1 = request.args.get('sma_period1', '')
        str_sma_period2 = request.args.get('sma_period2', '')
        str_sma_period3 = request.args.get('sma_period3', '')
        sma_periods = str2int([str_sma_period1, str_sma_period2, str_sma_period3], [7, 14, 50])
        df.add_sma(sma_periods[0])
        df.add_sma(sma_periods[1])
        df.add_sma(sma_periods[2])

    # EMA
    ema = request.args.get('ema')
    if ema:
        str_ema_period1 = request.args.get('ema_period1', '')
        str_ema_period2 = request.args.get('ema_period2', '')
        str_ema_period3 = request.args.get('ema_period3', '')
        ema_periods = str2int([str_ema_period1, str_ema_period2, str_ema_period3], [7, 14, 50])
        df.add_ema(ema_periods[0])
        df.add_ema(ema_periods[1])
        df.add_ema(ema_periods[2])
    
    # BBands
    bbands = request.args.get('bbands')
    if bbands:
        str_n = request.args.get('bbands_n')
        str_k = request.args.get('bbands_k')
        bbands_params = str2int([str_n, str_k], [20, 2])
        df.add_bbands(bbands_params[0], bbands_params[1])
    
    # Ichimoku
    ichimoku = request.args.get('ichimoku')
    if ichimoku:
        str_ichimoku_tenkan_period = request.args.get('ichimoku_tenkan_period', '')
        str_ichimoku_base_period = request.args.get('ichimoku_base_period', '')
        str_ichimoku_pre1_shift = request.args.get('ichimoku_pre1_shift', '')
        str_ichimoku_pre2_period = request.args.get('ichimoku_pre2_period', '')
        str_ichimoku_delay_period = request.args.get('ichimoku_delay_period', '')
        ichimoku_params = str2int(
            [str_ichimoku_tenkan_period, str_ichimoku_base_period, str_ichimoku_pre1_shift, str_ichimoku_pre2_period, str_ichimoku_delay_period],
            [9, 26, 26, 52, 26]
        )
        df.add_ichimoku(ichimoku_params[0], ichimoku_params[1], ichimoku_params[2], ichimoku_params[3], ichimoku_params[4])
    
    # RSI
    rsi = request.args.get('rsi')
    if rsi:
        str_rsi_period = request.args.get('rsi_period', '')
        rsi_periods = str2int([str_rsi_period], [14])
        df.add_rsi(rsi_periods[0])

    # MACD
    macd = request.args.get('macd')
    if macd:
        str_macd_short_period = request.args.get('macd_short_period', '')
        str_macd_long_period = request.args.get('macd_long_period', '')
        str_macd_signal_period = request.args.get('macd_signal_period', '')
        macd_periods = str2int([str_macd_short_period, str_macd_long_period, str_macd_signal_period], [12, 26, 9])
        df.add_macd(macd_periods[0], macd_periods[1], macd_periods[2])
    
    # HV
    hv = request.args.get('hv')
    if hv:
        str_hv_period1 = request.args.get('hv_period1', '')
        str_hv_period2 = request.args.get('hv_period2', '')
        str_hv_period3 = request.args.get('hv_period3', '')
        hv_periods = str2int([str_hv_period1, str_hv_period2, str_hv_period3], [21, 63, 252])
        df.add_hv(hv_periods[0])
        df.add_hv(hv_periods[1])
        df.add_hv(hv_periods[2])

    return jsonify(df.getall())






def start_webserver():
    app.debug = False
    app.run()