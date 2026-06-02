import requests, re, os, json, urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

# 설정
START_DATE = "2026-05-01" # 범위를 넉넉히 잡아 5월 데이터도 확인
USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")
FEMALE_PLAYERS = {"신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애", "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙", "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜"}

session = requests.Session()

def login():
    data = {"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD}
    r = session.post("https://screen.sggolf.com/login/checkProcess", data=data, verify=False)
    return "isLogin = true" in r.text

def get_rank_data(records, top_n=5):
    if not records: return []
    best_per_player = {}
    for r in records:
        p = r['name']
        val = int(r['score']) # 강제 정수 변환
        if p not in best_per_player or val < best_per_player[p]['score']:
            r['score'] = val
            best_per_player[p] = r
    # 오름차순 정렬: -5, -2, 0, 3 순서로 배치 (골프 원칙)
    sorted_list = sorted(best_per_player.values(), key=lambda x: (x['score'], x['date']))
    return [{"rank": i+1, **item} for i, item in enumerate(sorted_list[:top_n])]

# 날짜 및 변수 초기화
now = datetime.now(KST)
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
weekly_M, weekly_F, monthly_M, monthly_F = [], [], [], []

if not login(): exit("로그인 실패")

# 데이터 수집
resp = session.get("https://smanager.sggolf.com/gameInfo/gameDayState", params={"time_start1": START_DATE}, verify=False)
rows = re.findall(r"<tr.*?>(.*?)</tr>", resp.text, re.DOTALL)

for row in rows:
    d_m = re.search(r"(\d{4}-\d{2}-\d{2})", row)
    g_m = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
    if d_m and g_m:
        gserial, ccid, d_str = g_m.group(1).strip(), g_m.group(2).strip(), d_m.group(1)
        dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
        
        # 스코어카드 상세 조회
        r_json = session.get("https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json", params={"gserial": gserial, "game_id": "0", "iindex": "0", "ccid": ccid}, verify=False).json()
        members = r_json.get("GamePlayerMember", {})
        scores = r_json.get("GameInfoListScoreList", [])[:9]
        if len(scores) < 9: continue

        for i in range(1, 5):
            name = members.get(f"player{i}", "").strip()
            if not name or "guest" in name.lower(): continue
            try:
                # 타수 계산
                total = sum(int(s.get(f"shot{i}", 0)) for s in scores if s.get(f"shot{i}"))
                diff = total - 36
                clean_name = re.sub(r'\(.*?\)', '', name).strip()
                gender = "F" if clean_name in FEMALE_PLAYERS else "M"
                record = {"name": clean_name, "score": int(diff), "course": members.get("cc", "알수없음"), "date": d_str}
                
                # 기간별 분류
                if dt >= start_of_month:
                    monthly_M.append(record) if gender == "M" else monthly_F.append(record)
                if dt >= start_of_week:
                    weekly_M.append(record) if gender == "M" else weekly_F.append(record)
            except: continue

# JSON 저장
data = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "period": {"week_start": start_of_week.strftime("%Y-%m-%d"), "month_start": start_of_month.strftime("%Y-%m-%d")},
    "weekly": {"M": get_rank_data(weekly_M), "F": get_rank_data(weekly_F)},
    "monthly": {"M": get_rank_data(monthly_M), "F": get_rank_data(monthly_F)}
}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
