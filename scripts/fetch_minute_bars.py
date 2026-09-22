"""주식 모의투자(토스 미니앱) 타임머신용 1분봉 수집. GitHub Actions가 하루 1회(장 마감 뒤) 실행해요.

- 출처: Yahoo Finance 차트 API 1분봉(과거 데이터, 실시간 아님). 야후는 1분봉을 최근 약 30일치만 주고,
  한 번에 7일 구간까지만 요청할 수 있어서 7일 단위(period1/period2)로 나눠 받아요.
- 저장: data/minute/<symbol>/<YYYY-MM-DD>.json (날짜별 한 파일) + data/minute/index.json(종목별 날짜 목록).
  이미 있는 날짜는 건너뛰고 새 날짜만 추가해요(누적). 첫 실행이면 최근 30일을 채워요.
- 장중(아직 안 끝난) 날짜는 저장하지 않아요. 장 시간: KR 09:00~15:30 KST, US 09:30~16:00 ET.
- 파일 형식(작게): {"s","d","m","tz","open":"09:00","first":분 오프셋,"closeBar":1,"bars":[[시가,고가,저가,종가,거래량],...]}
  bars[i]는 장 시작 + (first + i)분 봉이에요. 거래가 없던 분은 직전 종가로 채워요(거래량 0) — 앱이 1분에 한 봉씩 넘겨요.
- 시가·종가는 공식 값으로 맞춰요(2026-09-23 확인): 첫 봉 시가 = 일봉 시가, 마지막 봉(closeBar) = 일봉 종가(거래량 0).
  야후 국내 1분봉은 대부분 09:00~14:59까지만 있고 15:30 종가(동시호가)가 빠져 있어서, 마지막 1분봉 종가가 공식 종가와
  최대 2% 달랐어요(320일 중 32일만 일치). 미국은 15:59 봉 뒤에 16:00 종가 봉을 붙여요.
- 장 시작부터 없는 날(야후 30일 한도 경계에서 잘린 날)과 일봉 종가가 아직 없는 날은 저장하지 않아요(다음 실행에 다시 봐요).
- 표준 라이브러리만 써요. 실행: python scripts/fetch_minute_bars.py [--days 30] [--rebuild]
  --rebuild: 받을 수 있는 날짜(최근 30일)를 모두 다시 만들어요(형식을 바꿨을 때).
"""
import datetime
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

KR = ['005930', '000660', '035420', '035720', '005380', '000270', '105560', '055550',
      '373220', '207940', '068270', '005490', '051910', '006400', '034020', '012450']
US = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AVGO',
      'NFLX', 'AMD', 'COST', 'JPM', 'V', 'KO', 'DIS', 'PLTR']
UA = {'User-Agent': 'Mozilla/5.0'}

SESSION = {
    # 시장: (시간대, 장 시작, 장 마감)
    'KR': ('Asia/Seoul', datetime.time(9, 0), datetime.time(15, 30)),
    'US': ('America/New_York', datetime.time(9, 30), datetime.time(16, 0)),
}
# 장 마감 뒤 이만큼 지나야 그날을 "끝난 날"로 봐요(야후 반영 지연 여유).
SETTLE_MINUTES = 20
# 봉이 이보다 적으면 불완전한 날로 보고 저장하지 않아요(미국 조기 폐장일 210봉은 통과).
MIN_BARS = 150
ROOT = pathlib.Path(__file__).resolve().parent.parent / 'data' / 'minute'


def fetch_window(ticker, p1, p2):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1m&includePrePost=false'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.load(r)['chart']['result'][0]
        except urllib.error.HTTPError as e:
            if e.code == 422:  # 30일보다 오래된 구간
                return None
            if attempt == 2:
                raise
        except Exception:
            if attempt == 2:
                raise
        time.sleep(2 + attempt * 3)
    return None


def collect(ticker, market, days):
    """최근 days일의 1분봉을 {날짜: {분 오프셋: [o,h,l,c,v]}}로 모아요."""
    tzname, open_t, close_t = SESSION[market]
    tz = ZoneInfo(tzname)
    now = int(time.time())
    start = now - days * 86400
    by_day = {}
    p1 = start
    while p1 < now:
        p2 = min(p1 + 7 * 86400, now)
        res = fetch_window(ticker, p1, p2)
        p1 = p2
        if not res:
            continue
        q = res['indicators']['quote'][0]
        for i, ts in enumerate(res.get('timestamp') or []):
            o, h, l, c, v = q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i]
            if None in (o, h, l, c):
                continue
            local = datetime.datetime.fromtimestamp(ts - ts % 60, tz)
            session_open = datetime.datetime.combine(local.date(), open_t, tz)
            off = int((local - session_open).total_seconds() // 60)
            session_len = int((datetime.datetime.combine(local.date(), close_t, tz) - session_open).total_seconds() // 60)
            if off < 0 or off > session_len or (market == 'US' and off == session_len):
                continue
            by_day.setdefault(local.date().isoformat(), {})[off] = [o, h, l, c, v or 0]
        time.sleep(0.3)
    return by_day


def fetch_daily(ticker):
    """{날짜: (공식 시가, 공식 종가)} — 일봉(최근 3개월). 값이 비어 있는 날은 빼요."""
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=3mo&interval=1d'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                res = json.load(r)['chart']['result'][0]
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 + attempt * 3)
    tz = datetime.timezone(datetime.timedelta(seconds=res['meta']['gmtoffset']))
    q = res['indicators']['quote'][0]
    opens, out = {}, {}
    for i, ts in enumerate(res.get('timestamp') or []):
        day = datetime.datetime.fromtimestamp(ts, tz).date().isoformat()
        o, c = q['open'][i], q['close'][i]
        if o is not None:
            opens[day] = o
        if o is not None and c is not None:
            out[day] = (o, c)
    # 장 마감 직후엔 최신 일봉 종가가 비어 있을 때가 있어요(fetch_stock_prices.py와 같은 처리): 확정 종가로 채워요.
    meta = res['meta']
    rm_time, rm_price = meta.get('regularMarketTime'), meta.get('regularMarketPrice')
    if rm_time and rm_price and time.time() > rm_time + 600:
        rm_day = datetime.datetime.fromtimestamp(rm_time, tz).date().isoformat()
        if rm_day not in out and rm_day in opens:
            out[rm_day] = (opens[rm_day], rm_price)
    return out


def is_settled(day_str, market):
    tzname, _, close_t = SESSION[market]
    tz = ZoneInfo(tzname)
    day = datetime.date.fromisoformat(day_str)
    close_at = datetime.datetime.combine(day, close_t, tz) + datetime.timedelta(minutes=SETTLE_MINUTES)
    return datetime.datetime.now(tz) >= close_at


def to_file(symbol, market, day_str, minutes, official):
    tzname, open_t, _ = SESSION[market]
    digits = 0 if market == 'KR' else 2

    def r(x):
        return int(round(x)) if digits == 0 else round(x, digits)

    # 국내 15:00 봉(가끔 있는 동시호가 자리)은 버리고 공식 종가 봉으로 다시 붙여요.
    cap = 360 if market == 'KR' else 390
    minutes = {off: bar for off, bar in minutes.items() if off < cap}
    offs = sorted(minutes)
    first, last = offs[0], offs[-1]
    bars = []
    prev = None
    for off in range(first, last + 1):
        bar = minutes.get(off)
        if bar is None:  # 거래가 없던 분: 직전 종가로 평평하게, 거래량 0
            c = prev[3]
            bars.append([c, c, c, c, 0])
            continue
        o, h, l, c, v = bar
        prev = [r(o), r(h), r(l), r(c), int(v)]
        bars.append(prev)
    day_open, day_close = r(official[0]), r(official[1])
    b0 = bars[0]
    bars[0] = [day_open, max(b0[1], day_open), min(b0[2], day_open), b0[3], b0[4]]
    bars.append([day_close, day_close, day_close, day_close, 0])  # 공식 종가 봉(국내 15:30·미국 16:00)
    return {'s': symbol, 'd': day_str, 'm': market, 'tz': tzname, 'open': open_t.strftime('%H:%M'), 'first': first, 'closeBar': 1, 'bars': bars}


def main():
    days = 30
    if '--days' in sys.argv:
        days = int(sys.argv[sys.argv.index('--days') + 1])
    days = min(days, 29)  # 야후 1분봉 한도(약 30일) 안쪽
    rebuild = '--rebuild' in sys.argv
    index_path = ROOT / 'index.json'
    index = json.loads(index_path.read_text(encoding='utf-8')) if index_path.exists() else {'symbols': {}}
    added = 0
    for symbol in KR + US:
        market = 'KR' if symbol in KR else 'US'
        ticker = f'{symbol}.KS' if market == 'KR' else symbol
        folder = ROOT / symbol
        folder.mkdir(parents=True, exist_ok=True)
        have = {p.stem for p in folder.glob('*.json')}
        try:
            by_day = collect(ticker, market, days)
            daily = fetch_daily(ticker)
        except Exception as e:  # 한 종목 실패가 전체를 막지 않게
            print('skip', symbol, e)
            by_day, daily = {}, {}
        for day_str, minutes in sorted(by_day.items()):
            complete = len(minutes) >= MIN_BARS and min(minutes) <= 1  # 장 시작부터 있어야 해요
            if rebuild and day_str in have and complete and day_str in daily:
                have.discard(day_str)
            elif rebuild and day_str in have and not complete:
                (folder / f'{day_str}.json').unlink()  # 예전에 잘못 들어간 잘린 날
                have.discard(day_str)
                print('removed partial', symbol, day_str)
                continue
            if day_str in have or not is_settled(day_str, market) or not complete or day_str not in daily:
                continue
            data = to_file(symbol, market, day_str, minutes, daily[day_str])
            (folder / f'{day_str}.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
            have.add(day_str)
            added += 1
        index['symbols'][symbol] = {'m': market, 'dates': sorted(have)}
        print(symbol, len(have), 'days')
    index['updatedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    index['source'] = 'Yahoo Finance 1분봉(과거 데이터, 실시간 아님)'
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('added', added)


if __name__ == '__main__':
    main()
