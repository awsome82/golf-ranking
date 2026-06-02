import requests, re, os, json, urllib3
from datetime import datetime, timezone, timedelta
import calendar

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

START_DATE = "2026-06-01" 
USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

FEMALE_PLAYERS = {"신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애", "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙", "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜"}

def get_rank_data(records, top_n=5):
    if not records: return []
    best_per_player = {}
    for r in records:
        p = r['name']
        score_val = int(r['score'])
        if p not in best_per_player or score_val < best_per_player[p]['score']:
            r['score'] = score_val
            best_per_player[p] = r
    sorted_list = sorted(best_per_player.values(), key=lambda x: (x['score'], x['date']))
    return [{"rank": i+1, **item} for i, item in enumerate(sorted_list[:top_n])]

session = requests.Session()
def login():
    data = {"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD}
    r = session.post("https://screen.sggolf.com/login/checkProcess", data=data, verify=False)
    return "isLogin = true" in r.text

now = datetime.now(KST)
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

if not login(): exit("로그인 실패")

# 1. 페이지 탐색
raw_candidates = []
for page in range(1, 4):
    resp = session.get("https://smanager.sggolf.com/gameInfo/gameDayState", 
                       params={"time_start1": START_DATE, "pageIndex": page}, verify=False)
    rows = re.findall(r"<tr.*?>(.*?)</tr>", resp.text, re.DOTALL)
    if not rows or "데이터가 없습니다" in resp.text: break
    for row in rows:
        d_m = re.search(r"(\d{4}-\d{2}-\d{2})", row)
        g_m = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
        if d_m and g_m:
            raw_candidates.append((g_m.group(1).strip(), g_m.group(2).strip(), d_m.group(1)))

weekly_M, weekly_F, monthly_M, monthly_F = [], [], [], []
printed_debug = False # 진단 로그 제어용

# 2. 데이터 분석
for gserial, ccid, d_str in raw_candidates:
    dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
    r_json = session.get("https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json", 
                         params={"gserial": gserial, "ccid": ccid}, verify=False).json()
    
    members = r_json.get("GamePlayerMember", {})
    scores = r_json.get("GameInfoListScoreList", [])[:9]
    if len(scores) < 9: continue

    # 🔍 [진단 블록] 딱 한 번만 JSON 내부의 진짜 키 값을 로그에 출력합니다.
    if not printed_debug:
        print("\n=== ⚙️ SG골프 스코어카드 데이터 구조 진단 ===")
        print("1. 요약 정보(members) 키 목록:", list(members.keys()))
        if scores:
            print("2. 홀별 정보(scores[0]) 키 목록:", list(scores[0].keys()))
            print("3. 첫 번째 홀 데이터 샘플:", scores[0])
        print("=============================================\n")
        printed_debug = True

    for i in range(1, 5):
        name = members.get(f"player{i}", "").strip()
        if not name or "guest" in name.lower(): continue
        
        # ⚠️ 진짜 키를 찾기 전까지 임시로 0 처리하여 필터링 오작동을 차단합니다.
        player_mulligans = 0 

        try:
            total = sum(int(s.get(f"shot{i}", 0)) for s in scores if s.get(f"shot{i}"))
            diff = int(total - 36)
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            record = {"name": clean_name, "score": diff, "course": members.get("cc", "알수없음"), "date": d_str}
            
            if dt >= start_of_month:
                monthly_M.append(record) if gender == "M" else monthly_F.append(record)
            if dt >= start_of_week:
                weekly_M.append(record) if gender == "M" else weekly_F.append(record)
            print(f"✅ 수집 성공: {clean_name} ({diff}타, {members.get('cc')})")
        except: continue

# 3. 데이터 저장
data = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "period": {
        "week_start": start_of_week.strftime("%Y-%m-%d"),
        "week_end": (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d"),
        "month_start": start_of_month.strftime("%Y-%m-%d")
    },
    "weekly": {"M": get_rank_data(weekly_M), "F": get_rank_data(weekly_F)},
    "monthly": {"M": get_rank_data(monthly_M), "F": get_rank_data(monthly_F)}
}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
