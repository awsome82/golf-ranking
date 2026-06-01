import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

# 설정
START_DATE = "2026-01-01"  # 수집 시작일
USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

# 여성 플레이어 명단 (제공해주신 리스트 유지)
FEMALE_PLAYERS = {
    "신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애",
    "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙",
    "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜",
}

LOGIN_URL = "https://screen.sggolf.com/login/checkProcess"
BASE_URL = "https://smanager.sggolf.com/gameInfo/gameDayState"
SCORE_URL = "https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json"
session = requests.Session()

def login():
    data = {"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD}
    r = session.post(LOGIN_URL, data=data, timeout=15, verify=False)
    return "isLogin = true" in r.text

def fetch_score_card(gserial, ccid):
    params = {"gserial": gserial, "game_id": "0", "iindex": "0", "ccid": ccid}
    try:
        r = session.get(SCORE_URL, params=params, timeout=20, verify=False)
        return r.json() if r.status_code == 200 else None
    except: return None

def get_rank_data(records, top_n=5):
    """베스트 스코어 기준 정렬 후 상위 n명 반환"""
    # 같은 사람이 여러번 쳤을 경우 가장 좋은 스코어 하나만 기록
    best_per_player = {}
    for r in records:
        p = r['name']
        if p not in best_per_player or r['score'] < best_per_player[p]['score']:
            best_per_player[p] = r
    
    sorted_list = sorted(best_per_player.values(), key=lambda x: (x['score'], x['date']))
    return [{"rank": i+1, **item} for i, item in enumerate(sorted_list[:top_n])]

# 1. 로그인 및 페이지 탐색
if not login(): exit("로그인 실패")

# 이번 주/이번 달 기준 설정
now = datetime.now(KST)
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0)

resp = session.get(BASE_URL, params={"time_start1": START_DATE}, verify=False)
page_html = resp.text
total_pages_match = re.findall(r'onclick="moveList\((\d+)\);', page_html)
total_pages = max(map(int, total_pages_match)) if total_pages_match else 1

raw_data = []

# 2. 데이터 수집 루프
for page in range(1, total_pages + 1):
    p_html = session.get(BASE_URL, params={"time_start1": START_DATE, "pageIndex": page}, verify=False).text
    rows = re.findall(r"<tr.*?>(.*?)</tr>", p_html, re.DOTALL)
    for row in rows:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", row)
        game_match = re.search(r"go_scoreCardPp_stat\('0',\s*'([^']+)'\s*,\s*'0',\s*'([^']+)'\s*\);", row)
        if date_match and game_match:
            g_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=KST)
            # 주간/월간 범위에 드는 데이터만 상세 조회
            if g_date >= start_of_month:
                raw_data.append((game_match.group(1), game_match.group(2), date_match.group(1), g_date))

# 3. 상세 스코어 파싱 및 분류
weekly_M, weekly_F = [], []
monthly_M, monthly_F = [], []

for gserial, ccid, date_str, dt_obj in raw_data:
    data = fetch_score_card(gserial, ccid)
    if not data: continue
    
    members = data.get("GamePlayerMember", {})
    cc_name = members.get("cc", "알 수 없음").strip()
    score_list = data.get("GameInfoListScoreList", [])[:9]
    if len(score_list) < 9: continue

    for i in range(1, 5):
        name = members.get(f"player{i}", "").strip()
        if not name or "guest" in name.lower(): continue
        
        # 멀리건 체크 (제공 코드 로직 활용)
        if any(str(score_obj.get(f"mul_cnt{i}", "0")) != "0" for score_obj in score_list): continue

        try:
            total_score = sum(int(s.get(f"shot{i}", 0)) for s in score_list)
            # 파72 기준 편차 (9홀 기준이므로 보통 36점 기준)
            diff = total_score - 36 
            
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            
            record = {"name": clean_name, "score": diff, "course": cc_name, "date": date_str}
            
            # 월간 데이터 추가
            if gender == "M": monthly_M.append(record)
            else: monthly_F.append(record)
            
            # 주간 데이터 추가
            if dt_obj >= start_of_week:
                if gender == "M": weekly_M.append(record)
                else: weekly_F.append(record)
        except: continue

# 4. 결과 저장
final_json = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "weekly": { "M": get_rank_data(weekly_M), "F": get_rank_data(weekly_F) },
    "monthly": { "M": get_rank_data(monthly_M), "F": get_rank_data(monthly_F) }
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)
