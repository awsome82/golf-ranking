import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
import calendar
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

# 이번 달 1일부터 수집
now = datetime.now(KST)
START_DATE = now.replace(day=1).strftime("%Y-%m-%d") 
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
        # ⚠️ 핵심: 모든 스코어를 정수(int)로 강제 변환
        try:
            score_val = int(r['score'])
        except:
            continue
            
        if p not in best_per_player or score_val < best_per_player[p]['score']:
            r['score'] = score_val
            best_per_player[p] = r
    
    # 낮은 타수가 상단에 오도록 오름차순 정렬 (Low Score Wins)
    # 정렬 기준 1: 스코어(낮은 순), 기준 2: 날짜(동점 시 먼저 친 사람 우대)
    sorted_list = sorted(best_per_player.values(), key=lambda x: (x['score'], x['date']))
    
    return [{"rank": i+1, **item} for i, item in enumerate(sorted_list[:top_n])]

def fetch_score_card(gserial, ccid):
    params = {"gserial": gserial.strip(), "game_id": "0", "iindex": "0", "ccid": ccid.strip()}
    try:
        r = session.get(SCORE_URL, params=params, timeout=20, verify=False)
        return r.json() if r.status_code == 200 else None
    except: return None

# 기간 계산
weekly_M, weekly_F = [], []
monthly_M, monthly_F = [], []
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
end_of_week = start_of_week + timedelta(days=6)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

if not login(): exit("로그인 실패")

resp = session.get(BASE_URL, params={"menuId": "57", "parentId": "33", "time_start1": START_DATE}, verify=False)
rows = re.findall(r"<tr.*?>(.*?)</tr>", resp.text, re.DOTALL)

for row in rows:
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", row)
    game_match = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
    if date_match and game_match:
        gserial, ccid, d_str = game_match.group(1).strip(), game_match.group(2).strip(), date_match.group(1)
        g_date = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
        
        # 상세 데이터 수집
        data = fetch_score_card(gserial, ccid)
        if not data: continue
        members = data.get("GamePlayerMember", {})
        score_list = data.get("GameInfoListScoreList", [])[:9]
        if len(score_list) < 9: continue

        for i in range(1, 5):
            name = members.get(f"player{i}", "").strip()
            if not name or "guest" in name.lower(): continue
            try:
                total = sum(int(s.get(f"shot{i}", 0)) for s in score_list if s.get(f"shot{i}"))
                diff = total - 36
                clean_name = re.sub(r'\(.*?\)', '', name).strip()
                gender = "F" if clean_name in FEMALE_PLAYERS else "M"
                record = {"name": clean_name, "score": int(diff), "course": members.get("cc", "알수없음"), "date": d_str}
                
                monthly_M.append(record) if gender == "M" else monthly_F.append(record)
                if start_of_week <= g_date <= end_of_week:
                    weekly_M.append(record) if gender == "M" else weekly_F.append(record)
            except: continue

final_json = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "period": {
        "week_start": start_of_week.strftime("%Y-%m-%d"),
        "week_end": end_of_week.strftime("%Y-%m-%d"),
        "month_start": start_of_month.strftime("%Y-%m-%d")
    },
    "weekly": { "M": get_rank_data(weekly_M), "F": get_rank_data(weekly_F) },
    "monthly": { "M": get_rank_data(monthly_M), "F": get_rank_data(monthly_F) }
}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)
