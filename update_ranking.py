"""
golf_ranking.py
────────────────────────────────────────────────────────────
sggolf.com 전체 구장 대상 주간·월간 베스트 스코어 Top5 수집기
- 구장(CC) 필터 없음 → 전 구장 통합 랭킹
- 멀리건 사용 라운드 제외
- 동일 플레이어는 기간 내 최고 스코어 1개만 반영
- 결과: data.json 저장
────────────────────────────────────────────────────────────
"""

import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── 상수 ────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
PAR_9 = 36          # 9홀 파 기준 (스코어 편차 계산용)
TOP_N = 5           # 랭킹 상위 인원 수
START_DATE = "2025-01-01"  # 수집 시작일 (월간 기준보다 충분히 이전)

USER_ID  = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

LOGIN_URL = "https://screen.sggolf.com/login/checkProcess"
BASE_URL  = "https://smanager.sggolf.com/gameInfo/gameDayState"
SCORE_URL = "https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json"

# ── 여성 플레이어 명단 ──────────────────────────────────────
FEMALE_PLAYERS = {
    "신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애",
    "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙",
    "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜",
}

# ── 세션 ─────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


# ─────────────────────────────────────────────────────────────
# 로그인
# ─────────────────────────────────────────────────────────────
def login() -> bool:
    resp = session.post(
        LOGIN_URL,
        data={"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD},
        timeout=15,
        verify=False,
    )
    return "isLogin = true" in resp.text


# ─────────────────────────────────────────────────────────────
# 스코어카드 API 호출
# ─────────────────────────────────────────────────────────────
def fetch_score_card(gserial: str, ccid: str) -> dict | None:
    try:
        resp = session.get(
            SCORE_URL,
            params={"gserial": gserial, "game_id": "0", "iindex": "0", "ccid": ccid},
            timeout=20,
            verify=False,
        )
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# Top-N 랭킹 계산 (플레이어별 최고 스코어 1개만)
# ─────────────────────────────────────────────────────────────
def build_ranking(records: list[dict], top_n: int = TOP_N) -> list[dict]:
    best: dict[str, dict] = {}
    for r in records:
        name = r["name"]
        if name not in best or r["score"] < best[name]["score"]:
            best[name] = r
    sorted_list = sorted(best.values(), key=lambda x: (x["score"], x["date"]))
    return [{"rank": i + 1, **item} for i, item in enumerate(sorted_list[:top_n])]


# ─────────────────────────────────────────────────────────────
# 게임 목록 HTML에서 (gserial, ccid, date, dt) 추출
# ─────────────────────────────────────────────────────────────
def extract_games(html: str, cutoff: datetime) -> list[tuple]:
    results = []
    rows = re.findall(r"<tr.*?>(.*?)</tr>", html, re.DOTALL)
    for row in rows:
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", row)
        game_m = re.search(
            r"go_scoreCardPp_stat\('0',\s*'([^']+)'\s*,\s*'0',\s*'([^']+)'\s*\);",
            row,
        )
        if date_m and game_m:
            dt = datetime.strptime(date_m.group(1), "%Y-%m-%d").replace(tzinfo=KST)
            if dt >= cutoff:
                results.append((game_m.group(1), game_m.group(2), date_m.group(1), dt))
    return results


# ─────────────────────────────────────────────────────────────
# 메인 수집 로직
# ─────────────────────────────────────────────────────────────
def main():
    if not login():
        raise SystemExit("❌ 로그인 실패 – SG_ID / SG_PW 환경변수를 확인하세요.")

    now = datetime.now(KST)
    start_of_week  = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1페이지 → 총 페이지 수 파악
    first_page = session.get(
        BASE_URL, params={"time_start1": START_DATE}, verify=False
    ).text
    page_nums = list(map(int, re.findall(r'onclick="moveList\((\d+)\);"', first_page)))
    total_pages = max(page_nums) if page_nums else 1

    print(f"📋 총 {total_pages}페이지 수집 시작 (월 기준: {start_of_month.date()})")

    # 월 기준 이후 게임만 수집 (월간 범위가 주간 범위를 포함하므로 cutoff = 월 시작)
    raw_games: list[tuple] = []
    for page in range(1, total_pages + 1):
        html = session.get(
            BASE_URL,
            params={"time_start1": START_DATE, "pageIndex": page},
            verify=False,
        ).text
        raw_games.extend(extract_games(html, cutoff=start_of_month))
        if not raw_games and page > 3:
            # 월초보다 이전 데이터만 있으면 중단
            break

    print(f"  → 대상 게임 {len(raw_games)}건 스코어 조회 중…")

    weekly_M,  weekly_F  = [], []
    monthly_M, monthly_F = [], []

    for gserial, ccid, date_str, dt_obj in raw_games:
        data = fetch_score_card(gserial, ccid)
        if not data:
            continue

        members    = data.get("GamePlayerMember", {})
        score_list = data.get("GameInfoListScoreList", [])[:9]
        cc_name    = members.get("cc", "알 수 없음").strip()

        if len(score_list) < 9:
            continue  # 9홀 미만 라운드 제외

        for i in range(1, 5):
            name = members.get(f"player{i}", "").strip()
            if not name or "guest" in name.lower():
                continue

            # 멀리건 사용 시 제외
            if any(str(s.get(f"mul_cnt{i}", "0")) != "0" for s in score_list):
                continue

            try:
                total = sum(int(s.get(f"shot{i}", 0)) for s in score_list)
            except (ValueError, TypeError):
                continue

            diff = total - PAR_9
            clean = re.sub(r"\(.*?\)", "", name).strip()
            gender = "F" if clean in FEMALE_PLAYERS else "M"

            record = {
                "name":   clean,
                "score":  diff,
                "course": cc_name,
                "date":   date_str,
            }

            # 월간 분류
            if gender == "M":
                monthly_M.append(record)
            else:
                monthly_F.append(record)

            # 주간 분류
            if dt_obj >= start_of_week:
                if gender == "M":
                    weekly_M.append(record)
                else:
                    weekly_F.append(record)

    result = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "period": {
            "week_start":  start_of_week.strftime("%Y-%m-%d"),
            "month_start": start_of_month.strftime("%Y-%m-%d"),
        },
        "weekly":  {"M": build_ranking(weekly_M),  "F": build_ranking(weekly_F)},
        "monthly": {"M": build_ranking(monthly_M), "F": build_ranking(monthly_F)},
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ data.json 저장 완료 – 주간 남{len(result['weekly']['M'])}·여{len(result['weekly']['F'])} / "
          f"월간 남{len(result['monthly']['M'])}·여{len(result['monthly']['F'])}")


if __name__ == "__main__":
    main()
