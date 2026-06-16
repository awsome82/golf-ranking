import requests, re, os, json, urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

# 여성 플레이어 명단
FEMALE_PLAYERS = {"신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애", "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙", "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜", "은하"}

def check_mulligan_value(val) -> bool:
    """코랩 소스 코드의 멀리건 판별 로직 적용"""
    if val is None:
        return False
    numbers = re.findall(r'\d+', str(val).strip())
    return sum(int(n) for n in numbers) > 0 if numbers else False

def get_total_pages(html: str) -> int:
    """코랩 소스 코드의 동적 페이지 수 계산 로직 적용"""
    nums = re.findall(r'onclick="moveList\((\d+)\);', html)
    return max(map(int, nums)) if nums else 1

def get_rank_data(records, top_n=5):
    if not records: return []
    best_per_player = {}
    for r in records:
        p = r['name']
        score_val = int(r['score'])
        if p not in best_per_player or score_val < best_per_player[p]['score']:
            r['score'] = score_val
            best_per_player[p] = r
            
    # 낮은 타수가 1등이 되도록 오름차순 정렬
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

START_DATE = start_of_month.strftime("%Y-%m-%d")

if not login(): exit("로그인 실패")

# 1. 첫 페이지를 먼저 호출하여 총 페이지 수를 동적으로 계산합니다.
first_resp = session.get("https://smanager.sggolf.com/gameInfo/gameDayState", 
                         params={"time_start1": START_DATE}, verify=False)
total_pages = get_total_pages(first_resp.text)
print(f"📊 이번 달 데이터 동적 분석 시작: 총 {total_pages}페이지 탐색")

raw_candidates = []
# 2. 계산된 total_pages 만큼 루프를 돌기 때문에 데이터 증가에 완벽히 대응합니다.
for page in range(1, total_pages + 1):
    page_html = first_resp.text if page == 1 else session.get(
        "https://smanager.sggolf.com/gameInfo/gameDayState", 
        params={"time_start1": START_DATE, "pageIndex": page}, verify=False
    ).text
    
    rows = re.findall(r"<tr.*?>(.*?)</tr>", page_html, re.DOTALL)
    for row in rows:
        d_m = re.search(r"(\d{4}-\d{2}-\d{2})", row)
        g_m = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
        if d_m and g_m:
            raw_candidates.append((g_m.group(1).strip(), g_m.group(2).strip(), d_m.group(1)))

weekly_M, weekly_F, monthly_M, monthly_F = [], [], [], []

for gserial, ccid, d_str in raw_candidates:
    dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
    try:
        params = {"gserial": gserial, "game_id": "0", "iindex": "0", "ccid": ccid}
        r_json = session.get("https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json", params=params, verify=False).json()
        
        members = r_json.get("GamePlayerMember", {})
        score_list = r_json.get("GameInfoListScoreList", [])
        if not score_list: continue

        for i in range(1, 5):
            name = members.get(f"player{i}", "").strip()
            if not name or "guest" in name.lower(): continue
            
            # 실제 타수가 적힌 유효 홀 필터링
            played_holes = []
            for s in score_list:
                has_shot = False
                for k in [f"shot{i}", f"shot{i:02d}"]:
                    if k in s and s[k] is not None and int(s[k]) > 0:
                        has_shot = True
                        break
                if has_shot:
                    played_holes.append(s)

            if len(played_holes) != 9: continue

            # ── 멀리건 체크 (코랩 소스 코드의 검증 구조 그대로 이식) ──────────────────
            is_mulligan = check_mulligan_value(members.get(f"mulligan{i}", "0"))
            if not is_mulligan:
                for hole in played_holes:
                    if check_mulligan_value(hole.get(f"mul_cnt{i}", "0")) or \
                       check_mulligan_value(hole.get(f"mulligan{i}", "0")):
                        is_mulligan = True
                        break
            if is_mulligan:
                print(f"⏩ 제외: {name} ({d_str}) - 개인 멀리건 사용 확인")
                continue

            # 타수 계산
            total_shots = 0
            for s in played_holes:
                for k in [f"shot{i}", f"shot{i:02d}"]:
                    if k in s and s[k] is not None:
                        total_shots += int(s[k])
                        break

            if total_shots == 0: continue
            
            diff = int(total_shots - 36)
            clean_name = re.sub(r'\(.*?\)', '', name).strip()
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            record = {"name": clean_name, "score": diff, "course": members.get("cc", "알수없음"), "date": d_str}
            
            if dt >= start_of_month:
                monthly_M.append(record) if gender == "M" else monthly_F.append(record)
            if start_of_week <= dt <= end_of_week:
                weekly_M.append(record) if gender == "M" else weekly_F.append(record)
                
            print(f"✅ 수집 성공: {clean_name} ({diff:+d}타, {members.get('cc')})")
    except:
        continue

# 데이터 저장
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
print("🚀 동적 페이지 확장 및 멀리건 이식 완료")
