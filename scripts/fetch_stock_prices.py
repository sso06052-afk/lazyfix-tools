"""주식 모의투자(토스 미니앱) 종가 스냅샷. GitHub Actions가 하루 2회 실행해 data/stocks/prices.json 을 갱신해요.
원본: appintoss/invest-friends-league/scripts/fetch_prices.py (같은 내용, 기본 출력 경로만 달라요).
출처: Yahoo Finance 차트(하루 1회 종가만 사용). 표준 라이브러리만 써요."""
import json, sys, time, urllib.request, datetime, pathlib

KR = ['005930', '000660', '035420', '035720', '005380', '000270', '105560', '055550',
      '373220', '207940', '068270', '005490', '051910', '006400', '034020', '012450']
US = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AVGO',
      'NFLX', 'AMD', 'COST', 'JPM', 'V', 'KO', 'DIS', 'PLTR']
UA = {'User-Agent': 'Mozilla/5.0'}


def chart(ticker, query):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?{query}&interval=1d'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                res = json.load(r)['chart']['result'][0]
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 + attempt * 3)
    tz = datetime.timezone(datetime.timedelta(seconds=res['meta']['gmtoffset']))
    series = []
    for ts, c in zip(res.get('timestamp', []), res['indicators']['quote'][0]['close']):
        if c is None:
            continue
        d = datetime.datetime.fromtimestamp(ts, tz).date().isoformat()
        if series and series[-1]['d'] == d:
            series[-1]['c'] = c
        else:
            series.append({'d': d, 'c': c})
    # 장이 아직 열려 있으면 오늘 봉은 확정 종가가 아니라서 빼요
    meta = res['meta']
    regular = meta.get('currentTradingPeriod', {}).get('regular', {})
    end = regular.get('end')
    if end and time.time() < end + 600 and series and series[-1]['d'] == datetime.datetime.fromtimestamp(end, tz).date().isoformat():
        series.pop()
    # 장 마감 직후엔 일봉 종가가 아직 비어 있을 때가 있어요(2026-09-22 09:44 KST 실행에서 미국 9/21 누락).
    # 그날 정규장이 끝났고(regularMarketTime이 장 마감 시각 이상이거나 다음 장이 이미 잡힘) 일봉이 없으면 확정 종가로 채워요.
    rm_time, rm_price = meta.get('regularMarketTime'), meta.get('regularMarketPrice')
    if rm_time and rm_price and time.time() > rm_time + 600:
        rm_day = datetime.datetime.fromtimestamp(rm_time, tz).date().isoformat()
        session_over = (end and rm_time >= end) or (regular.get('start') and regular['start'] > rm_time)
        if session_over and (not series or series[-1]['d'] < rm_day):
            series.append({'d': rm_day, 'c': rm_price})
    return series


def main():
    out_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'data' / 'stocks' / 'prices.json'
    out = {'updatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'symbols': {}}
    out['usdKrw'] = round(chart('KRW=X', 'range=5d')[-1]['c'], 2)
    for code in KR + US:
        series = chart(f'{code}.KS' if code in KR else code, 'range=3mo')
        digits = 0 if code in KR else 2
        pts = [{'d': p['d'], 'c': round(p['c'], digits) if digits else int(round(p['c']))} for p in series[-60:]]
        out['symbols'][code] = {'close': pts[-1]['c'], 'prevClose': pts[-2]['c'], 'date': pts[-1]['d'], 'series': pts}
        time.sleep(0.4)
    out_path.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('ok', len(out['symbols']), out['usdKrw'], out_path)


if __name__ == '__main__':
    main()
