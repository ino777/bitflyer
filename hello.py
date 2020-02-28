import sqlite3
import datetime
from pytz import timezone
import jinja2

"""""""""""""""""""""" db """""""""""""""""""""
# con = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)

# cur = con.cursor()
# cur.execute("create table test(d timestamp primarykey not null, ts integer)")

# today = datetime.date.today()
# now = datetime.datetime.now().replace(hour=0, microsecond=0).astimezone(timezone('UTC'))
# num = 122
# print(now)

# cur.execute(
#     '''
#     insert into test(d, ts) values (?, ?)
#     ''',
#     (now, num)
# )
# con.commit()
# cur.execute("select d, ts from test where d = ?", (now,))

# row = cur.fetchone()
# if not row:
#     print(False)
# else:
#     print([v for v in row])
# cur.close()
# con.close()


# con = sqlite3.connect("test.db", detect_types=sqlite3.PARSE_DECLTYPES)
# con.row_factory = sqlite3.Row
# cur = con.cursor()
# cur.execute('select d, ts from test')
# row = cur.fetchone()
# print("current_date", row[0], type(row[0]))
# print("current_timestamp", row[1], type(row[1]))
# print(dict(row))

# con.close()


"""""""""""""""""""""" webserver """""""""""""""""""""
# class CustomHTTPRequestHandler(http.server.CGIHTTPRequestHandler):
#     def do_GET(self):
#         parsed_path = urllib.parse.urlparse(self.path)
#         path = parsed_path.path
#         query = urllib.parse.parse_qs(parsed_path.query)
#         if path == "/":
#             product_code = query['product_code'][0] if query.get('product_code') else config.Config.product_code
#             duration = query['duration'][0] if query.get('duration') else config.Config.trade_duration

#             str_limit = query['limit'][0] if query.get('limit') else '0'
#             try:
#                 limit = int(str_limit)
#             except ValueError as e:
#                 self.send_error(400, 'Bad Request', 'Request:{}\n{}'.format(self.path, e))
#                 return
#             if limit < 0 or limit >  1000:
#                 limit = 1000

#             df = candle.get_all_candles(config.Config.product_code, duration, limit)

#             if self.is_XHR:
#                 try:
#                     js = json.dumps(df)
#                 except Exception as e:
#                     self.send_error(500)

#                 self.send_response(200)
#                 self.send_header('Content-type', 'application/json')
#                 self.end_headers()
#                 self.wfile.write(js)
#                 return

#             self.send_response(200)
#             self.send_header('Content-type', 'text/html; charset=utf-8')
#             self.end_headers()
#             t = jinja2.Template(INDEX_HTML)
#             self.wfile.write(str(t.render(candles=df.candles)).encode('utf-8'))

#         elif path == "/google":
#             self.send_response(200)
#             self.send_header('Content-type', 'text/html; charset=utf-8')
#             self.end_headers()
#             self.wfile.write(GOOGLE_HTML.encode('utf-8'))
#         else:
#             self.send_error(404)
    
#     def do_POST(self):
#         content_len = int(self.headers.get('Content-Length'))
#         data = self.rfile.read(content_len)
#         print(data, type(data))
#         self.send_response(200)
#         self.send_header('Content-type', 'text/plain; charset=utf-8')
#         self.end_headers()
#         self.wfile.write(data)

#     def is_XHR(self):
#         return self.headers.get('X-Requested-With') == 'XMLHTTPRequest'
            
# def start_webserver():
    # handler = CustomHTTPRequestHandler
    # server = http.server.HTTPServer(("", int(config.Config.port)), handler)
    # server.serve_forever()



# ema_ranking = dfcandle.Ranking(10)
# bb_ranking = dfcandle.Ranking(-100)
# ichimoku_ranking = dfcandle.Ranking(3)
# macd_ranking = dfcandle.Ranking(0)
# rsi_ranking = dfcandle.Ranking(-2)

# rankings = dfcandle.Rankings([ema_ranking, bb_ranking, ichimoku_ranking, macd_ranking, rsi_ranking])
# rankings.sort_by_performance()

# for i, ranking in enumerate(rankings.rankings):
#     if i >= config.Config.num_ranking:
#         break
#     if ranking.performance > 0:
#         ranking.enable = True

# print([ranking.__dict__ for ranking in rankings.rankings])
# print(ema_ranking.__dict__)