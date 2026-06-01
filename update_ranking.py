import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
import calendar
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

# [설정] 수집 시작일을 이번 달 1일로 자동 설정 (매월 리셋 대응)
now = datetime.now(KST)
START_DATE = now.replace(day=1).strftime("%Y-%m-%d") 

USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

# 여성 플레이어 명단
FEMALE_PLAYERS = {"신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애", "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙", "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜"}

LOGIN_URL = "https://screen.sggolf.com/login/checkProcess"
BASE_URL = "https://smanager.sggolf.com/gameInfo/gameDayState"
SCORE_URL = "https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json"

session = requests.Session()

def login():
    data = {"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD}
    r = session.post(LOGIN_URL, data=data, timeout=15, verify=False)
    return "isLogin = true" in r.text

def get_rank_data(records, top_n=5):
    if not records: return []
    best_per_player = {}
    for r in records:
        p = r['name']
        if p not in best_per_player or r['score'] < best_per_player[p]['score']:
            best_per_player[p] = r
    sorted_list = sorted(best_per_player.values(), key=lambda x: (x['score'], x['date']))
    return [{"rank": i+1, **item} for i, item in enumerate(sorted_list[:top_n])]

def fetch_score_card(gserial, ccid):
    params = {"gserial": gserial.strip(), "game_id": "0", "iindex": "0", "ccid": ccid.strip()}
    try:
        r = session.get(SCORE_URL, params=params, timeout=20, verify=False)
        return r.json() if r.status_code == 200 else None
    except: return None

# 1. 변수 초기화 및 기간 계산
raw_data = []
weekly_M, weekly_F = [], []
monthly_M, monthly_F = [], []

# 이번 주 월요일 00:00
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
end_of_week = start_of_week + timedelta(days=6)

# 이번 달 1일 00:00 및 말일 계산
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
last_day = calendar.monthrange(now.year, now.month)[1]
end_of_month = now.replace(day=last_day)

if not login(): exit("로그인 실패")

# 2. 데이터 수집
resp = session.get(BASE_URL, params={"menuId": "57", "parentId": "33", "time_start1": START_DATE}, verify=False)
rows = re.findall(r"<tr.*?>(.*?)</tr>", resp.text, re.DOTALL)

for row in rows:
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", row)
    game_match = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
    
    if date_match and game_match:
        gserial = game_match.group(1).strip()
        ccid = game_match.group(2).strip()
        g_date_str = date_match.group(1)
        g_date = datetime.strptime(g_date_str, "%Y-%m-%d").replace(tzinfo=KST)
        
        # 월간 데이터 필터 (이번 달 1일 ~ 말일)
        if start_of_month <= g_date <= end_of_month:
            raw_data.append((gserial, ccid, g_date_str, g_date))

# 3. 상세 스코어 파싱
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
        
        try:
            total_score = sum(int(s.get(f"shot{i}", 0)) for s in score_list if s.get(f"shot{i}"))
            diff = total_score - 36 
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            
            record = {"name": clean_name, "score": diff, "course": cc_name, "date": date_str}
            
            # 월간 리스트 추가 (이미 위에서 기간 필터링 됨)
            if gender == "M": monthly_M.append(record)
            else: monthly_F.append(record)
            
            # 주간 리스트 추가 (월~일 사이인지 확인)
            if start_of_week <= dt_obj <= end_of_week:
                if gender == "M": weekly_M.append(record)
                else: weekly_F.append(record)
        except: continue

# 4. 결과 저장 (시작/종료 날짜 정보를 모두 포함)
final_json = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "period": {
        "week_start": start_of_week.strftime("%Y-%m-%d"),
        "week_end": end_of_week.strftime("%Y-%m-%d"),
        "month_start": start_of_month.strftime("%Y-%m-%d"),
        "month_end": end_of_month.strftime("%Y-%m-%d")
    },
    "weekly": { "M": get_rank_data(weekly_M), "F": get_rank_data(weekly_F) },
    "monthly": { "M": get_rank_data(monthly_M), "F": get_rank_data(monthly_F) }
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)
