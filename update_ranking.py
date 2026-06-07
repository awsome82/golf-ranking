import requests, re, os, json, urllib3
from datetime import datetime, timezone, timedelta
import calendar

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
            
    # 낮은 타수가 1등이 되도록 오름차순 정렬 (-3, -2, E, +1...)
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
end_of_week = start_of_week + timedelta(days=6)

# 💡 가상 환경 초기화로 인한 데이터 누락을 방지하기 위해 이번 달 1일부터 깔끔하게 수집합니다.
# (3페이지 이내 탐색이므로 실행 속도는 3~5초 내외로 매우 빠르고 안전합니다.)
START_DATE = start_of_month.strftime("%Y-%m-%d")

if not login(): exit("로그인 실패")

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

print(f"🔎 이번 달 1일({START_DATE})부터 현재까지 총 {len(raw_candidates)}개의 라운드 분석 진행")

weekly_M, weekly_F, monthly_M, monthly_F = [], [], [], []
debug_done = False

for gserial, ccid, d_str in raw_candidates:
    dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
    try:
        # ⚠️ [핵심 복구] 필수 파라미터 game_id와 iindex를 다시 주입하여 진짜 스코어 데이터를 가져옵니다.
        params = {"gserial": gserial, "game_id": "0", "iindex": "0", "ccid": ccid}
        r_json = session.get("https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json", params=params, verify=False).json()
        
        members = r_json.get("GamePlayerMember", {})
        scores = r_json.get("GameInfoListScoreList", [])[:9]
        if len(scores) < 9: continue

        # 🔍 [올바른 데이터 상태에서의 키 값 진단 정보 출력]
        if not debug_done:
            print("\n=== 🎯 [정상 데이터 수신 상태] 홀 데이터 구조 ===")
            print("Hole 1 Keys:", list(scores[0].keys()))
            print("Hole 1 Data Sample:", scores[0])
            print("================================================\n")
            debug_done = True

        for i in range(1, 5):
            name = members.get(f"player{i}", "").strip()
            if not name or "guest" in name.lower(): continue
            
            # 파라미터가 복구되었으므로 기존의 직관적인 shot{i} 키값으로 타수가 완벽하게 계산됩니다.
            total = sum(int(s.get(f"shot{i}", 0)) for s in scores if s.get(f"shot{i}"))
            if total == 0: continue
            
            diff = int(total - 36)
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            record = {"name": clean_name, "score": diff, "course": members.get("cc", "알수없음"), "date": d_str}
            
            # 우선 필터 없이 모든 인원을 보드에 채웁니다. (윤기님 -2, 기성님 -3 정상 출력 목적)
            if dt >= start_of_month:
                monthly_M.append(record) if gender == "M" else monthly_F.append(record)
            if start_of_week <= dt <= end_of_week:
                weekly_M.append(record) if gender == "M" else weekly_F.append(record)
                
            print(f"✅ 수집 성공: {clean_name} ({diff:+d}타, {members.get('cc')})")
    except:
        continue

# 최종 저장
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
print("🚀 원상복구 완료 및 data.json 정상 저장 완료")
