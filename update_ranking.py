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

# 이번 달 1일부터 전체 수집 보장
START_DATE = start_of_month.strftime("%Y-%m-%d")

if not login(): exit("로그인 실패")

# 💡 기록이 많아 뒤로 밀린 경우를 대비하여 최대 10페이지까지 샅샅이 검색합니다.
raw_candidates = []
for page in range(1, 11):
    resp = session.get("https://smanager.sggolf.com/gameInfo/gameDayState", 
                       params={"time_start1": START_DATE, "pageIndex": page}, verify=False)
    rows = re.findall(r"<tr.*?>(.*?)</tr>", resp.text, re.DOTALL)
    if not rows or "데이터가 없습니다" in resp.text: break
    for row in rows:
        d_m = re.search(r"(\d{4}-\d{2}-\d{2})", row)
        g_m = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
        if d_m and g_m:
            raw_candidates.append((g_m.group(1).strip(), g_m.group(2).strip(), d_m.group(1)))

print(f"🔎 이번 달 1일부터 현재까지 총 {len(raw_candidates)}개의 라운드 정밀 분석 진행")

weekly_M, weekly_F, monthly_M, monthly_F = [], [], [], []

for gserial, ccid, d_str in raw_candidates:
    dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
    try:
        # ⚠️ [오류 해결] 충돌을 일으키던 game_id, iindex 파라미터를 제거하여 정상 스코어카드를 호출합니다.
        params = {"gserial": gserial, "ccid": ccid}
        r_json = session.get("https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json", params=params, verify=False).json()
        
        members = r_json.get("GamePlayerMember", {})
        score_list = r_json.get("GameInfoListScoreList", [])
        if not score_list: continue

        # 🎯 [신규] 9홀 / 18홀 라운드 동적 판별 및 기준 타수(Par) 설정
        num_holes = len(score_list)
        if num_holes >= 18:
            scores = score_list[:18]
            par_base = 72
        elif num_holes >= 9:
            scores = score_list[:9]
            par_base = 36
        else:
            continue # 9홀 미만 연습 라운드 제외

        for i in range(1, 5):
            name = members.get(f"player{i}", "").strip()
            if not name or "guest" in name.lower(): continue
            
            # ⚠️ [개인 멀리건 필터] 방 설정값인 mul_cnt 대신, 본인의 진짜 멀리건 키(m1, mm1 등)만 합산
            player_mulligans = sum(
                int(s.get(f"m{i}", s.get(f"m{i:02d}", 0))) + 
                int(s.get(f"mm{i}", s.get(f"mm{i:02d}", 0))) 
                for s in scores
            )
            
            if player_mulligans > 0:
                print(f"⏩ 제외: {name} ({d_str}) - 개인 멀리건 {player_mulligans}회 사용 발견")
                continue

            # 타수 계산 (shot1, shot01 유연하게 매칭)
            total_shots = sum(int(s.get(f"shot{i}", s.get(f"shot{i:02d}", 0))) for s in scores)
            if total_shots == 0: continue
            
            diff = int(total_shots - par_base)
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            record = {"name": clean_name, "score": diff, "course": members.get("cc", "알수없음"), "date": d_str}
            
            if dt >= start_of_month:
                monthly_M.append(record) if gender == "M" else monthly_F.append(record)
            if start_of_week <= dt <= end_of_week:
                weekly_M.append(record) if gender == "M" else weekly_F.append(record)
                
            print(f"✅ 수집 성공: {clean_name} ({diff:+d}타, {members.get('cc')} {num_holes}홀)")
    except:
        continue

# 최종 데이터 구조화 저장
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
print("🚀 9/18홀 동적 분석 및 개인 멀리건 필터링 완료")
