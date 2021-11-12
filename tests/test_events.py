import datetime
from unittest import TestCase
from unittest.mock import patch, MagicMock

from app.models.events import SignalEvent, SignalEvents, get_signal_events_by_count, get_signal_events_after_time

class TestEvent(TestCase):
    def setUp(self):
        self.product_code = 'BTC_JPY'


    def test_can_buy_time(self):
        now = datetime.datetime.now()

        test_petterns = [
            ([], now, True), # not signals
            ([now-datetime.timedelta(days=1)], now, True), # last signal time < now
            ([now+datetime.timedelta(days=1)], now, False), # last signal time > now
        ]

        
        for times, t, expect_result in test_petterns:
            with self.subTest(times=times, t=t):
                s = SignalEvents([SignalEvent(time, self.product_code, 'SELL', 1, 1) for time in times])
                self.assertEqual(s.can_buy(t), expect_result)
    
    def test_can_buy_side(self):
        now = datetime.datetime.now()
        test_petterns = [
            ('BUY', False),
            ('SELL', True)
        ]

        for side, expect_result in test_petterns:
            with self.subTest(side=side):
                s = SignalEvents([SignalEvent(now - datetime.timedelta(days=1), self.product_code, side, 1, 1)])
                self.assertEqual(s.can_buy(now), expect_result)
    
    def test_can_sell_time(self):
        now = datetime.datetime.now()

        test_petterns = [
            ([], now, False), # not signals
            ([now-datetime.timedelta(days=1)], now, True), # last signal time < now
            ([now+datetime.timedelta(days=1)], now, False), # last signal time > now
        ]

        
        for times, t, expect_result in test_petterns:
            with self.subTest(times=times, t=t):
                s = SignalEvents([SignalEvent(time, self.product_code, 'BUY', 1, 1) for time in times])
                self.assertEqual(s.can_sell(t), expect_result)
    
    def test_can_sell_side(self):
        now = datetime.datetime.now()
        test_petterns = [
            ('BUY', True),
            ('SELL', False)
        ]

        for side, expect_result in test_petterns:
            with self.subTest(side=side):
                s = SignalEvents([SignalEvent(now - datetime.timedelta(days=1), self.product_code, side, 1, 1)])
                self.assertEqual(s.can_sell(now), expect_result)
    
    def test_profit(self):
        now = datetime.datetime.now()
        signals = [
            SignalEvent(now-datetime.timedelta(days=3), self.product_code, 'BUY', 1, 1),
            SignalEvent(now-datetime.timedelta(days=2), self.product_code, 'SELL', 2, 1),
            SignalEvent(now-datetime.timedelta(days=1), self.product_code, 'BUY', 1, 0.5),
        ]
        s = SignalEvents(signals)
        self.assertEqual(s.profit(), 1.0)
