import datetime
import sqlite3
from unittest import TestCase
from unittest.mock import MagicMock, patch


from app.models.base import get_candle_table_name
from app.models.candle import Candle, get_candle, get_all_candles, create_or_update_candle
from app.models.dfcandle import DataFrameCandle
from bitflyer.bitflyer import Ticker


class TestCandle(TestCase):
    def setUp(self):
        self.db = 'TestDB.sql'
        self.product_code = 'BTC_JPY'
        self.duration = '1m'
        self.table = get_candle_table_name(self.product_code, self.duration)

        self.data = {
            'time': datetime.datetime.now(),
            'open': 200,
            'close': 300,
            'high': 450,
            'low': 150,
            'volume': 20
        }
        self.candle = Candle(
            self.product_code,
            self.duration,
            self.data['time'],
            self.data['open'],
            self.data['close'],
            self.data['high'],
            self.data['low'],
            self.data['volume']
        )
    

    def test_get_candle(self):
        curs_mock = MagicMock()
        curs_mock.fetchone.return_value = self.data

        conn_mock = MagicMock()
        conn_mock.cursor.return_value = curs_mock

        with patch('sqlite3.connect', return_value=conn_mock):
            candle = get_candle(self.product_code, self.duration, self.data['time'])
        
        conn_mock.commit.assert_not_called()
        conn_mock.rollback.assert_not_called()
        
        self.assertEqual(type(candle), Candle)
        self.assertEqual(candle.time, self.data['time'])

    
    def test_get_all_candles(self):
        curs_mock = MagicMock()
        curs_mock.fetchall.return_value = [list(self.data.values())]

        conn_mock = MagicMock()
        conn_mock.cursor.return_value = curs_mock

        with patch('sqlite3.connect', return_value=conn_mock):
            df = get_all_candles(self.product_code, self.duration, 10)
        
        conn_mock.commit.assert_not_called()
        conn_mock.rollback.assert_not_called()
        
        self.assertEqual(type(df), DataFrameCandle)
        self.assertEqual(len(df.candles), 1)
        self.assertEqual(df.candles[0].time, self.data['time'])
    
    @patch('app.models.candle.get_candle')
    def test_create_or_update_candle(self, mock_get_candle):
        test_patterns = [
            (None, True),           # get_candle returns None
            (self.candle, False)    # get_candle returns candle
        ]

        ticker = Ticker(
            self.product_code, '',  '2015-07-08T02:50:59.97', 0,
            0, 0, 0, 0, 0, 0, 0 ,0, 0, 0, 0
        )
        
        for m, expect_result in test_patterns:
            with self.subTest():
                mock_get_candle.return_value = m
                res = create_or_update_candle(ticker, self.product_code, self.duration)
                self.assertEqual(res, expect_result)

