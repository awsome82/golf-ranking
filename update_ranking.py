import requests, re, os, json, urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

# 여성 플레이어 명단
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

# 1. 기존 랭킹 데이터 로드 (데일리 누적용)
existing_data = {}
if os.path.exists("data.json"):
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except:
        pass

# 2. 기준 시간 및 최근 2일 데이터 수집 범위 설정
now = datetime.now(KST)
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
START_DATE = (now - timedelta(days=1)).strftime("%Y-%m-%d")

# 3. 주간/월간 리셋 조건 체크 및 기존 데이터 승계
old_period = existing_data.get("period", {})
base_weekly_M = existing_data.get("weekly", {}).get("M", []) if old_period.get("week_start") == start_of_week.strftime("%Y-%m-%d") else []
base_weekly_F = existing_data.get("weekly", {}).get("F", []) if old_period.get("week_start") == start_of_week.strftime("%Y-%m-%d") else []
base_monthly_M = existing_data.get("monthly", {}).get("M", []) if old_period.get("month_start") == start_of_month.strftime("%Y-%m-%d") else []
base_monthly_F = existing_data.get("monthly", {}).get("F", []) if old_period.get("month_start") == start_of_month.strftime("%Y-%m-%d") else []

if not login(): exit("로그인 실패")

# 4. 최근 데이터 가볍게 긁어오기
raw_candidates = []
resp = session.get("https://smanager.sggolf.com/gameInfo/gameDayState", params={"time_start1": START_DATE}, verify=False)
rows = re.findall(r"<tr.*?>(.*?)</tr>", resp.text, re.DOTALL)

for row in rows:
    d_m = re.search(r"(\d{4}-\d{2}-\d{2})", row)
    g_m = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
    if d_m and g_m:
        raw_candidates.append((g_m.group(1).strip(), g_m.group(2).strip(), d_m.group(1)))

print(f"🔎 최근 등록된 {len(raw_candidates)}개의 라운드 증분 분석 시작 (기준일: {START_DATE})")

new_weekly_M, new_weekly_F, new_monthly_M, new_monthly_F = [], [], [], []

# 5. 스코어카드 파싱 및 개인 멀리건 정밀 필터링
for gserial, ccid, d_str in raw_candidates:
    dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
    try:
        r_json = session.get("https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json", 
                             params={"gserial": gserial, "ccid": ccid}, verify=False).json()
        members = r_json.get("GamePlayerMember", {})
        scores = r_json.get("GameInfoListScoreList", [])[:9]
        if len(scores) < 9: continue

        for i in range(1, 5):
            name = members.get(f"player{i}", "").strip()
            if not name or "guest" in name.lower(): continue
            
            # ⚠️ 핵심 수정: 팀 전체가 아닌 오직 '해당 플레이어(i)'의 개인 멀리건 수만 체크합니다.
            # 룸 공통 일련번호 형식(m01)이 아닌 개인 식별 키(m1, mm1, mul_cnt1)를 합산합니다.
            player_mulligans = sum(
                int(s.get(f"m{i}", 0)) + int(s.get(f"mm{i}", 0)) + int(s.get(f"mul_cnt{i}", 0)) 
                for s in scores
            )
            
            if player_mulligans > 0:
                print(f"⏩ 제외: {name} ({d_str}) - 개인 멀리건 {player_mulligans}회 사용 검출")
                continue

            # 정상 스코어 계산 (기존에 완벽히 검증된 수식 유지)
            total = sum(int(s.get(f"shot{i}", 0)) for s in scores if s.get(f"shot{i}"))
            if total == 0: continue
            
            diff = int(total - 36)
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            record = {"name": clean_name, "score": diff, "course": members.get("cc", "알수없음"), "date": d_str}
            
            if dt >= start_of_month:
                new_monthly_M.append(record) if gender == "M" else new_monthly_F.append(record)
            if dt >= start_of_week:
                new_weekly_M.append(record) if gender == "M" else new_weekly_F.append(record)
            print(f"✅ 수집 성공: {clean_name} ({diff:+d}타, {members.get('cc')})")
    except: continue

# 6. 히스토리 데이터와 신규 데이터 병합 후 재정렬
final_weekly_M = get_rank_data(base_weekly_M + new_weekly_M)
final_weekly_F = get_rank_data(base_weekly_F + new_weekly_F)
final_monthly_M = get_rank_data(base_monthly_M + new_monthly_M)
final_monthly_F = get_rank_data(base_monthly_F + new_monthly_F)

# 7. 갱신된 내역 저장
data = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "period": {
        "week_start": start_of_week.strftime("%Y-%m-%d"),
        "week_end": (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d"),
        "month_start": start_of_month.strftime("%Y-%m-%d")
    },
    "weekly": {"M": final_weekly_M, "F": final_weekly_F},
    "monthly": {"M": final_monthly_M, "F": final_monthly_F}
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("🚀 개인 멀리건 정밀 필터링 및 데이터 증분 누적 완료")
