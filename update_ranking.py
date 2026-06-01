import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

# [설정] 5월 31일 데이터도 포함하시려면 날짜를 조정하세요.
START_DATE = "2026-05-31" 
USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

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

# 1. 변수 초기화 (NameError 방지)
raw_data = []
weekly_M, weekly_F = [], []
monthly_M, monthly_F = [], []
now = datetime.now(KST)
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0)

if not login(): exit("로그인 실패")

# 2. 데이터 수집
resp = session.get(BASE_URL, params={"time_start1": START_DATE}, verify=False)
rows = re.findall(r"<tr.*?>(.*?)</tr>", resp.text, re.DOTALL)

print(f"🚀 분석 시작: {len(rows)}개의 행 발견")

for row in rows:
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", row)
    # [수정] 공백과 쉼표 처리를 강화한 정규표현식
    game_match = re.search(r"go_scoreCardPp_stat\s*\(\s*'0'\s*,\s*'([^']+)'\s*,\s*'0'\s*,\s*'([^']+)'\s*\)", row)
    
    if date_match and game_match:
        gserial = game_match.group(1).strip() # 공백 제거 필수
        ccid = game_match.group(2).strip()
        g_date_str = date_match.group(1)
        g_date = datetime.strptime(g_date_str, "%Y-%m-%d").replace(tzinfo=KST)
        
        # 6월 1일 데이터라면 월간 데이터에 포함됨
        if g_date >= start_of_month:
            raw_data.append((gserial, ccid, g_date_str, g_date))

print(f"🔎 유효한 라운드 후보: {len(raw_data)}개")

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
            total_score = sum(int(s.get(f"shot{i}", 0)) for s in score_list)
            diff = total_score - 36
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            
            record = {"name": clean_name, "score": diff, "course": cc_name, "date": date_str}
            
            monthly_M.append(record) if gender == "M" else monthly_F.append(record)
            if dt_obj >= start_of_week:
                weekly_M.append(record) if gender == "M" else weekly_F.append(record)
            print(f"✅ 수집 성공: {clean_name} ({diff}타)")
        except: continue

# 4. 결과 저장
final_json = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "period": {
        "week_start": start_of_week.strftime("%Y-%m-%d"),
        "month_start": start_of_month.strftime("%Y-%m-%d")
    },
    "weekly": { "M": get_rank_data(weekly_M), "F": get_rank_data(weekly_F) },
    "monthly": { "M": get_rank_data(monthly_M), "F": get_rank_data(monthly_F) }
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)
