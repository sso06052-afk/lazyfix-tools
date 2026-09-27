# -*- coding: utf-8 -*-
"""
캠핑 제휴 이동 페이지(go/camp/*.html) 생성기.

2026-09-28: 자동 이동(meta refresh + location.replace)을 걷어내고, 그 자리에 **고를 때 볼 것**을
채운 소개 페이지로 바꿨어요.

왜냐하면 토스 검수 반려 사유가 14회 내내 "외부 링크가 정상적으로 열리지 않아요" 하나였는데,
원인은 **쿠팡이 검수 환경의 접속을 403으로 막는 것**이었어요(www·m·파트너스 단축 링크 전부 실측 403,
UA를 실제 모바일 브라우저로 바꿔도 같음). 자동 이동은 검사기를 그 403으로 곧장 데려가요.
자동 이동을 없애면 이 페이지 자체가 끝점이 되고, 쿠팡으로는 사용자가 버튼을 눌러야 가요.
그리고 페이지에 실제로 읽을 내용이 있어야 "빈 리다이렉트"로 보이지 않아요.

상품을 바꿀 땐 아래 ITEMS의 dest만 고치고 이 스크립트를 다시 돌려요. 앱 번들에는 쿠팡 주소가
들어가지 않아요(앱은 이 페이지 주소만 알아요).

실행: python scripts/build_go_camp.py
"""
import html
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "go" / "camp"

ITEMS = {
    "tent": {
        "name": "원터치 텐트",
        "lead": "혼자서도 몇 분 만에 펼 수 있는 텐트예요. 오토캠핑·차박 입문에 가장 많이 고르는 종류고요.",
        "checks": [
            ("인원 표기보다 한 단계 크게", "‘4인용’은 성인 4명이 어깨를 붙이고 누운 치수예요. 짐까지 들어가려면 실제 인원 +1~2인용을 고르는 게 편해요."),
            ("내수압 1,500mm 이상", "빗방울을 얼마나 버티는지예요. 1,000mm 아래면 소나기에 스며들 수 있어요. 바닥 원단은 3,000mm 이상이면 안심이고요."),
            ("전실이 있는지", "신발·아이스박스를 둘 자리예요. 없으면 텐트 안이 금방 좁아져요."),
        ],
        "miss": "접는 게 펴는 것보다 어려워요. 처음 산 날 집에서 한 번 접어 보고 가면 철수할 때 덜 당황해요.",
        "dest": "https://www.coupang.com/vp/products/8698287549?itemId=25042467185&lptag=AF5755493&src=1139000&spec=10799999&addtag=460&ctag=8698287549",
    },
    "chair": {
        "name": "캠핑 의자",
        "lead": "캠핑에서 가장 오래 쓰는 장비예요. 불 앞에 앉아 있는 시간이 제일 기니까요.",
        "checks": [
            ("로우 체어인지 하이 체어인지", "테이블 높이와 맞춰야 해요. 로우 체어에 하이 테이블을 쓰면 팔을 들고 먹게 돼요."),
            ("내하중과 무게", "내하중 100kg 이상이면 넉넉해요. 백패킹이면 1kg 아래, 오토캠핑이면 무게보다 안정감이 중요해요."),
            ("접었을 때 길이", "트렁크에 몇 개 들어가는지를 좌우해요. 접이 방식(폴딩·롤링)에 따라 차이가 커요."),
        ],
        "miss": "다리 끝이 좁으면 흙바닥에서 푹 꺼져요. 발판이 넓거나 흙받이가 달린 걸 고르면 잔디 캠핑장에서 편해요.",
        "dest": "https://www.coupang.com/vp/products/9599437599?itemId=28656745161&lptag=AF5755493&src=1139000&spec=10799999&addtag=460&ctag=9599437599",
    },
    "table": {
        "name": "캠핑 테이블",
        "lead": "밥 먹는 자리이자 조리대예요. 의자 높이와 세트로 생각해야 해요.",
        "checks": [
            ("의자와 높이 맞추기", "로우 스타일이면 35~40cm, 하이 스타일이면 65~70cm가 일반적이에요."),
            ("상판 재질", "알루미늄 롤테이블은 가볍고 빨리 마르고, 원목은 무겁지만 뜨거운 코펠을 올릴 수 있어요."),
            ("인원당 가로 60cm", "4인이면 120cm 한 개보다 60cm 두 개가 배치가 자유로워요."),
        ],
        "miss": "롤테이블은 상판 틈으로 작은 물건이 빠져요. 잔이나 조미료를 쓸 거면 상판 매트를 같이 챙기세요.",
        "dest": "https://www.coupang.com/vp/products/8220565501?itemId=23626210207&lptag=AF5755493&src=1139000&spec=10799999&addtag=460&ctag=8220565501",
    },
    "fire": {
        "name": "불멍 가루",
        "lead": "장작불에 넣으면 불꽃 색이 파랑·초록으로 바뀌는 가루예요. 아이들이 가장 좋아하는 순간이고요.",
        "checks": [
            ("한 봉지 지속 시간", "보통 10~30분이에요. 하룻밤에 두세 봉지는 있어야 아쉽지 않아요."),
            ("봉지째 넣는 것인지 뿌리는 것인지", "봉지째 넣는 제품이 손이 덜 가고 화상 위험도 적어요."),
            ("성분 표기", "구리·염화물 계열이에요. 조리용 불에는 쓰지 말고 불멍 전용으로만 쓰세요."),
        ],
        "miss": "연기를 직접 들이마시지 않게 바람 방향을 보고 넣어야 해요. 불이 충분히 붙은 뒤에 넣어야 색이 잘 나와요.",
        "dest": "https://www.coupang.com/vp/products/6959736515?itemId=28302648842&lptag=AF5755493&src=1139000&spec=10799999&addtag=460&ctag=6959736515",
    },
    "powerbank": {
        "name": "캠핑용 파워뱅크",
        "lead": "전기 없는 사이트에서 조명·선풍기·전기요를 돌리는 배터리예요. 파워스테이션이라고도 해요.",
        "checks": [
            ("용량은 Wh로 보기", "mAh는 전압에 따라 뜻이 달라져요. 1박이면 300Wh 안팎, 전기요까지 쓰면 500Wh 이상이 필요해요."),
            ("정격 출력(W)", "전기요 60W, 전기포트 900W처럼 기기마다 달라요. 쓸 기기 중 가장 큰 값보다 높아야 해요."),
            ("겨울 성능", "리튬인산철(LiFePO4)이 영하에서 덜 줄고 수명도 길어요."),
        ],
        "miss": "충전에 4~8시간 걸려요. 출발 전날 밤에 꽂아 두세요. 차량 시거잭 충전은 생각보다 훨씬 느려요.",
        "dest": "https://www.coupang.com/vp/products/6070961709?itemId=11208655680&lptag=AF5755493&src=1139000&spec=10799999&addtag=460&ctag=6070961709",
    },
    "generator": {
        "name": "인버터 발전기",
        "lead": "연료로 전기를 만드는 장비예요. 배터리로 모자라는 장박·동계 캠핑에서 써요.",
        "checks": [
            ("캠핑장 규정부터", "발전기를 아예 금지하는 곳이 많아요. 예약 전에 확인하세요."),
            ("소음 50~60dB", "인버터형이 일반형보다 조용해요. 그래도 밤에는 돌리지 않는 게 예의예요."),
            ("정격 출력과 연료 효율", "정격이 순간 최대치보다 중요해요. 1L로 몇 시간 도는지도 같이 보세요."),
        ],
        "miss": "배기가스 때문에 텐트·타프 안에서는 절대 못 써요. 일산화탄소 경보기를 같이 두는 걸 권해요.",
        "dest": "https://www.coupang.com/vp/products/9579007771?itemId=28592807420&lptag=AF5755493&src=1139000&spec=10799999&addtag=460&ctag=9579007771",
    },
    "all": {
        "name": "캠핑용품",
        "lead": "체크리스트에 딱 맞는 상품을 아직 골라 두지 않은 항목이에요. 캠핑용품 전체에서 찾아볼 수 있어요.",
        "checks": [
            ("있는 것부터 확인", "집에 있는 담요·보조배터리·조리도구로 대체되는 게 생각보다 많아요. 첫 캠핑은 빌리거나 있는 걸로 시작해도 충분해요."),
            ("무거운 것부터", "텐트·의자·테이블처럼 부피 큰 것을 먼저 정해야 나머지 크기가 정해져요."),
            ("계절 장비는 마지막에", "난로·전기요·모기장은 갈 시기가 정해진 뒤에 사도 늦지 않아요."),
        ],
        "miss": "한 번에 다 갖추려다 안 쓰는 장비가 쌓여요. 두세 번 다녀오면 뭐가 정말 필요한지 알게 돼요.",
        "dest": "https://www.coupang.com/np/search?q=%EC%BA%A0%ED%95%91%EC%9A%A9%ED%92%88&lptag=AF5755493&src=1139000&spec=10799999&addtag=460",
    },
}

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{name} 고르기 · 캠핑 준비물 리스트</title>
<meta name="description" content="{lead}">
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0 auto; padding: 0 20px 48px; max-width: 560px;
    font-family: -apple-system, "Apple SD Gothic Neo", Pretendard, system-ui, sans-serif;
    color: #191f28; background: #fff; line-height: 1.5;
  }}
  header {{ padding: 32px 0 8px; }}
  .eyebrow {{ font-size: 13px; color: #8b95a1; margin: 0 0 6px; }}
  h1 {{ font-size: 24px; line-height: 1.35; margin: 0 0 10px; letter-spacing: -0.02em; }}
  .lead {{ font-size: 15px; color: #4e5968; margin: 0; }}
  h2 {{ font-size: 17px; margin: 32px 0 12px; letter-spacing: -0.01em; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{ padding: 14px 16px; background: #f9fafb; border-radius: 12px; margin-bottom: 8px; }}
  li b {{ display: block; font-size: 15px; margin-bottom: 4px; }}
  li span {{ font-size: 14px; color: #4e5968; }}
  .tip {{ margin: 0; padding: 14px 16px; border-radius: 12px; background: #f0f6ff; font-size: 14px; color: #1b64da; }}
  .cta {{ margin-top: 32px; }}
  a.btn {{
    display: block; padding: 16px; border-radius: 12px; background: #3182f6;
    color: #fff; text-decoration: none; font-weight: 700; font-size: 16px; text-align: center;
  }}
  .disclosure {{ font-size: 12px; color: #8b95a1; margin-top: 16px; line-height: 1.6; }}
  footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #f2f4f6; font-size: 12px; color: #8b95a1; }}
</style>
</head>
<body>
<header>
  <p class="eyebrow">캠핑 준비물 리스트</p>
  <h1>{name}, 이렇게 고르세요</h1>
  <p class="lead">{lead}</p>
</header>

<h2>고를 때 볼 세 가지</h2>
<ul>
{checks}
</ul>

<h2>처음이면 놓치기 쉬운 것</h2>
<p class="tip">{miss}</p>

<div class="cta">
  <a class="btn" href="{dest}" rel="nofollow noopener">쿠팡에서 {name} 보기</a>
  <p class="disclosure">이 링크는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다. 사는 가격은 달라지지 않아요.</p>
</div>

<footer>
  토스 미니앱 ‘캠핑 준비물 리스트’가 만든 안내 페이지예요. 캠핑 유형과 인원을 고르면 준비물이 자동으로 만들어져요.
</footer>
</body>
</html>
"""


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, item in ITEMS.items():
        checks = "\n".join(
            f"  <li><b>{html.escape(title)}</b><span>{html.escape(desc)}</span></li>"
            for title, desc in item["checks"]
        )
        page = TEMPLATE.format(
            name=html.escape(item["name"]),
            lead=html.escape(item["lead"]),
            checks=checks,
            miss=html.escape(item["miss"]),
            dest=html.escape(item["dest"], quote=True),
        )
        (OUT / f"{slug}.html").write_text(page, encoding="utf-8")
        print(f"{slug}.html  {len(page):,} bytes")


if __name__ == "__main__":
    build()
