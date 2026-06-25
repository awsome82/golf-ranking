import requests, re, os, json, urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

# 여성 플레이어 명단
FEMALE_PLAYERS = {"신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애", "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙", "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜", "매실", "정진희"}

def check_mulligan_value(val) -> bool:
    if val is None:
        return False
    numbers = re.findall(r'\d+', str(val).strip())
    return sum(int(n) for n in numbers) > 0 if numbers else False

def get_total_pages(html: str) -> int:
    nums = re.findall(r'onclick="moveList\((\d+)\);', html)
    return max(map(int, nums)) if nums else 1

def get_rank_data(records, top_n=5):
    if not records: return []
    best_per_player = {}
    for r in records:
        p = r['name']
        score_val = int(r['score'])
        
        # 💡 [동점자 처리 핵심]: 한 플레이어의 베스트 스코어를 결정할 때도 이글 > 버디 > 파 순으로 판별
        if p not in best_per_player:
            best_per_player[p] = r
        else:
            current_best = best_per_player[p]
            new_key = (r['score'], -r['albatross_cnt'], -r['eagle_cnt'], -r['birdie_cnt'], -r['par_cnt'], r['date'])
            old_key = (current_best['score'], -current_best['albatross_cnt'], -current_best['eagle_cnt'], -current_best['birdie_cnt'], -current_best['par_cnt'], current_best['date'])
            if new_key < old_key:
                best_per_player[p] = r
            
    # 💡 [랭킹 정렬 규칙]: 총타수(낮은 순) -> 알바트로스 -> 이글 -> 버디 -> 파 개수(많은 순) -> 날짜 순
    sorted_list = sorted(
        best_per_player.values(), 
        key=lambda x: (x['score'], -x['albatross_cnt'], -x['eagle_cnt'], -x['birdie_cnt'], -x['par_cnt'], x['date'])
    )
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

first_resp = session.get("https://smanager.sggolf.com/gameInfo/gameDayState", params={"time_start1": START_DATE}, verify=False)
total_pages = get_total_pages(first_resp.text)
print(f"📊 동적 페이지 연산 완료: 총 {total_pages}개 페이지 전수 조사 시작")

raw_candidates = []
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
        hole_info_list = r_json.get("GameInfoListCCHoleInfo", [{}])
        hole_info = hole_info_list[0] if hole_info_list else {}
        if not score_list: continue

        for i in range(1, 5):
            raw_player_name = members.get(f"player{i}") or members.get(f"player{i:02d}")
            if not raw_player_name: continue
            
            player_name = str(raw_player_name).strip()
            clean_name = re.sub(r'\(.*?\)', '', player_name).strip()

            # 유효 홀 추출 및 1-based 홀 번호 매칭 (전/후반 9홀대응)
            played_holes = []
            for idx, s in enumerate(score_list):
                shot_val = None
                for k in [f"shot{i}", f"shot{i:02d}"]:
                    if k in s and s[k] not in (None, "-", "", "&nbsp;"):
                        shot_val = s[k]
                        break
                if shot_val is not None:
                    try:
                        if int(str(shot_val).strip()) > 0:
                            played_holes.append((s, int(str(shot_val).strip()), idx + 1))
                    except (ValueError, TypeError):
                        continue

            if len(played_holes) < 9: continue
            valid_holes = played_holes[:9]

            # 멀리건 체크
            is_mulligan = check_mulligan_value(members.get(f"mulligan{i}", "0")) or \
                          check_mulligan_value(members.get(f"mulligan{i:02d}", "0"))
            if not is_mulligan:
                for hole, _, _ in valid_holes:
                    if check_mulligan_value(hole.get(f"mul_cnt{i}", "0")) or \
                       check_mulligan_value(hole.get(f"mul_cnt{i:02d}", "0")) or \
                       check_mulligan_value(hole.get(f"mulligan{i}", "0")) or \
                       check_mulligan_value(hole.get(f"mulligan{i:02d}", "0")):
                        is_mulligan = True
                        break
            if is_mulligan:
                print(f"⏩ 제외: {clean_name} ({d_str}) - 개인 멀리건 사용 확인")
                continue

            # ── 💡 타수 및 스코어 종류별 카운팅 세부 연산 ──────────────────
            total_shots = 0
            albatross_cnt = 0
            eagle_cnt = 0
            birdie_cnt = 0
            par_cnt = 0

            for hole, shot, hole_num in valid_holes:
                total_shots += shot
                
                # 코스 고유의 파(Par) 규정 값 추출 (기본값 4)
                par_val = 4
                par_key = f"par{str(hole_num).zfill(2)}"
                if par_key in hole_info and hole_info[par_key] is not None:
                    try:
                        par_val = int(str(hole_info[par_key]).strip())
                    except:
                        par_val = 4
                
                # 기준파 대비 스코어 계산
                h_diff = shot - par_val
                if h_diff <= -3:
                    albatross_cnt += 1
                elif h_diff == -2:
                    eagle_cnt += 1
                elif h_diff == -1:
                    birdie_cnt += 1
                elif h_diff == 0:
                    par_cnt += 1

            if total_shots == 0: continue
            
            diff = int(total_shots - 36)
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            
            # 정렬 데이터를 레코드에 동시 바인딩
            record = {
                "name": clean_name, 
                "score": diff, 
                "course": members.get("cc", "알수없음"), 
                "date": d_str,
                "albatross_cnt": albatross_cnt,
                "eagle_cnt": eagle_cnt,
                "birdie_cnt": birdie_cnt,
                "par_cnt": par_cnt
            }
            
            if dt >= start_of_month:
                monthly_M.append(record) if gender == "M" else monthly_F.append(record)
            if start_of_week <= dt <= end_of_week:
                weekly_M.append(record) if gender == "M" else weekly_F.append(record)
                
            print(f"✅ 수집 성공: {clean_name} ({diff:+d}타, {members.get('cc')} | 이글:{eagle_cnt}, 버디:{birdie_cnt}, 파:{par_cnt})")
    except Exception as e:
        print(f"❌ [라운드 해석 에러] 일련번호: {gserial} | 원인: {e}")
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
print("🚀 동점자 백카운트 정렬 스크립트 고도화 완료")
