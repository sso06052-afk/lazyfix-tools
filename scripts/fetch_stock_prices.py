"""주식 모의투자(토스 미니앱) 종가 스냅샷. GitHub Actions가 하루 여러 번 실행해 data/stocks/prices.json 을 갱신해요.
원본: appintoss/invest-friends-league/scripts/fetch_prices.py (같은 내용, 기본 출력 경로만 달라요).
출처: Yahoo Finance 차트(하루 1회 종가만 사용). 표준 라이브러리만 써요.

종목 목록(2026-10-01 138종목, 근거: appintoss/docs/apps/invest-friends-league/universe-2026-10-01.md)
- 거래소를 종목마다 들고 있어요: KS=코스피(.KS), KQ=코스닥(.KQ), US=미국(티커 그대로). 국내 ETF는 코스피 상장이라 KS.
  출력에도 종목마다 "ex"(KS/KQ/US)로 남겨요.
- 종목 하나가 실패해도 나머지는 갱신해요 — 실패한 종목은 직전 파일의 값을 그대로 두고 로그(::warning::)에 남겨요.
  (예전엔 한 종목만 실패해도 스크립트가 통째로 죽어서 그날 전 종목이 옛 종가에 멈췄어요.)
- 전 종목이 실패하면(야후 차단 등) 파일을 쓰지 않고 실패(exit 1)로 끝나요.
- 타임머신 1분봉(fetch_minute_bars.py)은 이 목록과 따로 가요(기존 32종목 그대로).

지수(2026-10-01 추가): 코스피 지수 ^KS11 — 앱의 '오늘의 한 문제'(다음 거래일 코스피가 오를까 내릴까) 채점용.
- 매매 종목이 아니라서 앱 종목 목록·검색에는 없어요. 출력 키는 야후 티커 그대로 "^KS11", "ex": "IDX".
- 지수는 소수 둘째 자리까지 남겨요(6971.35). 실패 처리는 종목과 같아요(직전 값 유지).
"""
import json, sys, time, urllib.request, datetime, pathlib

# 코스피(.KS) — 대형주·인기주 + 국내 상장 ETF
KS = ['005930', '000660', '035420', '035720', '005380', '000270', '105560', '055550',
      '373220', '207940', '068270', '005490', '051910', '006400', '034020', '012450',
      '005935', '003670', '329180', '042660', '010140', '267260', '042700', '028260',
      '009150', '066570', '012330', '096770', '259960', '352820', '323410', '011200',
      '003490', '015760', '454910', '032830', '086790', '316140', '000810', '017670',
      '030200', '033780', '034730', '003550', '010130', '011070', '064350', '079550',
      '047810', '009540', '010120', '018260', '377300', '036570', '000100', '128940',
      '298040',
      # ETF
      '069500', '122630', '379800', '360750', '133690', '458730', '381170']
# 코스닥(.KQ)
KQ = ['086520', '247540', '196170', '028300', '141080', '000250', '277810', '263750',
      '214150', '058470', '145020', '293490', '035900', '041510', '039030', '403870']
# 미국 — 개별주 + ETF
US = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AVGO',
      'NFLX', 'AMD', 'COST', 'JPM', 'V', 'KO', 'DIS', 'PLTR',
      'IONQ', 'TSM', 'MU', 'INTC', 'QCOM', 'ORCL', 'SMCI', 'MSTR',
      'COIN', 'RKLB', 'LLY', 'BRK-B', 'CPNG', 'UBER', 'RIVN', 'CRCL',
      'UNH', 'O', 'PEP', 'MCD', 'SBUX', 'NKE', 'WMT', 'BA',
      'XOM', 'PFE', 'ADBE', 'CRM', 'SOFI', 'HOOD', 'ARM', 'ASML',
      'PYPL', 'OKLO',
      # ETF
      'QQQ', 'SPY', 'VOO', 'SCHD', 'TQQQ', 'SOXL', 'JEPI', 'TLT']
# 지수 — 매매 종목 아님(앱 퀴즈 채점용). 야후 티커 그대로 키로 써요.
IDX = ['^KS11']
EXCHANGE = {**{c: 'KS' for c in KS}, **{c: 'KQ' for c in KQ}, **{c: 'US' for c in US}, **{c: 'IDX' for c in IDX}}
UA = {'User-Agent': 'Mozilla/5.0'}


def yahoo_ticker(code):
    ex = EXCHANGE[code]
    if ex == 'IDX':
        return code.replace('^', '%5E')  # URL 경로에 '^'를 그대로 못 넣어요
    return code if ex == 'US' else f'{code}.{ex}'


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


def symbol_entry(code):
    series = chart(yahoo_ticker(code), 'range=3mo')
    digits = 2 if EXCHANGE[code] in ('US', 'IDX') else 0
    pts = [{'d': p['d'], 'c': round(p['c'], digits) if digits else int(round(p['c']))} for p in series[-60:]]
    if len(pts) < 2 or not all(p['c'] > 0 for p in pts):
        raise ValueError(f'시리즈 부족·이상({len(pts)}개)')
    return {'close': pts[-1]['c'], 'prevClose': pts[-2]['c'], 'date': pts[-1]['d'], 'ex': EXCHANGE[code], 'series': pts}


def load_previous(path):
    try:
        prev = json.loads(path.read_text(encoding='utf-8'))
        return prev if isinstance(prev.get('symbols'), dict) else None
    except Exception:
        return None


def main():
    out_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'data' / 'stocks' / 'prices.json'
    prev = load_previous(out_path) or {'symbols': {}}
    out = {'updatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'symbols': {}}
    try:
        out['usdKrw'] = round(chart('KRW=X', 'range=5d')[-1]['c'], 2)
    except Exception as e:
        if not prev.get('usdKrw'):
            raise
        out['usdKrw'] = prev['usdKrw']
        print(f'::warning::환율(KRW=X) 실패, 직전 값 {prev["usdKrw"]} 유지: {e}', file=sys.stderr)
    fresh, kept, lost = 0, [], []
    for code in KS + KQ + US + IDX:
        try:
            out['symbols'][code] = symbol_entry(code)
            fresh += 1
        except Exception as e:
            old = prev['symbols'].get(code)
            if old:
                out['symbols'][code] = old
                kept.append(code)
            else:
                lost.append(code)
            note = '직전 값 유지' if old else '직전 값 없음, 빠짐'
            print(f'::warning::{yahoo_ticker(code)} 실패({note}): {e}', file=sys.stderr)
        time.sleep(0.4)
    if fresh == 0:
        print('::error::전 종목 실패, 파일을 쓰지 않아요', file=sys.stderr)
        sys.exit(1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('ok', f'{fresh}/{len(EXCHANGE)} 갱신', f'유지 {kept}' if kept else '', f'빠짐 {lost}' if lost else '', out['usdKrw'], out_path)


if __name__ == '__main__':
    main()
